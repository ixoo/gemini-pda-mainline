#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual A/B helper: intervention ordering, refusal and unchanged time budget."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

SPEC = importlib.util.spec_from_file_location(
    'prime', Path(__file__).resolve().parents[1] / 'ssh-prime.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class PrimeTests(unittest.TestCase):
    def exercise(self, arm, prime_rc=0, query_timeout=False, consume=0):
        events, records, now = [], {}, [0.0]

        def runner(argv, **kwargs):
            events.append(argv)
            now[0] += consume
            if argv[0] != 'usb' and query_timeout:
                raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
            return subprocess.CompletedProcess(argv, prime_rc if argv[0] == 'usb' else 0,
                                               stdout=b'fixture\n')

        def wifi(remaining):
            events.append(['wifi', remaining])
            return {'attempted': True}

        result = P.exchange(prime=arm, laptop='10.0.0.2', device='10.0.0.3',
                            command='guarded-ping', usb_command=lambda c: ['usb', c],
                            wifi_exchange=wifi, retain=lambda k, d, r: records.update({k: (d, r)}),
                            budget_s=25, runner=runner, clock=lambda: now[0])
        return result, events, records

    def test_control_emits_no_ping_and_preserves_ssh(self):
        result, events, records = self.exercise(False)
        self.assertTrue(result['attempted'])
        self.assertFalse(any(e[0] == 'usb' for e in events))
        self.assertFalse(records['prime-arm'][1]['attempted'])
        self.assertEqual([e[0] for e in events],
                         ['/sbin/route', '/usr/sbin/arp', '/usr/sbin/arp', 'wifi', '/usr/sbin/arp'])

    def test_prime_between_snapshots_before_ssh(self):
        result, events, records = self.exercise(True, consume=0.2)
        self.assertTrue(result['attempted'])
        self.assertEqual([e[0] for e in events],
                         ['/sbin/route', '/usr/sbin/arp', 'usb', '/usr/sbin/arp', 'wifi', '/usr/sbin/arp'])
        self.assertLess(events[-2][1], 25)
        self.assertEqual(records['device-ping'][1]['exit'], 0)

    def test_guard_refusal_prevents_ssh(self):
        result, events, _ = self.exercise(True, prime_rc=13)
        self.assertFalse(result['attempted'])
        self.assertFalse(any(e[0] == 'wifi' for e in events))

    def test_unanswered_ping_still_observes_ssh_without_retry(self):
        result, events, _ = self.exercise(True, prime_rc=1)
        self.assertTrue(result['attempted'])
        self.assertEqual(sum(e[0] == 'usb' for e in events), 1)

    def test_query_timeout_is_unknown(self):
        result, _, records = self.exercise(False, query_timeout=True)
        self.assertTrue(result['attempted'])
        self.assertTrue(records['arp-before-prime'][1]['timeout'])
        self.assertIsNone(records['arp-before-prime'][1]['exit'])

    def test_budget_exhaustion_cannot_extend_ssh(self):
        result, events, _ = self.exercise(True, consume=13)
        self.assertFalse(result['attempted'])
        self.assertFalse(any(e[0] in ('usb', 'wifi') for e in events))

    def test_non_numeric_and_non_unicast_refused(self):
        for address in ('laptop.local', '10.0.0.2; id', '127.0.0.1', '0.0.0.0', '0.1.2.3', '224.0.0.1'):
            with self.assertRaises(ValueError):
                P.numeric_unicast(address)


if __name__ == '__main__':
    unittest.main()
