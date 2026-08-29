#!/usr/bin/env python3
"""Validate slice 7's late-target strict-verification preflight."""

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
    late_header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    mmu_header = (root / "arch/arm64/include/asm/mmu_context.h").read_text()
    cpufeature = (root / "arch/arm64/kernel/cpufeature.c").read_text()
    head = root / "arch/arm64/kernel/head.S"
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()
    smp = (root / "arch/arm64/kernel/smp.c").read_text()
    context = (root / "arch/arm64/mm/context.c").read_text()

    require(late_header.count("arm64_late_cpu_validate_boot_caps(void);") == 1,
            "boot-cap preflight declaration count changed")
    require(late_header.count(
        "arm64_validate_late_cpu_preflight(unsigned int cpu);") == 1,
        "late-target preflight declaration count changed")
    require(mmu_header.count(
        "arm64_late_cpu_asid_compatible(void);") == 1,
        "ASID preflight declaration count changed")

    asid = function(context, "arm64_late_cpu_asid_compatible(")
    for token in (
        "u32 system_asid_bits = READ_ONCE(asid_bits)",
        "system_asid_bits &&",
        "get_cpu_asid_bits() >= system_asid_bits",
    ):
        require(token in asid, f"ASID compatibility gate absent: {token}")
    for forbidden in ("\tasid_bits =", "WRITE_ONCE", "panic", "cpu_off"):
        require(forbidden not in asid,
                f"ASID preflight gained a mutation/action: {forbidden}")

    boot = function(cpufeature, "arm64_late_cpu_validate_boot_caps(")
    for token in (
        "for (i = 0; i < ARM64_NCAPS; i++)",
        "caps = cpucap_ptrs[i]",
        "!(caps->type & SCOPE_BOOT_CPU)",
        "caps->matches(caps, SCOPE_LOCAL_CPU)",
        "cpus_have_cap(caps->capability)",
        "!cpu_has_cap && !cpucap_late_cpu_optional(caps)",
        "cpu_has_cap && !cpucap_late_cpu_permitted(caps)",
        "return -ERANGE",
    ):
        require(token in boot,
                f"generic boot-capability preflight gate absent: {token}")
    require(boot.count("return -ERANGE;") == 2,
            "boot-capability conflict exits changed")
    for forbidden in (
        "ARM64_HAS_GICV3_CPUIF", "ARM64_HAS_GICV5_CPUIF",
        "ARM64_MTE", "ARM64_HAS_VIRT_HOST_EXTN", "cpu_enable(",
        "set_bit(", "clear_bit(", "system_cpucaps", "cpu_panic_kernel",
        "cpu_die_early", "cpu_up(", "cpu_off(",
    ):
        require(forbidden not in boot,
                f"boot preflight gained allowlist/action: {forbidden}")

    verify = function(cpufeature, "verify_local_cpu_caps(")
    for token in (
        "scope_mask &= ARM64_CPUCAP_SCOPE_MASK",
        "caps->matches(caps, SCOPE_LOCAL_CPU)",
        "cpus_have_cap(caps->capability)",
        "!cpu_has_cap && !cpucap_late_cpu_optional(caps)",
        "cpu_has_cap && !cpucap_late_cpu_permitted(caps)",
        "caps->cpu_enable(caps)",
        "cpucap_panic_on_conflict(caps)",
        "cpu_panic_kernel()",
        "cpu_die_early()",
    ):
        require(token in verify,
                f"standard capability verifier changed: {token}")

    preflight = function(core, "arm64_validate_late_cpu_preflight(")
    ordered = (
        "smp_load_acquire(&late_receipt.state)",
        "ARM64_LATE_CPU_PROFILE_READY",
        "cpumask_test_cpu(cpu, &late_plan.target_cpus)",
        "cpu != smp_processor_id()",
        "arm64_late_cpu_expected_pair_complete(&late_plan)",
        "arm64_late_cpu_asid_compatible()",
        "arm64_late_cpu_validate_boot_caps()",
    )
    position = -1
    for token in ordered:
        current = preflight.find(token)
        require(current > position,
                f"late-target preflight order changed: {token}")
        position = current
    require(preflight.count("return 0;") == 2,
            "non-READY/non-target pass-through changed")
    require(preflight.count("return -EINVAL;") == 1 and
            preflight.count("return -ERANGE;") == 1,
            "preflight fail-closed exits changed")
    for forbidden in (
        "expected_pair.", "target_cap[", "observed_target_", "cpu_up(",
        "cpu_down(", "cpu_off(", "psci_cpu_on", "psci_cpu_off",
    ):
        require(forbidden not in preflight,
                f"preflight gained forbidden producer/action: {forbidden}")

    secondary = function(smp, "secondary_start_kernel(")
    call_order = (
        "arm64_validate_late_cpu_preflight(cpu)",
        "check_local_cpu_capabilities()",
        "ops->cpu_postboot",
        "cpuinfo_store_cpu()",
        "arm64_validate_late_cpu_expected_target(cpu)",
        "store_cpu_topology(cpu)",
        "notify_cpu_starting(cpu)",
    )
    position = -1
    for token in call_order:
        current = secondary.find(token)
        require(current > position,
                f"secondary entry ordering changed: {token}")
        position = current
    require(secondary.count("arm64_validate_late_cpu_preflight(cpu)") == 1,
            "preflight call count changed")
    require(secondary.count("check_local_cpu_capabilities()") == 1,
            "standard verifier call count changed")
    require(secondary.count("arm64_validate_late_cpu_expected_target(cpu)") == 1,
            "full expectation call count changed")
    preflight_failure = secondary.split(
        "expectation_ret = arm64_validate_late_cpu_preflight(cpu);", 1
    )[1].split("check_local_cpu_capabilities();", 1)[0]
    for token in (
        "if (expectation_ret)",
        "update_cpu_boot_status(CPU_STUCK_IN_KERNEL)",
        "cpu_park_loop()",
    ):
        require(token in preflight_failure,
                f"preflight failure no longer parks target: {token}")
    for forbidden in (
        "CPU_PANIC_KERNEL", "panic(", "cpu_panic_kernel", "cpu_up(",
        "cpu_down(", "cpu_off(", "psci_cpu_on", "psci_cpu_off",
        "set_cpu_online",
    ):
        require(forbidden not in preflight_failure,
                f"preflight failure gained forbidden action: {forbidden}")

    expected = function(core, "arm64_validate_late_cpu_expected_target(")
    for token in (
        "smp_load_acquire(&late_receipt.state)",
        "ARM64_LATE_CPU_PROFILE_READY",
        "arm64_late_cpu_expected_pair_complete(&late_plan)",
        "late_expected_target_matches(expected, target, info)",
    ):
        require(token in expected,
                f"full expected-target validator changed: {token}")

    require(sha256(head) ==
            "17dac1b2a499bb21f8a0e160aff9fd9fd24343c0f6d0dc12a4f4cbafb99d0749",
            "assembly granule/VA gates changed")
    profile_prepare = function(profile, "mt6797_a72_profile_prepare(")
    require("return -EAGAIN;" in profile_prepare,
            "production profile stopped fail-closing")
    require("expected_pair." not in profile_prepare,
            "production profile activated the expected pair")

    joined = late_header + mmu_header + cpufeature + core + smp + context
    for forbidden in (
        "cpu_up(8", "cpu_up(9", "cpu_down(8", "cpu_down(9",
        "psci_cpu_on", "psci_cpu_off", "boot2", "expected_pair.abi =",
    ):
        require(forbidden not in joined,
                f"slice 7 gained forbidden action/activation: {forbidden}")
    require(core.count("ARM64_LATE_CPU_PROFILE_READY") == 4,
            "slice 7 changed READY paths beyond the preflight read")

    return [
        "validation=mainline-a72-slice7-preflight-pass",
        "preflight_scope=ready-target-only",
        "asid_check=non-mutating-at-least-system-width",
        "boot_cap_inventory=all-linked-boot-scope-descriptors",
        "boot_cap_conflict_semantics=standard-optional-permitted",
        "preflight_failure=target-park",
        "standard_verifier=retained",
        "full_expectation_validator=retained",
        "assembly_granule_va_gates=unchanged",
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
