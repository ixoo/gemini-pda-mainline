#!/usr/bin/env python3
"""Reject unsafe mutations of the dormant entry-validation source."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import tempfile
from typing import Callable


SCRIPT_DIR = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EDITS = load("source_edits")
VALIDATE = load("validate_source")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"mutation anchor absent: {old}")
    path.write_text(text.replace(old, new, 1))


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    header = Path("arch/arm64/include/asm/late_cpu_profile.h")
    core = Path("arch/arm64/kernel/late_cpu_profile.c")
    smp = Path("arch/arm64/kernel/smp.c")
    return [
        ("remove-expected-pair", lambda r: replace(r / header, "\tstruct arm64_late_cpu_expected_pair expected_pair;\n", "")),
        ("partial-valid-mask", lambda r: replace(r / core, "expected->valid != ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK", "!(expected->valid & ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK)")),
        ("allow-empty-source", lambda r: replace(r / core, "\t    !memchr_inv(expected->source_identity, 0,\n\t\t\t   sizeof(expected->source_identity)) ||\n", "")),
        ("restore-init-only-helper", lambda r: replace(r / core, "\t    !memchr_inv(expected->source_identity, 0,\n\t\t\t   sizeof(expected->source_identity)) ||\n", "\t    late_profile_identity_empty(expected->source_identity) ||\n")),
        ("allow-empty-capsule", lambda r: replace(r / core, "!expected->capsule_identity[target] ||\n\t\t    ", "")),
        ("drop-raw-ctr", lambda r: replace(r / core, "\t       expected->ctr == read_cpuid_cachetype() &&\n", "")),
        ("drop-clidr", lambda r: replace(r / core, "\t       expected->clidr_el1 == read_sysreg(clidr_el1) &&\n", "")),
        ("drop-aa64-field", lambda r: replace(r / core, "\t       expected->id_aa64isar1 == info->reg_id_aa64isar1 &&\n", "")),
        ("drop-a32-field", lambda r: replace(r / core, "\t       expected->id_mmfr3 == aarch32->reg_id_mmfr3 &&\n", "")),
        ("accept-mismatch", lambda r: replace(r / core, "? 0 : -ERANGE;", "? 0 : 0;")),
        ("remove-current-cpu-check", lambda r: replace(r / core, "cpu != smp_processor_id() || ", "")),
        ("remove-ready-acquire-comment", lambda r: replace(r / core, "\t/* Pairs with READY publication of late_plan and late_receipt. */\n", "")),
        ("validator-before-cpuinfo", lambda r: replace(r / smp, "\tcpuinfo_store_cpu();\n\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu);\n", "\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu);\n\tcpuinfo_store_cpu();\n")),
        ("validator-after-notify", lambda r: replace(r / smp, "\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu);\n", "\tnotify_cpu_starting(cpu);\n\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu);\n")),
        ("remove-failure-status", lambda r: replace(r / smp, "\t\tupdate_cpu_boot_status(CPU_STUCK_IN_KERNEL);\n", "")),
        ("replace-park-with-die", lambda r: replace(r / smp, "\t\tcpu_park_loop();\n", "\t\tcpu_die_early();\n")),
        ("add-cpu-off", lambda r: replace(r / core, "\treturn late_expected_target_matches", "\t/* cpu_off */\n\treturn late_expected_target_matches")),
    ]


def prepare(source_root: Path, destination: Path) -> None:
    for relative in EDITS.PARENT_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    EDITS.apply_schema(destination)
    EDITS.apply_validator(destination)
    EDITS.apply_runtime_fix(destination)
    VALIDATE.validate_runtime_fix(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-attestation-mutations-") as name:
        base = Path(name) / "base"
        prepare(source_root, base)
        for mutation_name, mutate in mutations():
            candidate = Path(name) / mutation_name
            shutil.copytree(base, candidate)
            mutate(candidate)
            try:
                VALIDATE.validate_runtime_fix(candidate)
            except VALIDATE.ValidationError:
                rejected += 1
            else:
                raise AssertionError(f"unsafe source mutation accepted: {mutation_name}")

    print("validation=mainline-a72-attestation-source-mutations-pass")
    print("positive_cases=1")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
