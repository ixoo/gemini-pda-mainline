#!/usr/bin/env python3
"""Reject unsafe mutations of the arm64 entry-ledger design."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("entry_oracle", SCRIPT_DIR / "oracle.py")
assert spec and spec.loader
oracle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = oracle
spec.loader.exec_module(oracle)


def stage_mutation(design, index: int, **changes):
    stages = list(design.stages)
    stages[index] = replace(stages[index], **changes)
    return replace(design, stages=tuple(stages))


def rejected(design) -> bool:
    try:
        oracle.validate(design)
    except AssertionError:
        return True
    return False


def main() -> None:
    design = oracle.exact_design()
    oracle.validate(design)
    cases = (
        replace(design, stages=design.stages[:3]),
        stage_mutation(design, 0, name="entry"),
        stage_mutation(design, 0, slot=170),
        replace(design, reservation=(0x44410000, 0x444BE000)),
        stage_mutation(design, 0, require_mmu_off=False),
        stage_mutation(design, 0, require_dcache_off=False),
        stage_mutation(design, 0, require_current_el=False),
        stage_mutation(design, 0, clobbers=design.stages[0].clobbers | {"x0"}),
        stage_mutation(design, 1, hook="inside-__primary_switch"),
        stage_mutation(design, 1, require_all_header_fingerprint=False),
        stage_mutation(design, 2, mode="linear-map"),
        stage_mutation(design, 2, independent_of_prior_write=False),
        stage_mutation(design, 3, require_exact_dt=False),
        stage_mutation(design, 3, require_memblock_reservation=False),
        stage_mutation(design, 3, data_before_start_before_size=False),
        stage_mutation(design, 3, full_readback=False),
        stage_mutation(design, 0, aligned_access_only=False),
        replace(design, normal_ramoops_bypassed=False),
        replace(design, default_off=False),
        replace(design, runtime_effects=frozenset({"retained-ram-record", "cpu-up"})),
    )
    failures = [index for index, case in enumerate(cases, 1) if not rejected(case)]
    if failures:
        raise AssertionError(f"unsafe mutations accepted: {failures}")
    print("validation=arm64-entry-ledger-design-mutations")
    print(f"negative_mutations_rejected={len(cases)}")
    print("result=pass")


if __name__ == "__main__":
    main()
