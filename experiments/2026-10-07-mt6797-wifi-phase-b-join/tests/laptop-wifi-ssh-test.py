#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The laptop's Wi-Fi SSH check: lease polling, one bounded exchange, identity binding, no address in the receipt."""
import pathlib
import runpy
import subprocess
import unittest

MOD = runpy.run_path(str(pathlib.Path(__file__).resolve().parents[1] / 'laptop-wifi-ssh.py'), run_name='x')
BOOT = '0123abcd-0123-0123-0123-0123456789ab'


class Result:
    def __init__(self, rc, out=b''):
        self.returncode, self.stdout = rc, out


class Clock:
    def __init__(self):
        self.t = 100.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += s


class WifiSsh(unittest.TestCase):
    def runner(self, leases, exchange):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            if cmd[-2:] == ['cat', MOD['LEASE']]:
                value = leases.pop(0) if leases else leases_default
                return Result(0, value) if value is not None else Result(1)
            self.assertEqual(cmd[-1], MOD['COMMAND'])
            return exchange(cmd)
        leases_default = None
        return run, calls

    def test_lease_then_one_bound_exchange(self):
        clock = Clock()
        run, calls = self.runner([None, None, b'192.168.4.20\n'], lambda cmd: Result(0, (BOOT + '\n').encode()))
        receipt = MOD['run']('usb', '/k', BOOT, 'root', 'usb', 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['lease_seen'] and receipt['ssh_attempted'] and receipt['boot_match'] and receipt['ssh_exit'] == 0)
        self.assertEqual(receipt['lease_wait_s'], 4.0)
        self.assertEqual(len([c for c in calls if c[-1] == MOD['COMMAND']]), 1)
        hop = [c for c in calls if c[-1] == MOD['COMMAND']][0]
        for option in ('BatchMode=yes', 'IdentitiesOnly=yes', 'IdentityAgent=none', 'StrictHostKeyChecking=yes',
                       'UpdateHostKeys=no', 'HostKeyAlias=usb'):
            self.assertIn(option, hop)
        self.assertIn('root@192.168.4.20', hop)
        self.assertNotIn('192.168.4.20', ' '.join('%s=%s' % kv for kv in receipt.items()))  # the receipt names no address

    def test_boot_mismatch_and_failed_exchange(self):
        clock = Clock()
        run, _ = self.runner([b'192.168.4.20\n'], lambda cmd: Result(0, b'ffffffff-0123-0123-0123-0123456789ab\n'))
        receipt = MOD['run']('usb', '/k', BOOT, 'root', None, 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['lease_seen'] and not receipt['boot_match'] and receipt['reason'] == 'boot identity differs')
        run, _ = self.runner([b'192.168.4.20\n'], lambda cmd: Result(255))
        receipt = MOD['run']('usb', '/k', BOOT, 'root', None, 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertEqual((receipt['ssh_exit'], receipt['boot_match'], receipt['reason']), (255, False, 'exchange failed'))

    def test_no_lease_within_budget_and_malformed_lease(self):
        clock = Clock()
        run, calls = self.runner([], lambda cmd: self.fail('no exchange without a lease'))
        receipt = MOD['run']('usb', '/k', BOOT, 'root', None, 10, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['lease_seen'] or receipt['ssh_attempted'])
        self.assertEqual(receipt['reason'], 'no lease within the poll budget')
        run, _ = self.runner([b'not an address\n', b'999.1.1.1\n', b'10.0.0.5 24\n'], lambda cmd: self.fail('malformed leases never admit'))
        receipt = MOD['run']('usb', '/k', BOOT, 'root', None, 10, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['lease_seen'])

    def test_exchange_timeout_is_a_receipt(self):
        clock = Clock()

        def exchange(cmd):
            raise subprocess.TimeoutExpired(cmd, 25)
        run, _ = self.runner([b'10.0.0.5\n'], exchange)
        receipt = MOD['run']('usb', '/k', BOOT, 'root', None, 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['ssh_attempted'] and receipt['ssh_exit'] is None and receipt['reason'] == 'exchange timed out')


if __name__ == '__main__':
    unittest.main()
