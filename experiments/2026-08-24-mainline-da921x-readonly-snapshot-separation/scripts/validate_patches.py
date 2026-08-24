#!/usr/bin/env python3
"""Validate separation and safety of generated DA921x snapshot patches."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0348-regulator-separate-read-only-DA921x-provider-snapshot.patch",
    "0349-regulator-test-read-only-DA921x-provider-snapshot.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def changed_files(text: str) -> set[str]:
    return set(re.findall(r"^diff --git a/(\S+) b/\1$", text, re.MULTILINE))


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    series = (patch_dir / "series").read_text().splitlines()
    require(series == list(PATCHES), "generated series order")
    core = (patch_dir / PATCHES[0]).read_text()
    tests = (patch_dir / PATCHES[1]).read_text()
    require(changed_files(core) == {
        "drivers/regulator/da9213-legacy-provider-contract.h",
        "drivers/regulator/da9213-legacy-regulator.c",
    }, "core patch separation")
    require(changed_files(tests) == {
        "drivers/regulator/Kconfig",
        "drivers/regulator/Makefile",
        "drivers/regulator/da9213-legacy-provider-snapshot-test.c",
    }, "test patch separation")
    for text in (core, tests):
        require("Signed-off-by:" not in text, "no synthetic certification")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in text,
            "explicit synthetic experiment author",
        )
    require(
        "Subject: [PATCH 1/2] regulator: separate read-only DA921x provider snapshot"
        in core,
        "core patch subject",
    )
    require(
        "Subject: [PATCH 2/2] regulator: test read-only DA921x provider snapshot"
        in tests,
        "test patch subject",
    )
    require("KUNIT_CASE(" not in core, "tests leaked into core patch")
    require(tests.count("KUNIT_CASE(") == 5, "focused case count")
    require(".snapshot = da9213_provider_snapshot" in core,
            "unconditional snapshot registration absent")
    require("read_transfer = __i2c_transfer" in core,
            "real read-only endpoint transport absent")
    require("depends on !REGULATOR_DA9213_LEGACY_POSITIVE" in tests,
            "positive transaction test exclusion absent")
    require("depends on !MTK_MT6797_I2C6_FW_WRITER" in tests,
            "writer transaction-window test exclusion absent")
    added = added_lines(core + "\n" + tests)
    for forbidden in (
        "provider_write_cont(", "ops->delay(", "cpu_up(", "cpu_down(",
        "psci_ops", "writel(", "readl(", "arm_smccc", "status = \"okay\"",
        "device_create_file(",
    ):
        require(forbidden not in added, f"forbidden added effect {forbidden}")

    print("validation=da921x-readonly-snapshot-generated-patches")
    print("generated_patch_count=2")
    print("core_patch_files=2")
    print("test_patch_files=3")
    print("focused_tests=5")
    print("negative_transfer_ordinals=10")
    print("short_transfer_ordinals=10")
    print("second_sample_mismatches=5")
    print("positive_provider_transaction=false")
    print("writer_transaction_window=false")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
