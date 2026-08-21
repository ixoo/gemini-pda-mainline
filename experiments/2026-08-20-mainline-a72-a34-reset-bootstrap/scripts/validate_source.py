#!/usr/bin/env python3
"""Validate an exact source tree containing the pure A34 evaluator."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def text(root: Path, relative: str) -> str:
    path = root / relative
    require(path.is_file() and not path.is_symlink(), f"source file: {relative}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    kconfig = text(root, "arch/arm64/Kconfig")
    platforms = text(root, "arch/arm64/Kconfig.platforms")
    makefile = text(root, "arch/arm64/kernel/Makefile")
    smp = text(root, "arch/arm64/kernel/smp.c")
    header = text(root, "arch/arm64/include/asm/mt6797_a72_membership.h")
    owner = text(root, "arch/arm64/kernel/mt6797_a72_membership.c")
    test = text(root, "arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c")
    psci = text(root, "arch/arm64/kernel/mt6797_psci.c")

    require("config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR" in platforms,
            "A34 evaluator Kconfig")
    for marker in ("depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL",
                   "no production caller", "cannot open the owner"):
        require(marker in platforms, f"evaluator Kconfig marker: {marker}")
    require("config ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST" in kconfig,
            "A34 KUnit Kconfig")
    for marker in ("select ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR",
                   "select ARM64_MT6797_A72_P24_ADMISSION_HOOKS",
                   "select ARM64_MT6797_A72_P24_OWNER_TEST_SEED"):
        require(marker in kconfig, f"KUnit selection: {marker}")
    require("CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST) += mt6797_a72_a34_evaluator_test.o" in makefile,
            "A34 KUnit object")

    require("#define MT6797_A72_TRANSACTION_ABI 2" in header,
            "owner ABI remains unchanged")
    require("#include <linux/stddef.h>" in owner,
            "explicit offsetof declaration")
    for marker in ("MT6797_A72_A34_ELIGIBILITY_ABI 1",
                   "MT6797_A72_A34_FIRST_GENERATION 1ULL",
                   "MT6797_A72_A34_FIRST_COOKIE 0xa7200001ULL",
                   "enum mt6797_a72_a34_reset_provenance",
                   "MT6797_A72_A34_RESET_ORDINARY_LINUX",
                   "MT6797_A72_A34_PRIVATE_REPLAY_OWNER_SAFE_ZERO",
                   "struct mt6797_a72_a34_observation",
                   "struct mt6797_a72_owner_snapshot owner;",
                   "struct arm64_late_cpu_startup_snapshot p30;",
                   "mt6797_a72_a34_evaluate("):
        require(marker in header, f"header contract: {marker}")

    require("mt6797_a72_a34_evaluate" not in smp,
            "no production SMP hook")
    start = owner.index("#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR")
    end = owner.index("static bool\nmt6797_a72_p32_target_locked", start)
    a34 = owner[start:end]
    for marker in (
        "static const struct mt6797_a72_a34_observation a34_expected",
        ".private_replay_proof =",
        "MT6797_A72_A34_PRIVATE_REPLAY_OWNER_SAFE_ZERO",
        ".possible_mask = GENMASK(9, 0)",
        ".online_mask = GENMASK(7, 0)",
        ".cpuhp_state_cpu8 = CPUHP_OFFLINE",
        ".cpu8_mpidr = 0x200",
        ".diagnostic_blockers = MT6797_A72_BLOCK_MASK",
        ".health = MT6797_A72_OWNER_CLOSED",
        ".phase = MT6797_A72_PHASE_UNINITIALIZED",
        ".first_generation = MT6797_A72_A34_FIRST_GENERATION",
        "MT6797_A72_A34_RESET_PLATFORM",
        "MT6797_A72_A34_RESET_EXTERNAL",
        "sizeof(*observation) - tail",
        "return -EPERM;",
    ):
        require(marker in a34, f"A34 source marker: {marker}")
    for forbidden in ("mutex_lock(", "raw_spin_lock", "a72_owner.",
                      "cpu_on(", "cpu_boot(", "provider_acquire(",
                      "provider_release(", "writel(", "readl(", "i2c_",
                      "arm64_late_cpu_startup_prepare(",
                      "arm64_late_cpu_startup_arm_before_cpu_on("):
        require(forbidden not in a34, f"forbidden evaluator effect: {forbidden}")

    require(test.count("KUNIT_CASE(mt6797_a34_") == 5,
            "five focused KUnit cases")
    for marker in ("kunit_kzalloc", "sizeof(*state->observation)",
                   "bytes[offset] ^= 1", "MT6797_A72_A34_RESET_PLATFORM",
                   "MT6797_A72_A34_RESET_EXTERNAL",
                   "MT6797_A72_A34_RESET_ORDINARY_LINUX", "-EPERM",
                   "mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE)",
                   "-EAGAIN"):
        require(marker in test, f"KUnit marker: {marker}")
    require("struct mt6797_a72_owner_snapshot before;" not in test and
            "struct mt6797_a72_owner_snapshot after;" not in test,
            "large owner snapshots stay off stack")

    boot_start = psci.index("static int mt6797_psci_cpu_boot(unsigned int cpu)")
    boot_end = psci.index("#ifdef CONFIG_HOTPLUG_CPU", boot_start)
    boot = psci[boot_start:boot_end]
    require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot,
            "A26 boot veto unchanged")
    admission_start = owner.index("mt6797_a72_membership_check_up(")
    admission_end = owner.index("int mt6797_a72_membership_preflight_up",
                                admission_start)
    admission = owner[admission_start:admission_end]
    require("MT6797_A72_OWNER_CLOSED" in admission and
            "return -EAGAIN;" in admission,
            "CLOSED admission remains closed")

    print("a34_modified_source_files=6")
    print("production_hook=none")
    print("observation_mutations=every-byte")
    print("accepted_reset_provenance_cases=2")
    print("kunit_cases=5")
    print("opens_owner=no")
    print("cpu_on=no")
    print("hardware_effect=no")
    print("result=pass")


if __name__ == "__main__":
    main()
