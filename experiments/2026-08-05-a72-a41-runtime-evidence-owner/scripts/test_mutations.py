#!/usr/bin/env python3
"""Require 29 adversarial ABI-6 repository and source mutations to fail."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
VALIDATOR_PATH = HERE / "validate.py"
SPEC = importlib.util.spec_from_file_location("a41_owner_validate", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load runtime-evidence-owner validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise RuntimeError(f"mutation source is missing in {path.name}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def copy_repository_inputs(source: Path, target: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory in ("configs", "kernel", "patches"):
        shutil.copytree(source / directory, target / directory, ignore=ignore)
    child = target / VALIDATE.EXPERIMENT
    child.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / VALIDATE.EXPERIMENT, child, ignore=ignore)


def copy_source_inputs(source: Path, target: Path) -> None:
    for relative in VALIDATE.CHANGED_PATHS:
        source_path = source / relative
        target_path = target / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def expect_repository_failure(root: Path, mutation) -> None:
    mutation(root)
    try:
        VALIDATE.validate_repository(root, pin_hashes=False)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
        return
    raise RuntimeError(f"unsafe repository mutation passed: {mutation.__name__}")


def expect_source_failure(root: Path, mutation, repo: Path) -> None:
    mutation(root)
    try:
        VALIDATE.validate_source_files(root, repo=repo)
    except (OSError, ValueError, RuntimeError):
        return
    raise RuntimeError(f"unsafe source mutation passed: {mutation.__name__}")


def mutate_manifest_profile_missing(root: Path) -> None:
    path = root / VALIDATE.MANIFEST
    data = json.loads(path.read_text())
    del data["config"]["profiles"][VALIDATE.PROFILE]
    path.write_text(json.dumps(data, indent=2) + "\n")


def mutate_profile_series(root: Path) -> None:
    path = root / VALIDATE.MANIFEST
    data = json.loads(path.read_text())
    data["config"]["profiles"][VALIDATE.PROFILE]["patch_series"] = str(
        VALIDATE.PARENT_SERIES
    )
    path.write_text(json.dumps(data, indent=2) + "\n")


def mutate_fragment_policy(root: Path) -> None:
    replace_once(
        root / VALIDATE.FRAGMENT,
        'CONFIG_LOCALVERSION="-gemini-a41-owner-blocked"',
        'CONFIG_LOCALVERSION="-gemini-a41-owner-open"',
    )


def mutate_selected_series_duplicate(root: Path) -> None:
    path = root / VALIDATE.SERIES
    text = path.read_text()
    path.write_text(text + VALIDATE.PATCH.relative_to("patches").as_posix() + "\n")


def mutate_canonical_order(root: Path) -> None:
    path = root / VALIDATE.CANONICAL_SERIES
    lines = path.read_text().splitlines()
    first = next(index for index, line in enumerate(lines) if "0154-" in line)
    second = next(index for index, line in enumerate(lines) if "0155-" in line)
    lines[first], lines[second] = lines[second], lines[first]
    path.write_text("\n".join(lines) + "\n")


def mutate_patch_source(root: Path) -> None:
    replace_once(root / VALIDATE.PATCH, VALIDATE.SOURCE, "0" * 40)


def mutate_patch_inventory(root: Path) -> None:
    path = root / VALIDATE.PATCH
    replace_once(
        path,
        "diff --git a/arch/arm64/kernel/smp.c b/arch/arm64/kernel/smp.c",
        "diff --git a/arch/arm64/kernel/unsafe.c b/arch/arm64/kernel/unsafe.c",
    )


def mutate_external_action(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT / "scripts/validate.py"
    path.write_text(
        path.read_text()
        + "\ndef unsafe_external_action():\n"
        + "    subprocess.run(['c' + 'url', 'https://invalid.example'])\n"
    )


REPOSITORY_CASES = (
    mutate_manifest_profile_missing,
    mutate_profile_series,
    mutate_fragment_policy,
    mutate_selected_series_duplicate,
    mutate_canonical_order,
    mutate_patch_source,
    mutate_patch_inventory,
    mutate_external_action,
)


def header_path(root: Path) -> Path:
    return root / "arch/arm64/include/asm/late_cpu_profile.h"


def kernel_path(root: Path, name: str) -> Path:
    return root / "arch/arm64/kernel" / name


def source_abi_downgrade(root: Path) -> None:
    replace_once(
        header_path(root),
        "#define ARM64_LATE_CPU_PLAN_ABI\t\t6",
        "#define ARM64_LATE_CPU_PLAN_ABI\t\t5",
    )


def source_seal_order(root: Path) -> None:
    replace_once(
        kernel_path(root, "smp.c"),
        "\tarm64_seal_late_cpu_runtime_evidence();\n"
        "\tarm64_prepare_late_cpu_profile();\n"
        "\tsetup_system_features();",
        "\tarm64_prepare_late_cpu_profile();\n"
        "\tsetup_system_features();\n"
        "\tarm64_seal_late_cpu_runtime_evidence();",
    )


def source_late_seal_guard_polarity(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "\t    system_capabilities_finalized() ||",
        "\t    !system_capabilities_finalized() ||",
    )


def source_runtime_binding_completeness_polarity(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "\t     !late_profile_runtime_binding_complete(&late_runtime_evidence.binding)))",
        "\t     late_profile_runtime_binding_complete(&late_runtime_evidence.binding)))",
    )


def source_runtime_seal_state_polarity(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "state = late_runtime_evidence.binding.origin ==\n"
        "\t\tARM64_LATE_CPU_BINDING_RUNTIME ?",
        "state = late_runtime_evidence.binding.origin !=\n"
        "\t\tARM64_LATE_CPU_BINDING_RUNTIME ?",
    )


def source_release_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "smp_store_release(&late_runtime_evidence_state, state);",
        "WRITE_ONCE(late_runtime_evidence_state, state);",
    )


def source_acquire_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "runtime_state = smp_load_acquire(&late_runtime_evidence_state);",
        "runtime_state = READ_ONCE(late_runtime_evidence_state);",
    )


def source_private_record_export(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "static struct arm64_late_cpu_evidence late_runtime_evidence __initdata",
        "struct arm64_late_cpu_evidence late_runtime_evidence __initdata",
    )


def source_private_record_pointer_escape(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "void __init arm64_seal_late_cpu_runtime_evidence(void)\n",
        "static struct arm64_late_cpu_evidence *\n"
        "late_runtime_evidence_writer(void)\n"
        "{\n"
        "\treturn &late_runtime_evidence;\n"
        "}\n\n"
        "void __init arm64_seal_late_cpu_runtime_evidence(void)\n",
    )


def source_runtime_rejection_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "if (profile_evidence.binding.origin ==\n"
        "\t    ARM64_LATE_CPU_BINDING_RUNTIME)",
        "if (profile_evidence.binding.origin ==\n"
        "\t    ARM64_LATE_CPU_BINDING_FIXTURE)",
    )


def source_observation_rejection_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "if (!late_profile_runtime_fields_empty(&profile_evidence)) {",
        "if (false && !late_profile_runtime_fields_empty(&profile_evidence)) {",
    )


def source_observed_field_gap(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "\t\t    evidence->observed_target_revidr[target] ||\n",
        "",
    )


def source_fixture_claims_runtime(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "evidence->binding.origin = ARM64_LATE_CPU_BINDING_FIXTURE;",
        "evidence->binding.origin = ARM64_LATE_CPU_BINDING_RUNTIME;",
    )


def source_runtime_overlay_condition(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "if (runtime_state == LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME)",
        "if (runtime_state != LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME)",
    )


def source_empty_runtime_blocker_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "late_runtime_evidence.blocker_mask |=\n"
        "\t\t\tARM64_LATE_CPU_BLOCK_RUNTIME_BINDING;",
        "late_runtime_evidence.blocker_mask |= 0;",
    )


def source_profile_prepare_success(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "/* No live system capability, alternative, vector, or HWCAP is changed. */\n"
        "\treturn -EAGAIN;",
        "/* Unsafe mutation: pretend profile preparation succeeded. */\n"
        "\treturn 0;",
    )


def source_profile_validator_success(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "/* Source-only fixture/expected evidence never publishes an identity. */\n"
        "\treturn -EAGAIN;",
        "/* Unsafe mutation: pretend profile validation succeeded. */\n"
        "\treturn 0;",
    )


def source_core_commit_blocker_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "draft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH;",
        "draft.evidence.blocker_mask |= 0;",
    )


def source_core_commit_panic_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        'panic("late CPU profile commit implementation is unavailable");',
        "return;",
    )


def source_cpu_boot_veto_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "return -EAGAIN;\n}\n\n#ifdef CONFIG_HOTPLUG_CPU",
        "return cpu_psci_ops.cpu_boot(cpu);\n}\n\n#ifdef CONFIG_HOTPLUG_CPU",
    )


def source_cpu_disable_veto_loss(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n\treturn false;",
        "mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n\treturn true;",
    )


SOURCE_CASES = (
    source_abi_downgrade,
    source_seal_order,
    source_late_seal_guard_polarity,
    source_runtime_binding_completeness_polarity,
    source_runtime_seal_state_polarity,
    source_release_loss,
    source_acquire_loss,
    source_private_record_export,
    source_private_record_pointer_escape,
    source_runtime_rejection_loss,
    source_observation_rejection_loss,
    source_observed_field_gap,
    source_fixture_claims_runtime,
    source_runtime_overlay_condition,
    source_empty_runtime_blocker_loss,
    source_profile_prepare_success,
    source_profile_validator_success,
    source_core_commit_blocker_loss,
    source_core_commit_panic_loss,
    source_cpu_boot_veto_loss,
    source_cpu_disable_veto_loss,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", "--repo-root", dest="repo", type=Path, default=VALIDATE.default_repo()
    )
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    source = args.source_root.resolve()
    if VALIDATE.run_git(source, ["rev-parse", "HEAD"]).strip() != VALIDATE.SOURCE:
        raise RuntimeError("source checkout is not at the pinned commit")
    if len(REPOSITORY_CASES) + len(SOURCE_CASES) != 29:
        raise RuntimeError("mutation suite must remain the bounded 29-case contract")
    if len(REPOSITORY_CASES) != len(VALIDATE.REPOSITORY_MUTATIONS):
        raise RuntimeError("repository mutation labels are out of sync")
    if len(SOURCE_CASES) != len(VALIDATE.SOURCE_MUTATIONS):
        raise RuntimeError("source mutation labels are out of sync")

    print("validation=a41-runtime-evidence-owner-mutations")
    passed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gemini-a41-owner-repo-baseline-") as temporary:
        root = Path(temporary)
        copy_repository_inputs(repo, root)
        VALIDATE.validate_repository(root, pin_hashes=False)
    with tempfile.TemporaryDirectory(prefix="gemini-a41-owner-source-baseline-") as temporary:
        root = Path(temporary)
        copy_source_inputs(source, root)
        VALIDATE.validate_source_files(root, repo=repo)

    for mutation, name in zip(REPOSITORY_CASES, VALIDATE.REPOSITORY_MUTATIONS):
        with tempfile.TemporaryDirectory(prefix="gemini-a41-owner-repo-") as temporary:
            root = Path(temporary)
            copy_repository_inputs(repo, root)
            expect_repository_failure(root, mutation)
        passed.append(name)
        print(f"PASS {name}")
    for mutation, name in zip(SOURCE_CASES, VALIDATE.SOURCE_MUTATIONS):
        with tempfile.TemporaryDirectory(prefix="gemini-a41-owner-source-") as temporary:
            root = Path(temporary)
            copy_source_inputs(source, root)
            expect_source_failure(root, mutation, repo)
        passed.append(name)
        print(f"PASS {name}")

    print(f"mutations_rejected={len(passed)}")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print(f"RESULT PASS {len(passed)}/{len(passed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
