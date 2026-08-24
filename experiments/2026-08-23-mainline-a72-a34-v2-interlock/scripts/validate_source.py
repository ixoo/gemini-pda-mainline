#!/usr/bin/env python3
"""Validate the cumulative A34-v2 and P30-interlock source phases."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def validate_interlock(root: Path) -> None:
    header = (root / "arch/arm64/include/asm/late_cpu_startup.h").read_text()
    source = (root / "arch/arm64/kernel/late_cpu_startup.c").read_text()
    test = (root / "arch/arm64/kernel/late_cpu_startup_test.c").read_text()

    for token in (
        "#define ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI 1",
        "struct arm64_late_cpu_bootstrap_claim {",
        "\tu32 abi;",
        "\tu32 reserved;",
        "\tu64 cookie;",
        "arm64_late_cpu_startup_claim_pristine(",
        "arm64_late_cpu_startup_release_pristine(",
    ):
        require(token in header, f"P30 header token {token}")
    snapshot = section(
        header,
        "struct arm64_late_cpu_startup_snapshot {",
        "\n};\n\n#define ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI 1",
    )
    require("bootstrap_claim" not in snapshot,
            "bootstrap claim leaked into public P30 snapshot")

    for token in (
        "u64 bootstrap_claim_cookie;",
        "u64 next_bootstrap_claim_cookie;",
        "static bool late_startup_pristine_locked(void)",
        "late_startup.bootstrap_claim_cookie = cookie;",
        "claim->abi = ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI;",
        "claim->cookie = cookie;",
        "claim->cookie != late_startup.bootstrap_claim_cookie",
        "late_startup.bootstrap_claim_cookie = 0;",
        "*claim = (struct arm64_late_cpu_bootstrap_claim){};",
    ):
        require(token in source, f"P30 interlock token {token}")
    pristine = section(
        source,
        "static bool late_startup_pristine_locked(void)",
        "\nint arm64_late_cpu_startup_claim_pristine(",
    )
    for token in (
        "ARM64_LATE_CPU_STARTUP_FREE",
        "late_startup.bootstrap_claim_cookie",
        "late_startup.token",
        "late_startup.retired_token[i]",
        "late_startup.quarantine_token",
        "late_startup.terminal",
        "late_startup.success_effects",
        "late_startup.quarantined",
        "late_startup.retired_mask",
        "late_startup.completion_consumed",
        "late_startup.online_validated",
        "late_startup.park_committed",
        "late_startup.stuck_interlock",
    ):
        require(token in pristine, f"pristine predicate {token}")
    prepare = section(
        source,
        "int arm64_late_cpu_startup_prepare(",
        "\nint arm64_late_cpu_startup_abort_unissued(",
    )
    require("if (late_startup.bootstrap_claim_cookie)" in prepare,
            "prepare does not honor bootstrap claim")
    require(prepare.index("if (late_startup.bootstrap_claim_cookie)") <
            prepare.index("atomic_read(&late_startup.state)"),
            "claim exclusion is after the state transition check")
    for forbidden in (
        "cpu_up(", "cpu_down(", "arm_smccc_smc(", "readl(", "writel(",
        "kernel_restart(", "emergency_restart(",
    ):
        require(forbidden not in pristine, f"P30 interlock effect {forbidden}")

    for name in (
        "late_cpu_startup_bootstrap_claim_excludes_prepare_test",
        "late_cpu_startup_bootstrap_claim_identity_test",
        "late_cpu_startup_bootstrap_claim_rejects_nonpristine_test",
    ):
        require(f"KUNIT_CASE({name})" in test, f"P30 KUnit case {name}")
    require(test.count("KUNIT_CASE(") == 20, "P30 focused case count")


def validate_direct(root: Path) -> None:
    header = (
        root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    ).read_text()
    source = (root / "arch/arm64/kernel/mt6797_a72_membership.c").read_text()
    test = (
        root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
    ).read_text()

    require("#define MT6797_A72_DIRECT_STATE_ABI 2" in header,
            "direct-state ABI 2")
    direct_header = section(
        header,
        "#define MT6797_A72_DIRECT_STATE_ABI 2",
        "\n#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR",
    )
    for field in (
        "cpu8_possible", "cpu9_possible", "cpu8_present", "cpu9_present",
        "cpu8_online", "cpu9_online", "cpu8_method_valid",
        "cpu9_method_valid",
    ):
        require(direct_header.count(f"u32 {field};") == 2,
                f"direct topology/snapshot field {field}")
    for field in ("cpu8_mpidr", "cpu9_mpidr"):
        require(direct_header.count(f"u64 {field};") == 2,
                f"direct topology/snapshot field {field}")

    direct = section(
        source,
        "#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR",
        "\n#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR",
    )
    for token in (
        "#include <asm/cpu_ops.h>",
        "extern const struct cpu_operations mt6797_psci_ops;",
        "topology->cpu8_method_valid == 1",
        "topology->cpu9_method_valid == 1",
        "topology->cpu8_mpidr == 0x200",
        "topology->cpu9_mpidr == 0x201",
        "get_cpu_ops(8) == &mt6797_psci_ops",
        "get_cpu_ops(9) == &mt6797_psci_ops",
        "cpu_logical_map(8)",
        "cpu_logical_map(9)",
    ):
        require(token in source, f"direct identity token {token}")
    for forbidden in (
        "arm_smccc_smc(", "readl(", "writel(", "cpu_up(", "cpu_down(",
        "arm64_late_cpu_startup_claim_pristine(",
    ):
        require(forbidden not in direct, f"direct-state effect {forbidden}")
    require("for (index = 0; index < 10; index++)" in test,
            "ten direct topology mutations")
    for token in (
        ".cpu8_method_valid = 1", ".cpu9_method_valid = 1",
        ".cpu8_mpidr = 0x200", ".cpu9_mpidr = 0x201",
    ):
        require(token in test, f"direct KUnit identity {token}")


def validate_a34(root: Path) -> None:
    header = (
        root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    ).read_text()
    source = (root / "arch/arm64/kernel/mt6797_a72_membership.c").read_text()
    test = (
        root / "arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c"
    ).read_text()
    kconfig = (root / "arch/arm64/Kconfig").read_text()
    platforms = (root / "arch/arm64/Kconfig.platforms").read_text()

    require("#define MT6797_A72_A34_ELIGIBILITY_ABI 2" in header,
            "A34 ABI 2")
    for obsolete in (
        "MT6797_A72_A34_FIRST_GENERATION",
        "MT6797_A72_A34_FIRST_COOKIE",
        "mt6797_a72_a34_reset_provenance",
        "mt6797_a72_a34_private_replay_proof",
    ):
        require(obsolete not in header, f"obsolete A34 ABI token {obsolete}")
    observation = section(
        header,
        "struct mt6797_a72_a34_observation {",
        "\n};\n\n#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR",
    )
    require("struct mt6797_a72_direct_state_snapshot direct;" in observation,
            "A34 direct-state record")
    require("struct mt6797_a72_a34_replay replay;" in observation,
            "A34 replay record")
    for duplicate in (
        "possible_count", "present_count", "online_count", "possible_mask",
        "present_mask", "online_mask", "owner_next_generation",
        "owner_next_cookie", "first_generation", "first_cookie",
        "arm64_late_cpu_startup_snapshot",
    ):
        require(duplicate not in observation,
                f"duplicated A34 caller field {duplicate}")

    a34 = section(
        source,
        "#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR",
        "\n#endif\n\nstatic bool\nmt6797_a72_p32_target_locked",
    )
    for token in (
        "MT6797_A72_DIRECT_STATE_ABI",
        "MT6797_A72_A34_REPLAY_ABI",
        "MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR",
        "memcmp(observation, &a34_expected, sizeof(*observation))",
    ):
        require(token in a34, f"A34 exact predicate {token}")
    for forbidden in (
        "offsetof(", "mt6797_a72_direct_state_snapshot(",
        "arm64_late_cpu_startup_claim_pristine(", "cpu_up(", "cpu_down(",
        "arm_smccc_smc(", "readl(", "writel(",
    ):
        require(forbidden not in a34, f"A34 caller/effect {forbidden}")
    require(test.count("KUNIT_CASE(") == 5, "A34-v2 focused case count")
    for token in (
        "mt6797_a34_every_byte_mutation_test",
        "mt6797_a34_missing_replay_test",
        "mt6797_a34_admission_remains_closed_test",
        "kunit_kzalloc(",
    ):
        require(token in test, f"A34 KUnit invariant {token}")
    require("primary-BL31 replay" in kconfig, "A34 KUnit help")
    require("direct-state-v2" in platforms, "A34 platform help")
    require("default y" not in platforms[platforms.index(
        "config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR"):],
        "A34 evaluator became default-on")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("interlock", "direct", "a34"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()

    validate_interlock(root)
    if args.phase in ("direct", "a34"):
        validate_direct(root)
    if args.phase == "a34":
        validate_a34(root)

    print("validation=a34-v2-interlock-source")
    print(f"phase={args.phase}")
    print("production_callers=0")
    print("owner_lifecycle=closed")
    print("physical_reader_binding=false")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
