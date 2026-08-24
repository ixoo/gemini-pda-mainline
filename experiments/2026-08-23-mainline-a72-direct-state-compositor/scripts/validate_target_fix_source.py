#!/usr/bin/env python3
"""Validate the test-only A72 preflight target correction."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve()
    membership_path = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    test_path = root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
    for path in (membership_path, test_path):
        require(path.is_file() and not path.is_symlink(),
                f"required source absent or unsafe: {path.name}")
    membership = membership_path.read_text(encoding="utf-8")
    test = test_path.read_text(encoding="utf-8")

    require("target != CPUHP_ONLINE" in membership,
            "admission API target contract changed")
    require("READ_ONCE(a72_owner.health) == MT6797_A72_OWNER_CLOSED" in
            membership and "return -EAGAIN;" in membership,
            "closed-owner admission contract changed")
    corrected = "mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE)"
    incorrect = "mt6797_a72_membership_preflight_up(8, CPUHP_OFFLINE)"
    require(test.count(corrected) == 2, "corrected preflight call count")
    require(incorrect not in test, "incorrect preflight target remains")

    start = test.index("static void direct_snapshot_success(")
    end = test.index("static void direct_registry_guards(", start)
    success = test[start:end]
    require(success.count(corrected) == 2,
            "target correction escaped success case")
    before = success.index("preflight_before =")
    compositor = success.index("mt6797_a72_direct_state_test_snapshot(")
    after = success.index("preflight_after =")
    require(before < compositor < after,
            "preservation probes no longer bracket compositor")
    require("KUNIT_EXPECT_EQ(test, preflight_before, -EAGAIN);" in success,
            "closed-owner expectation changed")
    require("KUNIT_EXPECT_EQ(test, preflight_after, preflight_before);" in
            success, "post-compositor admission preservation changed")
    require(test.count("KUNIT_CASE(") == 7, "focused case count changed")
    require("kunit_kzalloc(test, sizeof(*state), GFP_KERNEL)" in test,
            "KUnit-managed workspace removed")

    for forbidden in (
        "arm_smccc_smc(", "readl(", "writel(", "cpu_up(", "cpu_down(",
        "mt6797_a72_membership_test_seed_available();\n\tpreflight_before",
    ):
        require(forbidden not in success, f"forbidden test effect: {forbidden}")

    print("validation=a72-direct-state-target-fix-source")
    print("changed_test_calls=2")
    print("preflight_target=CPUHP_ONLINE")
    print("expected_closed_result=-EAGAIN")
    print("production_code_changes=0")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
