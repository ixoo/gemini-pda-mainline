#!/usr/bin/env python3
"""Validate generated A34-v2 and P30-interlock patches."""

from __future__ import annotations

import argparse
from pathlib import Path


INTERLOCK = "0342-arm64-add-P30-pristine-bootstrap-claim.patch"
DIRECT = "0343-arm64-bind-A72-direct-state-to-target-identity.patch"
A34 = "0344-arm64-revise-A34-for-direct-state-v2.patch"


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
    interlock = (patch_dir / INTERLOCK).read_text()
    direct = (patch_dir / DIRECT).read_text()
    a34 = (patch_dir / A34).read_text()
    series = (patch_dir / "series").read_text().splitlines()

    require(series == [INTERLOCK, DIRECT, A34], "generated series order")
    require(interlock.count("diff --git ") == 3, "interlock file count")
    require(direct.count("diff --git ") == 3, "direct file count")
    require(a34.count("diff --git ") == 5, "A34 file count")
    for path in (
        "arch/arm64/include/asm/late_cpu_startup.h",
        "arch/arm64/kernel/late_cpu_startup.c",
        "arch/arm64/kernel/late_cpu_startup_test.c",
    ):
        require(path in interlock, f"interlock path {path}")
    for path in (
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "arch/arm64/kernel/mt6797_a72_direct_state_test.c",
    ):
        require(path in direct, f"direct path {path}")
    for path in (
        "arch/arm64/Kconfig",
        "arch/arm64/Kconfig.platforms",
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c",
    ):
        require(path in a34, f"A34 path {path}")

    interlock_added = added(interlock)
    direct_added = added(direct)
    a34_added = added(a34)
    require("ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI" in interlock_added,
            "interlock claim ABI")
    require("late_startup_pristine_locked" in interlock_added,
            "interlock pristine predicate")
    require("MT6797_A72_DIRECT_STATE_ABI 2" in direct_added,
            "direct-state ABI 2")
    require("get_cpu_ops(8) == &mt6797_psci_ops" in direct_added,
            "direct CPU method identity")
    require("MT6797_A72_A34_ELIGIBILITY_ABI 2" in a34_added,
            "A34 ABI 2")
    require("struct mt6797_a72_direct_state_snapshot direct;" in a34_added,
            "A34 consumes direct record")
    require("MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR" in
            a34_added, "A34 typed replay proof")

    require("MT6797_A72_DIRECT_STATE_ABI" not in interlock_added,
            "direct change leaked into interlock patch")
    require("ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI" not in direct_added,
            "interlock change leaked into direct patch")
    require("arm64_late_cpu_startup_claim_pristine(" not in a34_added,
            "A34 acquired the P30 claim")

    combined = "\n".join((interlock_added, direct_added, a34_added))
    for forbidden in (
        "Signed-off-by:", "cpu_up(", "cpu_down(", "arm_smccc_smc(",
        "readl(", "writel(", "kernel_restart(", "emergency_restart(",
        "a72_owner.health = MT6797_A72_OWNER_AVAILABLE",
        "a72_owner.phase = MT6797_A72_PHASE_IDLE",
    ):
        require(forbidden not in combined, f"forbidden added effect {forbidden}")
    for marker in (
        "default y", "CONFIG_ARM64_MT6797_A72_P24_ADMISSION_HOOKS=y",
        "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y",
    ):
        require(marker not in combined, f"publication/config marker {marker}")

    print("validation=a34-v2-interlock-generated-patches")
    print("generated_patch_count=3")
    print("interlock_changed_files=3")
    print("direct_changed_files=3")
    print("a34_changed_files=5")
    print("production_callers=0")
    print("owner_publication=false")
    print("physical_reader_binding=false")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
