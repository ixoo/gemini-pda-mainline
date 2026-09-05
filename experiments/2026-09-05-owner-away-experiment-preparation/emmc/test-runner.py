#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Disposable local process fixtures; no observer, device or network commands."""
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
R = runpy.run_path(str(HERE / 'test_packet.py'))


class BoundedRunnerTests(unittest.TestCase):
    def setUp(self):
        managed = Path(os.environ.get('EMMC_TEST_WORK_ROOT', '/tmp')).resolve(strict=True)
        if not managed.is_dir() or managed == Path('/') or any(managed.is_relative_to(Path(name)) for name in ('/dev', '/proc', '/sys')):
            raise ValueError('unsafe runner fixture work root')
        self.temp = tempfile.TemporaryDirectory(prefix='gemini-emmc-fixture-', dir=managed)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, EMMC_FIXTURE_ROOT=str(self.root))

    def run_child(self, source, timeout=0.4):
        return R['bounded_process']([sys.executable, '-c', source], self.env, timeout)

    def refuse(self, source, reason):
        start = time.monotonic()
        with self.assertRaises(R['FixtureRunError']) as failure:
            self.run_child(source)
        diagnostic = failure.exception.diagnostic
        self.assertEqual(diagnostic['reason'], reason)
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(diagnostic['fixture_cleanup_seconds'], 1)
        self.assertLessEqual(len(diagnostic['stdout_tail']), 4096)
        self.assertLessEqual(len(diagnostic['stderr_tail']), 4096)
        return diagnostic

    def test_success_retains_separate_streams(self):
        result = self.run_child('import sys; print("out"); print("err",file=sys.stderr)', 2)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, 'out\n', 'err\n'))

    def test_timeout_retains_partial_output_and_recent_trace(self):
        (self.root / 'dispatch-calls.jsonl').write_text(''.join(json.dumps({'call': n}) + '\n' for n in range(2000)))
        diagnostic = self.refuse('import time; print("partial",flush=True); time.sleep(10)', 'fixture-timeout')
        self.assertEqual(diagnostic['stdout_tail'], 'partial\n')
        self.assertEqual(len(diagnostic['recent_dispatches']), 8)
        self.assertEqual(json.loads(diagnostic['recent_dispatches'][-1]), {'call': 1999})

    def test_stream_overflow_refuses_at_finite_capture_cap(self):
        for fd, name, cap in ((1, 'stdout', 131072), (2, 'stderr', 16384)):
            with self.subTest(stream=name):
                diagnostic = self.refuse(f'import os,time; os.write({fd},b"x"*262144); time.sleep(10)', name + '-limit')
                self.assertEqual(diagnostic['captured_bytes'][name], cap)

    def test_exited_leader_with_descendant_pipe_is_reaped(self):
        marker = self.root / 'forbidden-after-cleanup'
        descendant = f'import pathlib,time; time.sleep(1.5); pathlib.Path({str(marker)!r}).write_text("orphan")'
        source = f'import subprocess,sys; subprocess.Popen([sys.executable,"-c",{descendant!r}]); print("leader",flush=True)'
        diagnostic = self.refuse(source, 'fixture-timeout')
        self.assertEqual(diagnostic['return_code'], 0)
        time.sleep(1.55)
        self.assertFalse(marker.exists())

    def test_sigterm_during_capture_or_after_pipe_close_cannot_be_success(self):
        for before in ('print("partial",flush=True)', 'os.close(1); os.close(2)'):
            with self.subTest(before=before):
                source = f'import os,signal,time; {before}; os.kill(os.getppid(),signal.SIGTERM); time.sleep(10)'
                self.refuse(source, 'fixture-interrupted-' + str(signal.SIGTERM))

    def test_ignored_sigterm_is_killed_within_cleanup_budget(self):
        source = 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print("ready",flush=True); time.sleep(10)'
        diagnostic = self.refuse(source, 'fixture-timeout')
        self.assertEqual(diagnostic['return_code'], -signal.SIGKILL)


if __name__ == '__main__':
    unittest.main(verbosity=2)
