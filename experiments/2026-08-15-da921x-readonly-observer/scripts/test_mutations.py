#!/usr/bin/env python3
"""Reject decision-changing mutations of the DA921x observer source tool."""

import subprocess
import sys
import tempfile
from pathlib import Path


EDITOR = Path(__file__).with_name("source_edits.py")
VALIDATOR = Path(__file__).with_name("validate_tool.py")

MUTATIONS = (
    ("identity gate", "identity_reads != DA9213_LEGACY_PASSES *", "false &&"),
    ("provider gate", "provider_count != DA9213_LEGACY_BUCK_COUNT", "false &&"),
    ("write evidence", "provider_read_completed=%u register_data_writes=%u ",
     "provider_read_completed=%u writes-unknown=%u "),
    ("success attribution", "da921x-observer-v1 event=bound", "provider bound"),
    ("failure coverage",
     "KUNIT_CASE(da9213_legacy_observer_bounds_read_failures)",
     "KUNIT_CASE(da9213_legacy_observer_records_both_bucks)"),
    ("cleanup coverage",
     "KUNIT_CASE(da9213_legacy_observer_invalidates_on_cleanup)",
     "KUNIT_CASE(da9213_legacy_observer_records_both_bucks)"),
    ("selector reuse", "da9213_legacy_get_voltage_sel(chip->rdev[buck])", "return 0"),
    ("enable reuse", "da9213_legacy_is_enabled(chip->rdev[buck])", "return 0"),
    ("live cleanup count", "unsigned int providers = chip->provider_count;",
     "unsigned int providers = chip->observation.provider_count;"),
    ("provider cleanup", "&chip->provider_count", "NULL"),
)


def main() -> None:
    original = EDITOR.read_text()
    rejected = 0
    for label, old, new in MUTATIONS:
        if original.count(old) != 1:
            raise SystemExit(f"mutation anchor changed for {label}: {old}")
        with tempfile.TemporaryDirectory(prefix="da921x-observer-mutation-") as tmp:
            candidate = Path(tmp) / "source_edits.py"
            candidate.write_text(original.replace(old, new, 1))
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(candidate)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if result.returncode != 0:
                rejected += 1
                continue
            raise SystemExit(f"mutation unexpectedly survived: {label}")

    print("validation=da921x-observer-mutations")
    print(f"mutations_rejected={rejected}")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
