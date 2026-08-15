#!/usr/bin/env python3
"""Validate the deterministic DA921x observer source editor itself."""

import argparse
from pathlib import Path


REQUIRED = (
    "identity_reads != DA9213_LEGACY_PASSES *",
    "provider_count != DA9213_LEGACY_BUCK_COUNT",
    "provider_read_completed=%u register_data_writes=%u ",
    "da921x-observer-v1 event=bound",
    "KUNIT_CASE(da9213_legacy_observer_bounds_read_failures)",
    "KUNIT_CASE(da9213_legacy_observer_invalidates_on_cleanup)",
    "da9213_legacy_get_voltage_sel(chip->rdev[buck])",
    "da9213_legacy_is_enabled(chip->rdev[buck])",
    "unsigned int providers = chip->provider_count;",
    "&chip->provider_count",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("editor", type=Path)
    args = parser.parse_args()
    text = args.editor.read_text()
    for needle in REQUIRED:
        if needle not in text:
            raise SystemExit(f"source editor lost required contract: {needle}")
    for forbidden in (
        "i2c_master_send(", "i2c_smbus_write", "regmap_write(",
        "set_voltage_sel", ".enable =", ".disable =", ".set_mode =",
        ".set_current_limit =", "clk_set_", "cpu_up(", "cpu_down(",
        "arm_smccc", "psci_ops.cpu_on",
    ):
        if forbidden in text:
            raise SystemExit(f"source editor adds state-changing operation: {forbidden}")
    print("source_editor=passed")
    print("required_contracts=10")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
