#!/usr/bin/env python3
"""Exercise valid and rejected pre-ramoops pstore classifications."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("preledger_classify", SCRIPT_DIR / "classify-pstore.py")
assert spec and spec.loader
classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifier)


def record(stage: str, slot: int, crc: str | None = None) -> str:
    value = crc if crc is not None else classifier.integrity(stage, slot)
    return (
        f"{classifier.PREFIX} token={classifier.TOKEN} "
        f"stage={stage} slot={slot} crc32={value}\n"
    )


def run_case(lines: list[str]) -> tuple[str, str, list[int]]:
    with tempfile.TemporaryDirectory(prefix="gemini-preledger-test-") as raw:
        root = Path(raw)
        for index, line in enumerate(lines):
            (root / f"dmesg-ramoops-{index}").write_text(line, encoding="utf-8")
        return classifier.classify(root)


def main() -> None:
    stages = list(classifier.STAGES)
    expected = [
        "no-stage",
        "through-reserved-scan",
        "through-early-initcall",
        "through-core-initcall",
        "through-postcore-initcall",
    ]
    for count, wanted in enumerate(expected):
        result, _, _ = run_case([record(*stage) for stage in stages[:count]])
        if result != wanted:
            raise AssertionError(f"valid prefix {count}: {result} != {wanted}")

    rejected = (
        [record(*stages[1])],
        [record(*stages[0]), record(*stages[0])],
        [record("reserved-scan", 171, "00000000")],
        [record("core-initcall", 171)],
        [f"{classifier.PREFIX} token={classifier.TOKEN} truncated\n"],
    )
    count = 0
    for case in rejected:
        result, _, _ = run_case(case)
        if result == "rejected-attribution":
            count += 1
    if count != len(rejected):
        raise AssertionError(f"only {count} of {len(rejected)} invalid captures rejected")
    print("validation=mainline-pre-ramoops-ledger-classifier")
    print("valid_prefixes_accepted=5")
    print(f"invalid_captures_rejected={count}")
    print("result=pass")


if __name__ == "__main__":
    main()
