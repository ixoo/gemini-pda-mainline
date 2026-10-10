#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The laptop's Wi-Fi SSH check: readiness polling, one bounded exchange, the baseline's SSH options, identity binding, no address in the receipt."""
import json
import os
import pathlib
import runpy
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
MOD = runpy.run_path(str(HERE / 'laptop-wifi-ssh.py'), run_name='x')
BOOT = '0123abcd-0123-0123-0123-0123456789ab'
KEYS = pathlib.Path('/private/a53-auth')


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
    def runner(self, markers, exchange):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            if cmd[-1] == 'cat ' + MOD['READY']:
                value = markers.pop(0) if markers else None
                return Result(0, value) if value is not None else Result(1)
            self.assertEqual(cmd[-1], MOD['COMMAND'])
            return exchange(cmd)
        return run, calls

    def test_ready_then_one_bound_exchange_with_baseline_options(self):
        clock = Clock()
        run, calls = self.runner([None, None, b'192.168.4.20\n'], lambda cmd: Result(0, (BOOT + '\n').encode()))
        receipt = MOD['run'](KEYS, BOOT, 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['ready_seen'] and receipt['ssh_attempted'] and receipt['boot_match'] and receipt['ssh_exit'] == 0)
        self.assertEqual(receipt['ready_wait_s'], 4.0)
        hops = [c for c in calls if c[-1] == MOD['COMMAND']]
        self.assertEqual(len(hops), 1)
        base, target = MOD['base_command'](KEYS)
        usb = [c for c in calls if c[-1] != MOD['COMMAND']][0]
        # Both hops carry the baseline's exact direct options and identity; the USB hop its fixed target.
        self.assertEqual(usb[:len(base)], base)
        self.assertEqual(usb[len(base)], target)
        self.assertEqual(hops[0][:len(base)], base)
        self.assertEqual(hops[0][len(base):], ['-o', 'HostKeyAlias=' + target.split('@')[1], 'root@192.168.4.20', MOD['COMMAND']])
        for option in ('-F', '/dev/null', 'BatchMode=yes', 'IdentitiesOnly=yes', 'IdentityAgent=none', 'StrictHostKeyChecking=yes',
                       'UserKnownHostsFile=' + str(KEYS / 'known_hosts'), 'GlobalKnownHostsFile=/dev/null',
                       'HostKeyAlgorithms=ssh-ed25519', 'UpdateHostKeys=no', 'ProxyCommand=none', 'ControlMaster=no',
                       'ClearAllForwardings=yes', 'ConnectionAttempts=1'):
            self.assertIn(option, base)
        self.assertIn(str(KEYS / 'admin'), base)
        self.assertNotIn('192.168.4.20', ' '.join('%s=%s' % kv for kv in receipt.items()))  # the receipt names no address

    def test_boot_mismatch_and_failed_exchange(self):
        clock = Clock()
        run, _ = self.runner([b'192.168.4.20\n'], lambda cmd: Result(0, b'ffffffff-0123-0123-0123-0123456789ab\n'))
        receipt = MOD['run'](KEYS, BOOT, 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['ready_seen'] and not receipt['boot_match'] and receipt['reason'] == 'boot identity differs')
        run, _ = self.runner([b'192.168.4.20\n'], lambda cmd: Result(255))
        receipt = MOD['run'](KEYS, BOOT, 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertEqual((receipt['ssh_exit'], receipt['boot_match'], receipt['reason']), (255, False, 'exchange failed'))

    def test_no_marker_within_budget_and_malformed_marker(self):
        clock = Clock()
        run, _ = self.runner([], lambda cmd: self.fail('no exchange without the marker'))
        receipt = MOD['run'](KEYS, BOOT, 10, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['ready_seen'] or receipt['ssh_attempted'])
        self.assertEqual(receipt['reason'], 'no readiness marker within the poll budget')
        usb = MOD['base_command'](KEYS)[1].split('@')[1]
        bad = [b'not an address\n', b'999.1.1.1\n', b'10.0.0.5 24\n', usb.encode() + b'\n', b'127.0.0.1\n',
               b'224.0.0.1\n', b'0.0.0.0\n', b'255.255.255.255\n']
        run, _ = self.runner(bad, lambda cmd: self.fail('malformed or inadmissible markers never admit'))
        receipt = MOD['run'](KEYS, BOOT, 20, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['ready_seen'])
        self.assertTrue(MOD['admissible']('192.168.4.20', 'root@' + usb) and MOD['admissible']('10.0.0.5', 'root@' + usb))
        self.assertFalse(MOD['admissible'](usb, 'root@' + usb))

    def test_exchange_timeout_is_a_receipt(self):
        clock = Clock()

        def exchange(cmd):
            raise subprocess.TimeoutExpired(cmd, 25)
        run, _ = self.runner([b'10.0.0.5\n'], exchange)
        receipt = MOD['run'](KEYS, BOOT, 60, runner=run, monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['ssh_attempted'] and receipt['ssh_exit'] is None and receipt['reason'] == 'exchange timed out')

    def test_main_refuses_without_keys_and_writes_a_private_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            keys = pathlib.Path(directory) / 'keys'
            keys.mkdir()
            env = dict(os.environ)
            result = subprocess.run([str(HERE / 'laptop-wifi-ssh.py'), str(keys), BOOT, '--poll-seconds', '10'],
                                    capture_output=True, text=True, env=env, timeout=30)
            self.assertEqual(result.returncode, 2)
            self.assertIn('lacks admin or known_hosts', result.stderr)
            script = (HERE / 'join-once.sh').read_text()
            directory_name, marker = MOD['READY'].rsplit('/', 1)
            self.assertIn('data_dir=' + directory_name, script)
            self.assertIn('> "$data_dir/' + marker + '"', script, 'the device script writes the marker the helper polls')


if __name__ == '__main__':
    unittest.main()
