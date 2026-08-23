#!/usr/bin/env python3
"""Validate generated A72 direct-state compositor patches."""

from __future__ import annotations

import argparse
from pathlib import Path


CORE = "0337-arm64-add-closed-A72-direct-state-compositor.patch"
TEST = "0338-arm64-test-closed-A72-direct-state-compositor.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    core = (patch_dir / CORE).read_text(encoding="utf-8")
    test = (patch_dir / TEST).read_text(encoding="utf-8")
    series = (patch_dir / "series").read_text(encoding="utf-8").splitlines()

    require(series == [CORE, TEST], "generated series order")
    require(core.count("diff --git ") == 4, "core file count")
    require(test.count("diff --git ") == 3, "test file count")
    for path in (
        "arch/arm64/Kconfig.platforms",
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "include/linux/mt6797-a72-direct-state.h",
    ):
        require(path in core, f"core path {path}")
    for path in (
        "arch/arm64/Kconfig", "arch/arm64/kernel/Makefile",
        "arch/arm64/kernel/mt6797_a72_direct_state_test.c",
    ):
        require(path in test, f"test path {path}")
    combined = added(core) + "\n" + added(test)
    for forbidden in (
        "Signed-off-by:", "mt6797_a72_provider_snapshot(",
        "mt6797_a72_platform_state_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(", "arm_smccc_smc(",
        "readl(", "writel(", "cpu_up(", "cpu_down(",
        "kernel_restart(", "emergency_restart(",
    ):
        require(forbidden not in combined, f"forbidden added effect {forbidden}")
    for required in (
        "cpus_read_lock();", "mutex_lock(&a72_transition_lock);",
        "mutex_lock(&a72_direct_source_registry_lock);",
        "memset(snapshot, 0, sizeof(*snapshot));",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST",
    ):
        require(required in combined, f"required patch token {required}")

    print("validation=a72-direct-state-generated-patches")
    print("generated_patch_count=2")
    print("core_changed_files=4")
    print("test_changed_files=3")
    print("physical_reader_callers=0")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
