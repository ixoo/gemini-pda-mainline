#!/usr/bin/env python3
"""Mutation tests for the CPU9 cluster-reuse contract."""

import argparse
import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cpu9_validator", HERE / "validate_patch.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def rejected(sources: dict[str, str], name: str, old: str, new: str) -> None:
    if sources[name].count(old) != 1:
        raise AssertionError(f"mutation anchor changed: {name}: {old!r}")
    changed = dict(sources)
    changed[name] = sources[name].replace(old, new, 1)
    try:
        VALIDATOR.validate_source(changed)
    except VALIDATOR.ValidationError:
        return
    raise AssertionError(f"mutation survived: {name}: {old}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    sources = VALIDATOR.read_sources(args.source)
    sources["cpu"] = (args.source / "kernel/cpu.c").read_text()
    VALIDATOR.validate_source(sources)
    mutations = (
        ("psci", "if (cpu != 9)", "if (cpu != 8)"),
        ("psci", "atomic_xchg(&mt6797_a72_cpu9_attempted, 1)", "atomic_read(&mt6797_a72_cpu9_attempted)"),
        ("psci", "!(g_cl2_online & 1)", "(g_cl2_online & 1)"),
        ("psci", "!cpu_online(8) || cpu_online(9)", "cpu_online(8) || cpu_online(9)"),
        ("psci", "psci_ops.cpu_on(cpu_logical_map(cpu), __pa(secondary_entry))", "psci_ops.cpu_on(cpu_logical_map(8), __pa(secondary_entry))"),
        ("psci", "WRITE_ONCE(mt6797_a72_cpu9_psci_accepted, true)", "WRITE_ONCE(mt6797_a72_cpu9_psci_accepted, false)"),
        ("psci", "smp_call_function_single(8", "smp_call_function_single(7"),
        ("psci", "smp_call_function_single(9", "smp_call_function_single(8"),
        ("psci", "observed_cpu9 != 9", "observed_cpu9 != 8"),
        ("psci", "hits8 != hits9", "hits8 == hits9"),
        ("psci", "sample < 3", "sample < 2"),
        ("psci", "sample == 1 ? 5000 : 4000", "sample == 1 ? 5000 : 9000"),
        ("psci", "result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3", "result=pass sample=2 cpu8=8 cpu9=9 online8=1 online9=1 hits8=2 hits9=2"),
        ("smp", "|| cpu == 9", "|| cpu == 7"),
        ("smp", "&& cpu != 9", "&& cpu != 8"),
        ("kconfig", "depends on MTK_A72_ONE_WAY_CPU8", "depends on MTK_A72_TRANSITION_OBSERVER"),
    )
    for name, old, new in mutations:
        rejected(sources, name, old, new)
    print(f"PASS: CPU9 cluster-reuse source contract and {len(mutations)} mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
