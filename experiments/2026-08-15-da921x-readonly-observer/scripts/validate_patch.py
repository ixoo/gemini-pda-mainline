#!/usr/bin/env python3
"""Validate the generated DA921x observer format-patch."""

import argparse
from pathlib import Path


EXPECTED_PATHS = {
    "drivers/regulator/Kconfig",
    "drivers/regulator/Makefile",
    "drivers/regulator/da9213-legacy-observer-test.c",
    "drivers/regulator/da9213-legacy-observer.h",
    "drivers/regulator/da9213-legacy-regulator.c",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    text = args.patch.read_text()
    if not text.startswith("From 0000000000000000000000000000000000000000 "):
        raise SystemExit("patch is not a zero-commit git format-patch")
    if "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" not in text:
        raise SystemExit("unexpected experiment author identity")
    if "Signed-off-by:" in text:
        raise SystemExit("synthetic experiment patch must not carry a DCO sign-off")
    paths = {
        line.split(" b/", 1)[1]
        for line in text.splitlines()
        if line.startswith("diff --git a/") and " b/" in line
    }
    if paths != EXPECTED_PATHS:
        raise SystemExit(f"generated patch path inventory changed: {sorted(paths)}")

    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for needle in (
        "da921x-observer-v1 event=bound",
        "register_data_writes",
        "da9213_legacy_observer_bounds_read_failures",
        "da9213_legacy_observer_invalidates_on_cleanup",
    ):
        if needle not in added:
            raise SystemExit(f"generated patch lost required contract: {needle}")
    for forbidden in (
        "i2c_master_send(", "i2c_smbus_write", "regmap_write(",
        "set_voltage_sel", ".enable =", ".disable =", ".set_mode =",
        ".set_current_limit =", "clk_set_", "cpu_up(", "cpu_down(",
        "arm_smccc", "psci_ops.cpu_on",
    ):
        if forbidden in added:
            raise SystemExit(f"generated patch adds state-changing operation: {forbidden}")

    print(f"patch={args.patch.name}")
    print("format_patch=passed")
    print("changed_paths=5")
    print("synthetic_signoff=absent")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
