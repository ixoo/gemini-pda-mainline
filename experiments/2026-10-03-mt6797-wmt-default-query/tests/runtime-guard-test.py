#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the actual generated guard/trigger against isolated fake files."""
import os
import json
from pathlib import Path
import re
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('GEMINI_PRIVATE_REPO', str(Path(__file__).resolve().parents[3]))
HERE = Path(__file__).resolve().parents[1]
CAPTURE = runpy.run_path(str(HERE / 'capture-private.py'))
BOOT = '11111111-2222-3333-4444-555555555555'
FAKE_BB = r'''#!/usr/bin/env python3
import os,pathlib,shutil,sys
root=pathlib.Path(__file__).parent
cmd,*args=sys.argv[1:]
if cmd=='mount':
 with (root/'events').open('a') as f:f.write('mount '+ ' '.join(args)+'\n')
 mounts=root/'proc/mounts'
 text=mounts.read_text()
 if 'remount,rw' in args:
  mounts.write_text(text.replace('sysfs ro,','sysfs rw,'))
  if (root/'fail-rw').exists():sys.exit(1)
 elif 'remount,ro' in args:
  flag=root/'fail-ro-once'
  if flag.exists():flag.unlink();sys.exit(1)
  mounts.write_text(text.replace('sysfs rw,','sysfs ro,'))
 else:
  mounts.write_text(text+'debugfs '+str(root/'sys/kernel/debug')+' debugfs ro,relatime 0 0\n')
  c=root/'sys/kernel/debug/clk/infra_ap_dma';c.mkdir(parents=True,exist_ok=True)
  for n in ['clk_enable_count','clk_prepare_count']:(c/n).write_text('1\n')
elif cmd=='uname':print('7.1.3-gemini-a53-wmt-query')
elif cmd=='readlink':print(os.path.realpath(args[-1]))
elif cmd=='printf':
 with (root/'events').open('a') as f:f.write('trigger\n')
 os.execv('/usr/bin/printf',['printf']+args)
else:os.execv(shutil.which(cmd),[cmd]+args)
'''


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='wmt-query-guard-')
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.put('proc/sys/kernel/random/boot_id', BOOT+'\n')
        self.put('proc/cmdline', 'console=ttyS0,921600n8 earlycon\n')
        self.put('proc/consoles', 'ttyS0 -W- (EC p ) 4:64\n')
        self.put('proc/mounts', f'sysfs {self.root}/sys sysfs ro,relatime 0 0\n'
                 f'debugfs {self.root}/sys/kernel/debug debugfs ro,relatime 0 0\n')
        self.put('sys/bus/platform/devices/11002000.serial/power/runtime_status', 'active\n')
        driver = self.root/'sys/bus/platform/drivers/mt6577-uart'
        driver.mkdir(parents=True)
        (self.root/'sys/bus/platform/devices/11002000.serial/driver').symlink_to(driver)
        for name in ['clk_prepare_count', 'clk_enable_count']:
            self.put('sys/kernel/debug/clk/infra_ap_dma/'+name, '1\n')
        self.target = CAPTURE['START_TRIGGER'].lstrip('/')
        self.put(self.target, 'unused')
        self.put('events', '')
        self.put('bb', FAKE_BB)
        (self.root/'bb').chmod(0o700)

    def put(self, path, text):
        p=self.root/path
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(text)

    def run_script(self, script):
        script=re.sub(r'(?<![\w/])/(proc|sys)\b', lambda m: str(self.root)+'/'+m[1], script)
        script=script.replace('/bin/busybox',str(self.root/'bb'))
        result=subprocess.run(['/bin/sh'],input=script,text=True,capture_output=True,timeout=5)
        return result, (self.root/'events').read_text()

    def trigger(self):
        return self.run_script(CAPTURE['trigger_script'](BOOT,CAPTURE['START_TRIGGER']).decode())

    def test_success(self):
        r,events=self.trigger()
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(r.stdout,'sysfs_rw_verified\nsysfs_ro_restored\n')
        self.assertEqual(events.count('trigger\n'),1)
        self.assertEqual((self.root/self.target).read_text(),'1\n')
        self.assertIn('sysfs ro,',(self.root/'proc/mounts').read_text())

    def test_prerequisite_refusals(self):
        cases={'proc/cmdline':'console=tty0\n','proc/consoles':'ttyS0 -W- (C p ) 4:64\n',
               'sys/bus/platform/devices/11002000.serial/power/runtime_status':'suspended\n',
               'sys/kernel/debug/clk/infra_ap_dma/clk_prepare_count':'0\n',
               'sys/kernel/debug/clk/infra_ap_dma/clk_enable_count':'junk\n',
               'proc/sys/kernel/random/boot_id':'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n'}
        expected_codes = [20, 21, 23, 29, 29, 10]
        for (path,bad), expected_code in zip(cases.items(), expected_codes):
            with self.subTest(path=path):
                old=(self.root/path).read_text();self.put(path,bad)
                r,events=self.trigger()
                self.assertEqual(r.returncode,expected_code,r.stderr)
                self.assertEqual(events,'')
                self.assertEqual((self.root/self.target).read_text(),'unused')
                self.put(path,old)

    def test_partial_rw_failure_restores(self):
        self.put('fail-rw','')
        r,events=self.trigger()
        self.assertEqual(r.returncode,14,r.stderr)
        self.assertNotIn('trigger\n',events)
        self.assertIn('sysfs ro,',(self.root/'proc/mounts').read_text())

    def test_zero_enable_count(self):
        self.put('sys/kernel/debug/clk/infra_ap_dma/clk_enable_count', '0\n')
        r,events=self.trigger()
        self.assertEqual(r.returncode,29,r.stderr)
        self.assertEqual(events,'')
        self.assertEqual((self.root/self.target).read_text(),'unused')

    def test_late_trap_negative_control(self):
        self.put('fail-rw','')
        script=CAPTURE['trigger_script'](BOOT,CAPTURE['START_TRIGGER']).decode()
        script=script.replace('trap restore EXIT\n','')
        marker='$BB mount -o remount,rw /sys || exit 14\n'
        script=script.replace(marker,marker+'trap restore EXIT\n')
        r,events=self.run_script(script)
        self.assertEqual(r.returncode,14)
        self.assertNotIn('trigger\n',events)
        self.assertIn('sysfs rw,',(self.root/'proc/mounts').read_text())

    def test_restore_failure_keeps_exit_trap(self):
        self.put('fail-ro-once','')
        r,events=self.trigger()
        self.assertEqual(r.returncode,19,r.stderr)
        self.assertEqual(events.count('trigger\n'),1)
        self.assertEqual(events.count('remount,ro'),2)
        self.assertIn('sysfs ro,',(self.root/'proc/mounts').read_text())

    def test_debug_mount_once_only_in_identify(self):
        for name in ['clk_prepare_count','clk_enable_count']:
            (self.root/'sys/kernel/debug/clk/infra_ap_dma'/name).unlink()
        self.put('proc/mounts',f'sysfs {self.root}/sys sysfs ro,relatime 0 0\n')
        r,events=self.trigger()
        self.assertEqual(r.returncode,24,r.stderr)
        self.assertEqual(events,'')
        r,events=self.run_script('BB=/bin/busybox\n'+CAPTURE['admission_script'](True))
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(events.count('mount -t debugfs'),1)

    def test_deployment_receipt(self):
        image = b'synthetic image'
        padded = b'synthetic padded image'
        sha = CAPTURE['sha']
        candidate = self.root / ('candidate-' + sha(image))
        candidate.mkdir()
        manifest = {'files': {name: {'bytes': len(data), 'sha256': sha(data)}
                    for name, data in [('boot.img', image), ('boot2-padded.img', padded)]}}
        published = (json.dumps(manifest) + '\n').encode()
        for name, data in [('boot.img', image), ('boot2-padded.img', padded),
                           ('candidate.json', published)]:
            (candidate / name).write_bytes(data)
        receipt = self.root / 'published.json'
        receipt.write_bytes(published)
        deployment = self.root / 'deployment.txt'
        fields = {
            'experiment': 'mt6797-wmt-default-query',
            'candidate_manifest_sha256': sha(published), 'target_logical_name': 'boot2',
            'result': 'write-synced-flushed-full-readback-verified',
            'target': '/dev/mmcblk0p28', 'root': '/dev/mmcblk0p29',
            'target_major_minor': '179:28', 'root_major_minor': '179:29',
            'boot2_device_guard': 'passed',
            'boot2_device_guard_sha256':
                '0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf',
            'predecessor_sha256': 'a' * 64, 'fresh_predecessor_backup': 'no',
            'candidate_sha256': sha(padded), 'readback_sha256': sha(padded),
            'boot_id': BOOT, 'power': '1|90|Good|1', 'temporary_readback_removed': 'yes',
            'shutdown': 'requested-after-evidence-flush', 'poweroff_ssh_rc': '0',
            'post_shutdown_reachability': 'unreachable', 'reboot': 'no',
            'next_action': 'owner-physically-selects-boot2',
        }

        def write(values):
            deployment.write_text(''.join(k + '=' + v + '\n' for k, v in values.items()))

        module = CAPTURE['CAPTURE']
        with patch.object(module, 'RECEIPT', receipt), \
                patch.object(module, 'MANIFEST_SHA', sha(published)), \
                patch.object(module, 'DEPLOYMENT', deployment):
            write(fields)
            self.assertEqual(CAPTURE['prepare'](candidate), manifest)
            fields.update(result='skipped-already-matching', predecessor_sha256=sha(padded))
            write(fields)
            self.assertEqual(CAPTURE['prepare'](candidate), manifest)
            for key, bad in [('predecessor_sha256', 'b' * 64),
                             ('readback_sha256', 'b' * 64), ('boot2_device_guard', 'failed'),
                             ('root_major_minor', '179:28'),
                             ('post_shutdown_reachability', 'reachable')]:
                with self.subTest(key=key):
                    write(fields | {key: bad})
                    with self.assertRaises(ValueError):
                        CAPTURE['prepare'](candidate)

    def test_result_refusals(self):
        classify=CAPTURE['query_result']
        good=b'one-shot WMT default query: result=0 rx=16 irqs=1 clocks-held=1\n'
        self.assertTrue(classify(good)['matched_response'])
        for bad in [b'',good+good,good.replace(b'rx=16',b'rx=8'),
                    good.replace(b'irqs=1',b'irqs=32'),good.replace(b'result=0',b'result=-110'),
                    good.replace(b'clocks-held=1',b'clocks-held=0')]:
            self.assertFalse(classify(bad)['matched_response'])


if __name__ == '__main__':
    unittest.main()
