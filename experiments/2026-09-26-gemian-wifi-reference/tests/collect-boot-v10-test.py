#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The boot collector: changed-boot detection with exact release and architecture, bounded polling, captures,
before/after identity, private modes, sanitized receipt; SSH is mocked and never runs."""
import json
import os
import pathlib
import runpy
import stat
import subprocess
import tempfile
import unittest

MOD = runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/collect-boot-v10.py'), run_name='x')
OLD = 'cf68b54a-7a3d-4949-8e1e-db1784cdc7df'
NEW = '11111111-2222-3333-4444-555555555555'


class Result:
    def __init__(self, rc, out=b''):
        self.returncode, self.stdout = rc, out


class FakeDevice:
    def __init__(self, boots, release='3.18.41-gemini-wifi-ref10+', machine='aarch64', fail_dmesg=False, flip_after=None):
        self.boots = list(boots)  # boot id returned per identity query, last one repeats
        self.release, self.machine, self.fail_dmesg, self.flip_after = release, machine, fail_dmesg, flip_after
        self.calls = []
        self.identity_queries = 0

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw.get('timeout')))
        remote = cmd[-1]
        if remote == MOD['IDENTITY_COMMAND']:
            boot = self.boots[min(self.identity_queries, len(self.boots) - 1)]
            self.identity_queries += 1
            if self.flip_after is not None and self.identity_queries > self.flip_after:
                boot = self.flip_after_boot
            return Result(0, ('%s\n%s\n%s\n' % (boot, self.machine, self.release)).encode())
        if remote.startswith('sudo -n dmesg'):
            return Result(1) if self.fail_dmesg else Result(0, b'[    0.000000] Booting Linux\n')
        if remote.startswith('sudo -n cat /proc/cmdline'):
            return Result(0, b'console=tty0 androidboot.serialno=SECRET\n')
        if remote.startswith('cat /sys/class/net/wlan0/carrier'):
            return Result(0, b'1\n')
        if remote.startswith('ip -4 addr'):
            return Result(0, b'    inet 192.168.4.20/24 brd 192.168.4.255 scope global wlan0\n')
        return Result(1)


class Clock:
    def __init__(self, step=1.0):
        self.t, self.step = 0.0, step

    def monotonic(self):
        self.t += self.step
        return self.t


class CollectorTest(unittest.TestCase):
    def run_collect(self, device, predecessor=OLD, release='3.18.41-gemini-wifi-ref10+', deadline=180, step=1.0):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name) / 'capture'
        clock = Clock(step)
        receipt = MOD['collect']('dev', '/keys/dev', predecessor, release, out, deadline, runner=device,
                                 monotonic=clock.monotonic, sleep=lambda s: None, wall=lambda: 1_700_000_000)
        return receipt, out

    def test_changed_boot_captured(self):
        device = FakeDevice([OLD, OLD, NEW])
        receipt, out = self.run_collect(device)
        self.assertEqual(receipt['result'], 'changed boot captured')
        self.assertTrue(receipt['changed_boot'] and receipt['identity_stable'])
        self.assertEqual(receipt['identity_before']['boot_id'], NEW)
        self.assertEqual(receipt['identity_after'], receipt['identity_before'])
        self.assertEqual(sorted(receipt['files']), ['addr.txt', 'carrier.txt', 'cmdline.txt', 'dmesg.log'])
        self.assertTrue(any(cmd[-1] == 'sudo -n cat /proc/cmdline' for cmd, _ in device.calls))
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
        for name in receipt['files']:
            self.assertEqual(stat.S_IMODE((out / name).stat().st_mode), 0o600)
            self.assertEqual(len(receipt['files'][name]['sha256']), 64)
        saved = json.loads((out / 'receipt.json').read_text())
        self.assertEqual(saved['result'], 'changed boot captured')
        self.assertNotIn('SECRET', (out / 'receipt.json').read_text())   # the receipt holds digests, not contents
        self.assertNotIn('192.168', (out / 'receipt.json').read_text())
        for cmd, timeout in device.calls:
            for option in ('IdentitiesOnly=yes', 'IdentityAgent=none', 'StrictHostKeyChecking=yes', 'UpdateHostKeys=no', 'BatchMode=yes'):
                self.assertIn(option, cmd)
            self.assertEqual(cmd[cmd.index('-i') + 1], '/keys/dev')
            self.assertLessEqual(timeout, 30)
        self.assertEqual(receipt['boot_ids_seen'], [OLD, NEW])

    def test_wrong_release_or_machine_is_refused(self):
        receipt, out = self.run_collect(FakeDevice([NEW], release='3.18.41+'))
        self.assertTrue(receipt['changed_boot'])
        self.assertIn('refused', receipt['result'])
        self.assertEqual(receipt['files'], {})
        receipt, out = self.run_collect(FakeDevice([NEW], machine='armv7l'))
        self.assertIn('refused', receipt['result'])

    def test_deadline_without_change(self):
        device = FakeDevice([OLD])
        receipt, out = self.run_collect(device, deadline=180, step=10.0)
        self.assertFalse(receipt['changed_boot'])
        self.assertEqual(receipt['result'], 'no changed boot within the deadline')
        self.assertLessEqual(receipt['polls'], 19)
        self.assertTrue((out / 'receipt.json').exists())

    def test_partial_capture_and_unstable_identity(self):
        receipt, out = self.run_collect(FakeDevice([NEW], fail_dmesg=True))
        self.assertEqual(receipt['result'], 'changed boot captured partially')
        self.assertFalse(receipt['files']['dmesg.log']['captured'])
        device = FakeDevice([NEW])
        device.flip_after, device.flip_after_boot = 1, '99999999-9999-9999-9999-999999999999'
        receipt, out = self.run_collect(device)
        self.assertFalse(receipt['identity_stable'])
        self.assertEqual(receipt['result'], 'changed boot captured partially')

    def test_identity_output_must_be_exactly_three_lines(self):
        parse = MOD['parse_identity']
        self.assertEqual(parse(('%s\naarch64\n3.18.41+\n' % NEW).encode()), (NEW, 'aarch64', '3.18.41+'))
        for raw in (('%s\naarch64\n3.18.41+\nextra\n' % NEW), ('%s\naarch64\n' % NEW), ('%s\n\n3.18.41+\n' % NEW),
                    ('%s\naarch64\n3.18.41+\n%s\naarch64\n3.18.41+\n' % (NEW, NEW)), 'not-a-uuid\naarch64\n3.18.41+\n',
                    ('%s\naarch64 extra\n3.18.41+\n' % NEW)):
            self.assertIsNone(parse(raw.encode()), raw)
        self.assertIsNone(parse(None))

    def test_every_call_is_clamped_to_the_remaining_budget(self):
        # the changed boot appears with 12 s left: identity 10 s cap -> captures and the final read fit what remains
        device = FakeDevice([OLD, NEW])
        receipt, out = self.run_collect(device, deadline=15, step=1.0)
        self.assertTrue(all(timeout is not None and timeout <= 10 for cmd, timeout in device.calls), device.calls)
        remaining_at_last = 15 - (len(device.calls) + 1)
        self.assertLessEqual(device.calls[-1][1], max(1.0, remaining_at_last + 1))
        # a changed boot found just before the deadline: no capture or final read starts after it
        device = FakeDevice([NEW])
        receipt, out = self.run_collect(device, deadline=3, step=1.0)
        self.assertIn(receipt['result'], ('deadline during the captures', 'deadline before the final identity read'))
        self.assertFalse(receipt['identity_stable'])
        for cmd, timeout in device.calls:
            self.assertLessEqual(timeout, 3)

    def test_ssh_timeouts_are_tolerated_and_output_must_be_new(self):
        def runner(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, kw.get('timeout'))
        receipt, out = self.run_collect(runner, deadline=180, step=30.0)
        self.assertFalse(receipt['changed_boot'])
        with self.assertRaises(FileExistsError):
            MOD['collect']('dev', '/keys/dev', OLD, '3.18.41+', out, 180, runner=runner, monotonic=lambda: 0, sleep=lambda s: None)


if __name__ == '__main__':
    unittest.main()
