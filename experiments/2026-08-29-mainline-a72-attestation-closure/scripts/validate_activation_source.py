#!/usr/bin/env python3
"""Validate the named-device expected-pair activation and retained blocker."""

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


def block(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def validate(root: Path) -> list[str]:
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    expectation = block(
        profile,
        "static const struct arm64_late_cpu_expected_pair "
        "mt6797_a72_expected_pair __initconst = {",
        "\n};\n#endif",
    )
    for token in (
        ".abi = ARM64_LATE_CPU_EXPECTED_PAIR_ABI",
        ".target_count = ARM64_LATE_CPU_MAX_TARGETS",
        ".valid = ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK,",
        "0x04bd7f060613719e", "0x7836415f9dfbbc19",
        "0xdc1d97ee847eb811", "0xf765c5e8a01667cc",
        "0xe35596c52bc8b40b", "0x600c5e2d6733661d",
        ".mpidr = { 0x200, 0x201 }",
        ".midr = MIDR_CORTEX_A72", ".revidr = 0",
        ".cntfrq = 0x00c65d40", ".ctr = 0x8444c004",
        ".dczid = 0x00000004", ".clidr_el1 = 0x000000000a200023",
        ".id_aa64dfr0 = 0x0000000010305106",
        ".id_aa64isar0 = 0x0000000000011120",
        ".id_aa64isar1 = 0x0000000000000000",
        ".id_aa64mmfr0 = 0x0000000000001124",
        ".id_aa64mmfr1 = 0x0000000000000000",
        ".id_aa64pfr0 = 0x0000000001002222",
        ".id_aa64pfr1 = 0x0000000000000000",
        ".id_isar0 = 0x02101110", ".id_isar1 = 0x13112111",
        ".id_isar2 = 0x21232042", ".id_isar3 = 0x01112131",
        ".id_isar4 = 0x00011142", ".id_isar5 = 0x00011121",
        ".id_mmfr0 = 0x10201105", ".id_mmfr1 = 0x40000000",
        ".id_mmfr2 = 0x01260000", ".id_mmfr3 = 0x02102211",
        ".id_pfr0 = 0x00000131", ".id_pfr1 = 0x10011011",
    ):
        require(expectation.count(token) == 1,
                f"exact expected-pair field changed: {token}")
    require("Prior-cycle Gemian capsule stream" in profile and
            "never a current-boot observation" in profile,
            "prior-cycle provenance boundary is not explicit")
    require(expectation.count(".id_") == 19,
            "expected named register initializer count changed")
    for forbidden in (
        "target_cap", "observed_target_", "ID_REGS_VALID",
        "smccc_wa", "asid_bits", "page_shift", "va_bits",
        "icc_", "ich_", "hyp_",
    ):
        require(forbidden not in expectation,
                f"expected pair gained current/unmeasured input: {forbidden}")

    blocker_def = block(
        profile,
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "#define MT6797_A72_PROFILE_BLOCKERS",
        "\n#endif\n\nstatic const u64 mt6797_a72_source_parent_identity",
    )
    production_blockers = blocker_def.split("#else\n", 1)[1]
    require(production_blockers.count(
                "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS") == 1,
            "final attestation-users blocker is not retained exactly once")
    require(production_blockers.count(
                "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING") == 1,
            "runtime binding is not retained until the core merge")
    for forbidden in (
        "BLOCK_SOURCE_IDENTITY", "BLOCK_FIRMWARE_WA", "BLOCK_ID_REGISTERS",
        "BLOCK_CACHE_TYPE", "BLOCK_ASID", "BLOCK_GRANULE", "BLOCK_VA_MODE",
        "BLOCK_GIC", "BLOCK_HWCAP", "BLOCK_EFFECT_PLAN", "BLOCK_COMMIT_PATH",
    ):
        require(forbidden not in production_blockers,
                f"owned blocker remains in production baseline: {forbidden}")

    present = block(
        profile, "static const u16 mt6797_a72_present_caps[]", "\n};")
    required = block(
        profile, "static const u16 mt6797_a72_required_caps[]", "\n};")
    resolved_caps = (
        "ARM64_MISMATCHED_CACHE_TYPE", "ARM64_SPECTRE_V2",
        "ARM64_SPECTRE_V4", "ARM64_SPECTRE_BHB",
    )
    for cap in resolved_caps:
        require(present.count(cap) == 1 and required.count(cap) == 1,
                f"expected-planned capability not active: {cap}")
    require("mt6797_a72_unresolved_caps" not in profile,
            "old dormant unresolved-capability list remains")

    binding = function(profile, "mt6797_a72_binding_is_runtime(")
    require("binding->origin == ARM64_LATE_CPU_BINDING_RUNTIME" in binding,
            "binding helper no longer requires current runtime origin")
    require("ARM64_LATE_CPU_BINDING_FIXTURE" not in binding,
            "binding helper accepts fixture origin")
    require(binding.count("!memcmp(") == 3,
            "runtime binding identity equality inventory changed")

    system = function(profile, "mt6797_a72_system_evidence_exact(")
    for token in (
        "ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK",
        "~GENMASK_ULL(15, 14)", "GENMASK_ULL(31, 0)", "BIT(31)",
        "ARM64_LATE_CPU_MITIGATION_UNAFFECTED",
        "ARM64_LATE_CPU_BHB_STATE_UNAFFECTED",
        "!system->gicv5_legacy", "!system->ich_hcr_tdir",
    ):
        require(token in system, f"current-system exact gate changed: {token}")
    for forbidden in ("0xb4448004", "read_sysreg", "target_cap"):
        require(forbidden not in system,
                f"current-system gate gained prior-cycle/current-target input: {forbidden}")

    policy = function(profile, "mt6797_a72_policy_evidence_exact(")
    for token in (
        "ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK",
        "ARM64_LATE_CPU_SMCCC_SMC", "!policy->mitigations_off",
        "!policy->nospectre_v2", "ARM64_LATE_CPU_V4_POLICY_DYNAMIC",
    ):
        require(token in policy, f"current-policy exact gate changed: {token}")

    evidence = function(profile, "mt6797_a72_evidence_is_bound_expectation(")
    for token in (
        "memcmp(&evidence->expected_pair, &mt6797_a72_expected_pair",
        "mt6797_a72_binding_is_runtime(&evidence->binding)",
        "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS",
        "evidence->blocker_mask & ~allowed_blockers",
        "mt6797_a72_system_evidence_exact(&evidence->system_cap)",
        "memchr_inv(&evidence->target_cap[target], 0,",
        "mt6797_a72_policy_evidence_exact(",
        "memcmp(&evidence->target_policy[0]",
    ):
        require(token in evidence, f"bound-expectation gate changed: {token}")
    require(evidence.count("observed_target_") == 3,
            "current target observation emptiness inventory changed")
    for forbidden in (
        "ARM64_LATE_CPU_BINDING_FIXTURE", "target_cap[target].valid",
        "ID_REGS_VALID", "evidence->expected_pair =",
    ):
        require(forbidden not in evidence,
                f"bound expectation conflates evidence origin: {forbidden}")

    prepare = function(profile, "mt6797_a72_profile_prepare(")
    freeze = "evidence->expected_pair = mt6797_a72_expected_pair;"
    blocker = "evidence->blocker_mask = MT6797_A72_PROFILE_BLOCKERS;"
    require(freeze in prepare and prepare.index(freeze) < prepare.index(blocker),
            "expected pair is not frozen before blocker/planning handoff")
    require(prepare.count(freeze) == 1,
            "expected pair producer count changed")
    for forbidden in (
        "observed_target_", "target_cap[", "ARM64_LATE_CPU_PROFILE_READY",
        "cpu_up(", "cpu_down(", "cpu_off(", "psci_cpu_on", "psci_cpu_off",
        "boot2",
    ):
        require(forbidden not in prepare,
                f"activation prepare gained runtime/device action: {forbidden}")

    validate_plan = function(profile, "mt6797_a72_validate_cap_plan(")
    production = validate_plan.split(
        "#else\n\tif (!plan->local_caps_planned", 1)[1].split("#endif", 1)[0]
    for token in (
        "!plan->effects_planned", "!plan->hwcaps_planned",
        "mt6797_a72_evidence_is_bound_expectation",
        "mt6797_a72_effects_empty", "!memchr_inv(plan->expected_elf_hwcap",
    ):
        require(token in production,
                f"activated production plan gate changed: {token}")
    require("return -EAGAIN" not in validate_plan and
            validate_plan.rstrip().endswith("return 0;\n}"),
            "production plan validation remains dormant")

    profile_decl = block(
        profile, "static const struct arm64_late_cpu_profile mt6797_a72_profile",
        "\n};")
    for forbidden in (".verify_system", ".finalize_user"):
        require(forbidden not in profile_decl,
                f"activation slice crossed into READY finalization: {forbidden}")
    for forbidden in (
        "ARM64_LATE_CPU_PROFILE_READY", "arm64_get_late_cpu_ready_token",
        "cpu_up(", "cpu_down(", "cpu_off(", "psci_cpu_off", "boot2",
    ):
        require(forbidden not in profile,
                f"profile gained forbidden READY/device action: {forbidden}")

    return [
        "expected_pair_source=capsule-stream-sha256",
        "expected_pair_valid_fields=28",
        "expected_pair_targets=cpu8,cpu9",
        "current_target_evidence=empty",
        "planning_state=active",
        "clean_path_blocker_mask=0x2000",
        "remaining_blocker=attestation-users",
        "ready_publication=absent",
        "cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
        "device_action=none",
        "boot_candidate=false",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        markers = validate(args.source_root.resolve())
    except (OSError, ValueError, ValidationError) as exc:
        print(f"validation failed: {exc}")
        return 1
    for marker in markers:
        print(marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
