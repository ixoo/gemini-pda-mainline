#!/usr/bin/env python3
"""Reject unsafe slice-4 planner and identity mutations."""

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


EDITS = load("planner_edits")
VALIDATE = load("validate_planner_source")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"mutation anchor absent: {old}")
    path.write_text(text.replace(old, new, 1))


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    header = Path("arch/arm64/include/asm/late_cpu_profile.h")
    core = Path("arch/arm64/kernel/late_cpu_profile.c")
    cpufeature = Path("arch/arm64/kernel/cpufeature.c")
    profile = Path("arch/arm64/kernel/mt6797_psci.c")
    return [
        ("drop-hwcap-completion-bit", lambda r: replace(
            r / header, "\tu8 hwcaps_planned;\n", "")),
        ("probe-live-local-register", lambda r: replace(
            r / cpufeature, "read_sanitised_ftr_reg(cap->sys_reg)",
            "read_sysreg_s(cap->sys_reg)")),
        ("drop-one-target-intersection", lambda r: replace(
            r / cpufeature,
            "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)\n"
            "\t\tif (!late_cpu_hwcap_matches(\n"
            "\t\t\t    cap, &plan->evidence.target_cap[target].registers))\n"
            "\t\t\treturn false;\n",
            "\tif (!late_cpu_hwcap_matches(\n"
            "\t\t    cap, &plan->evidence.target_cap[0].registers))\n"
            "\t\treturn false;\n")),
        ("drop-id-register-validity", lambda r: replace(
            r / cpufeature,
            "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)\n"
            "\t\tif (!(plan->evidence.target_cap[target].valid &\n"
            "\t\t      ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID))\n"
            "\t\t\treturn -EAGAIN;\n\n", "")),
        ("publish-hwcaps-before-fill", lambda r: replace(
            r / cpufeature,
            "\t__set_bit(KERNEL_HWCAP_CPUID,\n",
            "\tplan->hwcaps_planned = 1;\n"
            "\t__set_bit(KERNEL_HWCAP_CPUID,\n")),
        ("hash-evidence-padding", lambda r: replace(
            r / core,
            "\tlate_canonical_update_u32(&ctx, evidence->abi);\n",
            "\tsha256_update(&ctx, (const u8 *)evidence, sizeof(*evidence));\n"
            "\tlate_canonical_update_u32(&ctx, evidence->abi);\n")),
        ("hash-derived-blocker", lambda r: replace(
            r / core,
            "\t/* blocker_mask is a derived admission result, not input evidence. */\n",
            "\tlate_canonical_update_u64(&ctx, evidence->blocker_mask);\n"
            "\t/* blocker_mask is a derived admission result, not input evidence. */\n")),
        ("omit-modern-id-field", lambda r: replace(
            r / core,
            "\tlate_canonical_update_u64(ctx, registers->id_aa64isar3);\n", "")),
        ("omit-runtime-binding", lambda r: replace(
            r / core,
            "\tlate_canonical_update_binding(&ctx, &evidence->binding);\n", "")),
        ("omit-effect-field", lambda r: replace(
            r / core,
            "\tlate_canonical_update_u8(ctx, effects->bhb.matcher_loop_count);\n",
            "")),
        ("omit-compat-hwcap2", lambda r: replace(
            r / core,
            "\tlate_canonical_update_u32(&ctx, plan->expected_compat_hwcap2);\n",
            "")),
        ("drop-plan-hash", lambda r: replace(
            r / core,
            "\tlate_canonical_hash_plan(plan, plan->identity);\n", "")),
        ("identity-before-profile-validation", lambda r: replace(
            r / core,
            "\tvalidate_ret = late_profile.validate_plan(&draft);\n"
            "\tidentity_ret = (plan_ret || effect_ret || hwcap_ret ||\n",
            "\tidentity_ret = (plan_ret || effect_ret || hwcap_ret ||\n"
            "\t\t\tvalidate_ret) ? -EAGAIN :\n"
            "\t\tlate_profile_finalize_plan_identity(&draft);\n"
            "\tvalidate_ret = late_profile.validate_plan(&draft);\n"
            "\tidentity_ret = (plan_ret || effect_ret || hwcap_ret ||\n")),
        ("restore-profile-identity", lambda r: replace(
            r / profile,
            "static bool __init mt6797_a72_kpti_policy_static(void)\n",
            "static const u64 mt6797_a72_fixture_evidence_identity[4];\n\n"
            "static bool __init mt6797_a72_kpti_policy_static(void)\n")),
        ("add-cpu-request", lambda r: replace(
            r / cpufeature,
            "\tplan->hwcaps_planned = 1;\n",
            "\t/* cpu_up(8) */\n\tplan->hwcaps_planned = 1;\n")),
        ("drop-compat-aes-fixup", lambda r: replace(
            r / cpufeature,
            "\t\tif (plan->effects.compat_aes_clear)\n"
            "\t\t\tplan->expected_compat_hwcap2 &= ~COMPAT_HWCAP2_AES;\n",
            "")),
    ]


def prepare(source_root: Path, destination: Path) -> None:
    for relative in EDITS.PARENT_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    EDITS.validate_parent(destination)
    # Use the same entry point behavior without reparsing command-line state.
    header = destination / "arch/arm64/include/asm/late_cpu_profile.h"
    # apply() is deliberately exposed below by the generator edit script.
    EDITS.apply(destination)
    assert header.is_file()
    VALIDATE.validate(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-slice4-mutations-") as name:
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
                    f"unsafe planner mutation accepted: {mutation_name}")

    print("validation=mainline-a72-slice4-mutations-pass")
    print("positive_cases=1")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
