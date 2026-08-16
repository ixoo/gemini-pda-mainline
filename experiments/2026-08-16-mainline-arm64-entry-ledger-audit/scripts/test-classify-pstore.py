#!/usr/bin/env python3
"""Exercise every independent entry-ledger subset and rejected capture."""

from __future__ import annotations

import importlib.util
import itertools
from pathlib import Path
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("entry_classify", SCRIPT_DIR / "classify-pstore.py")
assert spec and spec.loader
classifier = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = classifier
spec.loader.exec_module(classifier)


def record(stage: str, slot: int, crc: str | None = None) -> str:
    value = crc if crc is not None else classifier.integrity(stage, slot)
    return (
        f"{classifier.PREFIX} token={classifier.TOKEN} "
        f"stage={stage} slot={slot} crc32={value}\n"
    )


def run_case(lines: list[str]):
    with tempfile.TemporaryDirectory(prefix="gemini-entry-ledger-test-") as raw:
        root = Path(raw)
        for index, line in enumerate(lines):
            (root / f"dmesg-ramoops-{index}").write_text(line, encoding="utf-8")
        return classifier.classify(root)


def main() -> None:
    stages = list(classifier.STAGES)
    accepted = 0
    for mask in itertools.product((False, True), repeat=len(stages)):
        selected = [stage for stage, include in zip(stages, mask, strict=True) if include]
        result = run_case([record(*stage) for stage in selected])
        if not selected:
            wanted = "no-stage"
        else:
            wanted = f"through-{selected[-1][0]}"
        if result.result != wanted:
            raise AssertionError(f"subset {mask}: {result.result} != {wanted}")
        expected_missing = tuple(
            slot
            for _, slot in stages
            if selected
            and slot < selected[-1][1]
            and stage_missing(slot, selected)
        )
        if result.missing_before_highest != expected_missing:
            raise AssertionError(f"subset {mask}: missing-stage classification drift")
        accepted += 1

    rejected = (
        [record(*stages[0]), record(*stages[0])],
        [record("primary-entry", 171, "00000000")],
        [record("post-mmu", 171)],
        [f"{classifier.PREFIX} token={classifier.TOKEN} truncated\n"],
        [f"{classifier.PREFIX} token=FOREIGN stage=post-mmu slot=173 crc32=00000000\n"],
        [f"FOREIGN_PREFIX token={classifier.TOKEN} stage=post-mmu slot=173 crc32=00000000\n"],
        [record(*stages[2]), f"{classifier.PREFIX} malformed\n"],
    )
    count = sum(run_case(list(case)).result == "rejected-attribution" for case in rejected)
    if count != len(rejected):
        raise AssertionError(f"only {count} of {len(rejected)} invalid captures rejected")
    print("validation=arm64-entry-ledger-classifier")
    print(f"independent_stage_subsets_accepted={accepted}")
    print(f"invalid_captures_rejected={count}")
    print("result=pass")


def stage_missing(slot: int, selected: list[tuple[str, int]]) -> bool:
    return all(selected_slot != slot for _, selected_slot in selected)


if __name__ == "__main__":
    main()
