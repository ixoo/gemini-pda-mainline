#!/usr/bin/env python3
"""Validate strict system, alternatives, mitigation, and HWCAP finalization."""

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
    header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    cpufeature = (root / "arch/arm64/kernel/cpufeature.c").read_text()
    mitigations = (root / "arch/arm64/kernel/proton-pack.c").read_text()
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    for symbol in (
        "arm64_verify_late_cpu_mitigations",
        "arm64_verify_late_cpu_system",
        "arm64_finalize_late_cpu_hwcaps",
    ):
        require(header.count(symbol) == 1,
                f"public finalization declaration changed: {symbol}")

    verify = function(cpufeature, "arm64_verify_late_cpu_system(")
    for required in (
        "system_capabilities_finalized()",
        "receipt->state != ARM64_LATE_CPU_PROFILE_COMMITTED",
        "!receipt->commit_complete",
        "receipt->strict_caps_verified",
        "receipt->alternatives_finalized",
        "receipt->user_hwcaps_finalized",
        "bitmap_empty(plan->conflicting_local_caps, ARM64_NCAPS)",
        "bitmap_or(expected_caps, plan->early_local_caps,",
        "plan->required_local_caps, ARM64_NCAPS)",
        "bitmap_subset(expected_caps, plan->compiled_local_caps,",
        "bitmap_and(live_caps, system_cpucaps, plan->compiled_local_caps,",
        "bitmap_equal(live_caps, expected_caps, ARM64_NCAPS)",
        "for_each_set_bit(cap, plan->compiled_local_caps, ARM64_NCAPS)",
        "alternative_is_applied(cap) !=",
        "test_bit(cap, expected_caps)",
        "return arm64_verify_late_cpu_mitigations(&plan->effects);",
    ):
        require(required in verify, f"system verification lost: {required}")
    require(verify.index("bitmap_equal(live_caps") <
            verify.index("for_each_set_bit"),
            "alternative proof precedes exact capability equality")
    for forbidden in (
        "set_bit(", "clear_bit(", "bitmap_or(system_cpucaps",
        "bitmap_copy(system_cpucaps", "cpu_up(", "cpu_down(",
        "cpu_off(", "psci_cpu_on", "psci_cpu_off",
    ):
        require(forbidden not in verify,
                f"system verification gained a mutation/request: {forbidden}")

    mitigation = function(mitigations,
                          "arm64_verify_late_cpu_mitigations(")
    for required in (
        "system_capabilities_finalized()",
        "effects->spectre_v2.required",
        "READ_ONCE(spectre_v2_state) != v2",
        "effects->spectre_v4.required",
        "READ_ONCE(spectre_v4_state) != v4",
        "effects->bhb.required",
        "READ_ONCE(spectre_bhb_state) != bhb",
        "READ_ONCE(system_bhb_mitigations) !=",
        "effects->bhb.system_method",
        "READ_ONCE(max_bhb_k) != effects->bhb.matcher_loop_count",
    ):
        require(required in mitigation,
                f"mitigation verification lost: {required}")
    for forbidden in (
        "WRITE_ONCE(", "update_mitigation_state(", "set_bit(",
        "clear_bit(", "cpu_up(", "cpu_off(",
    ):
        require(forbidden not in mitigation,
                f"mitigation verification gained a write: {forbidden}")

    hwcap = function(cpufeature, "arm64_finalize_late_cpu_hwcaps(")
    for required in (
        "system_capabilities_finalized()",
        "receipt->state != ARM64_LATE_CPU_PROFILE_SYSTEM_VERIFIED",
        "!receipt->commit_complete",
        "!receipt->strict_caps_verified",
        "!receipt->alternatives_finalized",
        "receipt->user_hwcaps_finalized",
        "bitmap_subset(expected, elf_hwcap, MAX_CPU_FEATURES)",
        "plan->expected_compat_hwcap & ~compat_elf_hwcap",
        "plan->expected_compat_hwcap2 & ~compat_elf_hwcap2",
        "compat_elf_hwcap3",
        "bitmap_copy(elf_hwcap, expected, MAX_CPU_FEATURES)",
        "compat_elf_hwcap = plan->expected_compat_hwcap;",
        "compat_elf_hwcap2 = plan->expected_compat_hwcap2;",
        "bitmap_equal(elf_hwcap, expected, MAX_CPU_FEATURES)",
        "compat_elf_hwcap != plan->expected_compat_hwcap",
        "compat_elf_hwcap2 != plan->expected_compat_hwcap2",
        "late CPU compat HWCAP finalization changed outside its plan",
    ):
        require(required in hwcap, f"HWCAP finalization lost: {required}")
    first_write = hwcap.index("bitmap_copy(elf_hwcap")
    for check in (
        "bitmap_subset(expected, elf_hwcap",
        "plan->expected_compat_hwcap & ~compat_elf_hwcap",
        "compat_elf_hwcap3",
    ):
        require(hwcap.index(check) < first_write,
                f"fallible HWCAP check follows first write: {check}")
    for forbidden in (
        "bitmap_or(elf_hwcap", "|= plan->expected_compat",
        "cpu_up(", "cpu_down(", "cpu_off(", "psci_cpu_on",
        "psci_cpu_off", "receipt->user_hwcaps_finalized =",
    ):
        require(forbidden not in hwcap,
                f"HWCAP finalization gained unsafe behavior: {forbidden}")

    blocker = block(
        profile, "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE",
        "static const u64 mt6797_a72_source_parent_identity")
    fixture, production = blocker.split("#else\n", 1)
    require("ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS" in fixture,
            "historical fixture attestation blocker was removed")
    require(production.count("ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING") == 1,
            "production runtime-binding blocker changed")
    require("ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS" not in production,
            "production attestation blocker remains")

    prepare = function(profile, "mt6797_a72_profile_prepare(")
    require("#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
            "\treturn -EAGAIN;\n#else\n\treturn 0;\n#endif" in prepare,
            "production prepare does not succeed while fixture stays blocked")
    verify_profile = function(profile, "mt6797_a72_verify_system(")
    finalize_profile = function(profile, "mt6797_a72_finalize_user(")
    require("return arm64_verify_late_cpu_system(plan, receipt);" in
            verify_profile, "profile system callback is not architecture-owned")
    require("return arm64_finalize_late_cpu_hwcaps(plan, receipt);" in
            finalize_profile, "profile HWCAP callback is not architecture-owned")
    descriptor = block(
        profile,
        "static const struct arm64_late_cpu_profile mt6797_a72_profile",
        "void __init mt6797_activate_a72_capability_profile")
    require(descriptor.count(".verify_system = mt6797_a72_verify_system") == 1,
            "profile system verifier is not wired exactly once")
    require(descriptor.count(".finalize_user = mt6797_a72_finalize_user") == 1,
            "profile user finalizer is not wired exactly once")

    changed = verify + mitigation + hwcap + prepare + verify_profile + finalize_profile
    for forbidden in (
        "cpu_up(", "cpu_down(", "cpu_off(", "psci_cpu_on",
        "psci_cpu_off", "boot2", "ARM64_LATE_CPU_PROFILE_READY",
        "arm64_get_late_cpu_ready_token",
    ):
        require(forbidden not in changed,
                f"finalization slice gained forbidden path: {forbidden}")

    return [
        "source_validation=pass",
        "strict_local_caps=exact",
        "system_alternatives=exact",
        "mitigation_state=exact",
        "native_hwcap_finalization=one-way-subset",
        "compat_hwcap_finalization=one-way-subset",
        "clean_path_blocker_mask=0x0-after-runtime-binding",
        "fixture_ready_publication=blocked",
        "ready_callbacks=architecture-owned",
        "cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        markers = validate(args.source_root.resolve())
    except (OSError, ValueError, ValidationError) as error:
        print(f"validation_error={error}")
        return 1
    print("\n".join(markers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
