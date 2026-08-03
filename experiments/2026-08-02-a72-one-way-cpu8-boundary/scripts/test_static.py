#!/usr/bin/env python3
"""Mutation tests for the one-way CPU8 applied-source validator."""

from __future__ import annotations

import argparse
from pathlib import Path

from validate_patches import ValidationError, read_source, validate_files


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"mutation anchor count for {old!r}: {text.count(old)}")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    baseline = read_source(args.source)
    validate_files(baseline)
    mutations = (
        ("common", "mtk_wdt_recovery_arm(12, state)", "mtk_wdt_recovery_arm(20, state)"),
        ("common", "if (ret && !state->owned)", "if (ret)"),
        ("wdt", "timeout != 12", "timeout != 20"),
        ("psci", "if (cpu == 9) {", "if (cpu == 10) {"),
        ("psci", "if (cpu == 8 || cpu == 9)", "if (cpu == 9)"),
        ("psci", 'stage = "isolation-write"', 'stage = "isolation-skipped"'),
        ("psci", "mt6797_a72_one_way_dcm_enable(cpu)", "dcm_mcusys_mp2_sync_dcm(1)"),
        ("smp", "secondary_completed && cpu_online(cpu)", "cpu_online(cpu)"),
        ("idvfs", "calibration_first != calibration_second", "false"),
        ("idvfs", "(selector_second & 0xfff) != 0x8fb", "(selector_second & 0xfff) != 0x8fa"),
        ("dcm", "(snapshot.final & snapshot.mask) != 0x0d", "false"),
        ("kconfig", "depends on PSTORE && PSTORE_CONSOLE && PSTORE_RAM", "depends on PSTORE"),
    )
    for name, old, new in mutations:
        changed = dict(baseline)
        changed[name] = replace_once(changed[name], old, new)
        try:
            validate_files(changed)
        except ValidationError:
            continue
        raise AssertionError(f"mutation unexpectedly passed: {name}: {old}")
    print(f"PASS: {len(mutations)} one-way CPU8 validator mutations rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
