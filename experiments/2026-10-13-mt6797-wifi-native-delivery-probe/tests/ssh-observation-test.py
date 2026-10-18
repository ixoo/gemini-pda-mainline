#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the original CCMP verifier/ACK state machine through D1's runner."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ssh_observer_test', HERE / 'laptop-wifi-ssh-observe.py')
O = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(O)
BOOT = 'c3c13385-7138-493e-b7df-6fe5673c6739'
READY = ('boot=' + BOOT + '\ncycle=1\nsshd_pid=1234\naddress=10.0.0.55\n'
         'mode=ccmp-stable-monitor\nafter_active=1\n')
SERVED = (BOOT + '\n' + O.C.M.MARKER + '\n' + READY).encode()
PROBE = ('BOOT=' + BOOT + '\nFATAL=0\nTERM=0\nDMESG=ok\nREADY_BEGIN\n' +
         READY + 'READY_END\nLIVE=1\n').encode()


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.umask = os.umask(0o077)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'observed'
        O.C.MARKERS.clear()
        self.base_command = O.C.M.base_command
        O.C.M.base_command = lambda keys: (['ssh'], 'root@10.0.0.1')

    def tearDown(self):
        O.C.M.base_command = self.base_command
        self.temp.cleanup()
        os.umask(self.umask)

    def cycle(self, rc=0, served=SERVED, error=b'', timeout=False, closed=False):
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            if any(arg.startswith('HostKeyAlias=') for arg in argv):
                self.assertEqual(argv, O.C.M.wifi_command(Path('/unused'), '10.0.0.55', 1))
                self.assertEqual(kwargs['stdout'], subprocess.PIPE)
                self.assertLessEqual(kwargs['timeout'], 25)
                kwargs['stderr'].write(error)
                if timeout:
                    raise subprocess.TimeoutExpired(argv, kwargs['timeout'], output=served)
                return subprocess.CompletedProcess(argv, rc, stdout=served)
            self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
            data = PROBE.replace(b'TERM=0', b'TERM=1') if closed else PROBE
            return subprocess.CompletedProcess(argv, 0, stdout=data)

        result = O.C.run(Path('/unused'), BOOT, 1, 90,
                         runner=O.observing_runner(self.root, runner))
        return result, calls

    def test_success_preserves_identity_and_guarded_ack(self):
        result, calls = self.cycle()
        self.assertTrue(result['all_pass'])
        self.assertTrue(result['cycles'][0]['ack_written'])
        self.assertEqual(len(calls), 3)  # existing USB probe, Wi-Fi exchange, USB ACK
        self.assertEqual((self.root / 'stdout.bin').read_bytes(), SERVED)
        self.assertIn('set -C;', calls[-1][0][-1])
        for path in self.root.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_failed_exchange_retains_error_without_ack(self):
        error = b'ssh: connect to host 10.0.0.55 port 22: Operation timed out\r\n'
        result, calls = self.cycle(rc=255, served=b'partial', error=error)
        self.assertEqual(len(calls), 2)
        self.assertFalse(result['all_pass'])
        self.assertFalse(result['cycles'][0]['ack_written'])
        self.assertEqual(result['cycles'][0]['ssh_exit'], 255)
        self.assertEqual((self.root / 'stderr.bin').read_bytes(), error)
        self.assertEqual((self.root / 'stdout.bin').read_bytes(), b'partial')
        record = json.loads((self.root / 'process.json').read_text())
        self.assertEqual(record['exit'], 255)
        self.assertEqual(record['stderr_bytes'], len(error))
        self.assertGreaterEqual(record['ended_ns'], record['started_ns'])

    def test_wrong_served_boot_or_marker_never_acknowledged(self):
        for old, new in ((BOOT.encode(), b'deadbeef-0000-0000-0000-000000000000'),
                         (b'after_active=1', b'after_active=0'),
                         (b'ccmp-stable-monitor', b'other-mode')):
            with self.subTest(new=new):
                self.root = Path(self.temp.name) / new.decode()
                result, calls = self.cycle(served=SERVED.replace(old, new))
                self.assertFalse(result['all_pass'])
                self.assertFalse(result['cycles'][0]['ack_written'])
                self.assertEqual(len(calls), 2)

    def test_closed_window_has_no_wifi_acquisition(self):
        result, calls = self.cycle(closed=True)
        self.assertFalse(result['all_pass'])
        self.assertTrue(result['cycles'][0]['closed'])
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.root.exists())

    def test_timeout_keeps_original_failure_and_partial_output(self):
        result, calls = self.cycle(timeout=True, served=b'partial')
        self.assertEqual(result['cycles'][0]['reason'], 'exchange timed out')
        self.assertFalse(result['cycles'][0]['ack_written'])
        self.assertEqual(len(calls), 2)
        self.assertTrue(json.loads((self.root / 'process.json').read_text())['timeout'])
        self.assertEqual((self.root / 'stdout.bin').read_bytes(), b'partial')

    def test_existing_observation_refuses_before_process(self):
        self.root.mkdir()
        with self.assertRaises(FileExistsError):
            self.cycle()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_runner_refuses_a_second_wifi_attempt(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 255, stdout=b'')

        observed = O.observing_runner(self.root, runner)
        argv = O.C.M.wifi_command(Path('/unused'), '10.0.0.55', 1)
        kwargs = {'stdout': subprocess.PIPE, 'stderr': subprocess.DEVNULL, 'timeout': 10}
        observed(argv, **kwargs)
        with self.assertRaises(ValueError):
            observed(argv, **kwargs)
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
