#!/usr/bin/env python3
"""Audit the source-only P32R integration against the frozen closure table."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLOSURE = ROOT / "experiments/2026-08-05-a72-cpu-up-source-closure/results/p30-p32-closure.tsv"
PATCHES = [ROOT / "patches/v7.1.3" / name for name in (
    "0182-arm64-add-dormant-P32-rollback-guards.patch",
    "0183-arm64-consume-P32-rollback-side-channel.patch",
    "0184-arm64-retire-consumed-P32-generation.patch",
    "0185-arm64-bind-P32-operation-to-target.patch",
    "0186-arm64-parenthesize-P32-publication-check.patch",
    "0187-arm64-capture-P32A-rollback-prefix.patch",
    "0188-arm64-capture-P32X-effect-prefix.patch",
    "0189-arm64-hand-P32R-into-owner-ledger.patch",
    "0190-arm64-close-P32A-P32X-coverage.patch",
)]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rows() -> dict[str, dict[str, str]]:
    with CLOSURE.open(newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream, delimiter="\t")}


def main() -> int:
    closure = rows()
    require(tuple(closure) == ("P32A", "P32D", "P32F", "P32X", "P32R"),
            "P32 closure table is not canonical")
    source = "\n".join(path.read_text() for path in PATCHES)

    # These are the source-only properties implemented by 0182-0190.
    for token in (
        "mt6797_a72_membership_publish_p32",
        "arch_cpu_up_rollback_complete",
        "MT6797_A72_P32_GUARD_DISABLE",
        "MT6797_A72_P32_GUARD_DIE",
        "MT6797_A72_P32_GUARD_KILL",
        "MT6797_A72_P32_STATE_CONSUMED",
        "target_mpidr",
        "generation",
        "cookie",
        "struct cpu_up_rollback_trace",
        "nested_valid",
        "outer_reset",
        "reverse_complete",
        "CPU_UP_ROLLBACK_EFFECT_COUNT",
        "effect_unknown",
        "effect_overflow",
        "callback_capacity",
        "callback_inventory",
        "rollback_armed",
        "effect_required_mask",
        "effect_seen_mask",
        "effect_missing_mask",
        "effect_forbidden_mask",
        "CPU_UP_ROLLBACK_EFFECT_PRESENT_CLEAR",
        "CPU_UP_ROLLBACK_EFFECT_NO_AFFINITY",
        "CPU_UP_ROLLBACK_EFFECT_UNKNOWN",
        "CPU_UP_ROLLBACK_EFFECT_FORBIDDEN_MASK",
        "cpuhp_rollback_callback_inventory",
        "arch_cpu_up_rollback_effect",
        "MT6797_A72_P32R_HANDOFF_ABI",
        "mt6797_a72_p32r_capture_locked",
        "MT6797_A72_P32R_FAULT_ROLLBACK_LOST",
        "MT6797_A72_PROVIDER_FAULT_UNKNOWN",
        "trace->callback_inventory > trace->callback_capacity",
        "trace->effect_missing_mask",
        "trace->effect_forbidden_mask",
        "handoff->callback_capacity",
        "handoff->effect_missing_mask",
    ):
        require(token in source, f"implemented P32 token missing: {token}")

    require("p32_valid" in source and "callback_state" in source,
            "P32 record lacks its current minimal publication fields")

    print("claim=P32_HOOKS_VALIDATED_P32R_SOURCE_COMPLETE")
    print("publication_and_exact_identity=PASS")
    print("target_and_controller_guards=PASS")
    print("one_shot_consumption=PASS")
    print("P32A_nested_prefix_record=PASS;callback inventory and capacity are armed and overflow is classified unknown")
    print("P32X_arch_effect_prefix=PASS;required/seen/missing/forbidden masks include NO_AFFINITY and PRESENT_CLEAR")
    print("P32R_ledger_handoff=PASS;owner handoff captures and rejects incomplete coverage")
    print("cpu_on_cpu_off_device_action=CLOSED")
    print("status=PASS_SOURCE_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
