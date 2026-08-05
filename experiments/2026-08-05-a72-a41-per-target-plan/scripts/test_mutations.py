#!/usr/bin/env python3
"""Require focused ABI-4 per-target planning mutations to fail validation."""

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
SPEC = importlib.util.spec_from_file_location("a41_per_target_validate", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load per-target validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE)


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise RuntimeError(f"mutation source is missing in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def copy_inputs(source: Path, target: Path) -> None:
    for directory in ("configs", "docs", "kernel", "patches"):
        shutil.copytree(source / directory, target / directory)
    child = target / VALIDATE.EXPERIMENT
    child.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / VALIDATE.EXPERIMENT, child)
    parent = target / VALIDATE.PARENT_VALIDATOR
    parent.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / VALIDATE.PARENT_VALIDATOR, parent)


def copy_source_inputs(source: Path, target: Path) -> None:
    for relative in VALIDATE.CHANGED_PATHS:
        source_path = source / relative
        target_path = target / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def expect_failure(root: Path, mutation) -> None:
    mutation(root)
    try:
        VALIDATE.validate_repository(
            root, pin_hashes=False, skip_frozen_evidence=True
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
        return
    raise RuntimeError("unsafe mutation passed validation")


def expect_source_failure(root: Path, mutation) -> None:
    mutation(root)
    try:
        VALIDATE.validate_source_files(root)
    except (OSError, ValueError, RuntimeError):
        return
    raise RuntimeError("unsafe source mutation passed validation")


def patch(root: Path) -> Path:
    return root / VALIDATE.PATCH


def mutate_manifest_count(root: Path) -> None:
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


def mutate_fragment(root: Path) -> None:
    replace(root / VALIDATE.FRAGMENT, "target-blocked", "target-open")


def mutate_maxcpus(root: Path) -> None:
    replace(root / "configs/gemini-smp8.fragment", "maxcpus=8", "maxcpus=10")


def mutate_series_duplicate(root: Path) -> None:
    path = root / VALIDATE.SERIES
    path.write_text(path.read_text() + path.read_text().splitlines()[-1] + "\n")


def mutate_series_parent(root: Path) -> None:
    replace(root / VALIDATE.SERIES, "v7.1.3/0152-", "v7.1.3/0151-")


def mutate_author(root: Path) -> None:
    replace(patch(root), "Gemini Mainline Project", "Unknown Author")


def mutate_signoff(root: Path) -> None:
    replace(patch(root), "submission-ready.\n", "submission-ready.\nSigned-off-by: X <x@invalid>\n")


def mutate_callback_collapse(root: Path) -> None:
    replace(patch(root), "&draft->evidence, target);", "&draft->evidence, 0);")


def mutate_mapping_membership(root: Path) -> None:
    replace(patch(root), "!cpumask_test_cpu(cpu, &draft->target_cpus) ||", "false ||")


def mutate_mapping_unique(root: Path) -> None:
    replace(patch(root), "cpumask_test_and_set_cpu(cpu, &indexed_targets)", "false")


def mutate_mapping_swap(root: Path) -> None:
    replace(patch(root), "evidence->target_cpu[0] = 8;", "evidence->target_cpu[0] = 9;")


def mutate_per_target_bitmap(root: Path) -> None:
    replace(patch(root), "draft->target[target].local_caps", "draft->target[0].local_caps")


def mutate_aggregate_gate(root: Path) -> None:
    replace(patch(root), "if (!all_classified)\n+\t\t\tcontinue;", "if (false)\n+\t\t\tcontinue;")


def mutate_runtime_origin(root: Path) -> None:
    replace(patch(root), "ARM64_LATE_CPU_BINDING_RUNTIME ||", "ARM64_LATE_CPU_BINDING_FIXTURE ||")


def mutate_runtime_valid(root: Path) -> None:
    replace(patch(root), "binding->valid != ARM64_LATE_CPU_BIND_VALID_MASK", "false")


def mutate_runtime_equality(root: Path) -> None:
    replace(patch(root), "return !memcmp(binding->resolved_config_identity,", "return true || !memcmp(binding->resolved_config_identity,")


def mutate_runtime_blocker(root: Path) -> None:
    replace(patch(root), "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING;", "ARM64_LATE_CPU_BLOCK_EFFECT_PLAN;")


def mutate_validation_blocker(root: Path) -> None:
    replace(patch(root), "if (validate_ret)", "if (false)")


def mutate_ready_copy(root: Path) -> None:
    replace(patch(root), "late_ready_token.binding = late_plan.evidence.binding;", "late_ready_token.binding.valid = 0;")


def mutate_dirty_plan_guard(root: Path) -> None:
    replace(patch(root), "draft->local_caps_planned ||", "false ||")


def mutate_abi_commit_comment(root: Path) -> None:
    replace(
        patch(root),
        "ABI 4 deliberately publishes no mutation path",
        "ABI 4 publishes a mutation path",
    )


def mutate_boot_veto(root: Path) -> None:
    replace(root / VALIDATE.PATCH_0092, "return -EAGAIN;", "return cpu_psci_ops.cpu_boot(cpu);")


def mutate_disable_veto(root: Path) -> None:
    replace(root / VALIDATE.PATCH_0092, "return false;", "return true;")


def source_path(root: Path, name: str) -> Path:
    return root / "arch/arm64/kernel" / name


def source_binding_early_success(root: Path) -> None:
    path = source_path(root, "late_cpu_profile.c")
    replace(
        path,
        "late_profile_runtime_binding_complete("
        "const struct arm64_late_cpu_runtime_binding *binding)\n{\n",
        "late_profile_runtime_binding_complete("
        "const struct arm64_late_cpu_runtime_binding *binding)\n{\n"
        "\treturn true;\n\n",
    )


def source_binding_crosswire(root: Path) -> None:
    path = source_path(root, "late_cpu_profile.c")
    replace(
        path,
        "return !memcmp(binding->resolved_config_identity,\n"
        "\t\t       binding->running_config_identity,",
        "return !memcmp(binding->resolved_config_identity,\n"
        "\t\t       binding->running_image_identity,",
    )


def source_profile_early_success(root: Path) -> None:
    path = source_path(root, "mt6797_psci.c")
    replace(
        path,
        "mt6797_a72_validate_cap_plan(const struct arm64_late_cpu_plan *plan)\n{\n",
        "mt6797_a72_validate_cap_plan(const struct arm64_late_cpu_plan *plan)\n"
        "{\n\treturn 0;\n\n",
    )


def source_classifier_target_collapse(root: Path) -> None:
    path = source_path(root, "cpufeature.c")
    replace(
        path,
        "enum arm64_late_cpu_cap_state *target_state)\n{\n",
        "enum arm64_late_cpu_cap_state *target_state)\n{\n\ttarget = 0;\n",
    )


def source_commit_panic_removed(root: Path) -> None:
    replace(
        source_path(root, "late_cpu_profile.c"),
        'panic("late CPU profile commit implementation is unavailable");',
        "return;",
    )


def source_per_target_bitmap_collapse(root: Path) -> None:
    replace(
        source_path(root, "cpufeature.c"),
        "draft->target[target].local_caps",
        "draft->target[0].local_caps",
    )


def source_mapping_unique_removed(root: Path) -> None:
    replace(
        source_path(root, "cpufeature.c"),
        "cpumask_test_and_set_cpu(cpu, &indexed_targets)",
        "false",
    )


def source_runtime_origin_fixture(root: Path) -> None:
    replace(
        source_path(root, "late_cpu_profile.c"),
        "ARM64_LATE_CPU_BINDING_RUNTIME ||",
        "ARM64_LATE_CPU_BINDING_FIXTURE ||",
    )


MUTATIONS = (
    mutate_manifest_count,
    mutate_profile_series,
    mutate_fragment,
    mutate_maxcpus,
    mutate_series_duplicate,
    mutate_series_parent,
    mutate_author,
    mutate_signoff,
    mutate_callback_collapse,
    mutate_mapping_membership,
    mutate_mapping_unique,
    mutate_mapping_swap,
    mutate_per_target_bitmap,
    mutate_aggregate_gate,
    mutate_runtime_origin,
    mutate_runtime_valid,
    mutate_runtime_equality,
    mutate_runtime_blocker,
    mutate_validation_blocker,
    mutate_ready_copy,
    mutate_dirty_plan_guard,
    mutate_abi_commit_comment,
    mutate_boot_veto,
    mutate_disable_veto,
)
SOURCE_MUTATIONS = (
    source_binding_early_success,
    source_binding_crosswire,
    source_profile_early_success,
    source_classifier_target_collapse,
    source_commit_panic_removed,
    source_per_target_bitmap_collapse,
    source_mapping_unique_removed,
    source_runtime_origin_fixture,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = VALIDATE.default_repo()
    kernel_source = args.source_root.resolve()
    if VALIDATE.run_git(kernel_source, ["rev-parse", "HEAD"]).strip() != VALIDATE.SOURCE:
        raise RuntimeError("source checkout is not at the pinned commit")
    print("validation=a41-per-target-mutations")
    with tempfile.TemporaryDirectory(prefix="gemini-a41-target-baseline-") as tmp:
        baseline = Path(tmp)
        copy_inputs(source, baseline)
        VALIDATE.validate_repository(
            baseline, pin_hashes=False, skip_frozen_evidence=True
        )
    with tempfile.TemporaryDirectory(prefix="gemini-a41-source-baseline-") as tmp:
        baseline = Path(tmp)
        copy_source_inputs(kernel_source, baseline)
        VALIDATE.validate_source_files(baseline)
    passed = 0
    for mutation in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="gemini-a41-target-mutation-") as tmp:
            root = Path(tmp)
            copy_inputs(source, root)
            expect_failure(root, mutation)
            passed += 1
            print(f"PASS {mutation.__name__}")
    for mutation in SOURCE_MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="gemini-a41-source-mutation-") as tmp:
            root = Path(tmp)
            copy_source_inputs(kernel_source, root)
            expect_source_failure(root, mutation)
            passed += 1
            print(f"PASS {mutation.__name__}")
    if tuple(mutation.__name__ for mutation in (*MUTATIONS, *SOURCE_MUTATIONS)) != \
            VALIDATE.MUTATION_NAMES:
        raise RuntimeError("mutation inventory changed")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print(f"RESULT PASS {passed}/{len(MUTATIONS) + len(SOURCE_MUTATIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
