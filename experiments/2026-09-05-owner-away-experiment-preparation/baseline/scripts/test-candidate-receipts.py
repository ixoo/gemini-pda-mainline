#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pure receipt refusal fixtures; no package, credentials, process or device I/O."""

import ast
from pathlib import Path
import runpy
import unittest


HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / "validate-candidate.py"
CHECK = runpy.run_path(str(VALIDATOR))["check_unittest_receipt"]
SUITES = {"kmsg-parser-tests.txt": 15, "kmsg-io-tests.txt": 12,
          "kmsg-seal-tests.txt": 9, "emmc-shell-tests.txt": 28, "emmc-runner-tests.txt": 6}


def receipt(count, *, elapsed="0.123", prefix=b"", verdict="OK"):
    cases = b"".join(f"test_case_{number} (__main__.Fixture) ... ok\n".encode()
                     for number in range(count))
    return prefix + cases + (f"\n{'-' * 70}\nRan {count} tests in {elapsed}s\n\n{verdict}\n").encode()


class CandidateReceiptTests(unittest.TestCase):
    def refuse(self, raw, count):
        with self.assertRaises(ValueError):
            CHECK(raw, count)

    def test_exact_five_suites_pass_with_realistic_verbose_reports(self):
        for name, count in SUITES.items():
            with self.subTest(receipt=name):
                prefix = (b"emmc_fixture_mode=exact-busybox-qemu\n"
                          b"observer_busybox_identity=fixture-dispatcher-hash\n") if name == "emmc-shell-tests.txt" else b""
                CHECK(receipt(count, prefix=prefix), count)
                CHECK(receipt(count, elapsed="1"), count)
                CHECK(receipt(count).removesuffix(b"\n"), count)

    def test_incomplete_or_additional_tests_refuse(self):
        for count in SUITES.values():
            for actual in (1, count - 1, count + 1):
                with self.subTest(wanted=count, actual=actual):
                    self.refuse(receipt(actual), count)
            self.refuse(receipt(count).replace(f"Ran {count}".encode(), f"Ran 0{count}".encode()), count)

    def test_interrupted_truncated_or_appended_reports_refuse(self):
        for count in SUITES.values():
            good = receipt(count)
            for bad in (b"", good.split(b"\nRan ")[0], good.removesuffix(b"OK\n"),
                        good + b"unexpected trailing data\n", good.replace(b"Ran ", b"prefixRan "),
                        good.replace(b"\n\nOK\n", b"\nOK\n")):
                with self.subTest(count=count, report=bad[-80:]):
                    self.refuse(bad, count)

    def test_skipped_expected_failure_and_failed_outcomes_refuse(self):
        for count in SUITES.values():
            for verdict in ("OK (skipped=1)", "OK (expected failures=1)", "FAILED (failures=1)",
                            "FAILED (errors=1)", "FAILED (unexpected successes=1)"):
                with self.subTest(count=count, verdict=verdict):
                    self.refuse(receipt(count, verdict=verdict), count)
            # A forged plain OK must not hide a failed/skipped verbose case.
            for outcome in (b"skipped 'unavailable'", b"FAIL", b"ERROR", b"expected failure", b"unexpected success"):
                with self.subTest(count=count, outcome=outcome):
                    self.refuse(receipt(count).replace(b"... ok", b"... " + outcome, 1), count)

    def test_elapsed_field_must_be_one_numeric_value(self):
        for elapsed in ("", ".", "...", "1.2.3", "-1", "NaN", "inf", "1e3", " 0.1", "0.1 "):
            with self.subTest(elapsed=elapsed):
                self.refuse(receipt(15, elapsed=elapsed), 15)

    def test_multiple_reports_cannot_be_hidden_before_a_success(self):
        for count in SUITES.values():
            good = receipt(count)
            for earlier in (good, receipt(count - 1), receipt(count, verdict="FAILED (failures=1)"),
                            receipt(count, elapsed="...")):
                with self.subTest(count=count, earlier=earlier[-80:]):
                    self.refuse(earlier + good, count)

    def test_invalid_encoding_and_input_types_refuse(self):
        self.refuse(b"\xff" + receipt(15), 15)
        self.refuse(receipt(15).decode(), 15)
        for count in (0, -1, True, "15"):
            with self.subTest(count=count):
                self.refuse(receipt(15), count)

    def test_all_five_package_receipts_use_the_shared_gate(self):
        # Check the receipt-only production section, including its real loop,
        # while refusing any new call that would require broader fixtures.
        tree = ast.parse(VALIDATOR.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "check_userspace")
        blocks = [node for node in function.body if any(
            isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
            and child.func.id == "check_unittest_receipt" for child in ast.walk(node))]
        seen = []

        def regular(path):
            self.assertEqual(path.parent, Path("fixture-package"))
            self.assertIn(path.name, SUITES)
            return path.name.encode()

        def check(raw, count):
            seen.append((raw.decode(), count))

        for node in blocks:
            for call in (part for part in ast.walk(node) if isinstance(part, ast.Call)):
                self.assertIsInstance(call.func, ast.Name)
                self.assertIn(call.func.id, {"regular", "check_unittest_receipt"})
        namespace = {"__builtins__": {}, "package": Path("fixture-package"),
                     "regular": regular, "check_unittest_receipt": check}
        exec(compile(ast.Module(body=blocks, type_ignores=[]), str(VALIDATOR), "exec"), namespace)
        self.assertEqual(sorted(seen), sorted(SUITES.items()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
