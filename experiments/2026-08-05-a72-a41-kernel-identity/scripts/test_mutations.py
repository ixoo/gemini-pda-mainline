#!/usr/bin/env python3
"""Require every bounded ABI-7 repository/source mutation to fail its check."""

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
SPEC = importlib.util.spec_from_file_location("a41_identity_validate", HERE / "validate.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load kernel-identity validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor count changed in {path.name}: {old!r}")
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
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)


def expect_repository_failure(root: Path, mutation, expected: str) -> None:
    mutation(root)
    try:
        VALIDATE.validate_repository(root, pin_hashes=False)
    except VALIDATE.ValidationError as error:
        if error.check != expected:
            raise RuntimeError(
                f"{mutation.__name__} failed {error.check}, expected {expected}: {error}"
            ) from error
        return
    raise RuntimeError(f"unsafe repository mutation passed: {mutation.__name__}")


def expect_source_failure(root: Path, mutation, expected: str, repo: Path) -> None:
    mutation(root)
    try:
        VALIDATE.validate_source_files(root, repo=repo)
    except VALIDATE.ValidationError as error:
        if error.check != expected:
            raise RuntimeError(
                f"{mutation.__name__} failed {error.check}, expected {expected}: {error}"
            ) from error
        return
    raise RuntimeError(f"unsafe source mutation passed: {mutation.__name__}")


def repo_manifest_profile_missing(root: Path) -> None:
    path = root / VALIDATE.MANIFEST
    data = json.loads(path.read_text())
    del data["config"]["profiles"][VALIDATE.PROFILE]
    path.write_text(json.dumps(data, indent=2) + "\n")


def repo_profile_series_substitution(root: Path) -> None:
    path = root / VALIDATE.MANIFEST
    data = json.loads(path.read_text())
    data["config"]["profiles"][VALIDATE.PROFILE]["patch_series"] = str(
        VALIDATE.PARENT_SERIES
    )
    path.write_text(json.dumps(data, indent=2) + "\n")


def repo_fragment_fixture_enable(root: Path) -> None:
    replace_once(
        root / VALIDATE.FRAGMENT,
        "# CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE is not set",
        "CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE=y",
    )


def repo_selected_series_duplicate(root: Path) -> None:
    path = root / VALIDATE.SERIES
    path.write_text(path.read_text() + VALIDATE.PATCH_ARM64.relative_to("patches").as_posix() + "\n")


def repo_canonical_order_change(root: Path) -> None:
    path = root / VALIDATE.CANONICAL_SERIES
    lines = path.read_text().splitlines()
    first = next(i for i, line in enumerate(lines) if "0156-" in line)
    second = next(i for i, line in enumerate(lines) if "0157-" in line)
    lines[first], lines[second] = lines[second], lines[first]
    path.write_text("\n".join(lines) + "\n")


def repo_patch_source_change(root: Path) -> None:
    replace_once(root / VALIDATE.PATCH_BUILDID, VALIDATE.PATCH_BUILDID_COMMIT, "0" * 40)


def repo_patch_inventory_change(root: Path) -> None:
    replace_once(
        root / VALIDATE.PATCH_ARM64,
        "diff --git a/arch/arm64/kernel/smp.c b/arch/arm64/kernel/smp.c",
        "diff --git a/arch/arm64/kernel/unsafe.c b/arch/arm64/kernel/unsafe.c",
    )


def repo_external_action_injection(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT / "scripts/test_mutations.py"
    path.write_text(path.read_text() + "\ndef unsafe():\n    subprocess.run(['external'])\n")


REPOSITORY_CASES = (
    repo_manifest_profile_missing,
    repo_profile_series_substitution,
    repo_fragment_fixture_enable,
    repo_selected_series_duplicate,
    repo_canonical_order_change,
    repo_patch_source_change,
    repo_patch_inventory_change,
    repo_external_action_injection,
)


def source_path(root: Path, relative: str) -> Path:
    return root / relative


def source_abi_downgrade(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/include/asm/late_cpu_profile.h"), "#define ARM64_LATE_CPU_PLAN_ABI\t\t7", "#define ARM64_LATE_CPU_PLAN_ABI\t\t6")


def source_kconfig_producer_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/Kconfig"), "\tselect IKCONFIG\n", "")


def source_buildid_duplicate_loss(root: Path) -> None:
    replace_once(source_path(root, "lib/buildid.c"), "\t\t\tif (found || nhdr.n_descsz != expected_size ||", "\t\t\tif (nhdr.n_descsz != expected_size ||")


def source_buildid_bounds_loss(root: Path) -> None:
    replace_once(source_path(root, "lib/buildid.c"), "\t\t    note_size > buf_size - offset)", "\t\t    false)")


def source_buildid_zero_loss(root: Path) -> None:
    replace_once(source_path(root, "lib/buildid.c"), "\t\t\t    !memchr_inv(desc, 0, expected_size))", "\t\t\t    false)")


def source_buildid_alias_staging_loss(root: Path) -> None:
    replace_once(source_path(root, "lib/buildid.c"), "\tmemcpy(parsed, found, expected_size);", "\tmemcpy(build_id, found, expected_size);")


def source_buildid_failure_zero_loss(root: Path) -> None:
    replace_once(source_path(root, "lib/buildid.c"), "invalid:\n\tmemset(build_id, 0, BUILD_ID_SIZE_MAX);\n\treturn -EINVAL;", "invalid:\n\treturn -EINVAL;")


def source_buildid_kunit_wiring_loss(root: Path) -> None:
    replace_once(source_path(root, "lib/Makefile"), "obj-$(CONFIG_BUILDID_KUNIT_TEST) += buildid_test.o\n", "")


def source_private_owner_export(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "static struct late_runtime_identity late_runtime_identity __initdata;", "struct late_runtime_identity late_runtime_identity __initdata;")


def source_of_name_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), '[LATE_PROP_NAME] = "name",', '[LATE_PROP_NAME] = "unsafe-name",')


def source_of_dynamic_property_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "\t\tif (of_property_check_flag(property, OF_DYNAMIC))\n\t\t\tgoto out;\n", "")


def source_record_identity_polarity(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "\tif (memcmp(record_digest, record.record_identity,", "\tif (!memcmp(record_digest, record.record_identity,")


def source_digest_endian_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "get_unaligned_be64(digest + i * sizeof(u64))", "get_unaligned_le64(digest + i * sizeof(u64))")


def source_ikconfig_bound_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "if (!config_size || config_size > LATE_RUNTIME_IKCONFIG_MAX)", "if (!config_size)")


def source_exact_helper_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "build_id_parse_buf_exact(notes, build_id, notes_size,", "build_id_parse_buf(notes, build_id, notes_size) ||\n\t    false /* exact helper removed */ ||")


def source_cmdline_equality_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "memcmp(saved_command_line, CONFIG_CMDLINE, sizeof(CONFIG_CMDLINE))", "false")


def source_global_staging_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "late_runtime_parse_expected_record(&staged)", "late_runtime_parse_expected_record(&late_runtime_identity)")


def source_late_collect_guard_polarity(root: Path) -> None:
    replace_once(
        source_path(root, "arch/arm64/kernel/late_cpu_profile.c"),
        "\t\t    LATE_RUNTIME_IDENTITY_UNCOLLECTED ||\n\t    system_capabilities_finalized() ||",
        "\t\t    LATE_RUNTIME_IDENTITY_UNCOLLECTED ||\n\t    !system_capabilities_finalized() ||",
    )


def source_sealed_empty_polarity(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "\t    !memchr_inv(&late_runtime_identity, 0,", "\t    memchr_inv(&late_runtime_identity, 0,")


def source_sealed_identity_promotion(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "state = LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY;", "state = LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME;")


def source_release_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "smp_store_release(&late_runtime_evidence_state, state);", "WRITE_ONCE(late_runtime_evidence_state, state);")


def source_acquire_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "runtime_state = smp_load_acquire(&late_runtime_evidence_state);", "runtime_state = READ_ONCE(late_runtime_evidence_state);")


def source_crossbind_profile_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "if (strcmp(late_runtime_identity.profile_id, profile_id) ||", "if (false ||")


def source_crossbind_config_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "\t    memcmp(late_runtime_identity.config_input_identity,", "\t    false && memcmp(late_runtime_identity.config_input_identity,")


def source_crossbind_target_loss(root: Path) -> None:
    replace_once(
        source_path(root, "arch/arm64/kernel/late_cpu_profile.c"),
        "\t\t    !cpumask_test_cpu(late_runtime_identity.target_cpu[target],\n\t\t\t\t      registered_targets))",
        "\t\t    false)",
    )


def source_overlay_condition_change(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "if (runtime_state == LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY)", "if (runtime_state != LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY)")


def source_overlay_scope_broadened(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "draft.evidence.binding = late_runtime_evidence.binding;", "draft.evidence = late_runtime_evidence;")


def source_profile_observation_rejection_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "if (!late_profile_runtime_fields_empty(&profile_evidence)) {", "if (false && !late_profile_runtime_fields_empty(&profile_evidence)) {")


def source_fixture_claims_runtime(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/mt6797_psci.c"), "evidence->binding.origin = ARM64_LATE_CPU_BINDING_FIXTURE;", "evidence->binding.origin = ARM64_LATE_CPU_BINDING_RUNTIME;")


def source_collect_order_change(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/smp.c"), "\tarm64_collect_late_cpu_runtime_identity();\n\tarm64_seal_late_cpu_runtime_evidence();", "\tarm64_seal_late_cpu_runtime_evidence();\n\tarm64_collect_late_cpu_runtime_identity();")


def source_profile_prepare_success(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/mt6797_psci.c"), "\t/* No live system capability, alternative, vector, or HWCAP is changed. */\n\treturn -EAGAIN;", "\treturn 0;")


def source_profile_validator_success(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/mt6797_psci.c"), "\t/* Source-only fixture/expected evidence never publishes an identity. */\n\treturn -EAGAIN;", "\treturn 0;")


def source_core_commit_blocker_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), "draft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH;", "draft.evidence.blocker_mask |= 0;")


def source_core_commit_panic_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/late_cpu_profile.c"), 'panic("late CPU profile commit implementation is unavailable");', "return;")


def source_cpu_boot_veto_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/mt6797_psci.c"), "return -EAGAIN;\n}\n\n#ifdef CONFIG_HOTPLUG_CPU", "return cpu_psci_ops.cpu_boot(cpu);\n}\n\n#ifdef CONFIG_HOTPLUG_CPU")


def source_cpu_disable_veto_loss(root: Path) -> None:
    replace_once(source_path(root, "arch/arm64/kernel/mt6797_psci.c"), "mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n\treturn false;", "mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n\treturn true;")


SOURCE_CASES = (
    source_abi_downgrade,
    source_kconfig_producer_loss,
    source_buildid_duplicate_loss,
    source_buildid_bounds_loss,
    source_buildid_zero_loss,
    source_buildid_alias_staging_loss,
    source_buildid_failure_zero_loss,
    source_buildid_kunit_wiring_loss,
    source_private_owner_export,
    source_of_name_loss,
    source_of_dynamic_property_loss,
    source_record_identity_polarity,
    source_digest_endian_loss,
    source_ikconfig_bound_loss,
    source_exact_helper_loss,
    source_cmdline_equality_loss,
    source_global_staging_loss,
    source_late_collect_guard_polarity,
    source_sealed_empty_polarity,
    source_sealed_identity_promotion,
    source_release_loss,
    source_acquire_loss,
    source_crossbind_profile_loss,
    source_crossbind_config_loss,
    source_crossbind_target_loss,
    source_overlay_condition_change,
    source_overlay_scope_broadened,
    source_profile_observation_rejection_loss,
    source_fixture_claims_runtime,
    source_collect_order_change,
    source_profile_prepare_success,
    source_profile_validator_success,
    source_core_commit_blocker_loss,
    source_core_commit_panic_loss,
    source_cpu_boot_veto_loss,
    source_cpu_disable_veto_loss,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", "--repo-root", dest="repo", type=Path, default=VALIDATE.default_repo())
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    source = args.source_root.resolve()
    if len(REPOSITORY_CASES) != len(VALIDATE.REPOSITORY_MUTATIONS):
        raise RuntimeError("repository mutation labels are out of sync")
    if len(SOURCE_CASES) != len(VALIDATE.SOURCE_MUTATIONS):
        raise RuntimeError("source mutation labels are out of sync")

    print("validation=a41-kernel-identity-mutations")
    with tempfile.TemporaryDirectory(prefix="gemini-a41-identity-repo-base-") as temporary:
        root = Path(temporary)
        copy_repository_inputs(repo, root)
        VALIDATE.validate_repository(root, pin_hashes=False)
    with tempfile.TemporaryDirectory(prefix="gemini-a41-identity-source-base-") as temporary:
        root = Path(temporary)
        copy_source_inputs(source, root)
        VALIDATE.validate_source_files(root, repo=repo)

    passed: list[str] = []
    for mutation, (name, expected) in zip(REPOSITORY_CASES, VALIDATE.REPOSITORY_MUTATIONS):
        with tempfile.TemporaryDirectory(prefix="gemini-a41-identity-repo-") as temporary:
            root = Path(temporary)
            copy_repository_inputs(repo, root)
            expect_repository_failure(root, mutation, expected)
        passed.append(name)
        print(f"PASS {name} -> {expected}")
    for mutation, (name, expected) in zip(SOURCE_CASES, VALIDATE.SOURCE_MUTATIONS):
        with tempfile.TemporaryDirectory(prefix="gemini-a41-identity-source-") as temporary:
            root = Path(temporary)
            copy_source_inputs(source, root)
            expect_source_failure(root, mutation, expected, repo)
        passed.append(name)
        print(f"PASS {name} -> {expected}")

    print(f"mutations_rejected={len(passed)}")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print(f"RESULT PASS {len(passed)}/{len(passed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
