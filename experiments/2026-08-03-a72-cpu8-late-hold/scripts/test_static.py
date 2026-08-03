#!/usr/bin/env python3
"""Mutation tests for the CPU8 late-hold contract."""

import argparse
import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("late_validator", HERE / "validate_patch.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def rejected(text: str, old: str, new: str) -> None:
    if text.count(old) != 1:
        raise AssertionError(f"mutation anchor changed: {old!r}")
    changed = text.replace(old, new, 1)
    try:
        VALIDATOR.validate_source(changed)
    except VALIDATOR.ValidationError:
        return
    raise AssertionError(f"mutation survived: {old}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    text = VALIDATOR.read_source(args.source)
    VALIDATOR.validate_source(text)
    mutations = (
        ("smp_call_function_single(8", "smp_call_function_single(7"),
        ("observed_cpu != 8", "observed_cpu != 7"),
        ("!cpu_online(8)", "!cpu_online(7)"),
        ("cpu_online(9)", "cpu_online(7)"),
        ("sample < 3", "sample < 2"),
        ("sample == 1 ? 5000 : 4000", "sample == 1 ? 5000 : 9000"),
        (
            "result=pass sample=3 cpu=8 cpu8=1 cpu9=0 hits=3",
            "result=pass sample=2 cpu=8 cpu8=1 cpu9=0 hits=2",
        ),
    )
    for old, new in mutations:
        rejected(text, old, new)
    print(f"PASS: late-hold source contract and {len(mutations)} mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
