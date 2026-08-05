#!/usr/bin/env python3
"""Require unsafe closed-owner rule mutations to fail intended invariants."""

from __future__ import annotations

import sys
from dataclasses import replace

sys.dont_write_bytecode = True

from oracle import CORRECT_RULES, Rules, audit_contract  # noqa: E402


MUTATIONS: tuple[tuple[str, Rules, str], ...] = (
    (
        "caller-readiness-authorizes",
        replace(CORRECT_RULES, trust_caller_readiness=True),
        "CALLER_READINESS_NOT_AUTHORITY",
    ),
    (
        "bounded-list-authorizes",
        replace(CORRECT_RULES, bounded_list_sufficient=True),
        "BOUNDED_LIST_NOT_AUTHORITY",
    ),
    (
        "a26-veto-ignored",
        replace(CORRECT_RULES, ignore_a26_veto=True),
        "A26_VETO_REQUIRED",
    ),
    (
        "all-applicable-review-inferred",
        replace(CORRECT_RULES, infer_all_applicable_review=True),
        "ALL_APPLICABLE_REVIEW_REMAINS_FALSE",
    ),
    (
        "implementation-enabled-inferred",
        replace(CORRECT_RULES, infer_implementation_enabled=True),
        "IMPLEMENTATION_ENABLED_REMAINS_FALSE",
    ),
    (
        "malformed-identity-enters-owner",
        replace(CORRECT_RULES, accept_malformed_identity=True),
        "EXACT_REQUEST_IDENTITY",
    ),
    (
        "p31-entered-before-denial",
        replace(CORRECT_RULES, enter_p31=True),
        "P31_NOT_ENTERED",
    ),
    (
        "a38-consumed-before-denial",
        replace(CORRECT_RULES, consume_a38=True),
        "A38_NOT_CONSUMED",
    ),
    (
        "attempt-consumed-before-denial",
        replace(CORRECT_RULES, consume_attempt=True),
        "ATTEMPT_NOT_CONSUMED",
    ),
    (
        "live-token-allocated",
        replace(CORRECT_RULES, allocate_live_token=True),
        "NO_LIVE_TOKEN",
    ),
    (
        "membership-enters-frozen",
        replace(CORRECT_RULES, enter_frozen=True),
        "MEMBERSHIP_PHASE_UNINITIALIZED",
    ),
    (
        "p17-published",
        replace(CORRECT_RULES, publish_p17=True),
        "P17_NOT_PUBLISHED",
    ),
    (
        "p18-published",
        replace(CORRECT_RULES, publish_p18=True),
        "P18_NOT_PUBLISHED",
    ),
    (
        "p30-handoff",
        replace(CORRECT_RULES, handoff_p30=True),
        "P30_NOT_REACHED",
    ),
    (
        "provider-mutated",
        replace(CORRECT_RULES, mutate_provider=True),
        "PROVIDER_UNTOUCHED",
    ),
    (
        "membership-committed",
        replace(CORRECT_RULES, commit_member=True),
        "MEMBERSHIP_UNTOUCHED",
    ),
    (
        "hardware-mutated",
        replace(CORRECT_RULES, mutate_hardware=True),
        "HARDWARE_UNTOUCHED",
    ),
    (
        "cpu-on-issued",
        replace(CORRECT_RULES, issue_cpu_on=True),
        "CPU_ON_NOT_ISSUED",
    ),
    (
        "p14-published",
        replace(CORRECT_RULES, publish_p14=True),
        "P14_NOT_PUBLISHED",
    ),
    (
        "p15-published",
        replace(CORRECT_RULES, publish_p15=True),
        "P15_NOT_PUBLISHED",
    ),
    (
        "a33-committed",
        replace(CORRECT_RULES, commit_a33=True),
        "A33_NOT_COMMITTED",
    ),
    (
        "p32-entered",
        replace(CORRECT_RULES, enter_p32=True),
        "P32_NOT_ENTERED",
    ),
    (
        "denial-record-mutated",
        replace(CORRECT_RULES, mutable_denial=True),
        "DENIAL_IMMUTABLE",
    ),
    (
        "denial-acknowledged",
        replace(CORRECT_RULES, allow_ack=True),
        "ACK_NOT_AUTHORITY",
    ),
    (
        "reset-opens-owner",
        replace(CORRECT_RULES, allow_reset=True),
        "RESET_NOT_AUTHORITY",
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
    print("PASS intended-check CLOSED-owner mutation suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
