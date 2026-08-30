#!/usr/bin/env python3
"""Reject decision-changing mutations of the READY predicate diagnostic."""

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


def replace_in_function(
    path: Path, signature: str, old: str, new: str
) -> None:
    text = path.read_text(encoding="utf-8")
    body = validate_source.function(text, signature)
    mutated = replace_once(body, old, new)
    path.write_text(text.replace(body, mutated, 1), encoding="utf-8")


def mutate_profile_bypass(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(replace_once(
        text,
        ".validate_plan = mt6797_a72_validate_cap_plan,",
        ".validate_plan = mt6797_a72_validate_cap_plan_contract,",
    ), encoding="utf-8")


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    wrapper = "mt6797_a72_validate_cap_plan("
    evidence = "mt6797_a72_bound_expectation_diagnostic("
    plan = "mt6797_a72_plan_validation_diagnostic("
    return [
        ("accept-on-failure", lambda p: replace_in_function(
            p, wrapper, "\treturn ret;", "\treturn 0;")),
        ("log-on-success", lambda p: replace_in_function(
            p, wrapper, "\tif (ret)\n", "\tif (true)\n")),
        ("bypass-wrapper", mutate_profile_bypass),
        ("drop-evidence-bit", lambda p: replace_in_function(
            p, evidence,
            "\t\tmask |= BIT_ULL(A72_EVD_ABI);\n", "")),
        ("drop-plan-bit", lambda p: replace_in_function(
            p, plan, "\t\tmask |= BIT_ULL(A72_PVD_ABI);\n", "")),
        ("add-cpu-up", lambda p: replace_in_function(
            p, wrapper, "\tint ret;\n", "\tint ret;\n\n\tcpu_up(8);\n")),
        ("add-cpu-request", lambda p: replace_in_function(
            p, wrapper, "\tint ret;\n", "\tint ret;\n\n\tadd_cpu(8);\n")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validate_source.validate(source)
    rejected = 0
    with tempfile.TemporaryDirectory(
        prefix="a72-ready-predicate-mutations-"
    ) as name:
        temporary = Path(name)
        for index, (label, mutate) in enumerate(mutations()):
            root = temporary / str(index)
            target = root / source_edits.TARGET
            target.parent.mkdir(parents=True)
            shutil.copyfile(source / source_edits.TARGET, target)
            mutate(target)
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
