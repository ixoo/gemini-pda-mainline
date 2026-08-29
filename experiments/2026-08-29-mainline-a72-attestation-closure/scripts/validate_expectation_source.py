#!/usr/bin/env python3
"""Validate slice 6's expected/current planning-input separation."""

from __future__ import annotations

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for offset in range(brace, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[start:offset + 1]
    raise ValidationError(f"unterminated function: {signature}")


def validate(root: Path) -> list[str]:
    header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    cpufeature = (root / "arch/arm64/kernel/cpufeature.c").read_text()
    errata = (root / "arch/arm64/kernel/cpu_errata.c").read_text()
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    require(header.count("arm64_late_cpu_expected_pair_complete(") == 1,
            "expected-pair completeness declaration count changed")
    require(header.count("arm64_late_cpu_expected_cache_type_state(") == 1,
            "expected cache-state declaration count changed")
    require("late_expected_pair_complete(" not in core,
            "private expected-pair helper name remains")
    require(core.count("arm64_late_cpu_expected_pair_complete(") == 2,
            "expected-pair helper definition/call count changed")

    complete = function(core, "arm64_late_cpu_expected_pair_complete(")
    for token in (
        "expected->abi != ARM64_LATE_CPU_EXPECTED_PAIR_ABI",
        "expected->target_count != ARM64_LATE_CPU_MAX_TARGETS",
        "expected->valid != ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK",
        "memchr_inv(expected->source_identity",
        "cpumask_weight(&plan->target_cpus)",
        "expected->capsule_identity[target]",
        "expected->mpidr[target]",
        "plan->evidence.expected_target_mpidr[target]",
        "expected->midr",
        "plan->evidence.expected_target_midr[target]",
    ):
        require(token in complete,
                f"expected-pair completeness gate absent: {token}")

    entry = function(core, "arm64_validate_late_cpu_expected_target(")
    require("arm64_late_cpu_expected_pair_complete(&late_plan)" in entry,
            "runtime entry stopped using the shared completeness gate")

    runtime_empty = function(core, "late_profile_runtime_fields_empty(")
    for token in (
        "evidence->observed_target_mpidr[target]",
        "evidence->observed_target_midr[target]",
        "evidence->observed_target_revidr[target]",
        "memchr_inv(&evidence->target_cap[target]",
        "memchr_inv(&evidence->target_policy[target]",
        "evidence->system_cap",
    ):
        require(token in runtime_empty,
                f"profile runtime-empty gate weakened: {token}")

    runtime_complete = function(core, "late_runtime_evidence_storage_complete(")
    for token in (
        "memchr_inv(&late_runtime_evidence.expected_pair",
        "late_runtime_evidence.observed_target_mpidr[target]",
        "late_runtime_evidence.observed_target_midr[target]",
        "late_runtime_evidence.observed_target_revidr[target]",
        "memchr_inv(&late_runtime_evidence.target_cap[target]",
    ):
        require(token in runtime_complete,
                f"architecture runtime target-empty gate weakened: {token}")

    prepare = function(core, "arm64_prepare_late_cpu_profile(")
    require("target_cap[" not in prepare and
            "observed_target_" not in prepare,
            "prepare gained a pre-request target observation copy")

    field_valid = function(cpufeature, "late_cpu_expected_field_valid(")
    for token in (
        "expected->abi == ARM64_LATE_CPU_EXPECTED_PAIR_ABI",
        "expected->target_count == ARM64_LATE_CPU_MAX_TARGETS",
        "field < ARM64_LATE_CPU_EXPECT_FIELD_COUNT",
        "expected->valid & ~ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK",
        "expected->valid & BIT_ULL(field)",
    ):
        require(token in field_valid,
                f"named expected-field gate absent: {token}")

    register = function(cpufeature, "late_cpu_expected_hwcap_register(")
    expected_registers = {
        "SYS_ID_AA64DFR0_EL1": "ARM64_LATE_CPU_EXPECT_AA64DFR0",
        "SYS_ID_AA64ISAR0_EL1": "ARM64_LATE_CPU_EXPECT_AA64ISAR0",
        "SYS_ID_AA64ISAR1_EL1": "ARM64_LATE_CPU_EXPECT_AA64ISAR1",
        "SYS_ID_AA64MMFR0_EL1": "ARM64_LATE_CPU_EXPECT_AA64MMFR0",
        "SYS_ID_AA64MMFR1_EL1": "ARM64_LATE_CPU_EXPECT_AA64MMFR1",
        "SYS_ID_AA64PFR0_EL1": "ARM64_LATE_CPU_EXPECT_AA64PFR0",
        "SYS_ID_AA64PFR1_EL1": "ARM64_LATE_CPU_EXPECT_AA64PFR1",
        "SYS_ID_ISAR5_EL1": "ARM64_LATE_CPU_EXPECT_A32ISAR5",
    }
    require(register.count("case SYS_") == len(expected_registers),
            "expected HWCAP register allowlist count changed")
    for sys_reg, field in expected_registers.items():
        require(register.count(f"case {sys_reg}:") == 1 and
                register.count(field) == 1,
                f"expected HWCAP field mapping changed: {sys_reg}")
    for forbidden in (
        "SYS_ID_AA64DFR1_EL1", "SYS_ID_AA64ISAR2_EL1",
        "SYS_ID_AA64ISAR3_EL1", "SYS_ID_AA64MMFR2_EL1",
        "SYS_ID_AA64MMFR3_EL1", "SYS_ID_AA64MMFR4_EL1",
        "SYS_ID_AA64PFR2_EL1", "SYS_ID_AA64ZFR0_EL1",
        "SYS_ID_AA64SMFR0_EL1", "SYS_ID_AA64FPFR0_EL1",
        "SYS_ID_ISAR6_EL1", "SYS_ID_PFR2_EL1",
        "SYS_MVFR0_EL1", "SYS_MVFR1_EL1",
    ):
        require(forbidden not in register,
                f"unmeasured register was zero-filled: {forbidden}")
    require("default:\n\t\treturn -ENOENT;" in register,
            "unknown expected HWCAP register no longer fails closed")
    require("if (!late_cpu_expected_field_valid(expected, field))\n"
            "\t\treturn -ENOENT;\n"
            "\t*value = register_value;" in register,
            "HWCAP register lookup stopped enforcing named validity")

    match_one = function(cpufeature, "late_cpu_hwcap_match_one(")
    require("const struct arm64_late_cpu_expected_pair *expected" in match_one,
            "HWCAP matcher stopped consuming the expected contract")
    require(match_one.count("late_cpu_expected_hwcap_register(") >= 3,
            "HWCAP matcher bypasses expected register lookup")
    require(match_one.count("return false;") >= 5,
            "unavailable expected HWCAP fields stopped being omitted")
    require("arm64_late_cpu_register_image" not in match_one,
            "HWCAP matcher still consumes a coarse register image")

    all_cpus = function(cpufeature, "late_cpu_hwcap_all_cpus(")
    for token in (
        "arm64_late_cpu_expected_pair_complete(plan)",
        "late_cpu_hwcap_matches(cap, NULL)",
        "late_cpu_hwcap_matches(cap, &plan->evidence.expected_pair)",
    ):
        require(token in all_cpus,
                f"expected/system HWCAP intersection gate absent: {token}")
    require("target_cap" not in all_cpus,
            "HWCAP intersection still consumes runtime target_cap")

    compat = function(cpufeature, "late_cpu_all_support_32bit_el0(")
    for token in (
        "system_supports_32bit_el0()",
        "arm64_late_cpu_expected_pair_complete(plan)",
        "late_cpu_expected_hwcap_register(expected, SYS_ID_AA64PFR0_EL1",
        "id_aa64pfr0_32bit_el0(pfr0)",
    ):
        require(token in compat,
                f"compat expected/system intersection gate absent: {token}")
    require("target_cap" not in compat,
            "compat HWCAP still consumes runtime target_cap")

    hwcaps = function(cpufeature, "arm64_plan_late_cpu_hwcaps(")
    require("arm64_late_cpu_expected_pair_complete(plan)" in hwcaps,
            "HWCAP planner no longer requires a complete expected pair")
    require("target_cap" not in hwcaps and
            "ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID" not in hwcaps,
            "HWCAP planner still treats expectation as current ID registers")

    expected_cache = function(
        errata, "arm64_late_cpu_expected_cache_type_state(")
    for token in (
        "BIT_ULL(ARM64_LATE_CPU_EXPECT_CTR)",
        "BIT_ULL(ARM64_LATE_CPU_EXPECT_CLIDR)",
        "expected->valid & ~ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK",
        "(expected->valid & required) != required",
        "expected->ctr", "expected->clidr_el1",
        "system->ctr_strict_mask", "system->ctr_sys_val",
        "ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID",
    ):
        require(token in expected_cache,
                f"expected cache planning gate absent: {token}")
    require("target_cap" not in expected_cache and
            "arm64_late_cpu_target_cap_evidence" not in expected_cache,
            "expected cache planning still claims runtime target evidence")

    classifier = function(profile, "mt6797_a72_classify_local_cap(")
    require("#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE" in classifier,
            "cache fixture/production provenance split absent")
    require("arm64_late_cpu_expected_cache_type_state(" in classifier and
            "&evidence->expected_pair" in classifier,
            "production cache planning stopped using expected fields")
    require("arm64_late_cpu_cache_type_state(" in classifier and
            "&evidence->target_cap[target]" in classifier,
            "explicit fixture cache path changed")

    unresolved = profile.split(
        "static const u16 mt6797_a72_unresolved_caps[]", 1
    )[1].split("};", 1)[0]
    for cap in (
        "ARM64_HAS_GICV5_LEGACY", "ARM64_HAS_ICH_HCR_EL2_TDIR",
        "ARM64_SPECTRE_V2", "ARM64_SPECTRE_V4", "ARM64_SPECTRE_BHB",
    ):
        require(cap in unresolved,
                f"mixed/unmeasured input was prematurely resolved: {cap}")

    profile_prepare = function(profile, "mt6797_a72_profile_prepare(")
    require("return -EAGAIN;" in profile_prepare,
            "production profile stopped fail-closing")
    require("expected_pair." not in profile_prepare and
            "target_cap[" not in profile_prepare and
            "observed_target_" not in profile_prepare,
            "production profile activated or forged target evidence")

    joined = (field_valid + register + match_one + all_cpus + compat + hwcaps +
              expected_cache + complete + profile_prepare)
    for forbidden in (
        "cpu_up(", "cpu_down(", "cpu_off(", "psci_cpu_on",
        "psci_cpu_off", "request_cpu", "ARM64_LATE_CPU_PROFILE_READY",
        "observed_target_mpidr", "observed_target_midr",
        "observed_target_revidr", "ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID",
    ):
        require(forbidden not in joined,
                f"slice 6 gained forbidden action/provenance: {forbidden}")
    require(core.count("ARM64_LATE_CPU_PROFILE_READY") == 3,
            "slice 6 changed READY publication/token paths")

    return [
        "validation=mainline-a72-slice6-expected-planning-input-pass",
        "expected_planning_input=field-valid-prior-cycle",
        "runtime_target_cap_producer=absent",
        "pure_cache_planning=expected-pair",
        "hwcap_unknown_field=omit",
        f"expected_hwcap_registers={len(expected_registers)}",
        "gic_hyp_smccc_modern_id=unresolved",
        "ready_publication=unchanged",
        "cpu_request_paths=0",
        "device_action=none",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    for line in validate(args.source_root.resolve()):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
