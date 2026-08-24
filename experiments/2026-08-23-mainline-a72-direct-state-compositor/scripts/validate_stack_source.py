#!/usr/bin/env python3
"""Validate the A72 direct-state stack-safety follow-up source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("core", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    membership = (
        root / "arch/arm64/kernel/mt6797_a72_membership.c"
    ).read_text(encoding="utf-8")
    start = membership.index(
        "#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR"
    )
    end = membership.index(
        "#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR", start
    )
    direct = membership[start:end]

    for token in (
        "static const struct mt6797_a72_owner_snapshot "
        "a72_direct_expected_owner",
        "struct mt6797_a72_direct_state_workspace {",
        "static struct mt6797_a72_direct_state_workspace "
        "a72_direct_workspace;",
        "struct mt6797_a72_direct_state_workspace *workspace =",
        "struct mt6797_a72_direct_state_snapshot *observed =",
        "struct mt6797_a72_owner_snapshot *owner_after =",
        "mutex_lock(&a72_transition_lock);",
        "*snapshot = *observed;",
        "out_clear:",
    ):
        require(token in direct, f"core stack requirement {token}")
    require(direct.count("memset(workspace, 0, sizeof(*workspace));") == 2,
            "workspace entry and exit scrub")
    for forbidden in (
        "const struct mt6797_a72_owner_snapshot expected =",
        "struct mt6797_a72_direct_state_snapshot observed =",
        "struct mt6797_a72_owner_snapshot owner_after;",
        "mt6797_a72_provider_snapshot(",
        "mt6797_a72_platform_state_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(", "readl(", "writel(", "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in direct, f"core forbidden token {forbidden}")

    if args.phase == "tests":
        test = (
            root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
        ).read_text(encoding="utf-8")
        state_start = test.index("struct direct_test_state {")
        state_end = test.index("\n};", state_start)
        state = test[state_start:state_end]
        for record in (
            "struct mt6797_a72_direct_state_snapshot observed;",
            "struct mt6797_a72_owner_snapshot owner_before;",
            "struct mt6797_a72_owner_snapshot owner_after;",
            "struct arm64_late_cpu_startup_snapshot p30_before;",
            "struct arm64_late_cpu_startup_snapshot p30_after;",
        ):
            require(record in state, f"KUnit heap state {record}")
        require(test.count(
            "struct mt6797_a72_direct_state_snapshot *observed = "
            "&state->observed;") == 7, "seven heap-backed observations")
        for token in (
            "state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);",
            "KUNIT_EXPECT_PTR_EQ(test,",
            "memchr_inv(snapshot, 0, sizeof(*snapshot))",
            "memcmp(&state->owner_before,",
            "&state->owner_after,",
            "memcmp(&state->p30_before,",
            "&state->p30_after,",
            "sizeof(*observed)",
        ):
            require(token in test, f"KUnit stack requirement {token}")
        for forbidden in (
            "const struct mt6797_a72_direct_state_snapshot zero =",
            "struct mt6797_a72_direct_state_snapshot observed;\n",
            "struct mt6797_a72_owner_snapshot before;\n",
            "struct mt6797_a72_owner_snapshot after;\n",
            "struct arm64_late_cpu_startup_snapshot p30_before;\n",
            "struct arm64_late_cpu_startup_snapshot p30_after;\n",
            "sizeof(observed)", "readl(", "writel(", "cpu_up(",
            "cpu_down(",
        ):
            body = test[state_end + 3:] if forbidden.endswith(";\n") else test
            require(forbidden not in body,
                    f"KUnit forbidden stack/effect token {forbidden}")
        require(test.count("KUNIT_CASE(") == 7, "focused case count")

    print("validation=a72-direct-state-stack-source")
    print(f"phase={args.phase}")
    print("production_large_stack_records=0")
    if args.phase == "tests":
        print("kunit_large_stack_records=0")
    print("physical_reader_callers=0")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
