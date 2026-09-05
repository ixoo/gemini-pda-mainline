#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native pure-parser tests; no /dev/kmsg, signals or Linux I/O are exercised."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent / "src/kmsg-capture.c"
HARNESS = r'''
#define KMSG_CAPTURE_NO_MAIN
#include "kmsg-capture.c"

int main(void)
{
    struct capture state = {0};
    unsigned char data[RECORD_LIMIT + 1];
    char number[64];
    while (fgets(number, sizeof(number), stdin)) {
        char *end;
        unsigned long size = strtoul(number, &end, 10);
        const char *reason;
        if (*end != '\n' || size > sizeof(data) ||
            fread(data, 1, (size_t)size, stdin) != size)
            return 2;
        reason = accept_record(&state, data, (size_t)size);
        if (reason) {
            printf("failed %s %" PRIu64 " %" PRIu64 " %zu\n",
                   reason, state.first, state.records, state.bytes);
            return 1;
        }
    }
    printf("accepted %" PRIu64 " %" PRIu64 " %" PRIu64 " %zu\n",
           state.first, state.last, state.records, state.bytes);
    return 0;
}
'''


class KmsgParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="gemini-kmsg-parser-", dir="/tmp")
        cls.addClassCleanup(cls.temp.cleanup)
        root = Path(cls.temp.name)
        harness = root / "parser.c"
        harness.write_text(HARNESS)
        cls.binary = root / "parser"
        compiler = os.environ.get("CC", "cc")
        flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic"]
        subprocess.run([compiler, *flags, "-fsyntax-only", str(SOURCE)], check=True)
        subprocess.run([compiler, *flags, "-I", str(SOURCE.parent),
                        str(harness), "-o", str(cls.binary)], check=True)

    def records(self, entries):
        frame = b"".join(str(len(entry)).encode() + b"\n" + entry for entry in entries)
        return subprocess.run([str(self.binary)], input=frame, capture_output=True, timeout=10)

    def assert_rejects(self, entries, reason):
        result = self.records(entries)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(("failed " + reason + " ").encode(), result.stdout)

    def test_contiguous_records(self):
        entries = [b"6,0,1,-;first\n", b"7,1,2,c;fragment\n", b"6,2,3,-;third\n"]
        result = self.records(entries)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"accepted 0 2 3 {sum(map(len, entries))}\n".encode())

    def test_context_lines_stay_in_one_record(self):
        entry = b"6,0,1,-;PCI probe\n SUBSYSTEM=pci\n DEVICE=+pci:0000:00\n"
        result = self.records([entry])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, f"accepted 0 0 1 {len(entry)}\n".encode())

    def test_unknown_header_extensions(self):
        result = self.records([b"6,0,18446744073709551615,x,future,,other=7;message\n"])
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_initial_gap(self):
        self.assert_rejects([b"6,1,2,-;oldest retained\n"], "initial-sequence-gap")

    def test_later_gap(self):
        self.assert_rejects([b"6,0,1,-;first\n", b"6,2,2,-;gap\n"], "sequence-gap")

    def test_duplicate(self):
        self.assert_rejects([b"6,0,1,-;first\n", b"6,0,2,-;duplicate\n"], "sequence-gap")

    def test_uint_overflow(self):
        for entry in (b"6,18446744073709551616,1,-;bad\n", b"6,0,18446744073709551616,-;bad\n"):
            with self.subTest(entry=entry):
                self.assert_rejects([entry], "malformed-header")

    def test_missing_or_negative_numbers(self):
        for entry in (b",0,1,-;bad\n", b"6,-1,1,-;bad\n", b"6,0,-1,-;bad\n", b"6,0,,1;bad\n"):
            with self.subTest(entry=entry):
                self.assert_rejects([entry], "malformed-header")

    def test_priority_range(self):
        self.assert_rejects([b"2048,0,1,-;bad\n"], "malformed-header")

    def test_missing_flags(self):
        for entry in (b"6,0,1,;bad\n", b"6,0,1,,future;bad\n"):
            self.assert_rejects([entry], "missing-flags")

    def test_control_character_in_header(self):
        self.assert_rejects([b"6,0,1,-,\t;bad\n"], "malformed-flags-or-extension")

    def test_missing_newline_or_null(self):
        for entry in (b"6,0,1,-;bad", b"6,0,1,-;bad\0\n", b""):
            self.assert_rejects([entry], "malformed-record")

    def test_missing_semicolon(self):
        self.assert_rejects([b"6,0,1,-bad\n"], "malformed-header")

    def test_record_cap(self):
        header = b"6,0,1,-;"
        self.assert_rejects([header + b"x" * (65536 - len(header)) + b"\n"], "malformed-record")

    def test_total_byte_cap(self):
        entries = []
        for sequence in range(33):
            header = f"6,{sequence},1,-;".encode()
            entries.append(header + b"x" * (65536 - len(header) - 1) + b"\n")
        result = self.records(entries[:32])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, b"accepted 0 31 32 2097152\n")
        self.assert_rejects(entries, "byte-cap")


if __name__ == "__main__":
    unittest.main(verbosity=2)
