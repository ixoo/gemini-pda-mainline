#!/usr/bin/env python3
"""Reject decision-changing READY-plan value-observer mutations."""

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


def mutate_wrapper(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(source_edits.NEW) != 1:
        raise ValueError("exact observer wrapper count changed")
    changed = replace_once(source_edits.NEW, old, new)
    path.write_text(text.replace(source_edits.NEW, changed, 1), encoding="utf-8")


def mutate_file(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(replace_once(text, old, new), encoding="utf-8")


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    return [
        ("accept-on-failure", lambda p: mutate_wrapper(
            p, "\treturn ret;", "\treturn 0;")),
        ("log-on-success", lambda p: mutate_wrapper(
            p, "\tif (ret) {", "\tif (true) {")),
        ("drop-null-guard", lambda p: mutate_wrapper(
            p, "\t\tif (plan)\n", "\t\tif (true)\n")),
        ("duplicate-target-bitmap", lambda p: mutate_wrapper(
            p, "plan->target[1].local_caps", "plan->target[0].local_caps")),
        ("duplicate-conduit", lambda p: mutate_wrapper(
            p, "plan->evidence.target_policy[1].smccc_conduit",
            "plan->evidence.target_policy[0].smccc_conduit")),
        ("bypass-wrapper", lambda p: mutate_file(
            p, ".validate_plan = mt6797_a72_validate_cap_plan,",
            ".validate_plan = mt6797_a72_validate_cap_plan_contract,")),
        ("add-cpu-up", lambda p: mutate_wrapper(
            p, "\tint ret;\n", "\tint ret;\n\n\tcpu_up(8);\n")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validate_source.validate(source)
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-ready-value-mutations-") as name:
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
