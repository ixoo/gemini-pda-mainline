#!/usr/bin/env python3
"""Reject unsafe conservative-policy mutations."""

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


EDITS = load("policy_edits")
VALIDATE = load("validate_policy_source")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"mutation anchor absent: {old}")
    path.write_text(text.replace(old, new, 1))


def replace_in_function(
    path: Path, signature: str, old: str, new: str
) -> None:
    text = path.read_text()
    body = VALIDATE.function(text, signature)
    if old not in body:
        raise AssertionError(f"function mutation anchor absent: {old}")
    path.write_text(text.replace(body, body.replace(old, new, 1), 1))


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    header = Path("arch/arm64/include/asm/late_cpu_profile.h")
    cpufeature = Path("arch/arm64/kernel/cpufeature.c")
    core = Path("arch/arm64/kernel/late_cpu_profile.c")
    profile = Path("arch/arm64/kernel/mt6797_psci.c")
    proton = Path("arch/arm64/kernel/proton-pack.c")
    smp = Path("arch/arm64/kernel/smp.c")
    return [
        ("drop-early-valid-bit", lambda r: replace(
            r / header,
            "#define ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID\tBIT(3)\n",
            "")),
        ("drop-early-valid-production", lambda r: replace_in_function(
            r / cpufeature, "arm64_late_cpu_collect_system(",
            " |\n\t\t\tARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID",
            "")),
        ("drop-early-valid-policy-input", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_collect_policy(",
            " |\n\t\t\t      ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID",
            "")),
        ("hardcode-gic-absent", lambda r: replace_in_function(
            r / cpufeature, "arm64_late_cpu_collect_system(",
            "system->gicv5_legacy = cpus_have_cap(ARM64_HAS_GICV5_LEGACY);",
            "system->gicv5_legacy = 0;")),
        ("hardcode-ich-absent", lambda r: replace_in_function(
            r / cpufeature, "arm64_late_cpu_collect_system(",
            "\t\tcpus_have_cap(ARM64_HAS_ICH_HCR_EL2_TDIR);",
            "\t\t0;")),
        ("accept-unknown-system-valid", lambda r: replace_in_function(
            r / cpufeature, "arm64_late_cpu_early_system_cap_state(",
            "\t    system->valid & ~ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK ||\n",
            "")),
        ("accept-invalid-system-booleans", lambda r: replace_in_function(
            r / cpufeature, "arm64_late_cpu_early_system_cap_state(",
            "\t    system->gicv5_legacy > 1 || system->ich_hcr_tdir > 1 ||\n",
            "")),
        ("classify-present-gic-absent", lambda r: replace_in_function(
            r / cpufeature, "arm64_late_cpu_early_system_cap_state(",
            "return present ? ARM64_LATE_CPU_CAP_UNRESOLVED :",
            "return present ? ARM64_LATE_CPU_CAP_ABSENT :")),
        ("add-early-capability-allowlist-entry", lambda r: replace_in_function(
            r / cpufeature, "arm64_late_cpu_early_system_cap_state(",
            "\tdefault:\n",
            "\tcase ARM64_HAS_AMU_EXTN:\n\t\tpresent = false;\n\t\tbreak;\n"
            "\tdefault:\n")),
        ("drop-gic-canonical-field", lambda r: replace_in_function(
            r / core, "late_canonical_update_system_cap(",
            "\tlate_canonical_update_u8(ctx, system->gicv5_legacy);\n",
            "")),
        ("drop-ich-canonical-field", lambda r: replace_in_function(
            r / core, "late_canonical_update_system_cap(",
            "\tlate_canonical_update_u8(ctx, system->ich_hcr_tdir);\n",
            "")),
        ("accept-unmarked-expected-field", lambda r: replace_in_function(
            r / proton, "late_cpu_expected_field_valid(",
            "\t       expected->valid & BIT_ULL(field) &&\n",
            "\t       true &&\n")),
        ("accept-wrong-expected-midr", lambda r: replace_in_function(
            r / proton, "late_cpu_expected_field_valid(",
            "\t       expected->midr == MIDR_CORTEX_A72;\n",
            "\t       true;\n")),
        ("invert-v2-csv2", lambda r: replace_in_function(
            r / proton, "late_cpu_expected_v2_evidence_state(",
            "return csv2 ? ARM64_LATE_CPU_CAP_ABSENT :\n"
            "\t\t      ARM64_LATE_CPU_CAP_PRESENT;",
            "return csv2 ? ARM64_LATE_CPU_CAP_PRESENT :\n"
            "\t\t      ARM64_LATE_CPU_CAP_ABSENT;")),
        ("treat-v4-unknown-wa2-unaffected", lambda r: replace_in_function(
            r / proton, "late_cpu_expected_v4_evidence_state(",
            "\treturn ARM64_LATE_CPU_CAP_PRESENT;\n",
            "\treturn ssbs ? ARM64_LATE_CPU_CAP_PRESENT :\n"
            "\t\t      ARM64_LATE_CPU_CAP_ABSENT;\n")),
        ("invert-bhb-csv2", lambda r: replace_in_function(
            r / proton, "late_cpu_expected_bhb_evidence_state(",
            "return csv2 == 3 ? ARM64_LATE_CPU_CAP_ABSENT :\n"
            "\t\t\t ARM64_LATE_CPU_CAP_PRESENT;",
            "return csv2 == 3 ? ARM64_LATE_CPU_CAP_PRESENT :\n"
            "\t\t\t ARM64_LATE_CPU_CAP_ABSENT;")),
        ("claim-v2-mitigated", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_expected_effects(",
            "\t\t\tARM64_LATE_CPU_MITIGATION_VULNERABLE;\n",
            "\t\t\tARM64_LATE_CPU_MITIGATION_MITIGATED;\n")),
        ("invent-v2-firmware-callback", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_expected_effects(",
            "effects->spectre_v2_callback = ARM64_LATE_CPU_V2_CALLBACK_NONE;",
            "effects->spectre_v2_callback = ARM64_LATE_CPU_V2_CALLBACK_SMC;")),
        ("claim-v4-mitigated-without-ssbs", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_expected_effects(",
            "\tif (ssbs && !policy->mitigations_off &&\n",
            "\tif (!policy->mitigations_off &&\n")),
        ("invent-v4-firmware", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_expected_effects(",
            "effects->spectre_v4_conduit = ARM64_LATE_CPU_SMCCC_NONE;",
            "effects->spectre_v4_conduit = ARM64_LATE_CPU_SMCCC_SMC;")),
        ("mitigate-bhb-without-modern-ids", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_expected_effects(",
            "\t} else if (!effects->bhb_v2_non_vulnerable) {\n",
            "\t} else if (false) {\n")),
        ("consume-missing-wa1", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_expected_effects(",
            "\tu64 ssbs;\n",
            "\tu64 ssbs;\n\t/* smccc_wa1 */\n")),
        ("consume-missing-modern-id", lambda r: replace_in_function(
            r / proton, "arm64_late_cpu_expected_effects(",
            "\tu64 ssbs;\n",
            "\tu64 ssbs;\n\t/* id_aa64isar2 */\n")),
        ("drop-complete-expected-pair", lambda r: replace_in_function(
            r / profile, "mt6797_a72_derive_effects(",
            "\tif (!arm64_late_cpu_expected_pair_complete(plan))\n"
            "\t\treturn -EAGAIN;\n",
            "")),
        ("restore-production-target-evidence", lambda r: replace_in_function(
            r / profile, "mt6797_a72_classify_local_cap(",
            "arm64_late_cpu_expected_v2_state(",
            "arm64_late_cpu_a72_spectre_v2_state(")),
        ("activate-production-expectation", lambda r: replace_in_function(
            r / profile, "mt6797_a72_profile_prepare(",
            "\tevidence->target_cpu[0] = 8;\n",
            "\tevidence->expected_pair.abi = ARM64_LATE_CPU_EXPECTED_PAIR_ABI;\n"
            "\tevidence->target_cpu[0] = 8;\n")),
        ("add-cpu8-request", lambda r: replace_in_function(
            r / smp, "secondary_start_kernel(",
            "\texpectation_ret = arm64_validate_late_cpu_preflight(cpu);\n",
            "\t/* cpu_up(8) */\n"
            "\texpectation_ret = arm64_validate_late_cpu_preflight(cpu);\n")),
    ]


def prepare(source_root: Path, destination: Path) -> None:
    for relative in EDITS.PARENT_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    for relative in (
        "arch/arm64/kernel/head.S",
        "arch/arm64/kernel/smp.c",
    ):
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
    with tempfile.TemporaryDirectory(prefix="a72-policy-mutations-") as name:
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
                    f"unsafe policy mutation accepted: {mutation_name}")

    if rejected != len(mutations()):
        raise AssertionError("policy mutation rejection count changed")
    print(f"unsafe_policy_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
