#!/usr/bin/env python3
"""Validate the closed A72 direct-state compositor source."""

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

    header = (root / "include/linux/mt6797-a72-direct-state.h").read_text()
    membership_header = (
        root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    ).read_text()
    membership = (
        root / "arch/arm64/kernel/mt6797_a72_membership.c"
    ).read_text()
    platforms = (root / "arch/arm64/Kconfig.platforms").read_text()

    require("MT6797_A72_DIRECT_SOURCE_ABI\t1" in header, "source ABI")
    for record in (
        "mt6797_a72_provider_snapshot",
        "mt6797_a72_platform_state",
        "mt6797_dvfsp_clock_readback",
        "mt6797_bigidvfs_readback",
    ):
        require(record in header, f"source record missing {record}")
    require("MT6797_A72_DIRECT_STATE_ABI 1" in membership_header,
            "composite ABI")
    for field in (
        "cpu8_possible", "cpu9_possible", "cpu8_present", "cpu9_present",
        "cpu8_online", "cpu9_online",
    ):
        require(membership_header.count(f"u32 {field};") == 2,
                f"topology/composite field {field}")

    start = membership.index(
        "#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR"
    )
    end = membership.index(
        "#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR", start
    )
    direct = membership[start:end]
    for token in (
        "static DEFINE_MUTEX(a72_direct_source_registry_lock)",
        "cpus_read_lock();",
        "mutex_lock(&a72_transition_lock);",
        "mutex_lock(&a72_direct_source_registry_lock);",
        "a72_direct_source_ops->snapshot(",
        "mt6797_a72_direct_owner_pristine_locked",
        "memset(snapshot, 0, sizeof(*snapshot));",
        "source->provider.valid == 1",
        "source->platform.valid",
        "source->clock.sample_generation",
        "source->bigidvfs.sample_generation",
    ):
        require(token in direct, f"direct-state requirement {token}")
    production = direct[direct.index("int mt6797_a72_direct_state_snapshot("):]
    order = [
        production.index("cpus_read_lock();"),
        production.index("mutex_lock(&a72_transition_lock);"),
        production.index("mt6797_a72_direct_state_snapshot_locked("),
        production.index("mutex_unlock(&a72_transition_lock);"),
        production.index("cpus_read_unlock();"),
    ]
    require(order == sorted(order), "outer lock order")
    for forbidden in (
        "mt6797_a72_provider_snapshot(",
        "mt6797_a72_platform_state_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(", "readl(", "writel(", "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in direct, f"physical/effect call {forbidden}")
    for assignment in (
        "a72_owner.health =", "a72_owner.phase =",
        "a72_owner.bootstrap_valid =", "a72_owner.members_valid =",
        "a72_owner.next_generation =", "a72_owner.next_cookie =",
    ):
        require(assignment not in direct, f"owner mutation {assignment}")
    require("default n" in platforms[platforms.index(
        "config ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR"):],
        "compositor is not default-off")

    if args.phase == "tests":
        kconfig = (root / "arch/arm64/Kconfig").read_text()
        makefile = (root / "arch/arm64/kernel/Makefile").read_text()
        test = (
            root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
        ).read_text()
        require("config ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST" in kconfig,
                "KUnit selector")
        require("select ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR" in kconfig,
                "KUnit does not select core")
        require("mt6797_a72_direct_state_test.o" in makefile,
                "KUnit Makefile object")
        require(test.count("KUNIT_CASE(") == 7, "focused case count")
        require(test.count("case DIRECT_MUTATION_") == 15,
                "source mutation switch coverage")
        require("for (index = 0; index < 6; index++)" in test,
                "six topology mutations")
        for token in (
            "expect_zero(test, &observed)",
            "memcmp(&before, &after, sizeof(before))",
            "memcmp(&p30_before, &p30_after",
            "preflight_after, preflight_before",
            "mt6797_a72_membership_test_seed_available();",
        ):
            require(token in test, f"KUnit invariant {token}")
        for forbidden in ("readl(", "writel(", "cpu_up(", "cpu_down("):
            require(forbidden not in test, f"test effect {forbidden}")

    print("validation=a72-direct-state-source")
    print(f"phase={args.phase}")
    print("physical_reader_callers=0")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("owner_lifecycle=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
