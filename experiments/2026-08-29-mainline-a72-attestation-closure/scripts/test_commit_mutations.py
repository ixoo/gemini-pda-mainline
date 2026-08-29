#!/usr/bin/env python3
"""Reject unsafe slice-5 architecture-commit mutations."""

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


EDITS = load("commit_edits")
VALIDATE = load("validate_commit_source")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"mutation anchor absent: {old}")
    path.write_text(text.replace(old, new, 1))


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    core = Path("arch/arm64/kernel/late_cpu_profile.c")
    cpufeature = Path("arch/arm64/kernel/cpufeature.c")
    proton = Path("arch/arm64/kernel/proton-pack.c")
    profile = Path("arch/arm64/kernel/mt6797_psci.c")
    return [
        ("expand-capability-allowlist", lambda r: replace(
            r / cpufeature,
            "\tcase ARM64_WORKAROUND_SPECULATIVE_AT:\n\t\treturn true;",
            "\tcase ARM64_WORKAROUND_SPECULATIVE_AT:\n"
            "\tcase ARM64_HAS_LSE_ATOMICS:\n\t\treturn true;")),
        ("drop-finalization-gate", lambda r: replace(
            r / cpufeature,
            "\tif (!plan || system_capabilities_finalized() ||\n",
            "\tif (!plan ||\n")),
        ("drop-target-cap-subset", lambda r: replace(
            r / cpufeature,
            "\t    !bitmap_subset(plan->required_local_caps,\n"
            "\t\t\t   plan->target_local_caps, ARM64_NCAPS) ||\n",
            "")),
        ("drop-current-cap-disjointness", lambda r: replace(
            r / cpufeature,
            "\t    bitmap_intersects(plan->required_local_caps,\n"
            "\t\t\t      system_cpucaps, ARM64_NCAPS))\n",
            "\t    false)\n")),
        ("mutate-before-mitigation-preflight", lambda r: replace(
            r / cpufeature,
            "\tret = arm64_commit_late_cpu_mitigations(&plan->effects);\n"
            "\tif (ret)\n\t\treturn ret;\n\n"
            "\t/* No fallible operation may follow the first architecture-state write. */\n"
            "\tbitmap_or(system_cpucaps, system_cpucaps, plan->required_local_caps,\n"
            "\t\t  ARM64_NCAPS);\n",
            "\tbitmap_or(system_cpucaps, system_cpucaps, plan->required_local_caps,\n"
            "\t\t  ARM64_NCAPS);\n"
            "\tret = arm64_commit_late_cpu_mitigations(&plan->effects);\n"
            "\tif (ret)\n\t\treturn ret;\n")),
        ("invoke-capability-callback", lambda r: replace(
            r / cpufeature,
            "\t\t    cpucap_late_cpu_permitted(descriptor))\n",
            "\t\t    cpucap_late_cpu_permitted(descriptor))\n"
            "\t\t\tdescriptor->cpu_enable(descriptor);\n"
            "\t\tif (false)\n")),
        ("drop-v2-monotonic-gate", lambda r: replace(
            r / proton, " || READ_ONCE(spectre_v2_state) > v2", "")),
        ("drop-v4-monotonic-gate", lambda r: replace(
            r / proton, " || READ_ONCE(spectre_v4_state) > v4", "")),
        ("drop-bhb-monotonic-gate", lambda r: replace(
            r / proton, " || READ_ONCE(spectre_bhb_state) > bhb", "")),
        ("drop-bhb-method-subset", lambda r: replace(
            r / proton,
            "\t\t    current_bhb_methods & ~effects->bhb.system_method ||\n",
            "")),
        ("probe-firmware-during-commit", lambda r: replace(
            r / proton,
            "\tif (!effects || system_capabilities_finalized())\n",
            "\t/* arm_smccc_1_1_invoke is forbidden during commit. */\n"
            "\tif (!effects || system_capabilities_finalized())\n")),
        ("drop-receipt-effects", lambda r: replace(
            r / core, "\tlate_receipt.committed = late_plan.effects;\n", "")),
        ("publish-before-complete", lambda r: replace(
            r / core,
            "\tlate_receipt.commit_complete = 1;\n"
            "\t/* Publish the complete receipt after all architecture state is committed. */\n"
            "\tsmp_store_release(&late_receipt.state,\n"
            "\t\t\t  ARM64_LATE_CPU_PROFILE_COMMITTED);\n",
            "\tsmp_store_release(&late_receipt.state,\n"
            "\t\t\t  ARM64_LATE_CPU_PROFILE_COMMITTED);\n"
            "\tlate_receipt.commit_complete = 1;\n")),
        ("weaken-receipt-publication", lambda r: replace(
            r / core, "smp_store_release(&late_receipt.state,",
            "WRITE_ONCE(late_receipt.state,")),
        ("restore-commit-blocker", lambda r: replace(
            r / core,
            "\tplan_ret = arm64_plan_late_cpu_capabilities(&draft, &late_profile);\n",
            "\tdraft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH;\n"
            "\tplan_ret = arm64_plan_late_cpu_capabilities(&draft, &late_profile);\n")),
        ("publish-ready-from-commit", lambda r: replace(
            r / core, "ARM64_LATE_CPU_PROFILE_COMMITTED);",
            "ARM64_LATE_CPU_PROFILE_READY);")),
        ("add-cpu-request", lambda r: replace(
            r / cpufeature,
            "\treturn 0;\n}\n\n#endif\n\nstatic void cap_set_elf_hwcap",
            "\t/* cpu_up(8) */\n\treturn 0;\n}\n\n#endif\n\n"
            "static void cap_set_elf_hwcap")),
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
    with tempfile.TemporaryDirectory(prefix="a72-slice5-mutations-") as name:
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
                    f"unsafe commit mutation accepted: {mutation_name}")

    print("validation=mainline-a72-slice5-mutations-pass")
    print("positive_cases=1")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
