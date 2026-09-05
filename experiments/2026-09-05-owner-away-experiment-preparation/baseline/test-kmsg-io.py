#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the unchanged kmsg main with modeled syscalls; never open real /dev/kmsg."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
HARNESS = HERE / "tests/kmsg-io-harness.c"
ALLOWED_UNDEFINED = {
    "abort", "exit", "error", "errno_location", "fprintf", "printf", "putchar",
    "putc", "puts", "fputs", "fwrite", "snprintf", "memchr", "memcpy", "memset",
    "memmove", "memcmp", "bzero", "strcmp", "strlen", "sigemptyset", "sigaddset",
    "sigismember", "stderr", "stderrp", "stdout", "stdoutp", "stack_chk_fail",
    "stack_chk_guard", "chkstk_darwin", "cxa_finalize", "gmon_start",
    "ITM_deregisterTMCloneTable", "ITM_registerTMCloneTable", "libc_start_main",
    "dyld_stub_binder",
}


def small_record(sequence=0):
    return f"6,{sequence},1,-;record-{sequence}\n".encode()


def large_records(count):
    result = bytearray()
    for sequence in range(count):
        header = f"6,{sequence},1,-;".encode()
        result.extend(header + b"x" * (65536 - len(header) - 1) + b"\n")
    return bytes(result)


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f"{value:016x}"


class KmsgIOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work_root = Path(os.environ.get("KMSG_TEST_WORK_ROOT", "/tmp")).resolve(strict=True)
        if not work_root.is_dir() or work_root == Path("/") or any(
            work_root.is_relative_to(Path(item)) for item in ("/dev", "/sys", "/proc")
        ):
            raise RuntimeError("unsafe managed test root")
        cls.temp = tempfile.TemporaryDirectory(prefix="gemini-kmsg-io-", dir=work_root)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / "kmsg-io-harness"
        compiler = os.environ.get("CC", "cc")
        subprocess.run([compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
                        "-I", str(HERE / "src"), str(HARNESS), "-o", str(cls.binary)], check=True)
        # Only stdio reporting, memory/string operations, pure signal-set
        # manipulation and runtime startup may remain linked to host libc.
        # Unexpected real I/O linkage fails before the harness is executed.
        symbols = subprocess.run(["nm", "-u", str(cls.binary)], text=True,
                                 capture_output=True, check=True).stdout.splitlines()
        for line in symbols:
            if not line.strip():
                continue
            symbol = line.split()[-1].split("@", 1)[0].lstrip("_")
            if symbol not in ALLOWED_UNDEFINED:
                raise RuntimeError(f"unreviewed host linkage in syscall fixture: {symbol}")

    def run_case(self, name):
        process = subprocess.run([str(self.binary), name], text=True, capture_output=True, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn("model refusal", process.stderr)
        match = re.fullmatch(r"(.*?)status_begin\n(.*?)status_end\ntrace_begin\n(.*?)trace_end\n",
                             process.stdout, re.DOTALL)
        self.assertIsNotNone(match, process.stdout)
        metadata_text, status_text, trace_text = match.groups()
        metadata = dict(line.split("=", 1) for line in metadata_text.splitlines())
        status = {}
        for line in status_text.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                self.assertNotIn(key, status)
                status[key] = value
        return metadata, status, trace_text.splitlines(), status_text

    def check(self, name, reason, data, records, *, passed=False, reads=None):
        metadata, status, trace, _ = self.run_case(name)
        self.assertEqual(metadata["return_code"], "0" if passed else "1", name)
        self.assertEqual(metadata["final_exists"], "1", name)
        self.assertEqual(metadata["publications"], "1", name)
        self.assertEqual(metadata["log_bytes"], str(len(data)), name)
        self.assertEqual(metadata["log_fnv64"], fnv(data), name)
        self.assertEqual(status["schema"], "gemini-kmsg-v1", name)
        self.assertEqual(status["sealed"], "yes", name)
        self.assertEqual(status["result"], "pass" if passed else "failed", name)
        self.assertEqual(status["reason"], reason, name)
        self.assertEqual(status["bytes"], str(len(data)), name)
        self.assertEqual(status["records"], str(records), name)
        self.assertEqual(status["first_seq"], "0", name)
        self.assertEqual(status["last_seq"], str(max(0, records - 1)), name)
        self.assertEqual(status["byte_limit"], "2097152", name)
        self.assertEqual(status["deadline_ms"], "600000", name)
        self.assertEqual(set(status), {"schema", "sealed", "result", "reason", "first_seq",
                                       "last_seq", "records", "bytes", "elapsed_ms",
                                       "byte_limit", "deadline_ms"}, name)
        if reads is not None:
            self.assertEqual(metadata["reads"], str(reads), name)
        self.assertLess(trace.index("SYNC_LOG"), trace.index("WRITE_PARTIAL"), name)
        self.assertLess(trace.index("SYNC_PARTIAL"), trace.index("LINK_FINAL"), name)
        self.assertLess(trace.index("LINK_FINAL"), trace.index("PUBLISH_FINAL_ATOMIC"), name)
        self.assertLess(trace.index("PUBLISH_FINAL_ATOMIC"), trace.index("UNLINK_PARTIAL"), name)
        self.assertFalse(any(event.startswith("READ_") for event in trace[trace.index("PUBLISH_FINAL_ATOMIC") + 1:]), name)
        return metadata, status, trace

    def test_success_and_pending_signal_drain(self):
        self.check("pass", "sealed-on-sigterm", small_record(), 1, passed=True, reads=2)
        _, _, trace = self.check("sigterm-drain", "sealed-on-sigterm",
                                 b"".join(small_record(i) for i in range(3)), 3, passed=True, reads=5)
        term = trace.index("SIGNAL_TERM")
        self.assertEqual(trace[term + 1:].count("READ_RECORD"), 2)
        self.assertLess(term, trace.index("CLOSE_KMSG"))

    def test_interruptions_are_not_promoted_by_sigterm(self):
        for name in ("interrupt", "interrupt-term", "term-interrupt", "hup"):
            with self.subTest(name=name):
                self.check(name, "interrupted", small_record(), 1)
        self.check("empty", "empty-log", b"", 0)

    def test_gaps_overrun_and_malformed_records(self):
        for name, reason, data, count in (
            ("initial-gap", "initial-sequence-gap", b"", 0),
            ("later-gap", "sequence-gap", small_record(), 1),
            ("duplicate", "sequence-gap", small_record(), 1),
            ("malformed-record", "malformed-header", b"", 0),
            ("epipe", "ring-overrun", small_record(), 1),
            ("pollerr-epipe", "ring-overrun", small_record(), 1),
        ):
            with self.subTest(name=name):
                self.check(name, reason, data, count)

    def test_exact_cap_and_over_cap(self):
        data = large_records(32)
        self.check("cap-exact", "sealed-on-sigterm", data, 32, passed=True, reads=33)
        self.check("cap", "byte-cap", data, 32, reads=33)

    def test_read_poll_clock_errors_and_deadline(self):
        self.check("read-eintr", "sealed-on-sigterm", small_record(), 1, passed=True, reads=3)
        self.check("poll-eintr", "sealed-on-sigterm", small_record(), 1, passed=True, reads=3)
        for name, reason, data, count in (
            ("read-eio", "kmsg-read-failed", small_record(), 1),
            ("read-einval", "kmsg-read-failed", small_record(), 1),
            ("read-eof", "unexpected-eof", small_record(), 1),
            ("poll-error", "poll-failed", small_record(), 1),
            ("poll-lost", "poll-device-lost", small_record(), 1),
            ("clock-error", "monotonic-clock-failed", b"", 0),
            ("clock-backward", "monotonic-clock-failed", small_record(), 1),
        ):
            with self.subTest(name=name):
                self.check(name, reason, data, count)
        _, status, _ = self.check("deadline", "deadline-expired", small_record(), 1, reads=2)
        self.assertEqual(status["elapsed_ms"], "600000")

    def test_partial_and_interrupted_writes(self):
        for name in ("log-partial", "log-eintr", "status-partial", "status-eintr"):
            with self.subTest(name=name):
                self.check(name, "sealed-on-sigterm", small_record(), 1, passed=True)
        self.check("log-partial-error", "log-write-failed", small_record()[:5], 0)
        self.check("log-zero", "log-write-failed", b"", 0)
        self.check("log-sync-error", "log-sync-failed", small_record(), 1)
        self.check("kmsg-close-error", "kmsg-close-failed", small_record(), 1)

    def test_failed_status_never_publishes_success(self):
        for name in ("status-error", "status-sync-error", "link-error"):
            with self.subTest(name=name):
                metadata, status, trace, _ = self.run_case(name)
                self.assertEqual(metadata["return_code"], "1")
                self.assertEqual(metadata["final_exists"], "0")
                self.assertEqual(metadata["partial_exists"], "1")
                self.assertEqual(metadata["publications"], "0")
                self.assertEqual(status, {})
                self.assertNotIn("PUBLISH_FINAL_ATOMIC", trace)

    def test_post_publication_failure_requires_process_status(self):
        for name in ("unlink-error", "directory-sync-error"):
            with self.subTest(name=name):
                metadata, status, _, _ = self.run_case(name)
                self.assertEqual(metadata["return_code"], "1")
                self.assertEqual(metadata["final_exists"], "1")
                self.assertEqual(status["result"], "pass")
                # This is a complete content receipt, but the main operation
                # failed. A receipt-only acceptance rule would be incorrect.
                accepted = metadata["return_code"] == "0" and status["result"] == "pass"
                self.assertFalse(accepted)

    def test_existing_evidence_and_raced_receipt_are_preserved(self):
        for name in ("log-present", "partial-present", "final-present"):
            with self.subTest(name=name):
                metadata, _, trace, text = self.run_case(name)
                self.assertEqual(metadata["return_code"], "1")
                self.assertEqual(metadata["kmsg_opens"], "0")
                self.assertNotIn("WRITE_LOG", trace)
                self.assertNotIn("WRITE_PARTIAL", trace)
                if name == "final-present":
                    self.assertEqual(text, "previous-receipt\n")
                if name == "log-present":
                    self.assertEqual(metadata["log_fnv64"], fnv(b"previous-receipt\n"))
        metadata, _, trace, text = self.run_case("link-exists")
        self.assertEqual(metadata["return_code"], "1")
        self.assertEqual(text, "previous-receipt\n")
        self.assertNotIn("PUBLISH_FINAL_ATOMIC", trace)

    def test_second_invocation_cannot_reopen_or_replace(self):
        metadata, status, trace, _ = self.run_case("second-run")
        self.assertEqual(metadata["return_code"], "0")
        self.assertEqual(metadata["second_return_code"], "1")
        self.assertEqual(metadata["publications"], "1")
        self.assertEqual(metadata["kmsg_opens"], "1")
        self.assertEqual(metadata["log_fnv64"], fnv(small_record()))
        self.assertEqual(status["records"], "1")
        after = trace[trace.index("SECOND_INVOCATION") + 1:]
        self.assertNotIn("OPEN_KMSG_READONLY", after)
        self.assertNotIn("WRITE_LOG", after)
        self.assertNotIn("WRITE_PARTIAL", after)

    def test_owner_mode_and_device_refusals(self):
        for name in ("bad-owner", "bad-mode"):
            with self.subTest(name=name):
                metadata, status, _, _ = self.run_case(name)
                self.assertEqual(metadata["return_code"], "1")
                self.assertEqual(metadata["kmsg_opens"], "0")
                self.assertEqual(status, {})
        self.check("non-character-device", "kmsg-not-character-device", b"", 0, reads=0)
        self.check("kmsg-open-error", "kmsg-open-failed", b"", 0, reads=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
