#!/usr/bin/env python3
"""Validate the slice-4 pure planner and canonical identities."""

from __future__ import annotations

import argparse
import re
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
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    cpufeature = (root / "arch/arm64/kernel/cpufeature.c").read_text()
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    require("\tu8 hwcaps_planned;\n" in header,
            "HWCAP planning completion bit absent")
    require(header.count("arm64_plan_late_cpu_hwcaps(") == 1,
            "HWCAP planner declaration count changed")
    require("Core-owned SHA-256 over named fields" in header,
            "canonical identity ownership comment absent")

    register_map = function(cpufeature, "late_cpu_hwcap_register(")
    hwcap_match = function(cpufeature, "late_cpu_hwcap_match_one(")
    all_cpus = function(cpufeature, "late_cpu_hwcap_all_cpus(")
    compat_cpus = function(
        cpufeature, "late_cpu_plan_all_cpus_support_32bit_el0(")
    hwcap_plan = function(cpufeature, "arm64_plan_late_cpu_hwcaps(")
    mappings = (
        "SYS_ID_AA64DFR0_EL1", "SYS_ID_AA64DFR1_EL1",
        "SYS_ID_AA64ISAR0_EL1", "SYS_ID_AA64ISAR1_EL1",
        "SYS_ID_AA64ISAR2_EL1", "SYS_ID_AA64ISAR3_EL1",
        "SYS_ID_AA64MMFR0_EL1", "SYS_ID_AA64MMFR1_EL1",
        "SYS_ID_AA64MMFR2_EL1", "SYS_ID_AA64MMFR3_EL1",
        "SYS_ID_AA64MMFR4_EL1", "SYS_ID_AA64PFR0_EL1",
        "SYS_ID_AA64PFR1_EL1", "SYS_ID_AA64PFR2_EL1",
        "SYS_ID_AA64ZFR0_EL1", "SYS_ID_AA64SMFR0_EL1",
        "SYS_ID_AA64FPFR0_EL1", "SYS_ID_ISAR5_EL1",
        "SYS_ID_ISAR6_EL1", "SYS_ID_PFR2_EL1", "SYS_MVFR0_EL1",
        "SYS_MVFR1_EL1",
    )
    for token in mappings:
        require(register_map.count(f"case {token}:") == 1,
                f"target register mapping changed: {token}")
    for token in (
        "read_sanitised_ftr_reg(cap->sys_reg)",
        "late_cpu_hwcap_field_visible(cap)",
        "feature_matches(value, cap)",
        "cap->matches == compat_has_neon",
        "sve_match = cap->matches == has_sve_feature",
        "sme_match = cap->matches == has_sme_feature",
    ):
        require(token in hwcap_match, f"HWCAP matcher gate absent: {token}")
    for forbidden in ("read_sysreg_s", "read_sysreg(", "SCOPE_LOCAL_CPU",
                      "raw_smp_processor_id", "smp_processor_id"):
        require(forbidden not in hwcap_match + all_cpus + hwcap_plan,
                f"HWCAP planner probes a live local CPU: {forbidden}")
    require("late_cpu_hwcap_matches(cap, NULL)" in all_cpus,
            "sanitized system HWCAP comparison absent")
    require(all_cpus.count("ARM64_LATE_CPU_MAX_TARGETS") == 1 and
            "plan->evidence.target_cap[target].registers" in all_cpus,
            "all target HWCAP comparisons absent")
    require("system_supports_32bit_el0()" in compat_cpus and
            compat_cpus.count("ARM64_LATE_CPU_MAX_TARGETS") == 1 and
            "id_aa64pfr0_32bit_el0(" in compat_cpus and
            "target_cap[target].registers.id_aa64pfr0" in compat_cpus,
            "system/target AArch32 EL0 policy intersection absent")
    require(re.search(r"\bARM64_HAS_32BIT_EL0\b", cpufeature) is None,
            "nonexistent AArch32 EL0 capability token used")
    for token in (
        "ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID",
        "KERNEL_HWCAP_CPUID", "COMPAT_ELF_HWCAP_DEFAULT",
        "late_cpu_plan_all_cpus_support_32bit_el0(plan)",
        "plan->effects.compat_aes_clear", "COMPAT_HWCAP2_AES",
        "ARM64_WORKAROUND_2658417", "KERNEL_HWCAP_BF16",
        "KERNEL_HWCAP_EBF16", "ARM64_WORKAROUND_SPECULATIVE_SSBS",
        "KERNEL_HWCAP_SSBS", "plan->hwcaps_planned = 1",
    ):
        require(token in hwcap_plan or token in cpufeature,
                f"HWCAP plan/fixup absent: {token}")
    require(hwcap_plan.index("ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID") <
            hwcap_plan.index("KERNEL_HWCAP_CPUID") <
            hwcap_plan.index("plan->hwcaps_planned = 1"),
            "HWCAP validity/commit order changed")

    evidence_hash = function(core, "late_canonical_hash_evidence(")
    plan_hash = function(core, "late_canonical_hash_plan(")
    finalizer = function(core, "late_profile_finalize_plan_identity(")
    prepare = function(core, "arm64_prepare_late_cpu_profile(")
    for token in (
        '"gemini-late-cpu-evidence-v1"',
        '"gemini-late-cpu-plan-v1"',
        "cpu_to_be32(value)", "cpu_to_be64(value)",
        "get_unaligned_be64(digest + i * sizeof(u64))",
    ):
        require(token in core, f"canonical hash primitive absent: {token}")
    require("blocker_mask is a derived admission result" in evidence_hash,
            "blocker exclusion is not explicit")
    require("evidence->blocker_mask" not in evidence_hash,
            "derived blocker mask entered evidence identity")
    for forbidden in ("sizeof(*evidence)", "sizeof(*plan)",
                      "sizeof(plan->effects)", "sizeof(*registers)"):
        require(forbidden not in evidence_hash + plan_hash,
                f"canonical identity hashes structure padding: {forbidden}")

    evidence_fields = (
        "source_parent_identity", "config_input_identity", "expected_pair",
        "binding", "target_cpu[target]", "expected_target_mpidr[target]",
        "observed_target_mpidr[target]", "expected_target_midr[target]",
        "observed_target_midr[target]", "observed_target_revidr[target]",
        "target_cap[target]", "target_policy[target]", "system_cap",
    )
    for token in evidence_fields:
        require(token in evidence_hash,
                f"evidence identity input absent: {token}")
    register_hash = function(core, "late_canonical_update_registers(")
    for token in (
        "registers->ctr", "registers->cntfrq", "registers->dczid",
        "registers->midr", "registers->revidr", "registers->aidr",
        "registers->gmid", "registers->smidr", "registers->mpamidr",
        "registers->id_aa64dfr0", "registers->id_aa64dfr1",
        "registers->id_aa64isar0", "registers->id_aa64isar1",
        "registers->id_aa64isar2", "registers->id_aa64isar3",
        "registers->id_aa64mmfr0", "registers->id_aa64mmfr1",
        "registers->id_aa64mmfr2", "registers->id_aa64mmfr3",
        "registers->id_aa64mmfr4", "registers->id_aa64pfr0",
        "registers->id_aa64pfr1", "registers->id_aa64pfr2",
        "registers->id_aa64zfr0", "registers->id_aa64smfr0",
        "registers->id_aa64fpfr0", "aarch32->id_dfr0",
        "aarch32->id_dfr1", "aarch32->id_isar0", "aarch32->id_isar1",
        "aarch32->id_isar2", "aarch32->id_isar3", "aarch32->id_isar4",
        "aarch32->id_isar5", "aarch32->id_isar6", "aarch32->id_mmfr0",
        "aarch32->id_mmfr1", "aarch32->id_mmfr2", "aarch32->id_mmfr3",
        "aarch32->id_mmfr4", "aarch32->id_mmfr5", "aarch32->id_pfr0",
        "aarch32->id_pfr1", "aarch32->id_pfr2", "aarch32->mvfr0",
        "aarch32->mvfr1", "aarch32->mvfr2",
    ):
        require(register_hash.count(token) == 1,
                f"register identity field count changed: {token}")

    for token in (
        "plan->abi", "plan->profile_id", "plan->target_cpus",
        "plan->evidence.evidence_identity", "plan->canonical_caps",
        "plan->compiled_local_caps", "plan->classified_local_caps",
        "plan->early_local_caps", "plan->target_local_caps",
        "plan->target[target].classified_local_caps",
        "plan->target[target].local_caps", "plan->required_local_caps",
        "plan->conflicting_local_caps", "plan->effects",
        "plan->expected_elf_hwcap", "plan->expected_compat_hwcap",
        "plan->expected_compat_hwcap2", "plan->local_caps_planned",
        "plan->effects_planned", "plan->hwcaps_planned",
    ):
        require(token in plan_hash, f"plan identity input absent: {token}")
    effects_hash = function(core, "late_canonical_update_effects(")
    for token in (
        "ctr_mismatch.required", "ctr_mismatch.target_mask",
        "ctr_mismatch.trap_ctr_el0", "ctr_mismatch.alternative",
        "spectre_v2.required", "spectre_v2.callback",
        "spectre_v4.required", "spectre_v4.callback_required_mask",
        "bhb.required", "bhb.matcher_loop_count", "bhb.vector_template",
        "target[target]", "compat_aes_clear",
        "speculative_at_finalization",
    ):
        require(token in effects_hash,
                f"effect identity input absent: {token}")
    require("late_canonical_hash_evidence" in finalizer and
            "late_canonical_hash_plan" in finalizer and
            "late_profile_identity_empty" in finalizer,
            "identity finalizer does not fail closed")

    sequence = (
        "arm64_plan_late_cpu_capabilities(&draft, &late_profile)",
        "arm64_plan_late_cpu_effects(&draft, &late_profile)",
        "arm64_plan_late_cpu_hwcaps(&draft)",
        "late_profile.validate_plan(&draft)",
        "late_profile_finalize_plan_identity(&draft)",
    )
    positions = [prepare.index(token) for token in sequence]
    require(positions == sorted(positions), "pure planner sequence changed")
    for token in (
        "ARM64_LATE_CPU_BLOCK_HWCAP",
        "ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY",
        "!draft.hwcaps_planned",
    ):
        require(token in prepare, f"prepare fail-closed gate absent: {token}")

    profile_validate = function(profile, "mt6797_a72_validate_cap_plan(")
    require("plan->hwcaps_planned" in profile_validate,
            "profile does not distinguish planned HWCAP output")
    require("The core owns canonical identities" in profile_validate,
            "profile/core identity ownership boundary absent")
    require("mt6797_a72_fixture_evidence_identity" not in profile,
            "profile still supplies an evidence identity")
    require("late CPU profile commit implementation is unavailable" in core,
            "slice 4 changed the commit stub")
    require(core.count("ARM64_LATE_CPU_PROFILE_READY") == 3,
            "slice 4 changed READY code/token count")
    for forbidden in ("cpu_up(", "add_cpu(", "cpu_down(", "cpu_off(",
                      "psci_cpu_off", "request_cpu"):
        require(forbidden not in evidence_hash + plan_hash + hwcap_plan,
                f"planner gained a CPU/power action: {forbidden}")

    return [
        "validation=mainline-a72-slice4-planner-pass",
        "target_register_mappings=22",
        "identity_encoding=sha256-big-endian-named-fields",
        "evidence_padding_hashed=false",
        "plan_padding_hashed=false",
        "hwcap_scope=sanitized-system-and-all-targets",
        "target_cap_producer=absent",
        "architecture_commit=absent",
        "ready_publication=unchanged",
        "cpu_request_paths=0",
        "device_action=none",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.source_root.resolve())
    except (ValidationError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print("\n".join(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
