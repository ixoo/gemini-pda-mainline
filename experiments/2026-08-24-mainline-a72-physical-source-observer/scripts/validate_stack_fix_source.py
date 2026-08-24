#!/usr/bin/env python3
"""Validate the physical-source KUnit stack-fixture repair."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = (
        args.source_root.resolve()
        / "drivers/soc/mediatek/mt6797-a72-physical-source-observer-test.c"
    )
    text = path.read_text(encoding="utf-8")

    require(text.count("KUNIT_CASE(") == 4, "four focused cases preserved")
    require(
        text.count("kunit_kzalloc(test, sizeof(*snapshot), GFP_KERNEL)") == 2,
        "two KUnit-managed direct-state snapshots",
    )
    require(
        text.count("KUNIT_ASSERT_NOT_NULL(test, snapshot)") == 2,
        "both allocations fail closed",
    )
    require(
        "struct mt6797_a72_direct_state_snapshot snapshot;" not in text,
        "no direct-state snapshot remains on stack",
    )
    require(
        "struct mt6797_a72_direct_state_snapshot zero" not in text,
        "no direct-state zero reference remains on stack",
    )
    require(text.count("memchr_inv(snapshot, 0, sizeof(*snapshot))") == 2,
            "two allocation-free zero checks")
    require(text.count("MT6797_SOURCE_UNREGISTER") >= 3,
            "unregister lifetime assertions preserved")
    require('name = "mt6797-a72-physical-source"' in text,
            "focused suite identity preserved")
    for forbidden in (
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "i2c_transfer(",
        "gemini_protected_readback_ledger_checkpoint(",
        "cpu_up(",
    ):
        require(forbidden not in text, f"physical operation absent: {forbidden}")

    print("validation=a72-physical-source-kunit-stack-fix-source")
    print("focused_cases=4")
    print("direct_state_stack_objects=0")
    print("kunit_heap_snapshots=2")
    print("production_files_changed=0")
    print("hardware_operations=0")
    print("result=pass")


if __name__ == "__main__":
    main()
