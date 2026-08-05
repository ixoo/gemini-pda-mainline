#!/usr/bin/env python3
"""Require each bounded unsafe P30 rule mutation to fail its intended check."""

from __future__ import annotations

import sys
from dataclasses import replace

sys.dont_write_bytecode = True

from oracle import CORRECT_RULES, Rules, audit_contract  # noqa: E402


MUTATIONS: tuple[tuple[str, Rules, str], ...] = (
    (
        "global-generation-floor",
        replace(CORRECT_RULES, global_generation_order=True),
        "PER_OPERATION_OPAQUE_GENERATION",
    ),
    (
        "retired-token-replay",
        replace(CORRECT_RULES, allow_retired_replay=True),
        "ONE_SHOT_RETIREMENT",
    ),
    (
        "prepared-ambiguity-aborts",
        replace(CORRECT_RULES, ambiguity_aborts=True),
        "PREPARED_FAULTING",
    ),
    (
        "armed-fault-without-quarantine",
        replace(CORRECT_RULES, armed_fault_without_quarantine=True),
        "ARMED_FAULTING",
    ),
    (
        "prearmed-target-claim-dropped",
        replace(CORRECT_RULES, drop_prearmed_claim_fault=True),
        "PREARMED_TARGET_CLAIM_FAULT",
    ),
    (
        "second-winner",
        replace(CORRECT_RULES, allow_second_winner=True),
        "SINGLE_WINNER",
    ),
    (
        "publishing-interrupted",
        replace(CORRECT_RULES, interrupt_publishing=True),
        "PUBLISHING_INDIVISIBLE",
    ),
    (
        "quarantined-retirement",
        replace(CORRECT_RULES, allow_retire_with_quarantine=True),
        "QUARANTINE_RETIREMENT",
    ),
    (
        "quarantine-blocks-drain",
        replace(CORRECT_RULES, quarantine_blocks_drain=True),
        "QUARANTINE_ALLOWS_DRAIN",
    ),
    (
        "retirement-without-drain",
        replace(CORRECT_RULES, allow_retire_without_drain=True),
        "DRAIN_BEFORE_RETIREMENT",
    ),
    (
        "caller-owned-online-result",
        replace(CORRECT_RULES, trust_claimed_online=True),
        "INTERNAL_ONLINE_OBSERVATION",
    ),
    (
        "target-tuple-ignored",
        replace(CORRECT_RULES, ignore_target_tuple=True),
        "EXACT_TARGET_TUPLE",
    ),
    (
        "c-to-k-cross-closure",
        replace(CORRECT_RULES, allow_c_to_k=True),
        "K_C_P_E_U_TERMINAL_RULES",
    ),
    (
        "p-generic-park",
        replace(CORRECT_RULES, allow_p_park=True),
        "P_INTERLOCK",
    ),
    (
        "panic-without-interlock",
        replace(CORRECT_RULES, panicked_without_interlock=True),
        "P_INTERLOCK",
    ),
    (
        "quarantine-first-cause-replaced",
        replace(CORRECT_RULES, replace_quarantine=True),
        "QUARANTINE_STICKY",
    ),
    (
        "terminal-record-mutated",
        replace(CORRECT_RULES, mutable_terminal=True),
        "TERMINAL_IMMUTABILITY",
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
    print("PASS intended-check mutation suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
