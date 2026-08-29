#!/usr/bin/env python3
"""Validate slice 5's callback-free architecture commit and receipt."""

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
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    proton = (root / "arch/arm64/kernel/proton-pack.c").read_text()
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    require(header.count("arm64_commit_late_cpu_plan(") == 1,
            "architecture commit declaration count changed")
    require(header.count("arm64_commit_late_cpu_mitigations(") == 1,
            "mitigation commit declaration count changed")

    allow = function(cpufeature, "late_cpu_commit_cap_allowed(")
    allowed_caps = (
        "ARM64_MISMATCHED_CACHE_TYPE", "ARM64_SPECTRE_V2",
        "ARM64_SPECTRE_V4", "ARM64_SPECTRE_BHB",
        "ARM64_WORKAROUND_1742098", "ARM64_WORKAROUND_SPECULATIVE_AT",
    )
    require(allow.count("case ") == len(allowed_caps),
            "late-required capability allowlist count changed")
    for cap in allowed_caps:
        require(allow.count(f"case {cap}:") == 1,
                f"late-required capability allowlist changed: {cap}")
    require("default:" in allow and "return false;" in allow,
            "capability allowlist does not fail closed")

    commit = function(cpufeature, "arm64_commit_late_cpu_plan(")
    require("if (!plan || system_capabilities_finalized() ||" in commit,
            "architecture commit finalization gate changed")
    require("!bitmap_subset(plan->required_local_caps,\n"
            "\t\t\t   plan->target_local_caps, ARM64_NCAPS)" in commit,
            "late-required capabilities stopped being a target subset")
    require("bitmap_intersects(plan->required_local_caps,\n"
            "\t\t\t      system_cpucaps, ARM64_NCAPS)" in commit,
            "late-required capabilities stopped being disjoint from live state")
    for token in (
        "ARM64_ALWAYS_SYSTEM",
        "plan->abi != ARM64_LATE_CPU_PLAN_ABI",
        "plan->evidence.blocker_mask", "plan->local_caps_planned",
        "plan->effects_planned", "plan->hwcaps_planned",
        "memchr_inv(plan->identity", "plan->conflicting_local_caps",
        "bitmap_subset(plan->required_local_caps",
        "plan->target_local_caps", "plan->canonical_caps",
        "bitmap_intersects(plan->required_local_caps",
        "plan->early_local_caps", "system_cpucaps",
        "for_each_set_bit(cap, plan->required_local_caps",
        "descriptor->capability != cap", "descriptor->type & SCOPE_LOCAL_CPU",
        "cpucap_late_cpu_permitted(descriptor)",
        "arm64_commit_late_cpu_mitigations(&plan->effects)",
        "bitmap_or(system_cpucaps, system_cpucaps",
        "bitmap_equal(system_cpucaps, expected_caps",
    ):
        require(token in commit, f"architecture commit gate absent: {token}")
    require(commit.index("arm64_commit_late_cpu_mitigations") <
            commit.index("bitmap_or(system_cpucaps, system_cpucaps"),
            "fallible mitigation validation follows capability mutation")
    require(commit.count("bitmap_or(system_cpucaps, system_cpucaps") == 1,
            "system capability state has multiple write sites")
    require("__clear_bit" not in commit and "bitmap_andnot" not in commit,
            "architecture commit can clear capability state")

    state_map = function(proton, "late_cpu_commit_mitigation_state(")
    for token in (
        "ARM64_LATE_CPU_MITIGATION_UNAFFECTED",
        "ARM64_LATE_CPU_MITIGATION_MITIGATED",
        "ARM64_LATE_CPU_MITIGATION_VULNERABLE",
        "SPECTRE_UNAFFECTED", "SPECTRE_MITIGATED", "SPECTRE_VULNERABLE",
        "default:", "return -EINVAL;",
    ):
        require(token in state_map,
                f"mitigation state mapping changed: {token}")

    mitigation = function(proton, "arm64_commit_late_cpu_mitigations(")
    for token in (
        "system_capabilities_finalized()",
        "effects->spectre_v2.required", "effects->spectre_v4.required",
        "effects->bhb.required", "READ_ONCE(spectre_v2_state) > v2",
        "READ_ONCE(spectre_v4_state) > v4",
        "READ_ONCE(spectre_bhb_state) > bhb",
        "effects->bhb.system_method & ~GENMASK(BHB_INSN, BHB_LOOP)",
        "current_bhb_methods & ~effects->bhb.system_method",
        "current_bhb_loop > effects->bhb.matcher_loop_count",
        "update_mitigation_state(&spectre_v2_state, v2)",
        "update_mitigation_state(&spectre_v4_state, v4)",
        "WRITE_ONCE(max_bhb_k, effects->bhb.matcher_loop_count)",
        "WRITE_ONCE(system_bhb_mitigations",
        "update_mitigation_state(&spectre_bhb_state, bhb)",
    ):
        require(token in mitigation,
                f"monotonic mitigation commit absent: {token}")
    first_write = min(
        mitigation.index("update_mitigation_state(&spectre_v2_state"),
        mitigation.index("update_mitigation_state(&spectre_v4_state"),
        mitigation.index("WRITE_ONCE(max_bhb_k"),
    )
    require(mitigation.rfind("return -EINVAL;") < first_write,
            "fallible mitigation gate follows its first state write")

    profile_commit = function(core, "arm64_commit_late_cpu_profile(")
    sequence = (
        "arm64_commit_late_cpu_plan(&late_plan)",
        "late_receipt.committed = late_plan.effects",
        "late_receipt.commit_complete = 1",
        "smp_store_release(&late_receipt.state",
        "ARM64_LATE_CPU_PROFILE_COMMITTED",
    )
    positions = [profile_commit.index(token) for token in sequence]
    require(positions == sorted(positions),
            "architecture commit/receipt publication order changed")
    for token in (
        "late_receipt.blocker_mask", "late_receipt.commit_complete",
        "late_receipt.strict_caps_verified",
        "late_receipt.alternatives_finalized",
        "late_receipt.user_hwcaps_finalized",
        "memchr_inv(&late_receipt.committed",
        "late CPU architecture commit failed",
        "Publish the complete receipt after all architecture state",
    ):
        require(token in profile_commit,
                f"receipt precondition/publication gate absent: {token}")
    require("commit implementation is unavailable" not in profile_commit,
            "old architecture commit stub remains")
    require("ARM64_LATE_CPU_BLOCK_COMMIT_PATH" not in
            function(core, "arm64_prepare_late_cpu_profile("),
            "prepare still injects the obsolete commit-path blocker")

    setup = function(cpufeature, "setup_system_capabilities(")
    require(setup.index("arm64_commit_late_cpu_profile()") <
            setup.index("update_cpu_capabilities(SCOPE_SYSTEM)") <
            setup.index("enable_cpu_capabilities(") <
            setup.index("apply_alternatives_all()"),
            "commit no longer precedes normal capability finalization")

    prepare = function(profile, "mt6797_a72_profile_prepare(")
    require("return -EAGAIN;" in prepare and
            "No live system capability, alternative, vector, or HWCAP" in prepare,
            "production target-cap profile stopped fail-closing")
    require(core.count("ARM64_LATE_CPU_PROFILE_READY") == 3,
            "slice 5 changed READY publication/token code")

    joined = commit + mitigation + profile_commit
    for forbidden in (
        "cpu_up(", "add_cpu(", "cpu_down(", "cpu_off(",
        "psci_cpu_off", "psci_cpu_on", "request_cpu", "cpu_boot(",
        "profile->", ".prepare(", ".derive_effects(", ".validate_plan(",
        "arm_smccc_1_1_invoke", "cpu_enable(", "apply_alternatives",
        "setup_elf_hwcaps",
    ):
        require(forbidden not in joined,
                f"commit gained callback/power/finalization action: {forbidden}")

    return [
        "validation=mainline-a72-slice5-architecture-commit-pass",
        "late_required_cap_allowlist=6",
        "capability_commit=monotonic-set-only",
        "mitigation_commit=monotonic-typed-state",
        "profile_callbacks=0",
        "target_cap_producer=absent",
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
