#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Executor fixture: runs trace-lifecycle-v10.sh against a fake device (fake sysfs, procfs, kmsg, iw, connmanctl, ip,
ping, uname, id) through the script's path and command overrides, for the complete cycle and the failure paths:
refusals before any radio action, a failed positive control, an off-target reconnect, a missing seal, a budget
overrun, a failed restoration. Every scenario checks the admitted operation counts and the receipts."""
import json
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / 'trace-lifecycle-v10.sh'
BOOT = '12345678-1234-1234-1234-123456789abc'
RELEASE = '3.18.41-gemini-wifi-ref10+'
SERVICE = 'wifi_0211223344aa_4e657420576f726b_managed_psk'
TARGET = {'ssid': 'Net Work', 'bssid': '02:11:22:33:44:55', 'frequency_mhz': 5200, 'channel': 40}

FAKE_LIB = r'''
import fcntl, json, os, sys, time
ROOT = os.environ['FAKE_ROOT']
def state(key, default=None):
    with open(os.path.join(ROOT, 'state.json')) as f:
        return json.load(f).get(key, default)
def set_state(key, value):
    path = os.path.join(ROOT, 'state.json')
    with open(path, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        data = json.load(f); data[key] = value
        f.seek(0); f.truncate(); json.dump(data, f)
def scenario(key, default=None):
    with open(os.path.join(ROOT, 'scenario.json')) as f:
        return json.load(f).get(key, default)
def kmsg(message, prio=7):
    path = os.path.join(ROOT, 'kmsg.log'); seqf = os.path.join(ROOT, 'seq')
    with open(seqf, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        seq = int(f.read() or '0'); f.seek(0); f.truncate(); f.write(str(seq + 1))
    with open(path, 'a') as f:
        f.write('%d,%d,%d,-;%s\n' % (prio, seq, seq * 1000, message))
def control():
    with open(os.path.join(ROOT, 'sys/module/wlan_gen3/parameters/gwref10')) as f:
        return f.read().strip()
def log(line):
    with open(os.path.join(ROOT, 'ops.log'), 'a') as f:
        f.write(line + '\n')
'''

FAKES = {
    'id': 'print(0)',
    'uname': "import sys; print({'-r': %r, '-m': 'aarch64'}[sys.argv[1]])" % RELEASE,
    'iw': '''
import sys
if sys.argv[1:4] == ['dev', 'wlan0', 'link']:
    log('iw link')
    if control() == '1':
        n = state('n', 0) + 1; set_state('n', n)
        pc = scenario('positive_control', 'ok')
        if pc != 'none':
            kmsg('gwref10 cmd: n=%d cid=0x81 seq=%d set=0 len=16 bss=0 type=1' % (n, 40 + n))
            n += 1; set_state('n', n)
            kmsg('gwref10 event: n=%d eid=0x02 seq=%d len=20 hif=24' % (n, 40 + n - 1 if pc == 'ok' else 99))
    if state('connected'):
        t = state('target')
        print('Connected to %s (on wlan0)\\n\\tSSID: %s\\n\\tfreq: %d\\n\\tsignal: -50 dBm' % (t['bssid'], t['ssid'], t['frequency_mhz']))
    else:
        print('Not connected.')
''',
    'connmanctl': '''
import sys, time
args = sys.argv[1:]
log('connmanctl ' + ' '.join(args))
S = %r
if args == ['services']:
    flag = '*AO' if state('connected') else '*A '
    print('%%s Net Work             %%s' %% (flag, S))
elif args[:1] == ['services'] and len(args) == 2:
    print('/net/connman/service/' + args[1])
    print('  Type = wifi'); print('  State = %%s' %% ('online' if state('connected') else 'idle'))
    print('  AutoConnect = %%s' %% ('True' if state('autoconnect') else 'False'))
    print('  Favorite = True'); print('  Passphrase = SHOULD-NOT-BE-COPIED'); print('  Name = Net Work')
elif args[:1] == ['connect']:
    set_state('connect_calls', state('connect_calls', 0) + 1)
    if scenario('connect_result', 'ok') == 'fail' or (scenario('restore_result') == 'fail' and state('connect_calls') >= 2):
        set_state('connected', False)
    else:
        set_state('connected', True)
        set_state('target', scenario('reconnect_target', None) or state('target'))
        if scenario('lose_identity_after_connect') and state('connect_calls') == 1:
            with open(os.path.join(ROOT, 'proc/sys/kernel/random/boot_id'), 'w') as f:
                f.write('ffffffff-ffff-ffff-ffff-ffffffffffff' + chr(10))
        for i in range(3):
            n = state('n', 0) + 1; set_state('n', n)
            kmsg('gwref10 txd: n=%%d cls=data pid=%%d wlan=1 bss=0 sta=0 len=98 fmt=0 tid=0 prot=1 is80211=0 tc=1' %% (n, i))
elif args[:1] == ['disconnect']:
    time.sleep(scenario('disconnect_delay', 0))
    set_state('connected', False)
elif args[:1] == ['config']:
    set_state('autoconnect_writes', state('autoconnect_writes', []) + [args[-1]])
    if args[-1] == 'yes' and scenario('autoconnect_config_fail'):
        sys.exit(1)
    set_state('autoconnect', args[-1] == 'yes')
''' % SERVICE,
    'ip': '''
import sys
a = ' '.join(sys.argv[1:])
if a == '-4 route show default dev wlan0':
    print('default via 192.168.4.1 proto dhcp metric 600')
elif a == '-4 addr show dev wlan0':
    print('3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP>')
    if state('connected'): print('    inet 192.168.4.20/24 brd 192.168.4.255 scope global wlan0')
elif a == 'route':
    print('default via 192.168.4.1 dev wlan0')
elif a == '-4 route show dev wlan0':
    if state('connected'):
        print('192.168.4.0/24 proto kernel scope link src 192.168.4.20'); print('192.168.4.1 scope link')
elif a == '-4 route get 192.168.4.1':
    print('192.168.4.1 via ??? ??? dev wlan0 src 192.168.4.20'); print('    cache')
''',
    'ping': "log('ping ' + ' '.join(sys.argv[1:])); print('5 packets transmitted, 5 received')",
    'dmesg': "print('[    0.000000] fake dmesg')",
}

KERNEL = '''
import os, sys, time
# The fake kernel: arms and seals the observer when the control file changes.
last = None
end = time.time() + 120
while time.time() < end:
    c = control()
    if c != last:
        if c == '1':
            kmsg('gwref10 arm: deadline_s=240 caps=512/1024/1024/2048/1024/256', 6)
        if c == '2' and scenario('emit_seal', True):
            counts = {k: 0 for k in ('cmd', 'event', 'credit', 'rxd', 'txd', 'state')}
            with open(os.path.join(ROOT, 'kmsg.log')) as f:
                for line in f:
                    m = line.split(';', 1)[1] if ';' in line else ''
                    for k in counts:
                        if m.startswith('gwref10 %s: n=' % k):
                            counts[k] += 1
            kmsg('gwref10 seal: reason=explicit records=%d truncated=0 cmd=%d/0/0 event=%d/0/0 credit=%d/0/0 rxd=%d/0/0 txd=%d/0/0 state=%d/0/0'
                 % (sum(counts.values()), counts['cmd'], counts['event'], counts['credit'], counts['rxd'], counts['txd'], counts['state']), 6)
        last = c
    time.sleep(0.02)
'''


class Device:
    def __init__(self, scenario):
        self.tmp = tempfile.TemporaryDirectory(prefix='gwref10-exec-')
        self.root = pathlib.Path(self.tmp.name)
        for rel in ('sys/module/wlan_gen3/parameters', 'proc/sys/kernel/random', 'proc/sys/kernel', 'sys/class/net/wlan0',
                    'sys/class/power_supply/battery', 'bin', 'bound', 'out'):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        (self.root / 'sys/module/wlan_gen3/parameters/gwref10').write_text('0')
        (self.root / 'proc/sys/kernel/random/boot_id').write_text(BOOT + '\n')
        (self.root / 'proc/sys/kernel/printk').write_text('7\t4\t1\t7\n')
        (self.root / 'sys/class/net/wlan0/carrier').write_text('1\n')
        (self.root / 'sys/class/power_supply/battery/present').write_text('1\n')
        (self.root / 'sys/class/power_supply/battery/health').write_text('Good\n')
        (self.root / 'bound/approved-service').write_text(SERVICE + '\n')
        (self.root / 'bound/ap-target.json').write_text(json.dumps(TARGET) + '\n')
        for name in ('approved-service', 'ap-target.json'):
            os.chmod(self.root / 'bound' / name, 0o600)
        (self.root / 'kmsg.log').write_text('')
        (self.root / 'seq').write_text('100')
        (self.root / 'ops.log').write_text('')
        (self.root / 'state.json').write_text(json.dumps({'connected': True, 'autoconnect': scenario.get('autoconnect', True),
                                                           'target': TARGET, 'n': 0}))
        (self.root / 'scenario.json').write_text(json.dumps(scenario))
        (self.root / 'fakelib.py').write_text(FAKE_LIB)
        for name, body in FAKES.items():
            path = self.root / 'bin' / name
            path.write_text('#!/usr/bin/env python3\nimport sys\nsys.path.insert(0, %r)\nfrom fakelib import *\n' % str(self.root) + textwrap.dedent(body))
            path.chmod(0o755)
        (self.root / 'kernel.py').write_text('import sys\nsys.path.insert(0, %r)\nfrom fakelib import *\n' % str(self.root) + KERNEL)
        self.env = dict(os.environ, FAKE_ROOT=str(self.root), PATH=str(self.root / 'bin') + ':' + os.environ['PATH'],
                        GWREF10_SYSROOT=str(self.root), GWREF10_OUTPUT=str(self.root / 'out/cycle'),
                        GWREF10_KMSG_SOURCE=str(self.root / 'kmsg.log'), GWREF10_TICK='0.05',
                        GWREF10_IW=str(self.root / 'bin/iw'), GWREF10_BOUND_DIR=str(self.root / 'bound'),
                        GWREF10_BUDGET_DIVISOR='5')
        self.env['GWREF10_CHECK'] = str(ROOT / 'lifecycle/cycle-check.py')

    def run(self, boot=BOOT, timeout=120):
        kernel = subprocess.Popen(['python3', str(self.root / 'kernel.py')], env=self.env)
        try:
            result = subprocess.run(['bash', str(SCRIPT), boot], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        finally:
            kernel.kill()
            kernel.wait()
        self.rc = result.returncode
        self.stderr = result.stderr.decode()
        return self

    def receipt(self):
        path = self.root / 'out/cycle/receipt.txt'
        return path.read_text() if path.exists() else ''

    def ops(self):
        return (self.root / 'ops.log').read_text()

    def state(self):
        return json.loads((self.root / 'state.json').read_text())

    def out(self, name):
        return self.root / 'out/cycle' / name


class ExecutorTest(unittest.TestCase):
    def device(self, scenario):
        dev = Device(scenario)
        self.addCleanup(dev.tmp.cleanup)
        return dev

    def test_complete_cycle(self):
        dev = self.device({}).run()
        self.assertEqual(dev.rc, 0, dev.stderr + dev.receipt())
        receipt = dev.receipt()
        for line in ('positive_control=1', 'teardown1=1', 'connect=1 target_match=1', 'gateway_recheck=1', 'teardown2=1',
                     'seal_state=2', 'seal_captured=1', 'stream_intact=1', 'cycle=complete', 'manifest_complete=1 manifest_missing= none frozen=1',
                     'ops_connect=1 ops_disconnect=2 ops_ping=1 ops_observer_writes=2 ops_autoconnect_writes=1',
                     'logger_stopped=1 logger_rc=0 logger_report=bytes=', 'stopped_by=signal',
                     'autoconnect_after=True autoconnect_restored=1', 'restore_connected=1 ops_restore=1', 'result=complete exit=0',
                     'identity_post_seal=1', 'logger_report=bytes=', 'capped=0'):
            self.assertIn(line, receipt, line)
        ops = dev.ops()
        self.assertEqual(ops.count('connmanctl connect'), 2)   # one measured, one restoration
        self.assertEqual(ops.count('connmanctl disconnect'), 2)
        self.assertEqual(dev.state()['autoconnect_writes'], ['no', 'yes'])
        self.assertTrue(dev.state()['autoconnect'])
        # frozen outputs are read-only and hashed; the checksum files never list themselves
        sums = dev.out('MANIFEST').read_text()
        self.assertIn('kmsg-cycle.log', sums)
        self.assertNotIn('MANIFEST', sums)
        self.assertNotIn('run.log', sums)
        self.assertNotIn('receipt.txt', sums)
        self.assertEqual(stat.S_IMODE(dev.out('MANIFEST').stat().st_mode), 0o400)
        final = dev.out('SHA256SUMS.final').read_text()
        self.assertIn('run.log', final)
        self.assertIn('restore.log', final)
        self.assertEqual(stat.S_IMODE(dev.out('kmsg-cycle.log').stat().st_mode), 0o400)
        self.assertNotIn('Passphrase', dev.out('service-before.txt').read_text())
        self.assertIn('AutoConnect = True', dev.out('service-before.txt').read_text())
        window = dev.out('traffic-window').read_text().split()
        self.assertEqual(len(window), 3)
        self.assertEqual(window[2], BOOT)
        self.assertEqual(int(window[1]) - int(window[0]), 4)   # 20 s divided by the fixture's budget divisor
        kmsg = dev.out('kmsg-cycle.log').read_text()
        self.assertEqual(kmsg.count('gwref10 arm:'), 1)
        self.assertEqual(kmsg.count('gwref10 seal:'), 1)

    def test_refusals_before_any_change(self):
        dev = self.device({}).run(boot='00000000-0000-0000-0000-000000000000')
        self.assertEqual(dev.rc, 2)
        self.assertEqual(dev.ops(), '')
        self.assertFalse(dev.out('receipt.txt').exists())
        dev = self.device({})
        os.chmod(dev.root / 'bound/ap-target.json', 0o644)
        dev.run()
        self.assertEqual(dev.rc, 2)
        self.assertIn('bound files invalid', dev.stderr)
        self.assertNotIn('connmanctl', dev.ops())
        dev = self.device({})
        (dev.root / 'out/cycle').mkdir()
        dev.run()
        self.assertEqual(dev.rc, 2)
        self.assertIn('output directory exists', dev.stderr)
        dev = self.device({})
        (dev.root / 'proc/sys/kernel/printk').write_text('8\t4\t1\t7\n')
        dev.run()
        self.assertEqual(dev.rc, 2)
        dev = self.device({})
        (dev.root / 'bound/ap-target.json').write_text(json.dumps(dict(TARGET, bssid='02:11:22:33:44:99')) + '\n')
        dev.run()
        self.assertEqual(dev.rc, 2)
        self.assertIn('not the bound target', dev.stderr)
        self.assertNotIn('connmanctl connect', dev.ops())
        self.assertNotIn('connmanctl disconnect', dev.ops())

    def test_positive_control_failure_takes_no_radio_action(self):
        for pc in ('none', 'mismatch'):
            dev = self.device({'positive_control': pc}).run()
            self.assertEqual(dev.rc, 2, pc)  # refused before any radio action; sealed, frozen, restoration verified
            receipt = dev.receipt()
            self.assertIn('positive_control=0', receipt)
            self.assertNotIn('connmanctl disconnect', dev.ops())
            self.assertEqual(dev.ops().count('connmanctl connect'), 1)  # the restoration call only
            self.assertIn('seal_captured=1', receipt)
            self.assertIn('restore_connected=1', receipt)
            self.assertIn('result=partial exit=2', receipt)

    def test_off_target_reconnect_is_a_partial_result(self):
        dev = self.device({'reconnect_target': dict(TARGET, bssid='02:11:22:33:44:66')}).run()
        self.assertEqual(dev.rc, 5)
        receipt = dev.receipt()
        self.assertIn('connect=1 target_match=0', receipt)
        self.assertIn('exit_step=connect rc_before_finish=5', receipt)
        self.assertIn('seal_captured=1', receipt)
        self.assertIn('restore_connected=0', receipt)   # the restoration lands off target too and is not counted as restored
        self.assertIn('autoconnect_left_off=1', receipt)
        self.assertEqual(dev.state()['autoconnect_writes'], ['no'])
        self.assertNotIn('ping', dev.ops())
        self.assertNotIn('autoconnect_restored=1', receipt)

    def test_missing_seal_is_not_complete(self):
        dev = self.device({'emit_seal': False}).run()
        receipt = dev.receipt()
        self.assertIn('seal_captured=0', receipt)
        self.assertNotIn('cycle=complete', receipt)
        self.assertIn('reason=missing', receipt)
        self.assertNotEqual(dev.rc, 0)
        self.assertIn('result=partial', receipt)

    def test_budget_overrun_and_failed_restoration(self):
        dev = self.device({'connect_result': 'fail'}).run()
        self.assertEqual(dev.rc, 5)
        receipt = dev.receipt()
        self.assertIn('connect=0', receipt)
        self.assertIn('autoconnect_left_off=1', receipt)
        self.assertIn('restore_connected=0', receipt)
        self.assertEqual(dev.state()['autoconnect_writes'], ['no'])
        dev = self.device({'restore_result': 'fail'}).run()
        self.assertEqual(dev.rc, 3)
        self.assertIn('cycle=complete', dev.receipt())
        self.assertIn('result=partial exit=3', dev.receipt())
        self.assertFalse(dev.state()['autoconnect'])
        # the original True AutoConnect must come back; a config failure forces a partial result
        dev = self.device({'autoconnect_config_fail': True}).run()
        self.assertEqual(dev.rc, 3)
        self.assertIn('autoconnect_restored=0', dev.receipt())
        self.assertIn('result=partial exit=3', dev.receipt())

    def test_original_autoconnect_false_is_left_false(self):
        dev = self.device({'autoconnect': False}).run()
        self.assertEqual(dev.rc, 0)
        self.assertEqual(dev.state()['autoconnect_writes'], ['no'])
        self.assertIn('autoconnect_after=False autoconnect_restored=1', dev.receipt())

    def test_identity_loss_stops_actions(self):
        dev = self.device({'lose_identity_after_connect': True}).run()
        self.assertEqual(dev.rc, 7)
        receipt = dev.receipt()
        self.assertIn('identity_lost_at=', receipt)
        self.assertIn('restore_skipped=identity', receipt)
        self.assertEqual(dev.ops().count('connmanctl connect'), 1)   # no restoration connect after the loss
        self.assertNotIn('cycle=complete', receipt)


if __name__ == '__main__':
    unittest.main()
