#!/usr/bin/env python3
"""Reject unsafe slice-7 late-target preflight mutations."""

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


EDITS = load("preflight_edits")
VALIDATE = load("validate_preflight_source")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"mutation anchor absent: {old}")
    path.write_text(text.replace(old, new, 1))


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    late_header = Path("arch/arm64/include/asm/late_cpu_profile.h")
    cpufeature = Path("arch/arm64/kernel/cpufeature.c")
    head = Path("arch/arm64/kernel/head.S")
    core = Path("arch/arm64/kernel/late_cpu_profile.c")
    profile = Path("arch/arm64/kernel/mt6797_psci.c")
    smp = Path("arch/arm64/kernel/smp.c")
    context = Path("arch/arm64/mm/context.c")
    return [
        ("drop-ready-gate", lambda r: replace(
            r / core,
            "\tif (smp_load_acquire(&late_receipt.state) !=\n"
            "\t    ARM64_LATE_CPU_PROFILE_READY)\n\t\treturn 0;\n",
            "\tif (false)\n\t\treturn 0;\n")),
        ("drop-target-membership", lambda r: replace(
            r / core,
            "\tif (!cpumask_test_cpu(cpu, &late_plan.target_cpus))\n"
            "\t\treturn 0;\n",
            "")),
        ("drop-current-cpu-check", lambda r: replace(
            r / core,
            "\tif (cpu != smp_processor_id() ||\n",
            "\tif (false ||\n")),
        ("drop-complete-pair-check", lambda r: replace(
            r / core,
            "\t    !arm64_late_cpu_expected_pair_complete(&late_plan))\n",
            "\t    false)\n")),
        ("drop-asid-preflight", lambda r: replace(
            r / core,
            "\tif (!arm64_late_cpu_asid_compatible())\n"
            "\t\treturn -ERANGE;\n",
            "")),
        ("drop-system-asid-initialization", lambda r: replace(
            r / context,
            "\treturn system_asid_bits &&\n"
            "\t       get_cpu_asid_bits() >= system_asid_bits;\n",
            "\treturn get_cpu_asid_bits() >= system_asid_bits;\n")),
        ("require-equal-asid-width", lambda r: replace(
            r / context,
            "get_cpu_asid_bits() >= system_asid_bits",
            "get_cpu_asid_bits() == system_asid_bits")),
        ("mutate-system-asid-width", lambda r: replace(
            r / context,
            "\tu32 system_asid_bits = READ_ONCE(asid_bits);\n",
            "\tu32 system_asid_bits = ++asid_bits;\n")),
        ("skip-last-boot-cap", lambda r: replace(
            r / cpufeature,
            "for (i = 0; i < ARM64_NCAPS; i++)",
            "for (i = 0; i < ARM64_NCAPS - 1; i++)")),
        ("scan-local-not-boot", lambda r: replace(
            r / cpufeature,
            "!(caps->type & SCOPE_BOOT_CPU)",
            "!(caps->type & SCOPE_LOCAL_CPU)")),
        ("allow-missing-system-cap", lambda r: replace(
            r / cpufeature,
            "!cpu_has_cap && !cpucap_late_cpu_optional(caps)",
            "false")),
        ("allow-new-forbidden-cap", lambda r: replace(
            r / cpufeature,
            "cpu_has_cap && !cpucap_late_cpu_permitted(caps)",
            "false")),
        ("add-capability-allowlist", lambda r: replace(
            r / cpufeature,
            "\t\tcaps = cpucap_ptrs[i];\n",
            "\t\tcaps = cpucap_ptrs[i];\n"
            "\t\tif (caps && caps->capability != ARM64_HAS_GICV3_CPUIF)\n"
            "\t\t\tcontinue;\n")),
        ("call-cpu-enable", lambda r: replace(
            r / cpufeature,
            "\t\tsystem_has_cap = cpus_have_cap(caps->capability);\n",
            "\t\tsystem_has_cap = cpus_have_cap(caps->capability);\n"
            "\t\tif (caps->cpu_enable)\n\t\t\tcaps->cpu_enable(caps);\n")),
        ("panic-on-preflight-failure", lambda r: replace(
            r / smp,
            "\t\tupdate_cpu_boot_status(CPU_STUCK_IN_KERNEL);\n"
            "\t\tcpu_park_loop();\n",
            "\t\tupdate_cpu_boot_status(CPU_PANIC_KERNEL);\n"
            "\t\tcpu_panic_kernel();\n")),
        ("fail-open-preflight", lambda r: replace(
            r / smp,
            "\tif (expectation_ret) {\n"
            "\t\tpr_crit(\"CPU%u: late target preflight mismatch: %d\\n\",\n",
            "\tif (false) {\n"
            "\t\tpr_crit(\"CPU%u: late target preflight mismatch: %d\\n\",\n")),
        ("move-preflight-after-standard-check", lambda r: replace(
            r / smp,
            "\texpectation_ret = arm64_validate_late_cpu_preflight(cpu);\n",
            "\tcheck_local_cpu_capabilities();\n"
            "\texpectation_ret = arm64_validate_late_cpu_preflight(cpu);\n")),
        ("remove-standard-verifier", lambda r: replace(
            r / smp,
            "\tcheck_local_cpu_capabilities();\n",
            "")),
        ("remove-full-expectation", lambda r: replace(
            r / smp,
            "\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu);\n",
            "\texpectation_ret = 0;\n")),
        ("alter-granule-gate", lambda r: replace(
            r / head,
            "\tb.lt    __no_granule_support\n",
            "\tb.lt    1f\n")),
        ("activate-production-expectation", lambda r: replace(
            r / profile,
            "\tevidence->target_cpu[0] = 8;\n",
            "\tevidence->expected_pair.abi = ARM64_LATE_CPU_EXPECTED_PAIR_ABI;\n"
            "\tevidence->target_cpu[0] = 8;\n")),
        ("add-cpu-request", lambda r: replace(
            r / smp,
            "\texpectation_ret = arm64_validate_late_cpu_preflight(cpu);\n",
            "\t/* cpu_up(8) */\n"
            "\texpectation_ret = arm64_validate_late_cpu_preflight(cpu);\n")),
        ("add-cpu-off", lambda r: replace(
            r / smp,
            "\t\tcpu_park_loop();\n",
            "\t\t/* cpu_off() */\n\t\tcpu_park_loop();\n")),
        ("drop-preflight-declaration", lambda r: replace(
            r / late_header,
            "int arm64_validate_late_cpu_preflight(unsigned int cpu);\n",
            "")),
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
    with tempfile.TemporaryDirectory(prefix="a72-slice7-mutations-") as name:
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
                    f"unsafe preflight mutation accepted: {mutation_name}")

    print("validation=mainline-a72-slice7-mutations-pass")
    print("positive_cases=1")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
