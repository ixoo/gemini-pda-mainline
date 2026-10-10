#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The window orchestration sends exactly once inside a window with room for the schedule, never otherwise;
SSH is mocked and its options and clamped timeouts are checked."""
import pathlib
import runpy
import subprocess
import unittest

MOD = runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/laptop-trigger-window.py'), run_name='x')
BOOT = '12345678-1234-1234-1234-123456789abc'


class FakeResult:
    def __init__(self, rc, out=b''):
        self.returncode, self.stdout = rc, out


class WindowTest(unittest.TestCase):
    def scenario(self, outputs, wall, mono):
        calls, sends, timeouts = [], [], []

        def runner(cmd, **kw):
            calls.append(cmd)
            timeouts.append(kw.get('timeout'))
            return outputs.pop(0) if outputs else FakeResult(1)

        wall_it, mono_it = iter(wall), iter(mono)
        return dict(runner=runner, clock=lambda: next(wall_it), monotonic=lambda: next(mono_it), sleep=lambda s: None,
                    send=lambda l, p: sends.append((l, p))), calls, sends, timeouts

    def test_sends_once_inside_window_with_room(self):
        kw, calls, sends, timeouts = self.scenario([FakeResult(1), FakeResult(0, ('1000 1020 %s\n' % BOOT).encode())],
                                                    wall=[1005, 1006], mono=[0, 0, 0, 1, 1, 1, 2])
        outcome = MOD['run']('dev', '/keys/dev', BOOT, '192.168.4.17', 24, 60, **kw)
        self.assertTrue(outcome['sent'] and outcome['window_seen'], outcome)
        self.assertEqual(sends, [('192.168.4.17', 24)])
        cmd = calls[0]
        for option in ('IdentitiesOnly=yes', 'IdentityAgent=none', 'StrictHostKeyChecking=yes', 'UpdateHostKeys=no', 'BatchMode=yes'):
            self.assertIn(option, cmd)
        self.assertEqual(cmd[cmd.index('-i') + 1], '/keys/dev')
        self.assertEqual(cmd[-4:], ['sudo', '-n', 'cat', MOD['MARKER']])

    def test_not_enough_room_or_closed_or_future(self):
        for wall, reason in ((1017, 'not enough window left'), (1050, 'not enough window left'), (990, 'window start is in the future')):
            kw, calls, sends, timeouts = self.scenario([FakeResult(0, ('1000 1020 %s\n' % BOOT).encode())], wall=[wall], mono=[0, 0, 0, 1])
            outcome = MOD['run']('dev', '/keys/dev', BOOT, '192.168.4.17', 24, 60, **kw)
            self.assertFalse(outcome['sent'])
            self.assertIn(reason, outcome['reason'])
            self.assertEqual(sends, [])

    def test_wrong_boot_id_and_malformed_marker(self):
        kw, calls, sends, timeouts = self.scenario([FakeResult(0, b'1000 1020 ffffffff-ffff-ffff-ffff-ffffffffffff\n')], wall=[1005], mono=[0, 0, 0, 1])
        outcome = MOD['run']('dev', '/keys/dev', BOOT, '192.168.4.17', 24, 60, **kw)
        self.assertFalse(outcome['sent'])
        self.assertIn('boot id differs', outcome['reason'])
        kw, calls, sends, timeouts = self.scenario([FakeResult(0, b'1000 1020\n'), FakeResult(0, b'soon\n')], wall=[], mono=[0, 0, 0, 1, 1, 1, 2, 2, 2, 3])
        outcome = MOD['run']('dev', '/keys/dev', BOOT, '192.168.4.17', 24, 3, **kw)
        self.assertFalse(outcome['window_seen'] or outcome['sent'])

    def test_monotonic_budget_and_clamped_ssh_timeout(self):
        kw, calls, sends, timeouts = self.scenario([], wall=[], mono=[0, 0, 0, 5, 5, 5, 25, 25, 25, 29.5, 29.5, 29.5, 30])
        outcome = MOD['run']('dev', '/keys/dev', BOOT, '192.168.4.17', 24, 30, **kw)
        self.assertFalse(outcome['sent'])
        self.assertEqual(outcome['reason'], 'no window within the poll budget')
        self.assertTrue(all(t <= 10 for t in timeouts), timeouts)
        self.assertLessEqual(timeouts[-1], 5.0 + 1e-6)   # the last call is clamped to what remained
        self.assertEqual(sends, [])

    def test_ssh_timeout_is_tolerated(self):
        def runner(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 10)
        mono = iter([0, 0, 0, 1, 1, 1, 2, 2, 2, 3])
        outcome = MOD['run']('dev', '/keys/dev', BOOT, '192.168.4.17', 24, 2, runner=runner, clock=lambda: 0,
                             monotonic=lambda: next(mono), sleep=lambda s: None, send=lambda l, p: None)
        self.assertFalse(outcome['sent'])


if __name__ == '__main__':
    unittest.main()
