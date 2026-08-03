#!/usr/bin/env python3
"""Mutation tests for the CPU8 held-online source contract."""

import argparse
import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("hold_validator", HERE / "validate_patches.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"mutation anchor changed: {old!r}")
    return text.replace(old, new, 1)


def rejected(files: dict[str, str], name: str, old: str, new: str) -> None:
    changed = files.copy()
    changed[name] = replace_once(changed[name], old, new)
    try:
        VALIDATOR.validate_files(changed)
    except VALIDATOR.ValidationError:
        return
    raise AssertionError(f"mutation survived: {name}: {old}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    files = VALIDATOR.read_source(args.source)
    VALIDATOR.validate_files(files)
    mutations = (
        ("cpu", "if (cpu == 8 || cpu == 9)", "if (cpu == 9)"),
        ("cpu", "return -EPERM", "return 0"),
        ("hps", "cpu_id_min == 8 && cpu_id_max == 9", "cpu_id_min == 0 && cpu_id_max == 9"),
        ("hps", "target_cores = 1", "target_cores = 0"),
        ("psci", "smp_call_function_single(8", "smp_call_function_single(7"),
        ("psci", "observed_cpu != 8", "observed_cpu != 7"),
        ("psci", "!cpu_online(8)", "!cpu_online(7)"),
        ("psci", "cpu_online(9)", "cpu_online(7)"),
        ("psci", "msecs_to_jiffies(5000)", "msecs_to_jiffies(15000)"),
        ("psci", "msecs_to_jiffies(1000)", "msecs_to_jiffies(11000)"),
        ("psci", "result=pass sample=2 cpu=8 cpu8=1 cpu9=0", "result=pass sample=1 cpu=8 cpu8=1 cpu9=0"),
    )
    for mutation in mutations:
        rejected(files, *mutation)
    print(f"PASS: held-online source contract and {len(mutations)} mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
