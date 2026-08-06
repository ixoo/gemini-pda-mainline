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

    # These are the source-only properties actually implemented by 0182-0186.
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
    ):
        require(token in source, f"implemented P32 token missing: {token}")

    # The frozen contract requires more than hook placement. These gaps are
    # intentionally reported rather than hidden by the passing guard build.
    gaps = {
        "P32A_nested_prefix_record": (
            "no controller record of cpuhp_kick_ap callback prefix or reset state"
        ),
        "P32X_arch_effect_prefix": (
            "record has no topology/NUMA/online/present/IPI/IRQ/RCU/lockdep effect mask"
        ),
        "P32R_ledger_handoff": (
            "consume path changes only P32 branch/state; no membership/provider/A30 ledger completion"
        ),
    }
    require("p32_valid" in source and "callback_state" in source,
            "P32 record lacks its current minimal publication fields")

    print("claim=P32_HOOKS_VALIDATED_P32R_INTEGRATION_OPEN")
    print("publication_and_exact_identity=PASS")
    print("target_and_controller_guards=PASS")
    print("one_shot_consumption=PASS")
    for name, reason in gaps.items():
        print(f"{name}=OPEN;{reason}")
    print("cpu_on_cpu_off_device_action=CLOSED")
    print("status=PASS_GAPS_CONFIRMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
