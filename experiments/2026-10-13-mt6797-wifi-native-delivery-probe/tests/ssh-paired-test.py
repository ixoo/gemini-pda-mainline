#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual C10 verifier and A/B wrapper: no implicit retries or verdict replacement."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load('paired_test', HERE.parent / 'laptop-wifi-ssh-paired.py')
F = load('paired_existing_fixture', HERE / 'ssh-observation-test.py')


class PairedTests(unittest.TestCase):
    def exercise(self, a_rc=255, closed=False, prime_rc=0, after_prime_closed=False,
                 local_address=b'10.0.0.2\n', timed_out=False, b_rc=0, exhausted=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'observed'
            calls, attempts, primed = [], [], [False]
            now = [0.0]
            old = P.C.M.base_command
            P.C.M.base_command = lambda keys: (['ssh'], 'root@10.0.0.1')
            P.C.MARKERS.clear()

            def runner(argv, **kwargs):
                calls.append(argv)
                if argv[0] == '/sbin/route':
                    return subprocess.CompletedProcess(argv, 0, stdout=b' interface: en0\n')
                if argv[0] == '/usr/sbin/arp':
                    return subprocess.CompletedProcess(argv, 0, stdout=b'fixture neighbor state\n')
                if argv[0] == '/usr/sbin/ipconfig':
                    output = {'getifaddr': local_address, 'getoption': b'255.255.255.0\n',
                              'getpacket': b'yiaddr = 10.0.0.2\n'}[argv[1]]
                    return subprocess.CompletedProcess(argv, 0, stdout=output)
                if any(arg.startswith('HostKeyAlias=') for arg in argv):
                    self.assertEqual(argv, P.C.M.wifi_command(Path('/unused'), '10.0.0.55', 1))
                    self.assertLessEqual(kwargs['timeout'], 25)
                    attempts.append(argv)
                    rc = a_rc if len(attempts) == 1 else b_rc
                    if exhausted:
                        now[0] = 26.0
                    if rc:
                        kwargs['stderr'].write(b'ssh: connect to host fixture port 22: No route to host\n')
                    if timed_out and len(attempts) == 1:
                        raise subprocess.TimeoutExpired(argv, kwargs['timeout'], output=b'partial')
                    return subprocess.CompletedProcess(argv, rc, stdout=F.SERVED if not rc else b'')
                if '/bin/busybox ping -I wlan0' in argv[-1]:
                    primed[0] = True
                    self.assertIn('data phase end:', argv[-1])
                    return subprocess.CompletedProcess(argv, prime_rc, stdout=b'fixture ping\n')
                data = F.PROBE
                if attempts and (closed or (primed[0] and after_prime_closed)):
                    data = data.replace(b'FATAL=0', b'FATAL=1')
                return subprocess.CompletedProcess(argv, 0, stdout=data)

            try:
                result = P.paired_run(Path('/unused'), F.BOOT, 1, 90, root, runner,
                                      clock=lambda: now[0])
            finally:
                P.C.M.base_command = old
            a_error = (root / 'arm-a/stderr.bin').read_bytes()
            b_error = (root / 'arm-b/stderr.bin').read_bytes() if (root / 'arm-b').exists() else None
            return result, attempts, primed[0], a_error, b_error, calls

    def test_a_success_stops_without_prime_or_second_attempt(self):
        result, attempts, primed, _, _, _ = self.exercise(a_rc=0)
        self.assertTrue(result['all_pass'])
        self.assertEqual(len(attempts), 1)
        self.assertFalse(primed)
        self.assertIsNone(result['paired']['arm_b'])

    def test_a_failure_and_separate_b_success_never_replace_a(self):
        result, attempts, primed, a_error, b_error, _ = self.exercise()
        self.assertFalse(result['all_pass'])
        self.assertEqual(result['cycles'][0]['ssh_exit'], 255)
        self.assertTrue(result['paired']['arm_b']['all_pass'])
        self.assertEqual(len(attempts), 2)
        self.assertTrue(primed)
        self.assertIn(b'No route to host', a_error)
        self.assertEqual(b_error, b'')

    def test_closed_window_after_a_never_primes_or_runs_b(self):
        result, attempts, primed, _, _, _ = self.exercise(closed=True)
        self.assertEqual(len(attempts), 1)
        self.assertFalse(primed)
        self.assertIn('not freshly live', result['paired']['b_not_reached'])

    def test_guard_refusal_prevents_b(self):
        result, attempts, primed, _, _, _ = self.exercise(prime_rc=12)
        self.assertTrue(primed)
        self.assertEqual(len(attempts), 1)
        self.assertIn('guard/transport refused', result['paired']['b_not_reached'])

    def test_window_change_during_prime_prevents_b(self):
        result, attempts, _, _, _, _ = self.exercise(after_prime_closed=True)
        self.assertEqual(len(attempts), 1)
        self.assertIn('changed after prime', result['paired']['b_not_reached'])

    def test_unverified_laptop_address_prevents_intervention(self):
        result, attempts, primed, _, _, _ = self.exercise(local_address=b'10.0.1.2\n')
        self.assertFalse(primed)
        self.assertEqual(len(attempts), 1)
        self.assertIn('LAN lease not established', result['paired']['b_not_reached'])

    def test_unanswered_ping_is_recorded_not_retried(self):
        result, attempts, primed, _, _, _ = self.exercise(prime_rc=1)
        self.assertTrue(primed)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(result['paired']['prime_exit'], 1)

    def test_a_timeout_output_is_retained_separately(self):
        result, attempts, _, _, _, _ = self.exercise(timed_out=True, closed=True)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(result['cycles'][0]['reason'], 'exchange timed out')
        self.assertIsNone(result['paired']['arm_b'])

    def test_b_failure_never_attempts_a_third_exchange(self):
        result, attempts, _, _, _, _ = self.exercise(b_rc=255)
        self.assertEqual(len(attempts), 2)
        self.assertFalse(result['paired']['arm_b']['all_pass'])

    def test_exhausted_original_exchange_budget_prevents_b(self):
        result, attempts, primed, _, _, _ = self.exercise(exhausted=True)
        self.assertEqual(len(attempts), 1)
        self.assertFalse(primed)
        self.assertIsNone(result['paired']['arm_b'])

    def test_actual_cli_writes_one_owned_receipt_without_recursion(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary).resolve()
            keys = runtime / 'keys'
            keys.mkdir()
            (keys / 'admin').touch(); (keys / 'known_hosts').touch()
            receipt = runtime / 'ccmp-stable-monitor/session-ccmp10/wifi-ssh-receipt.json'
            receipt.parent.mkdir(parents=True)
            result = {'boot_id': F.BOOT, 'cycles_expected': 1, 'cycles': [], 'all_pass': False}
            original = P.C.M.run
            try:
                with patch.object(P.sys, 'platform', 'darwin'), \
                     patch.object(P.sys, 'argv', ['paired', str(keys), F.BOOT, '--cycles', '1',
                                                 '--receipt', str(receipt)]), \
                     patch.dict(os.environ, {'GEMINI_RUNTIME_ROOT': str(runtime)}), \
                     patch.object(P, 'paired_run', return_value=result) as run:
                    self.assertEqual(P.main(), 1)
                    run.assert_called_once_with(keys, F.BOOT, 1, 90,
                                                receipt.parent / 'ssh-client-observation')
                self.assertEqual(json.loads(receipt.read_text()), result)
            finally:
                P.C.M.run = original


if __name__ == '__main__':
    unittest.main()
