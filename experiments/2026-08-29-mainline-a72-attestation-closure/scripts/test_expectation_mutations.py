#!/usr/bin/env python3
"""Reject unsafe slice-6 expected/current planning mutations."""

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


EDITS = load("expectation_edits")
VALIDATE = load("validate_expectation_source")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"mutation anchor absent: {old}")
    path.write_text(text.replace(old, new, 1))


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    core = Path("arch/arm64/kernel/late_cpu_profile.c")
    cpufeature = Path("arch/arm64/kernel/cpufeature.c")
    errata = Path("arch/arm64/kernel/cpu_errata.c")
    profile = Path("arch/arm64/kernel/mt6797_psci.c")
    return [
        ("copy-expected-into-target-cap", lambda r: replace(
            r / core,
            "\tdraft.evidence = profile_evidence;\n",
            "\tdraft.evidence = profile_evidence;\n"
            "\tdraft.evidence.target_cap[0].registers.id_aa64pfr0 =\n"
            "\t\tdraft.evidence.expected_pair.id_aa64pfr0;\n")),
        ("copy-expected-into-observed-target", lambda r: replace(
            r / core,
            "\tdraft.evidence = profile_evidence;\n",
            "\tdraft.evidence = profile_evidence;\n"
            "\tdraft.evidence.observed_target_midr[0] =\n"
            "\t\tdraft.evidence.expected_pair.midr;\n")),
        ("mark-partial-id-image-current", lambda r: replace(
            r / core,
            "\tdraft.evidence = profile_evidence;\n",
            "\tdraft.evidence = profile_evidence;\n"
            "\tdraft.evidence.target_cap[0].valid |=\n"
            "\t\tARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID;\n")),
        ("zero-fill-pfr2", lambda r: replace(
            r / cpufeature,
            "\tcase SYS_ID_ISAR5_EL1:\n"
            "\t\tfield = ARM64_LATE_CPU_EXPECT_A32ISAR5;\n"
            "\t\tregister_value = expected ? expected->id_isar5 : 0;\n"
            "\t\tbreak;\n\tdefault:\n",
            "\tcase SYS_ID_ISAR5_EL1:\n"
            "\t\tfield = ARM64_LATE_CPU_EXPECT_A32ISAR5;\n"
            "\t\tregister_value = expected ? expected->id_isar5 : 0;\n"
            "\t\tbreak;\n"
            "\tcase SYS_ID_AA64PFR2_EL1:\n"
            "\t\tfield = ARM64_LATE_CPU_EXPECT_AA64PFR1;\n"
            "\t\tregister_value = 0;\n"
            "\t\tbreak;\n\tdefault:\n")),
        ("zero-fill-isar2", lambda r: replace(
            r / cpufeature,
            "\tcase SYS_ID_ISAR5_EL1:\n"
            "\t\tfield = ARM64_LATE_CPU_EXPECT_A32ISAR5;\n"
            "\t\tregister_value = expected ? expected->id_isar5 : 0;\n"
            "\t\tbreak;\n\tdefault:\n",
            "\tcase SYS_ID_ISAR5_EL1:\n"
            "\t\tfield = ARM64_LATE_CPU_EXPECT_A32ISAR5;\n"
            "\t\tregister_value = expected ? expected->id_isar5 : 0;\n"
            "\t\tbreak;\n"
            "\tcase SYS_ID_AA64ISAR2_EL1:\n"
            "\t\tfield = ARM64_LATE_CPU_EXPECT_AA64ISAR1;\n"
            "\t\tregister_value = 0;\n"
            "\t\tbreak;\n\tdefault:\n")),
        ("accept-invalid-expected-field", lambda r: replace(
            r / cpufeature,
            "\tif (!late_cpu_expected_field_valid(expected, field))\n"
            "\t\treturn -ENOENT;\n"
            "\t*value = register_value;\n",
            "\tif (!late_cpu_expected_field_valid(expected, field))\n"
            "\t\tregister_value = 0;\n"
            "\t*value = register_value;\n")),
        ("drop-named-validity-bit", lambda r: replace(
            r / cpufeature,
            "\t       expected->valid & BIT_ULL(field);\n",
            "\t       true;\n")),
        ("drop-expected-completeness-from-hwcap", lambda r: replace(
            r / cpufeature,
            "\tif (!arm64_late_cpu_expected_pair_complete(plan) ||\n"
            "\t    !late_cpu_hwcap_matches(cap, NULL))\n",
            "\tif (!late_cpu_hwcap_matches(cap, NULL))\n")),
        ("drop-system-hwcap-intersection", lambda r: replace(
            r / cpufeature,
            "\tif (!arm64_late_cpu_expected_pair_complete(plan) ||\n"
            "\t    !late_cpu_hwcap_matches(cap, NULL))\n",
            "\tif (!arm64_late_cpu_expected_pair_complete(plan))\n")),
        ("restore-runtime-target-hwcap", lambda r: replace(
            r / cpufeature,
            "\treturn late_cpu_hwcap_matches(cap, &plan->evidence.expected_pair);\n",
            "\treturn plan->evidence.target_cap[0].valid;\n")),
        ("restore-runtime-target-compat", lambda r: replace(
            r / cpufeature,
            "\texpected = &plan->evidence.expected_pair;\n",
            "\tif (plan->evidence.target_cap[0].valid)\n"
            "\t\treturn true;\n"
            "\texpected = &plan->evidence.expected_pair;\n")),
        ("drop-expected-hwcap-plan-gate", lambda r: replace(
            r / cpufeature,
            "\tif (!arm64_late_cpu_expected_pair_complete(plan))\n"
            "\t\treturn -EAGAIN;\n",
            "")),
        ("drop-cache-ctr-validity", lambda r: replace(
            r / errata,
            "\tconst u64 required = BIT_ULL(ARM64_LATE_CPU_EXPECT_CTR) |\n"
            "\t\tBIT_ULL(ARM64_LATE_CPU_EXPECT_CLIDR);\n",
            "\tconst u64 required = BIT_ULL(ARM64_LATE_CPU_EXPECT_CLIDR);\n")),
        ("drop-cache-clidr-validity", lambda r: replace(
            r / errata,
            "\tconst u64 required = BIT_ULL(ARM64_LATE_CPU_EXPECT_CTR) |\n"
            "\t\tBIT_ULL(ARM64_LATE_CPU_EXPECT_CLIDR);\n",
            "\tconst u64 required = BIT_ULL(ARM64_LATE_CPU_EXPECT_CTR);\n")),
        ("restore-runtime-target-cache", lambda r: replace(
            r / profile,
            "\t\treturn arm64_late_cpu_expected_cache_type_state(\n"
            "\t\t\tcap, match, &evidence->expected_pair,\n"
            "\t\t\t&evidence->system_cap);\n",
            "\t\treturn arm64_late_cpu_cache_type_state(\n"
            "\t\t\tcap, match, &evidence->target_cap[target],\n"
            "\t\t\t&evidence->system_cap);\n")),
        ("weaken-profile-runtime-empty-gate", lambda r: replace(
            r / core,
            "\t\t    memchr_inv(&evidence->target_cap[target], 0,\n"
            "\t\t\t       sizeof(evidence->target_cap[target])) ||\n",
            "")),
        ("weaken-architecture-target-empty-gate", lambda r: replace(
            r / core,
            "\t\t    memchr_inv(&late_runtime_evidence.target_cap[target], 0,\n"
            "\t\t\t       sizeof(late_runtime_evidence.target_cap[target])))\n",
            "\t\t    false)\n")),
        ("weaken-complete-valid-mask", lambda r: replace(
            r / core,
            "\t    expected->valid != ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK ||\n",
            "\t    !(expected->valid & ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK) ||\n")),
        ("activate-production-expectation", lambda r: replace(
            r / profile,
            "\tevidence->target_cpu[0] = 8;\n",
            "\tevidence->expected_pair.abi = ARM64_LATE_CPU_EXPECTED_PAIR_ABI;\n"
            "\tevidence->target_cpu[0] = 8;\n")),
        ("publish-ready", lambda r: replace(
            r / cpufeature,
            "\treturn id_aa64pfr0_32bit_el0(pfr0);\n",
            "\t/* ARM64_LATE_CPU_PROFILE_READY */\n"
            "\treturn id_aa64pfr0_32bit_el0(pfr0);\n")),
        ("add-cpu-request", lambda r: replace(
            r / errata,
            "\traw = expected->ctr;\n",
            "\t/* cpu_up(8) */\n"
            "\traw = expected->ctr;\n")),
        ("make-production-profile-succeed", lambda r: replace(
            r / profile,
            "\t/* No live system capability, alternative, vector, or HWCAP is changed. */\n"
            "\treturn -EAGAIN;\n",
            "\t/* No live system capability, alternative, vector, or HWCAP is changed. */\n"
            "\treturn 0;\n")),
    ]


def prepare(source_root: Path, destination: Path) -> None:
    for relative in EDITS.PARENT_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    EDITS.validate_parent(destination)
    EDITS.apply(destination)
    VALIDATE.validate(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-slice6-mutations-") as name:
        base = Path(name) / "base"
        prepare(source_root, base)
        for mutation_name, mutate in mutations():
            candidate = Path(name) / mutation_name
            shutil.copytree(base, candidate)
            mutate(candidate)
            try:
                VALIDATE.validate(candidate)
            except (VALIDATE.ValidationError, ValueError):
                rejected += 1
            else:
                raise AssertionError(
                    f"unsafe expectation mutation accepted: {mutation_name}")

    print("validation=mainline-a72-slice6-mutations-pass")
    print("positive_cases=1")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
