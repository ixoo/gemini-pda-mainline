#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native host processes only; fixture build cannot exec the device observer."""
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2] / 'artifacts/a53-authenticated/development/keyboard-monitor-tests'


class MonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True, mode=0o700)
        if WORK.is_symlink() or WORK.stat().st_mode & 0o777 != 0o700:
            raise RuntimeError('unsafe managed fixture root')
        cls.build = tempfile.TemporaryDirectory(prefix='build-', dir=WORK)
        cls.addClassCleanup(cls.build.cleanup)
        cls.fixture = Path(cls.build.name) / 'fixture'
        cls.disabled = Path(cls.build.name) / 'disabled'
        for source, dest, extra in [('monitor-fixture.c', cls.fixture, ['-DFIXTURE_ROOT=' + json.dumps(str(WORK))]),
                                    ('monitor.c', cls.disabled, [])]:
            subprocess.run(['cc', '-std=c11', '-Os', '-Wall', '-Wextra', '-Werror',
                            str(HERE / source), '-o', str(dest), *extra],
                           check=True, capture_output=True, timeout=30)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='case-', dir=WORK)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_case(self, mode, *, sig=None, close=False, stall=False, limit=131072):
        # A deliberately inherited fd checks the fixture child close policy.
        fd = os.open('/dev/null', os.O_RDONLY)
        os.dup2(fd, 47, inheritable=True)
        os.close(fd)

        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
            resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))

        try:
            p = subprocess.Popen([str(self.fixture), str(self.root), mode], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=(47,),
                                 start_new_session=True, preexec_fn=limits)
        finally:
            os.close(47)
        output = bytearray()
        error = bytearray()
        start = time.monotonic()
        delivered = False
        timed_out = False
        terminal = False
        captured = self.root / 'keyboard-attempt/observer.stdout'
        for stream in (p.stdout, p.stderr):
            os.set_blocking(stream.fileno(), False)

        def drain(stream, buffer):
            if stream.closed:
                return
            try:
                data = os.read(stream.fileno(), 131073)
            except BlockingIOError:
                return
            buffer.extend(data)
            self.assertLessEqual(len(buffer), 131072)

        try:
            while True:
                # Retain the monitor PID until all fixture-group cleanup ends.
                info = os.waitid(os.P_PID, p.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                if info is not None and info.si_pid == p.pid:
                    terminal = True
                    break
                if not delivered and captured.exists() and captured.stat().st_size:
                    if sig:
                        os.kill(p.pid, sig)
                    if close:
                        p.stdout.close()
                    delivered = True
                if not stall:
                    drain(p.stdout, output)
                drain(p.stderr, error)
                if time.monotonic() - start > 3:
                    timed_out = True
                    break
                time.sleep(.002)
        finally:
            # Our fixture has only the monitor and its one builtin child.
            # A terminal monitor reporting a reaped child has no live group
            # member to kill (Darwin can return EPERM for a zombie-only group).
            status_path = self.root / 'keyboard-attempt/monitor.status'
            child_reaped = terminal and status_path.exists() and '\nreaped=1\n' in status_path.read_text()
            try:
                if not child_reaped:
                    # WNOWAIT still holds the identity on the failure path.
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            finally:
                p.wait(timeout=1)
            for stream, buffer in ((p.stdout, output), (p.stderr, error)):
                try:
                    if not stream.closed:
                        for _ in range(33):
                            old = len(buffer)
                            drain(stream, buffer)
                            if len(buffer) == old:
                                break
                finally:
                    stream.close()
        self.assertFalse(timed_out, 'outer fixture deadline; group killed before releasing monitor identity')
        raw = (self.root / 'keyboard-attempt/monitor.status').read_text()
        fields = dict(line.split('=', 1) for line in raw.splitlines())
        self.assertEqual(fields['reaped'], '1')
        self.assertEqual(fields['identity_lost'], '0')
        self.assertLess(time.monotonic() - start, 3)
        return p.returncode, bytes(output), bytes(error), fields

    def test_default_entry_disabled_and_no_claim(self):
        result = subprocess.run([str(self.disabled)], capture_output=True, timeout=1)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'target-admission-disabled', result.stderr)
        self.assertFalse((self.root / 'keyboard-attempt').exists())

    def test_normal_direct_retention_forwarding_and_once_only_claim(self):
        code, out, err, f = self.run_case('normal')
        self.assertEqual((code, err, f['reason'], f['term_ms'], f['kill_ms']),
                         (0, b'', 'normal-lifecycle-only', '-1', '-1'))
        self.assertEqual(out, (self.root / 'keyboard-attempt/observer.stdout').read_bytes())
        self.assertTrue(out.endswith(b'fixture-done\n'))
        before = {p.name: p.read_bytes() for p in (self.root / 'keyboard-attempt').iterdir()}
        second = subprocess.run([str(self.fixture), str(self.root), 'normal'], capture_output=True, timeout=1)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / 'keyboard-attempt').iterdir()})

    def test_cancellation_signals(self):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGPIPE):
            with self.subTest(signal=sig):
                # Each subcase has a different exclusive claim parent.
                with tempfile.TemporaryDirectory(prefix='signal-', dir=WORK) as path:
                    self.root = Path(path)
                    code, _, _, f = self.run_case('wait', sig=sig)
                    self.assertEqual((code, int(f['cancel'])), (2, sig))
                    self.assertGreaterEqual(int(f['term_ms']), 0)

    def test_ignored_term_forced_cleanup(self):
        code, _, _, f = self.run_case('ignore')
        self.assertEqual((code, int(f['signal'])), (2, signal.SIGKILL))
        self.assertGreaterEqual(int(f['term_ms']), 300)
        self.assertGreaterEqual(int(f['kill_ms']), 380)
        self.assertLess(int(f['reap_ms']), 500)

    def test_closed_child_output_does_not_mean_exit(self):
        code, _, _, f = self.run_case('close-live')
        self.assertEqual(code, 2)
        self.assertGreaterEqual(int(f['term_ms']), 300)

    def test_forwarding_close_retains_capture(self):
        code, _, _, f = self.run_case('fill', close=True)
        self.assertEqual(code, 2)
        self.assertGreater(int(f['stdout_bytes']), int(f['forwarded_bytes']))
        self.assertGreater((self.root / 'keyboard-attempt/observer.stdout').stat().st_size, 0)

    def test_forwarding_stall_retains_capture(self):
        code, _, _, f = self.run_case('fill', stall=True)
        self.assertEqual((code, f['reason']), (2, 'forward-close-or-stall'))
        self.assertGreater(int(f['stdout_bytes']), int(f['forwarded_bytes']))

    def test_nonzero_exit_and_stderr_refuse(self):
        for mode in ('nonzero', 'stderr'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='failure-', dir=WORK) as path:
                self.root = Path(path)
                self.assertEqual(self.run_case(mode)[0], 2)

    def test_inherited_smaller_limit_is_not_raised(self):
        code, _, _, _ = self.run_case('limit', limit=512)
        self.assertEqual(code, 2)
        self.assertEqual((self.root / 'keyboard-attempt/observer.stdout').stat().st_size, 512)

    def test_late_cancellation_cannot_accept_ram_status_alone(self):
        code, _, _, f = self.run_case('late')
        self.assertEqual((code, f['reason']), (2, 'normal-lifecycle-only'))

    def test_signal_after_default_restoration_is_nonzero(self):
        code, _, _, f = self.run_case('late-default')
        self.assertEqual((code, f['reason']), (-signal.SIGHUP, 'normal-lifecycle-only'))


if __name__ == '__main__':
    unittest.main()
