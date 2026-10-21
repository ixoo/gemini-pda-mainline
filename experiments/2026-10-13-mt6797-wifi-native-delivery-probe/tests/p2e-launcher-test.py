#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed P2E launch sequencing; no network or device process is allowed."""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('p2e_launcher', HERE/'laptop-run-ccmp-p2e.py')
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
BOOT = '11111111-2222-3333-4444-555555555555'
PREVIOUS = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.calls = []
        self.uptime = '20.00'
        self.note = L.NOTES_SHA
        self.release = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
        self.fail_identity = False
        self.capture_rc = self.session_rc = 0
        self.capture_boot = BOOT
        self.state = dict(runtime=self.root, keys=Path('/unused/keys'),
                          protocol={'kernel_release': self.release, 'live_root_sha256': {'init': 'f'*64}},
                          candidate=Path('/unused/candidate'), env={'GEMINI_WIFI_SSH_BOOT': 'stale'},
                          previous_boot=PREVIOUS,
                          collector={'ssh_command': lambda _keys: ['forbidden-SSH'],
                                     'run_once': self.collect})

    def tearDown(self):
        self.temp.cleanup()

    def collect(self, command, script, attempt, timeout, **limits):
        # Reproduce the collector's real requirement which the ad hoc launch missed.
        self.assertTrue(attempt.is_dir())
        self.assertEqual(timeout, 10)
        self.assertEqual(limits, {'stdout_limit': 4096, 'stderr_limit': 4096})
        self.calls.append('identity')
        if self.fail_identity:
            raise FileNotFoundError('injected identity-output failure')
        (attempt/'stdout.txt').write_text(
            self.release+'\naarch64\n'+BOOT+'\n'+self.note+'  /sys/kernel/notes\n84\n'+
            self.uptime+' 0.00\nlogger_active=yes\n'+'f'*64+'  /init\n')
        return {'exit_status': 0, 'reason': None, 'stdin_complete': True}

    def phase(self, name, state):
        self.assertEqual(state['env']['GEMINI_WIFI_SSH_BOOT'], BOOT)
        self.assertTrue((self.root/'live-identity.json').is_file())
        self.calls.append(name)
        if name == 'capture':
            if self.capture_rc == 0:
                path = self.root/'ccmp-stable-monitor/capture-ccmp-p2e'
                path.mkdir(parents=True)
                (path/'preflight.json').write_text(json.dumps(
                    {'boot_id': self.capture_boot, 'release': self.release}))
            return self.capture_rc
        return self.session_rc

    def run_launcher(self):
        with patch.object(L, 'phase', self.phase), \
                patch.object(L.subprocess, 'Popen', side_effect=AssertionError('no process allowed')):
            return L.execute(self.state)

    def result(self):
        return json.loads((self.root/'launcher-result.json').read_bytes())

    def test_directory_created_then_fresh_boot_bound_before_one_capture_and_session(self):
        self.assertEqual(self.run_launcher(), 0)
        self.assertEqual(self.calls, ['identity', 'capture', 'session'])
        self.assertEqual(self.result()['phase'], 'complete')

    def test_local_identity_failure_never_bootstraps_or_runs_session(self):
        self.fail_identity = True
        self.assertEqual(self.run_launcher(), 2)
        self.assertEqual(self.calls, ['identity'])
        self.assertFalse(self.result()['bootstrap_attempted'])
        self.assertFalse(self.result()['session_attempted'])

    def test_claim_cannot_be_reused_after_failure(self):
        self.fail_identity = True
        self.run_launcher()
        with self.assertRaises(FileExistsError):
            self.run_launcher()
        self.assertEqual(self.calls, ['identity'])

    def test_wrong_notes_never_bootstrap(self):
        self.note = '0'*64
        self.assertEqual(self.run_launcher(), 2)
        self.assertEqual(self.calls, ['identity'])
        self.assertEqual(self.result()['refusal'], 'kernel notes identity')

    def test_wrong_kernel_never_bootstraps(self):
        self.release = 'wrong-kernel'
        # Preserve the expected receipt; only the acquired line is changed.
        self.assertEqual(self.run_launcher(), 2)
        self.assertEqual(self.calls, ['identity'])

    def test_existing_whole_second_boundary_is_not_extended_or_shortened(self):
        self.uptime = '50.99'
        self.assertEqual(self.run_launcher(), 0)

    def test_late_boot_never_bootstraps(self):
        self.uptime = '51.00'
        self.assertEqual(self.run_launcher(), 2)
        self.assertEqual(self.calls, ['identity'])
        self.assertEqual(self.result()['refusal'], 'cold logger admission')

    def test_capture_refusal_enters_original_failure_session_once(self):
        self.capture_rc = self.session_rc = 1
        self.assertEqual(self.run_launcher(), 1)
        self.assertEqual(self.calls, ['identity', 'capture', 'session'])

    def test_capture_boot_change_holds_before_session(self):
        self.capture_boot = PREVIOUS
        self.assertEqual(self.run_launcher(), 2)
        self.assertEqual(self.calls, ['identity', 'capture'])
        self.assertFalse(self.result()['session_attempted'])

    @unittest.skipUnless(os.environ.get('GEMINI_SESSION_SOURCE_ROOT'), 'retained collector fixture')
    def test_real_collector_opens_files_then_runs_only_local_identity_child(self):
        cohort = Path(os.environ['GEMINI_SESSION_SOURCE_ROOT'])
        path = cohort/'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/collect-baseline.py'
        self.assertEqual(L.digest(path), L.COLLECT_SHA)
        collector = runpy.run_path(str(path))
        raw = (self.release+'\naarch64\n'+BOOT+'\n'+L.NOTES_SHA+'  /sys/kernel/notes\n'
               '84\n20.00 0.00\nlogger_active=yes\n'+'f'*64+'  /init\n').encode()
        collector['ssh_command'] = lambda _keys: [sys.executable, '-c',
            'import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write('+repr(raw)+')']
        self.state['collector'] = collector
        with patch.object(L, 'phase', self.phase):
            self.assertEqual(L.execute(self.state), 0)
        self.assertEqual((self.root/'identity/stdout.txt').read_bytes(), raw)
        self.assertEqual(json.loads((self.root/'identity/process.json').read_bytes())['exit_status'], 0)
        self.assertEqual(self.calls, ['capture', 'session'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
