#!/usr/bin/env python3
"""Require unsafe closed-hook rule mutations to fail intended invariants."""

from __future__ import annotations

import sys
from dataclasses import replace

sys.dont_write_bytecode = True

from oracle import CORRECT_RULES, Rules, audit_contract  # noqa: E402


MUTATIONS: tuple[tuple[str, Rules, str], ...] = (
    (
        "public-hook-omitted",
        replace(CORRECT_RULES, omit_public_hook=True),
        "PUBLIC_HOOK_PRESENT",
    ),
    (
        "internal-hook-omitted",
        replace(CORRECT_RULES, omit_internal_hook=True),
        "INTERNAL_HOOK_PRESENT",
    ),
    (
        "public-after-cpu-possible",
        replace(CORRECT_RULES, public_after_cpu_possible=True),
        "PUBLIC_BEFORE_CPU_POSSIBLE",
    ),
    (
        "public-after-node-work",
        replace(CORRECT_RULES, public_after_node_work=True),
        "PUBLIC_BEFORE_NODE_WORK",
    ),
    (
        "public-after-maps",
        replace(CORRECT_RULES, public_after_maps=True),
        "PUBLIC_BEFORE_MAPS",
    ),
    (
        "internal-after-per-cpu",
        replace(CORRECT_RULES, internal_after_per_cpu=True),
        "INTERNAL_BEFORE_PER_CPU",
    ),
    (
        "internal-after-cpus-write",
        replace(CORRECT_RULES, internal_after_cpus_write=True),
        "INTERNAL_BEFORE_CPUS_WRITE",
    ),
    (
        "internal-after-cpuhp",
        replace(CORRECT_RULES, internal_after_cpuhp=True),
        "INTERNAL_BEFORE_CPUHP",
    ),
    (
        "internal-after-callback",
        replace(CORRECT_RULES, internal_after_callback=True),
        "INTERNAL_BEFORE_CALLBACK",
    ),
    (
        "internal-after-cpu-boot",
        replace(CORRECT_RULES, internal_after_boot=True),
        "INTERNAL_BEFORE_CPU_BOOT",
    ),
    (
        "thaw-bypasses-internal",
        replace(CORRECT_RULES, bypass_thaw=True),
        "THAW_USES_INTERNAL_HOOK",
    ),
    (
        "smt-bypasses-internal",
        replace(CORRECT_RULES, bypass_smt=True),
        "SMT_USES_INTERNAL_HOOK",
    ),
    (
        "weak-default-denies",
        replace(CORRECT_RULES, deny_other_arch=True),
        "WEAK_DEFAULT_PASS_THROUGH",
    ),
    (
        "optional-method-denies",
        replace(CORRECT_RULES, deny_other_method=True),
        "OPTIONAL_CALLBACK_PASS_THROUGH",
    ),
    (
        "mt6797-a53-denied",
        replace(CORRECT_RULES, deny_a53=True),
        "MT6797_A53_PASS_THROUGH",
    ),
    (
        "bounds-capture-policy",
        replace(CORRECT_RULES, deny_out_of_range=True),
        "BOUNDS_PRESERVE_GENERIC",
    ),
    (
        "closed-a72-admitted",
        replace(CORRECT_RULES, admit_a72=True),
        "A72_CLOSED_DENIAL",
    ),
    (
        "intermediate-target-accepted",
        replace(CORRECT_RULES, accept_intermediate=True),
        "INTERMEDIATE_TARGET_REJECTED",
    ),
    (
        "frozen-internal-accepted",
        replace(CORRECT_RULES, accept_frozen=True),
        "FROZEN_INTERNAL_REJECTED",
    ),
    (
        "transaction-begin-called",
        replace(CORRECT_RULES, call_begin_up=True),
        "NO_BEGIN_UP",
    ),
    (
        "early-transition-mutex",
        replace(CORRECT_RULES, take_transition_mutex_early=True),
        "EARLY_NO_TRANSITION_MUTEX",
    ),
    (
        "transaction-allocated",
        replace(CORRECT_RULES, allocate_transaction=True),
        "NO_TRANSACTION",
    ),
    (
        "output-persisted",
        replace(CORRECT_RULES, persist_output=True),
        "NO_OUTPUT",
    ),
    (
        "owner-opened",
        replace(CORRECT_RULES, add_opener=True),
        "NO_OPENER",
    ),
    (
        "p31-entered",
        replace(CORRECT_RULES, enter_p31=True),
        "NO_P31",
    ),
    (
        "a38-consumed",
        replace(CORRECT_RULES, consume_a38=True),
        "NO_A38",
    ),
    (
        "attempt-consumed",
        replace(CORRECT_RULES, consume_attempt=True),
        "NO_ATTEMPT_CONSUMPTION",
    ),
    (
        "token-allocated",
        replace(CORRECT_RULES, allocate_token=True),
        "NO_TOKEN",
    ),
    (
        "membership-phase-entered",
        replace(CORRECT_RULES, enter_membership_phase=True),
        "MEMBERSHIP_REMAINS_UNINITIALIZED",
    ),
    (
        "p17-published",
        replace(CORRECT_RULES, publish_p17=True),
        "NO_P17",
    ),
    (
        "p18-published",
        replace(CORRECT_RULES, publish_p18=True),
        "NO_P18",
    ),
    (
        "p30-mutated",
        replace(CORRECT_RULES, mutate_p30=True),
        "NO_P30",
    ),
    (
        "provider-mutated",
        replace(CORRECT_RULES, mutate_provider=True),
        "NO_PROVIDER_EFFECT",
    ),
    (
        "membership-mutated",
        replace(CORRECT_RULES, mutate_members=True),
        "NO_MEMBER_EFFECT",
    ),
    (
        "hardware-mutated",
        replace(CORRECT_RULES, mutate_hardware=True),
        "NO_HARDWARE_EFFECT",
    ),
    (
        "cpu-on-issued",
        replace(CORRECT_RULES, issue_cpu_on=True),
        "NO_CPU_ON",
    ),
    (
        "cpu-boot-called",
        replace(CORRECT_RULES, call_cpu_boot=True),
        "NO_CPU_BOOT",
    ),
    (
        "cpu-boot-backstop-removed",
        replace(CORRECT_RULES, remove_cpu_boot_backstop=True),
        "CPU_BOOT_BACKSTOP_RETAINED",
    ),
    (
        "cpu-disable-backstop-removed",
        replace(CORRECT_RULES, remove_cpu_disable_backstop=True),
        "CPU_DISABLE_BACKSTOP_RETAINED",
    ),
)


def main() -> int:
    baseline = audit_contract()
    if baseline.violations:
        print("baseline contract failed:", ", ".join(sorted(baseline.violations)))
        return 1

    passed = 0
    for name, rules, expected in MUTATIONS:
        report = audit_contract(rules)
        if expected not in report.violations:
            found = ", ".join(sorted(report.violations)) or "none"
            print(f"FAIL {name}: expected {expected}; found {found}")
            return 1
        passed += 1
        print(f"PASS {name}: {expected}")

    print(f"mutations_rejected={passed}/{len(MUTATIONS)}")
    print("PASS intended-check closed-hook mutation suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
