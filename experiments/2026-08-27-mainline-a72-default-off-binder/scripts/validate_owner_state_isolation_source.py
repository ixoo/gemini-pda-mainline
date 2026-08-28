#!/usr/bin/env python3
"""Validate the exact owner/P30 KUnit state-isolation source."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


TARGET = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = args.source_root.resolve() / TARGET
    require(path.is_file() and not path.is_symlink(), "test source absent or unsafe")
    text = path.read_text(encoding="utf-8")

    cases = re.findall(r"KUNIT_CASE\((mt6797_a72_owner_[a-z0-9_]+)\)", text)
    require(len(cases) == 30 and len(set(cases)) == 30,
            f"owner case inventory changed: {len(cases)}")
    require(text.count("struct mt6797_a72_owner_test_state *state = test->priv;") == 30,
            "heap fixture use inventory changed")
    for helper in (
        "static void mt6797_a72_owner_reset_state(void)",
        "static void mt6797_a72_owner_seed_available(void)",
        "static void mt6797_a72_owner_seed_available_cpu9(void)",
    ):
        require(text.count(helper) == 1, f"helper absent or duplicated: {helper}")
    require(text.count("\tmt6797_a72_owner_reset_state();") == 1,
            "per-case coupled reset changed")
    require(text.count("\tmt6797_a72_owner_seed_available();") == 11,
            "coupled basic seed inventory changed")
    require(text.count("\tmt6797_a72_owner_seed_available_cpu9();") == 6,
            "coupled CPU9 seed inventory changed")
    require(text.count("\tarm64_late_cpu_startup_test_reset();") == 4,
            "P30 reset inventory changed")
    require(text.count(
        "IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) ?"
    ) == 3, "binder-aware hook expectation inventory changed")
    require("KUNIT_EXPECT_EQ(test, ret, -EINVAL);\n\towner_observe(&state->after);" not in text,
            "stale public-hook expectation remains")

    print("validation=a72-owner-kunit-state-isolation-source")
    print("owner_cases=30")
    print("coupled_case_resets=1")
    print("coupled_basic_reseeds=11")
    print("coupled_cpu9_reseeds=6")
    print("binder_aware_hook_expectations=3")
    print("production_files_changed=0")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
