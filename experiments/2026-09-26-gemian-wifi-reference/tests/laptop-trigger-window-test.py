#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The window orchestration sends exactly once inside an open window and never otherwise; SSH is mocked."""
import pathlib
import runpy
import subprocess
import unittest

MOD = runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/laptop-trigger-window.py'), run_name='x')


class FakeResult:
    def __init__(self, rc, out=b''):
        self.returncode, self.stdout = rc, out


class WindowTest(unittest.TestCase):
    def scenario(self, outputs, times):
        calls = []
        sends = []

        def runner(cmd, **kw):
            calls.append(cmd)
            return outputs.pop(0) if outputs else FakeResult(1)

        clock = iter(times)
        return runner, calls, sends, (lambda: next(clock)), (lambda s: None), (lambda l, p: sends.append((l, p)))

    def test_sends_once_inside_window(self):
        runner, calls, sends, clock, sleep, send = self.scenario([FakeResult(1), FakeResult(0, b'1000 1020\n')], [900, 901, 902, 1005, 1006, 1007])
        outcome = MOD['run'](['ssh', 'dev'], '192.168.4.17', 24, 60, runner, clock, sleep, send)
        self.assertTrue(outcome['sent'] and outcome['window_seen'])
        self.assertEqual(sends, [('192.168.4.17', 24)])
        self.assertEqual(calls[0][-2:], ['cat', MOD['MARKER']])

    def test_closed_window_and_no_window(self):
        runner, calls, sends, clock, sleep, send = self.scenario([FakeResult(0, b'1000 1020\n')], [900, 1050, 1051])
        outcome = MOD['run'](['ssh', 'dev'], '192.168.4.17', 24, 60, runner, clock, sleep, send)
        self.assertFalse(outcome['sent'])
        self.assertEqual(sends, [])
        runner, calls, sends, clock, sleep, send = self.scenario([], [0, 1, 2, 3, 4, 5, 6])
        outcome = MOD['run'](['ssh', 'dev'], '192.168.4.17', 24, 3, runner, clock, sleep, send)
        self.assertFalse(outcome['window_seen'] or outcome['sent'])

    def test_malformed_marker_is_ignored(self):
        runner, calls, sends, clock, sleep, send = self.scenario([FakeResult(0, b'soon\n'), FakeResult(0, b'1000 1020 1030\n')], [0, 1, 2, 3, 4, 5])
        outcome = MOD['run'](['ssh', 'dev'], '192.168.4.17', 24, 3, runner, clock, sleep, send)
        self.assertFalse(outcome['sent'])

    def test_ssh_timeout_is_tolerated(self):
        def runner(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 10)
        times = iter([0, 1, 2, 3, 4])
        outcome = MOD['run'](['ssh', 'dev'], '192.168.4.17', 24, 2, runner, lambda: next(times), lambda s: None, lambda l, p: None)
        self.assertFalse(outcome['sent'])


if __name__ == '__main__':
    unittest.main()
