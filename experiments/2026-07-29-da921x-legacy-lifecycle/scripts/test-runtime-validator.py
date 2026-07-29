#!/usr/bin/env python3
"""Self-tests for the exact Gate 3 runtime result classifier."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("validate-runtime.py")
BASE = {
    "experiment": "2026-07-29-da921x-legacy-lifecycle",
    "kernel_release": "7.1.3-gemini-da921x-life",
    "cpu_online": "0-7",
    "cpu_offline": "8-9",
    "i2c_device": "6-0068",
    "identity_log_count": "2",
    "provider": "absent",
    "consumer": "absent",
    "automatic_reboot": "no",
    "gate3_result": "PASS",
}
COUNTERS = {
    "initial": (14, 8, 6),
    "post_unbind": (14, 8, 6),
    "post_rebind": (28, 16, 12),
}
ZERO_SUFFIXES = (
    "oracle_write_only_messages",
    "oracle_register_data_write_messages",
    "oracle_other_transfers",
    "oracle_other_address_transfers",
)


def passing_record() -> dict[str, str]:
    values = dict(BASE)
    for phase, (combined, primary, page2) in COUNTERS.items():
        values[f"{phase}_oracle_combined_pointer_reads"] = str(combined)
        values[f"{phase}_oracle_primary_pointer_reads"] = str(primary)
        values[f"{phase}_oracle_page2_pointer_reads"] = str(page2)
        for suffix in ZERO_SUFFIXES:
            values[f"{phase}_{suffix}"] = "0"
    return values


class RuntimeValidatorTests(unittest.TestCase):
    def run_case(self, values: dict[str, str]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            record = pathlib.Path(temporary) / "record.txt"
            record.write_text(
                "".join(f"{key}={value}\n" for key, value in values.items()),
                encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(record)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_exact_record_passes(self) -> None:
        result = self.run_case(passing_record())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gate3_result=PASS", result.stdout)

    def test_unbind_transaction_fails(self) -> None:
        values = passing_record()
        values["post_unbind_oracle_other_transfers"] = "1"
        result = self.run_case(values)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected '0'", result.stderr)

    def test_rebind_count_fails(self) -> None:
        values = passing_record()
        values["post_rebind_oracle_combined_pointer_reads"] = "27"
        result = self.run_case(values)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected '28'", result.stderr)


if __name__ == "__main__":
    unittest.main()
