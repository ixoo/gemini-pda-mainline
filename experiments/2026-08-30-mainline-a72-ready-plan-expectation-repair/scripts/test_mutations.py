#!/usr/bin/env python3
"""Reject decision-changing READY-plan expectation-repair mutations."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile
from typing import Callable

import source_edits
import validate_source


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor count changed: {old!r}")
    return text.replace(old, new, 1)


def mutate_file(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(replace_once(text, old, new), encoding="utf-8")


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    return [
        ("omit-early-845719", lambda p: mutate_file(
            p, source_edits.EARLY_NEW, source_edits.EARLY_OLD)),
        ("restore-present-cache-mismatch", lambda p: mutate_file(
            p, source_edits.PRESENT_NEW, source_edits.PRESENT_OLD)),
        ("restore-required-cache-mismatch", lambda p: mutate_file(
            p, source_edits.REQUIRED_NEW, source_edits.REQUIRED_OLD)),
        ("restore-production-smc", lambda p: mutate_file(
            p, source_edits.POLICY_NEW, source_edits.POLICY_OLD)),
        ("restore-diagnostic-smc", lambda p: mutate_file(
            p, source_edits.DIAG_NEW, source_edits.DIAG_OLD)),
        ("change-fixture-to-none", lambda p: mutate_file(
            p,
            "policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_SMC &&",
            "policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_NONE &&")),
        ("bypass-wrapper", lambda p: mutate_file(
            p, ".validate_plan = mt6797_a72_validate_cap_plan,",
            ".validate_plan = mt6797_a72_validate_cap_plan_contract,")),
        ("add-cpu-up", lambda p: mutate_file(
            p, "\tint ret;\n\n\tret = mt6797_a72_validate_cap_plan_contract(plan);",
            "\tint ret;\n\n\tcpu_up(8);\n"
            "\tret = mt6797_a72_validate_cap_plan_contract(plan);")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validate_source.validate(source)
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-ready-repair-mutations-") as name:
        temporary = Path(name)
        for index, (label, change) in enumerate(mutations()):
            root = temporary / str(index)
            target = root / source_edits.TARGET
            target.parent.mkdir(parents=True)
            shutil.copyfile(source / source_edits.TARGET, target)
            change(target)
            try:
                validate_source.validate(root)
            except validate_source.ValidationError:
                rejected += 1
            else:
                raise SystemExit(f"unsafe mutation accepted: {label}")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
