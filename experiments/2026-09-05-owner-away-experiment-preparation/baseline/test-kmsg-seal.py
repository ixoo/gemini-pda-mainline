#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise kmsg-seal with modeled files/pidfds; never signal a host process."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ALLOWED_UNDEFINED = {
    "exit", "error", "errno_location", "fprintf", "printf", "puts", "fputs", "fwrite",
    "snprintf", "memcpy", "memset", "memmove", "memcmp", "bzero", "strcmp", "strlen",
    "stderr", "stderrp", "stdout", "stdoutp", "stack_chk_fail", "stack_chk_guard",
    "chkstk_darwin", "cxa_finalize", "gmon_start", "ITM_deregisterTMCloneTable",
    "ITM_registerTMCloneTable", "libc_start_main", "dyld_stub_binder",
}


class KmsgSealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(os.environ.get("KMSG_TEST_WORK_ROOT", "/tmp")).resolve(strict=True)
        if not root.is_dir() or root == Path("/") or any(root.is_relative_to(Path(item)) for item in ("/dev", "/proc", "/sys")):
            raise RuntimeError("unsafe seal-test managed root")
        cls.temp = tempfile.TemporaryDirectory(prefix="gemini-kmsg-seal-", dir=root)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / "kmsg-seal-harness"
        subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-O2", "-DNDEBUG",
                        "-Wall", "-Wextra", "-Werror", "-pedantic", "-I", str(HERE / "src"),
                        str(HERE / "tests/kmsg-seal-harness.c"), "-o", str(cls.binary)], check=True)
        output = subprocess.run(["nm", "-u", str(cls.binary)], text=True,
                                capture_output=True, check=True).stdout
        for line in output.splitlines():
            if line.strip():
                symbol = line.split()[-1].split("@", 1)[0].lstrip("_")
                if symbol not in ALLOWED_UNDEFINED:
                    raise RuntimeError(f"unreviewed host syscall linkage: {symbol}")

    def case(self, name):
        process = subprocess.run([str(self.binary), name], text=True,
                                 capture_output=True, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn("seal model refusal", process.stderr)
        match = re.fullmatch(r"(.*?)trace_begin\n(.*?)trace_end\n", process.stdout, re.DOTALL)
        self.assertIsNotNone(match, process.stdout)
        # Any production success output before these fixture fields is a
        # failure: the real helper must remain silent on successful dispatch.
        metadata = dict(line.split("=", 1) for line in match[1].splitlines())
        self.assertEqual(set(metadata), {"return_code", "pidfd_opens", "proc_opens",
                                         "signal_attempts", "delivered", "reads"})
        self.assertLessEqual(int(metadata["reads"]), 16)
        return metadata, match[2].splitlines(), process.stderr

    def refusal(self, name, *, pidfd=0, proc=0, attempts=0):
        metadata, trace, stderr = self.case(name)
        self.assertEqual(metadata["return_code"], "1", name)
        self.assertEqual(metadata["pidfd_opens"], str(pidfd), name)
        self.assertEqual(metadata["proc_opens"], str(proc), name)
        self.assertEqual(metadata["signal_attempts"], str(attempts), name)
        self.assertEqual(metadata["delivered"], "0", name)
        self.assertIn("kmsg-seal refused:", stderr, name)
        self.assertNotIn("SIGNAL_DELIVERED", trace, name)
        return metadata, trace

    def test_matching_executable_uses_held_pidfd_once(self):
        for name in ("pass", "short-reads", "read-eintr"):
            with self.subTest(name=name):
                metadata, trace, stderr = self.case(name)
                self.assertEqual(metadata["return_code"], "0")
                self.assertEqual(metadata["pidfd_opens"], "1")
                self.assertEqual(metadata["signal_attempts"], "1")
                self.assertEqual(metadata["delivered"], "1")
                self.assertEqual(stderr, "")
                self.assertLess(trace.index("PIDFD_OPEN"), trace.index("OPEN_PROCESS_EXE"))
                self.assertLess(trace.index("STAT_PROCESS_EXE"), trace.index("PIDFD_SEND_TERM"))
                self.assertLess(trace.index("PIDFD_SEND_TERM"), trace.index("CLOSE_PIDFD"))

    def test_pid_reuse_cannot_signal_the_new_matching_process(self):
        _, trace = self.refusal("pid-reused", pidfd=1, proc=1, attempts=1)
        self.assertIn("STAT_PROCESS_EXE", trace)
        self.assertLess(trace.index("PIDFD_OPEN"), trace.index("OPEN_PROCESS_EXE"))
        self.assertLess(trace.index("PIDFD_SEND_TERM"), trace.index("CLOSE_PIDFD"))

    def test_unsupported_or_gone_process_has_no_numeric_fallback(self):
        for name in ("pidfd-unsupported", "process-gone"):
            with self.subTest(name=name):
                self.refusal(name, pidfd=1)
        for name in ("send-unsupported", "send-denied", "send-unexpected-result"):
            with self.subTest(name=name):
                self.refusal(name, pidfd=1, proc=1, attempts=1)

    def test_mismatching_or_missing_executable_is_not_signaled(self):
        for name in ("wrong-inode", "wrong-device", "proc-not-regular", "proc-missing"):
            with self.subTest(name=name):
                self.refusal(name, pidfd=1, proc=1)

    def test_untrusted_files_are_refused_before_pidfd_open(self):
        for name in ("directory-owner", "directory-mode", "pid-symlink", "pid-not-regular",
                     "pid-owner", "pid-mode", "candidate-not-regular", "candidate-owner", "candidate-mode"):
            with self.subTest(name=name):
                self.refusal(name)

    def test_malformed_or_changed_pid_file_is_refused(self):
        for name in ("pid-zero", "pid-init", "pid-negative", "pid-leading-zero", "pid-extra-line",
                     "pid-overflow", "pid-no-newline", "pid-whitespace", "pid-empty", "pid-changed-size"):
            with self.subTest(name=name):
                self.refusal(name)

    def test_read_failures_and_eintr_budget(self):
        self.refusal("read-error")
        metadata, _ = self.refusal("eintr-storm")
        self.assertEqual(metadata["reads"], "16")

    def test_arguments_cannot_select_another_target(self):
        metadata, trace, stderr = self.case("arguments")
        self.assertEqual(metadata["return_code"], "2")
        self.assertEqual(metadata["signal_attempts"], "0")
        self.assertEqual(trace, [])
        self.assertIn("takes no arguments", stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
