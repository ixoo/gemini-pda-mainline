#!/usr/bin/env python3
"""Validate the dormant conservative GIC and mitigation policy slice."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()
    proton = (root / "arch/arm64/kernel/proton-pack.c").read_text()
    smp = (root / "arch/arm64/kernel/smp.c").read_text()
    head = root / "arch/arm64/kernel/head.S"

    for token in (
        "ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID\tBIT(3)",
        "ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID)",
        "u8 gicv5_legacy;",
        "u8 ich_hcr_tdir;",
        "arm64_late_cpu_early_system_cap_state(",
        "arm64_late_cpu_expected_a72_spectre_v2_state(",
        "arm64_late_cpu_expected_a72_spectre_v4_state(",
        "arm64_late_cpu_expected_a72_spectre_bhb_state(",
        "arm64_late_cpu_expected_a72_effects(",
    ):
        require(token in header, f"public conservative-policy contract absent: {token}")
    require(header.count("ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID") == 2,
            "early-local system validity escaped its definition/mask")

    collector = function(cpufeature, "arm64_late_cpu_collect_system(")
    for token in (
        "system_capabilities_finalized()",
        "cpus_have_cap(ARM64_HAS_GICV5_LEGACY)",
        "cpus_have_cap(ARM64_HAS_ICH_HCR_EL2_TDIR)",
        "ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID",
    ):
        require(token in collector, f"early-system producer changed: {token}")
    for forbidden in (
        "this_cpu_has_cap", "read_sysreg", "target_cap", "expected_pair",
        "= 1;", "set_bit(", "clear_bit(",
    ):
        require(forbidden not in collector,
                f"early-system producer gained another owner/action: {forbidden}")

    early = function(cpufeature, "arm64_late_cpu_early_system_cap_state(")
    for token in (
        "ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID",
        "system->valid & ~ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK",
        "system->gicv5_legacy > 1",
        "system->ich_hcr_tdir > 1",
        "cpucap_late_cpu_permitted(cap)",
        "late_cpu_gic_descriptor_valid(cap, match)",
        "late_cpu_ich_descriptor_valid(cap, match)",
        "present ? ARM64_LATE_CPU_CAP_UNRESOLVED",
        "ARM64_LATE_CPU_CAP_ABSENT",
    ):
        require(token in early, f"early-system classifier changed: {token}")
    require(early.count("case ARM64_HAS_") == 2,
            "early-system classifier capability allowlist changed")
    for forbidden in (
        "ARM64_LATE_CPU_CAP_PRESENT", "target_cap", "expected_pair",
        "cpus_have_cap", "read_sysreg", "set_bit(", "clear_bit(",
    ):
        require(forbidden not in early,
                f"early-system classifier gained unsafe input/action: {forbidden}")

    canonical = function(core, "late_canonical_update_system_cap(")
    for token in (
        "late_canonical_update_u8(ctx, system->gicv5_legacy)",
        "late_canonical_update_u8(ctx, system->ich_hcr_tdir)",
    ):
        require(token in canonical, f"canonical early-system field absent: {token}")
    require(canonical.find("system->gicv5_legacy") <
            canonical.find("system->ich_hcr_tdir"),
            "canonical early-system field order changed")

    field_valid = function(proton, "late_cpu_expected_a72_field_valid(")
    for token in (
        "expected->abi == ARM64_LATE_CPU_EXPECTED_PAIR_ABI",
        "expected->target_count == ARM64_LATE_CPU_MAX_TARGETS",
        "expected->valid & ~ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK",
        "expected->valid & BIT_ULL(field)",
        "expected->midr == MIDR_CORTEX_A72",
    ):
        require(token in field_valid, f"expected-field proof changed: {token}")

    expected_v2 = function(
        proton, "late_cpu_expected_a72_spectre_v2_evidence_state(")
    expected_v4 = function(
        proton, "late_cpu_expected_a72_spectre_v4_evidence_state(")
    expected_bhb = function(
        proton, "late_cpu_expected_a72_spectre_bhb_evidence_state(")
    expected_functions = "\n".join((
        expected_v2,
        expected_v4,
        expected_bhb,
        function(proton, "arm64_late_cpu_expected_a72_spectre_v2_state("),
        function(proton, "arm64_late_cpu_expected_a72_spectre_v4_state("),
        function(proton, "arm64_late_cpu_expected_a72_spectre_bhb_state("),
        function(proton, "arm64_late_cpu_expected_a72_effects("),
    ))
    for token in (
        "ARM64_LATE_CPU_EXPECT_AA64PFR0",
        "ARM64_LATE_CPU_EXPECT_AA64PFR1",
        "ARM64_LATE_CPU_EXPECT_MIDR",
        "ID_AA64PFR0_EL1_CSV2_SHIFT",
        "ID_AA64PFR1_EL1_SSBS_SHIFT",
        "ARM64_LATE_CPU_MITIGATION_VULNERABLE",
        "ARM64_LATE_CPU_V2_CALLBACK_NONE",
        "ARM64_LATE_CPU_V4_NONE",
        "ARM64_LATE_CPU_BHB_STATE_VULNERABLE",
        "A non-vulnerable v2 path would need the missing BHB IDs",
        "return -EAGAIN",
        "return csv2 ? ARM64_LATE_CPU_CAP_ABSENT :\n"
        "\t\t      ARM64_LATE_CPU_CAP_PRESENT",
        "return csv2 == 3 ? ARM64_LATE_CPU_CAP_ABSENT :\n"
        "\t\t\t ARM64_LATE_CPU_CAP_PRESENT",
        "Without a current WA2 result, even SSBS==0 remains affected",
    ):
        require(token in expected_functions,
                f"expected-only conservative proof changed: {token}")
    require("\treturn ARM64_LATE_CPU_CAP_PRESENT;\n" in expected_v4,
            "unknown WA2 result stopped selecting affected Spectre-v4 state")
    for forbidden in (
        "target_cap", "smccc_wa1", "smccc_wa2", "smccc_wa3",
        "id_aa64isar2", "id_aa64mmfr1", "ARM64_LATE_CPU_SMCCC_SMC",
        "ARM64_LATE_CPU_SMCCC_HVC", "ARM64_LATE_CPU_V2_CALLBACK_SMC",
        "ARM64_LATE_CPU_V2_CALLBACK_HVC", "ARM64_LATE_CPU_BHB_LOOP",
        "ARM64_LATE_CPU_BHB_FIRMWARE", "ARM64_LATE_CPU_BHB_INSTRUCTION",
        "ARM64_LATE_CPU_BHB_HARDWARE",
    ):
        require(forbidden not in expected_functions,
                f"expected-only proof consumed missing evidence: {forbidden}")

    effects = function(proton, "arm64_late_cpu_expected_a72_effects(")
    for token in (
        "effects->valid = ARM64_LATE_CPU_TARGET_EFFECT_VALID_MASK",
        "effects->spectre_v2_hyp_vector = ARM64_LATE_CPU_HYP_VECTOR_DIRECT",
        "effects->spectre_v2_conduit = ARM64_LATE_CPU_SMCCC_NONE",
        "effects->spectre_v2_callback = ARM64_LATE_CPU_V2_CALLBACK_NONE",
        "effects->spectre_v4_conduit = ARM64_LATE_CPU_SMCCC_NONE",
        "effects->bhb_conduit = ARM64_LATE_CPU_SMCCC_NONE",
        "effects->bhb_vector_template = ARM64_LATE_CPU_BHB_VECTOR_NONE",
        "!effects->bhb_v2_non_vulnerable",
        "effects->bhb_method = ARM64_LATE_CPU_BHB_NONE",
        "ARM64_LATE_CPU_BHB_STATE_VULNERABLE",
        "v2_state == ARM64_LATE_CPU_CAP_ABSENT ?\n"
        "\t\t\tARM64_LATE_CPU_MITIGATION_UNAFFECTED :\n"
        "\t\t\tARM64_LATE_CPU_MITIGATION_VULNERABLE",
        "if (ssbs && !policy->mitigations_off &&",
        "} else if (!effects->bhb_v2_non_vulnerable) {",
    ):
        require(token in effects, f"conservative effect shape changed: {token}")
    require(effects.count("return -EAGAIN;") == 2,
            "conservative effect fail-closed exits changed")

    classifier = function(profile, "mt6797_a72_classify_local_cap(")
    for token in (
        "arm64_late_cpu_early_system_cap_state(",
        "arm64_late_cpu_expected_a72_spectre_v2_state(",
        "arm64_late_cpu_expected_a72_spectre_v4_state(",
        "arm64_late_cpu_expected_a72_spectre_bhb_state(",
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE",
    ):
        require(token in classifier, f"MT6797 policy routing changed: {token}")
    derive = function(profile, "mt6797_a72_derive_effects(")
    for token in (
        "arm64_late_cpu_expected_pair_complete(plan)",
        "arm64_late_cpu_expected_a72_effects(",
        "&plan->evidence.expected_pair",
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE",
    ):
        require(token in derive, f"MT6797 expected-effect routing changed: {token}")
    production = profile.split(
        "#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE", 1)[1]
    unresolved = production.split(
        "static const u16 mt6797_a72_unresolved_caps[]", 1)[1].split("};", 1)[0]
    require("ARM64_HAS_GICV5_LEGACY" not in unresolved and
            "ARM64_HAS_ICH_HCR_EL2_TDIR" not in unresolved,
            "unused early GIC/hyp capabilities stayed unconditionally unresolved")
    absent = profile.split(
        "static const u16 mt6797_a72_absent_caps[]", 1)[1].split("};", 1)[0]
    require("ARM64_HAS_GICV5_LEGACY" in absent and
            "ARM64_HAS_ICH_HCR_EL2_TDIR" in absent,
            "unused early GIC/hyp absent plan changed")
    fixture_check = function(profile, "mt6797_a72_evidence_is_fixture(")
    for token in (
        "evidence->system_cap.gicv5_legacy",
        "evidence->system_cap.ich_hcr_tdir",
    ):
        require(token in fixture_check, f"fixture early-system shape changed: {token}")

    preflight = function(smp, "secondary_start_kernel(")
    for token in (
        "arm64_validate_late_cpu_preflight(cpu)",
        "check_local_cpu_capabilities()",
        "arm64_validate_late_cpu_expected_target(cpu)",
    ):
        require(token in preflight, f"entry preflight path changed: {token}")
    require(sha256(head) ==
            "17dac1b2a499bb21f8a0e160aff9fd9fd24343c0f6d0dc12a4f4cbafb99d0749",
            "assembly granule/VA gates changed")
    prepare = function(profile, "mt6797_a72_profile_prepare(")
    require("return -EAGAIN;" in prepare,
            "production profile stopped fail-closing")
    require("expected_pair." not in prepare,
            "production profile activated the expected pair")

    joined = header + cpufeature + core + profile + proton
    for forbidden in (
        "cpu_up(8", "cpu_up(9", "cpu_down(8", "cpu_down(9",
        "psci_cpu_on", "psci_cpu_off", "boot2", "expected_pair.abi =",
    ):
        require(forbidden not in joined,
                f"policy slice gained forbidden activation/action: {forbidden}")

    return [
        "validation=mainline-a72-conservative-policy-pass",
        "early_gic_owner=finalized-system-capability-bitmap",
        "early_gic_absent=planned-absent",
        "early_gic_present=unresolved",
        "expected_spectre_fields=midr,pfr0,pfr1",
        "unknown_wa1=vulnerable-no-callback",
        "unknown_wa2=vulnerable-no-callback",
        "vulnerable_v2_bhb=vulnerable-no-method",
        "missing_modern_ids=not-consumed",
        "expected_pair_activation=absent",
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
