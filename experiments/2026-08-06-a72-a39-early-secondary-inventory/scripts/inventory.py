#!/usr/bin/env python3
"""Validate the pinned A39 early-secondary source inventory."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INVENTORY = ROOT / "experiments/2026-08-06-a72-a39-early-secondary-inventory/results/early-secondary-inventory.tsv"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with INVENTORY.open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    ids = [row["id"] for row in rows]
    require(ids == [f"A39-{index:02d}" for index in range(1, 18)],
            "A39 inventory ids are not canonical")
    require(sum(row["decision"] == "OPEN_TERMINAL_GUARD" for row in rows) == 15,
            "early terminal branch count changed")
    require(sum(row["decision"] == "COVERAGE_NOT_EARLY" for row in rows) == 2,
            "P32 coverage rows changed")
    require(any(row["branch"] == "CPU_PANIC_KERNEL" for row in rows),
            "panic branch missing")
    require(any(row["branch"] == "cpu_die_early" for row in rows),
            "cpu_die_early branch missing")
    require(all("no exact P32" in row["current_guard"] or
                "no P32" in row["current_guard"] or
                "no separate P32" in row["current_guard"] or
                "P32 guards" in row["current_guard"] or
                "p32_valid" in row["current_guard"] or
                "P32 publication" in row["current_guard"] or
                "P30E marker" in row["current_guard"] or
                "no target" in row["current_guard"] or
                "does not run" in row["current_guard"]
                for row in rows if row["decision"] == "OPEN_TERMINAL_GUARD"),
            "an open row lacks an explicit guard observation")
    print("claim=A39_EARLY_SECONDARY_SOURCE_INVENTORY")
    print("rows=17")
    print("early_terminal_branches=15")
    print("p32_not_early_coverage_rows=2")
    print("cpu_die_early_present_clear=OBSERVED")
    print("cpu_panic_kernel_unconditional=OBSERVED")
    print("terminal_guard_closure=OPEN")
    print("device_action=NOT_PERFORMED")
    print("status=PASS_A39_INVENTORY_BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
