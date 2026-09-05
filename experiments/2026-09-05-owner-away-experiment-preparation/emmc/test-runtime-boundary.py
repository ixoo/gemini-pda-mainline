#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""New-session parser and unconditional launcher/completion gate fixtures."""
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
L = runpy.run_path(str(HERE / 'collect-emmc.py'))
M = runpy.run_path(str(HERE / 'finish-emmc.py'))
R = runpy.run_path(str(HERE / 'recovery_v2.py'))
BOOT = '11111111-1111-4111-8111-111111111111'


class RuntimeBoundaryTests(unittest.TestCase):
    def test_both_runtime_entries_refuse_before_context_or_transport(self):
        def disabled():
            raise ValueError('execution disabled')
        with patch('subprocess.Popen', side_effect=AssertionError('no process')), \
             patch.dict(L['collect'].__globals__, {'execution_gate': disabled}), \
             patch.dict(M['L'], {'execution_gate': disabled}):
            for entry in (L['collect'], M['perform']):
                with self.assertRaisesRegex(ValueError, 'execution disabled'):
                    entry(None, True)

    def test_new_wrapper_output_exact_and_transport_stays_strict(self):
        frame = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={BOOT}\nreboot_sha256={R["REBOOT_SHA"]}\n'
                 'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode()
        raw = frame + R['ANNOUNCEMENT']
        proc = {'stdin_complete': True, 'reason': None, 'exit_status': 255}
        self.assertEqual(R['parse_recovery_request'](raw, proc, BOOT)['classification'], 'native-recovery-requested')
        for invalid in (frame, raw[:-1], raw + b'extra\n', raw + R['ANNOUNCEMENT'],
                        raw.replace(b'Candidate AB', b'Candidate XX'), raw.replace(b'request_count=1', b'request_count=2')):
            with self.assertRaises(ValueError): R['parse_recovery_request'](invalid, proc, BOOT)
        for change in ({'reason': 'outer-timeout'}, {'reason': 'interrupted'},
                       {'stdin_complete': False}, {'exit_status': 0}, {'exit_status': 94}):
            with self.assertRaises(ValueError): R['parse_recovery_request'](raw, {**proc, **change}, BOOT)
        original = runpy.run_path(str(HERE.parent / 'baseline/scripts/session_steps.py'))
        with self.assertRaises(ValueError): original['parse_recovery_request'](raw, proc, BOOT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
