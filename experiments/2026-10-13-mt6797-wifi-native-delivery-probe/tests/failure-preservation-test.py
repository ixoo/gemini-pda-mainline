#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The refused session stops, re-checks and seals, or exports then refuses (failure_preservation.py)."""
from pathlib import Path
import json
import os
import runpy
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent.parent
FP = runpy.run_path(str(HERE/'hosts/failure_preservation.py'), run_name='failure_preservation')
BOOT = '00000000-0000-0000-0000-000000000001'
STOPPED = ('__OWNED_STOP_BEGIN__\nboot_id=%s\nbefore=9:wpa_supplicant \nafter_term=\nafter=\n'
           '__OWNED_STOP_END__\nboot_after=%s\n' % (BOOT, BOOT)).encode()


class Collector:
    def write_new(self, path, data):
        assert not path.exists(), path
        path.write_bytes(data)


class FailurePreservationTests(unittest.TestCase):
    def session(self, recheck_processes, recheck_quiesced, refusal='owned supplicant not confirmed quiesced'):
        root = Path(tempfile.mkdtemp())
        (root/'observation-result.json').write_text(json.dumps({'boot_id': BOOT}))
        calls = []
        state = {'refused': False}

        def phase_b(active, label, script, *, network_status=None):
            calls.append(label)
            if label == 'log-export' and not state['refused']:
                state['refused'] = True
                raise RuntimeError(refusal + ' (supplicant_processes=1); refusing seal and recovery')
            return {'owned-stop': STOPPED}.get(label, label.encode()), b'', {'exit_status': 0}

        c2 = {'LOG_LIMIT': 1024,
              'log_script': lambda boot: b'log', 'quiescence_script': lambda boot: b'quiet',
              'cycles_export_script': lambda boot: b'cycles',
              'log_result': lambda raw, err, p, boot: {'supplicant_processes': recheck_processes},
              'quiescence_result': lambda raw, err, p, boot: {'quiesced': recheck_quiesced},
              'cycles_export_result': lambda raw, err, p, boot: {'boot_match': True, 'transport_ok': True}}

        def execute(prepared):
            return None
        execute.__globals__['invoke'] = phase_b
        execute.__globals__['BUDGETS'] = {}
        prepared = {'execute': execute, 'claim': {'phase_budgets': {}}}
        ph = types.SimpleNamespace(
            SCAN=types.SimpleNamespace(PREPARE=lambda candidate: prepared), C2=c2, ROOT=root,
            HOST=types.SimpleNamespace(DOMAIN=types.SimpleNamespace(HOST=types.SimpleNamespace(
                encoded=lambda value: json.dumps(value).encode()))))
        ns = {'runpy': runpy, 'os': os}
        exec(FP['session_source'](), ns)
        ns['_bind_failure_preservation'](ph)
        ph.SCAN.PREPARE('candidate')
        return execute.__globals__['invoke'], {'collector': Collector()}, root, calls

    def test_stop_recheck_then_seal(self):
        invoke, active, root, calls = self.session(0, True)
        raw, _, _ = invoke(active, 'log-export', b'seal')
        self.assertEqual(raw, b'log-export')
        self.assertEqual(calls, ['log-export', 'owned-stop', 'supplicant-log-recheck',
                                 'quiescence-recheck', 'cycles-export', 'log-export'])
        self.assertTrue(json.loads((root/'owned-stop-result.json').read_text())['stopped'])
        self.assertTrue((root/'cycles-evidence.raw').exists())

    def test_still_not_quiesced_exports_then_refuses(self):
        for processes, quiesced in ((1, True), (0, False)):
            invoke, active, root, calls = self.session(processes, quiesced)
            with self.assertRaisesRegex(RuntimeError, 'kernel record exported before the refusal'):
                invoke(active, 'log-export', b'seal')
            self.assertEqual(calls[-1], 'refusal-log-export')
            self.assertEqual((root/'refusal-log-export.raw').read_bytes(), b'refusal-log-export')
            self.assertNotIn('cycles-export', calls)

    def test_other_refusals_and_labels_pass_through(self):
        invoke, active, root, calls = self.session(0, True, refusal='Wi-Fi helper process group not confirmed quiescent')
        self.assertEqual(invoke(active, 'passive-scan', b'scan')[0], b'passive-scan')
        with self.assertRaisesRegex(RuntimeError, 'helper process group'):
            invoke(active, 'log-export', b'seal')
        self.assertEqual(calls, ['passive-scan', 'log-export'])

    def test_stop_result_and_script_shape(self):
        self.assertTrue(FP['stop_result'](STOPPED, b'', {'exit_status': 0}, BOOT)['stopped'])
        left = STOPPED.replace(b'\nafter=\n', b'\nafter=9:wpa_supplicant \n')
        self.assertFalse(FP['stop_result'](left, b'', {'exit_status': 0}, BOOT)['stopped'])
        script = FP['stop_script'](BOOT, FP['OWNED'])
        self.assertIn('wpa_supplicant|nc|dhcpcd|udhcpc)', script)
        self.assertIn("= '%s' ] || exit 3" % BOOT, script)


if __name__ == '__main__':
    unittest.main()
