#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Metadata framing, capability and pre-effect refusal checks; no device access."""
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
N = runpy.run_path(str(HERE/'metadata.py'))


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.admission = {'id':'11111111-1111-1111-1111-111111111111',
            'boot_id':'22222222-2222-2222-2222-222222222222'}
        names = ('init', 'bin/busybox', 'bin/reboot', 'bin/kmsg-capture', 'bin/kmsg-seal',
            'bin/emmc-observe', 'bin/console-keymap-verify', 'etc/gemini-us.bkeymap', 'bin/keyboard-observe')
        self.candidate = {'files':{'boot.img':'a'*64},
            'members':{n:{'sha256':'a'*64} for n in names}}
        self.candidate['members']['bin/reboot']['sha256'] = N['S']['REBOOT_SHA']
        key_bits = sum(1 << key for key in N['M']['K']['SCANS'])
        key_words = f'{key_bits:032x}'
        self.values = {'event':'event0', 'minor':'64',
            'input_path':'/sys/devices/platform/keyboard-matrix/input/input0',
            'provider':'0-005b', 'logger_age_seconds':'120', 'boot_id':self.admission['boot_id'],
            **{'cap_'+name:'0' for name in N['CAPABILITIES']}}
        self.values.update(cap_ev='13', cap_msc='10', cap_key=key_words[:16]+' '+key_words[16:])

    def raw(self, values):
        return ''.join(k+'='+v+'\n' for k,v in values.items()).encode()+b'__KEYBOARD_METADATA_PASS__\n'

    def parse(self, raw, **changes):
        process = {'exit_status':0, 'reason':None, 'stdin_complete':True,
            'elapsed_seconds':1, 'stdout_bytes':len(raw), 'stderr_bytes':0, **changes}
        return N['parse'](raw,b'',process,self.admission,self.candidate)

    def test_complete_metadata_binds_existing_prerequisite(self):
        runtime, receipt = self.parse(self.raw(self.values))
        self.assertEqual(runtime['event'], 'event0')
        self.assertEqual(len(runtime['resource_paths']), 4)
        raw = N['encode'](receipt)
        N['P']['runtime'](raw, N['sha'](raw), {**self.admission,'runtime':runtime}, self.candidate)

    def test_wrong_identity_capabilities_and_age_refuse(self):
        for field,value in (('event','event256'), ('minor','064'), ('minor','1048576'),
                ('input_path','/sys/devices/platform/other/input/input0'),
                ('provider','0-005c'), ('logger_age_seconds','240'),
                ('boot_id','33333333-3333-3333-3333-333333333333'),
                ('cap_ev','1'), ('cap_msc','0'), ('cap_key','0'),
                ('cap_key','123456789abcdef01'), ('cap_sw','bad;command')):
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                self.parse(self.raw({**self.values,field:value}))

    def test_partial_duplicate_and_transport_failure_refuse(self):
        raw = self.raw(self.values)
        for changed in (raw[:-1],raw+b'extra\n',b'event=event0\n'+raw,
                self.raw({**self.values,'extra':'1'})):
            with self.assertRaises(ValueError):self.parse(changed)
        for process in ({'exit_status':1}, {'reason':'outer-timeout'},
                {'stdin_complete':False}, {'stdout_bytes':0}, {'elapsed_seconds':32}):
            with self.assertRaises(ValueError):self.parse(raw,**process)

    def test_generated_shell_is_valid_and_source_is_bound(self):
        command = N['script'](self.candidate,self.admission['boot_id'])
        with tempfile.TemporaryDirectory() as work:
            path = Path(work)/'metadata.sh';path.write_bytes(command)
            subprocess.run(['sh','-n',str(path)],check=True,capture_output=True)
            subprocess.run(['shellcheck','-s','sh','-e','SC2016',str(path)],check=True,capture_output=True)
        self.assertEqual(N['M']['source_identity']()['local_and_direct']['metadata.py'],
            N['sha']((HERE/'metadata.py').read_bytes()))

    def test_missing_disconnect_proof_refuses_before_claim_or_transport(self):
        with tempfile.TemporaryDirectory() as work:
            with patch.dict(N['D'], {'prepare':lambda *a:{'candidate':self.candidate}, 'ROOT':Path(work).resolve()}), \
                    patch.object(Path,'mkdir',side_effect=AssertionError('claim')), \
                    patch('subprocess.Popen',side_effect=AssertionError('transport')):
                with self.assertRaises(FileNotFoundError):
                    N['perform'](self.admission,Path(work),True)


if __name__ == '__main__':
    unittest.main()
