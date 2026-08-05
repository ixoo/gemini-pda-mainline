#!/usr/bin/env python3
"""Validate the blocked A41 ABI-4 per-target planning boundary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

sys.dont_write_bytecode = True

EXPERIMENT = Path("experiments/2026-08-05-a72-a41-per-target-plan")
PARENT_VALIDATOR = Path(
    "experiments/2026-08-05-a72-a41-static-census/scripts/validate.py"
)
PATCH = Path(
    "patches/v7.1.3/0153-arm64-preserve-per-target-late-CPU-capability-state.patch"
)
PATCH_0092 = Path(
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
)
SERIES = Path("patches/series-a72-reject-gate-a41-per-target-plan")
PARENT_SERIES = Path("patches/series-a72-reject-gate-a41-static-census")
CANONICAL_SERIES = Path("patches/series")
FRAGMENT = Path("configs/gemini-a72-a41-per-target-plan.fragment")
MANIFEST = Path("kernel/manifest.json")
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-per-target-plan"
)

PATCH_SHA256 = "c89fa4c00ee56fbf259f3ddbc19d7434fb08d7bac91530db5f8d5f5d54e3caa7"
SERIES_SHA256 = "85874b97036200f24cb0f72cc4bc2592963f8aeb71fa9dfeb88d6e2c95ff19ca"
PATCHSET_SHA256 = "e7f8a5aadc4103ae0723bdac55ec5405600cabdcca9bfd0fe50453f09e0af012"
SOURCE_STATE_SHA256 = "78fcb018e5693cc258127ea6e2655319f55b80135c1230cb42fbf70c6d2e6deb"
PARENT_SOURCE_STATE_SHA256 = (
    "f073150a6bbfb6af1d4262f4b754534118181ee40284d60a59aa1068740d118d"
)
CONFIG_SHA256 = "4dfe301404e0d972342311b51e9c9674d7ec3bc5198912fb2ec7f6167f72fb3e"
PARENT_VALIDATOR_SHA256 = (
    "a52019ee9021b507f91876ff22eeb1580108e7c18f4fb918c5b7f58bf058dfbd"
)
PARENT = "63e5d894150a5d5d1d897a639199a096815bb385"
PARENT_TREE = "c3db9d87cf885b6e2313041e1e3b8b28ea8e98c1"
SOURCE = "7fcc8ca433d2306d2e3d005289d6cf01dfbf0f4c"
SOURCE_TREE = "47133d89119afe60e38057c8ac39840665a1f142"
SOURCE_DIFF_SHA256 = "a4927f805364a0cace03dd1c0326c59f33479b9d47e3db2600541969e52a5d1f"
PROFILE_COUNT = 59
SERIES_ENTRY_COUNT = 95

EXPECTED_EXPERIMENT_FILES = {
    "DESIGN.md",
    "README.md",
    "results/implementation.tsv",
    "results/kernel-static-review-20260805.txt",
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
    "scripts/test_mutations.py",
    "scripts/validate.py",
}
FROZEN_TRANSCRIPTS = {
    "results/kernel-static-review-20260805.txt",
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
}
FROZEN_FILE_SHA256 = {
    "DESIGN.md": "e1725c952ac491284bbc73f3f011ab9a05e64584eb817bef519c9847d9250819",
    "README.md": "99e06cf286d33fdb97ef7639c91a55e948fa47088e73bae1f872816fe791899e",
    "results/implementation.tsv":
        "2e747e38b7ec3a0429a28ec2caaf9ecc97aa1ff63faf13473ac434d5cd8f2a04",
    "results/kernel-static-review-20260805.txt":
        "cc1dd49c8e6af1c382679fe64f0b7bb6a864fc56b0b0f79afbfdb1cc9a732760",
    "results/mutation-validation-20260805.txt":
        "bd3f2fd74f81e991ace4cb725107fc6149bffd273836c84c1960e6408b1394ab",
    "results/offline-validation-20260805.txt":
        "bf3897756e6e4f3151cbc4cc55106092223a9c978605f8671aa59bb1968958c0",
    "scripts/test_mutations.py":
        "3b7247c0f9cdf614b989d27bb1478c49832a7729742fc49ccbab3bed094254d9",
}
CHANGED_PATHS = (
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/cpufeature.c",
    "arch/arm64/kernel/late_cpu_profile.c",
    "arch/arm64/kernel/mt6797_psci.c",
)
REPOSITORY_CHECKS = (
    "experiment-inventory",
    "manifest-profile",
    "configuration-identity",
    "all-profile-series",
    "selected-series",
    "patch-provenance",
    "claim-boundary",
    "veto-preservation",
    "frozen-results",
)
SOURCE_CHECKS = (
    "source-identity",
    "patch-application",
    "per-target-planner",
    "runtime-binding-guard",
    "publication-vetoes",
    "static-tooling",
)
MUTATION_NAMES = (
    "mutate_manifest_count",
    "mutate_profile_series",
    "mutate_fragment",
    "mutate_maxcpus",
    "mutate_series_duplicate",
    "mutate_series_parent",
    "mutate_author",
    "mutate_signoff",
    "mutate_callback_collapse",
    "mutate_mapping_membership",
    "mutate_mapping_unique",
    "mutate_mapping_swap",
    "mutate_per_target_bitmap",
    "mutate_aggregate_gate",
    "mutate_runtime_origin",
    "mutate_runtime_valid",
    "mutate_runtime_equality",
    "mutate_runtime_blocker",
    "mutate_validation_blocker",
    "mutate_ready_copy",
    "mutate_dirty_plan_guard",
    "mutate_abi_commit_comment",
    "mutate_boot_veto",
    "mutate_disable_veto",
    "source_binding_early_success",
    "source_binding_crosswire",
    "source_profile_early_success",
    "source_classifier_target_collapse",
    "source_commit_panic_removed",
    "source_per_target_bitmap_collapse",
    "source_mapping_unique_removed",
    "source_runtime_origin_fixture",
)


def load_parent(repo: Path):
    path = repo / PARENT_VALIDATOR
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_VALIDATOR_SHA256:
        raise ValueError("parent validator identity changed")
    spec = importlib.util.spec_from_file_location("a41_static_parent", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load parent validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config_hash(repo: Path, profile: dict) -> str:
    lines = [f"profile={PROFILE}", f"base={profile['base']}"]
    for name in profile["fragments"]:
        digest = hashlib.sha256((repo / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def validate_inventory(repo: Path, *, skip_frozen_evidence: bool) -> None:
    root = repo / EXPERIMENT
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    required = EXPECTED_EXPERIMENT_FILES - FROZEN_TRANSCRIPTS
    if skip_frozen_evidence:
        if not required <= actual <= EXPECTED_EXPERIMENT_FILES:
            raise ValueError("experiment inventory changed")
    elif actual != EXPECTED_EXPERIMENT_FILES:
        raise ValueError("frozen experiment inventory changed")
    for relative in actual:
        path = root / relative
        if path.is_symlink():
            raise ValueError(f"experiment symlink is forbidden: {relative}")
        text = path.read_text()
        if ("/" + "Users/") in text:
            raise ValueError(f"experiment file exposes a host path: {relative}")
        if ("arti" + "facts/") in text:
            raise ValueError(f"experiment file refers to private artifacts: {relative}")
        if any(line.endswith((" ", "\t")) for line in text.splitlines()):
            raise ValueError(f"experiment file has trailing whitespace: {relative}")
        forbidden = (
            "cu" + "rl", "wg" + "et", "s" + "sh", "sc" + "p",
            "rsy" + "nc", "nc" + "at", "so" + "cat",
            "build" + "-kernel", "dev" + "-vm",
        )
        if relative.startswith("scripts/") and re.search(
            r"(?<![A-Za-z0-9_])(?:" + "|".join(map(re.escape, forbidden)) +
            r")(?![A-Za-z0-9_])", text
        ):
            raise ValueError(f"experiment script contains an external action: {relative}")
    for relative, digest in FROZEN_FILE_SHA256.items():
        path = root / relative
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"frozen experiment file changed: {relative}")


def validate_markers(repo: Path) -> None:
    path = repo / EXPERIMENT / "results/implementation.tsv"
    rows = [line.split("\t", 2) for line in path.read_text().splitlines()[1:]]
    markers = {row[0]: row[1] for row in rows if len(row) == 3}
    wanted = {
        "implementation_state": "PARTIAL_PER_TARGET_PLAN_BOUNDARY",
        "a41_complete": "no",
        "plan_abi": "4",
        "target_slot_0": "CPU8",
        "target_slot_1": "CPU9",
        "per_target_classified_count": "34",
        "per_target_present_count": "4",
        "per_target_absent_count": "30",
        "per_target_unresolved_count": "6",
        "runtime_binding_origin": "NONE",
        "runtime_binding_complete": "no",
        "effect_plan_complete": "no",
        "local_caps_planned": "0",
        "canonical_plan_identity": "unavailable",
        "profile_validate_plan": "-EAGAIN",
        "profile_prepare": "-EAGAIN",
        "plan_frozen_reachable": "no",
        "committed_reachable": "no",
        "ready_reachable": "no",
        "cpu_boot_veto": "-EAGAIN",
        "cpu_disable_veto": "false",
        "maxcpus": "8",
        "build_authorized": "no",
        "device_action_authorized": "no",
        "boot_candidate": "false",
    }
    if markers != wanted:
        raise ValueError("implementation claim boundary changed")


def offline_result_lines() -> list[str]:
    checks = (*REPOSITORY_CHECKS, *SOURCE_CHECKS)
    return [
        "validation=a41-per-target-plan-offline",
        *(f"PASS {check}" for check in checks),
        f"patch_sha256={PATCH_SHA256}",
        f"series_sha256={SERIES_SHA256}",
        f"patchset_sha256={PATCHSET_SHA256}",
        f"source_state_sha256={SOURCE_STATE_SHA256}",
        f"config_sha256={CONFIG_SHA256}",
        "target0=CPU8:34-classified:4-present:6-unresolved",
        "target1=CPU9:34-classified:4-present:6-unresolved",
        "implementation_state=PARTIAL_PER_TARGET_PLAN_BOUNDARY",
        "a41_complete=no",
        "network_accessed=no",
        "build_invoked=no",
        "device_accessed=no",
        "build_authorized=no",
        "device_action_authorized=no",
        f"RESULT PASS {len(checks)}/{len(checks)}",
    ]


def mutation_result_lines() -> list[str]:
    return [
        "validation=a41-per-target-mutations",
        *(f"PASS {name}" for name in MUTATION_NAMES),
        "network_accessed=no",
        "build_invoked=no",
        "device_accessed=no",
        f"RESULT PASS {len(MUTATION_NAMES)}/{len(MUTATION_NAMES)}",
    ]


def validate_frozen_results(repo: Path, *, skip_frozen_evidence: bool) -> None:
    results = repo / EXPERIMENT / "results"
    offline = results / "offline-validation-20260805.txt"
    mutations = results / "mutation-validation-20260805.txt"
    if skip_frozen_evidence and (not offline.exists() or not mutations.exists()):
        return
    if offline.read_text().splitlines() != offline_result_lines():
        raise ValueError("offline result is not exact validator stdout")
    if mutations.read_text().splitlines() != mutation_result_lines():
        raise ValueError("mutation result is not exact suite stdout")
    static = results / "kernel-static-review-20260805.txt"
    fields = dict(
        line.split("=", 1) for line in static.read_text().splitlines()
        if "=" in line
    )
    expected = {
        "validation": "a41-per-target-kernel-static-review",
        "source_commit": SOURCE,
        "source_tree": SOURCE_TREE,
        "source_diff_sha256": SOURCE_DIFF_SHA256,
        "format_patch_sha256": PATCH_SHA256,
        "source_diff_checkpatch_errors": "0",
        "source_diff_checkpatch_warnings": "0",
        "source_diff_checkpatch_checks": "0",
        "format_patch_checkpatch_errors": "0",
        "format_patch_checkpatch_warnings": "0",
        "format_patch_checkpatch_checks": "0",
        "duplicate_includes": "0",
        "python_syntax": "PASS",
        "native_build_invoked": "no",
        "buildbox_build_invoked": "no",
        "network_accessed": "no",
        "device_accessed": "no",
    }
    for key, value in expected.items():
        if fields.get(key) != value:
            raise ValueError(f"kernel static result changed: {key}")
    if static.read_text().splitlines()[-1] != "RESULT PASS":
        raise ValueError("kernel static result is incomplete")


def validate_repository(repo: Path, *, pin_hashes: bool = True,
                        skip_frozen_evidence: bool = False) -> list[str]:
    repo = repo.resolve()
    parent = load_parent(repo)
    require = parent.require
    validate_inventory(repo, skip_frozen_evidence=skip_frozen_evidence)
    validate_markers(repo)
    validate_frozen_results(repo, skip_frozen_evidence=skip_frozen_evidence)

    patch_path = repo / PATCH
    patch = patch_path.read_text()
    manifest = json.loads((repo / MANIFEST).read_text())
    profiles = manifest["config"]["profiles"]
    require(len(profiles) == PROFILE_COUNT, "manifest profile count changed")
    require(PROFILE in profiles, "per-target profile is missing")
    profile = profiles[PROFILE]
    require(profile.get("base") == "defconfig", "profile base changed")
    require(profile.get("patch_series") == str(SERIES), "profile series changed")
    require(profile.get("fragments", [])[-1] == str(FRAGMENT),
            "profile fragment changed")
    for name, candidate in profiles.items():
        if name != PROFILE:
            require(candidate.get("patch_series") != str(SERIES),
                    f"per-target series leaked into profile {name}")
            require(str(FRAGMENT) not in candidate.get("fragments", []),
                    f"per-target fragment leaked into profile {name}")
    assignments = [
        line.strip() for line in (repo / FRAGMENT).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(assignments == [
        "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
        'CONFIG_LOCALVERSION="-gemini-a41-target-blocked"',
    ], "per-target fragment gained an unreviewed setting")
    require("maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(),
            "inherited maxcpus=8 changed")
    require(config_hash(repo, profile) == CONFIG_SHA256,
            "configuration-input identity changed")

    selected = parent.series_entries((repo / SERIES).read_text())
    parent_selected = parent.series_entries((repo / PARENT_SERIES).read_text())
    canonical = parent.series_entries((repo / CANONICAL_SERIES).read_text())
    parent.validate_all_profile_series(repo, manifest, canonical)
    require(len(selected) == SERIES_ENTRY_COUNT, "selected series count changed")
    require(selected[:-1] == parent_selected, "parent series prefix changed")
    require(selected[-1] == str(PATCH.relative_to("patches")),
            "patch 0153 is not the selected tail")
    if pin_hashes:
        require(parent.file_sha256(repo / PATCH) == PATCH_SHA256,
                "format-patch identity changed")
        require(parent.file_sha256(repo / SERIES) == SERIES_SHA256,
                "selected series identity changed")
        require(parent.patchset_hash(repo, SERIES) == PATCHSET_SHA256,
                "patchset identity changed")
        require(parent.source_state_hash(repo, SERIES) == SOURCE_STATE_SHA256,
                "source-state identity changed")
        require(parent.source_state_hash(repo, PARENT_SERIES) ==
                PARENT_SOURCE_STATE_SHA256, "parent source state changed")

    match = re.match(r"From ([0-9a-f]{40}) ", patch)
    require(match is not None and match.group(1) == SOURCE,
            "patch source commit changed")
    parent.tokens(patch.split("\n---\n", 1)[0], [
        "From: Gemini Mainline Project <noreply@invalid>",
        "Subject: [PATCH] arm64: preserve per-target late-CPU capability state",
        "This experiment-only change has no certifying sign-off and is not\n"
        "submission-ready.",
    ], "patch metadata")
    require("Signed-off-by:" not in patch, "synthetic patch gained a sign-off")
    sections = parent.patch_sections(patch)
    require(tuple(sections) == CHANGED_PATHS, "patch changed-path set changed")

    additions = parent.added_lines(patch)
    for forbidden in (
        "ARM64_LATE_CPU_PROFILE_READY);",
        "cpu_psci_ops.cpu_boot(cpu)",
        "plan->identity[0] =",
        "local_caps_planned = 1",
    ):
        require(forbidden not in additions, f"patch added forbidden path {forbidden}")
    exact_counts = {
        "&draft->evidence, target);": 2,
        "draft->target[target].classified_local_caps": 3,
        "draft->target[target].local_caps": 2,
        "if (!all_classified)": 1,
        "ARM64_LATE_CPU_BINDING_RUNTIME ||": 1,
        "binding->valid != ARM64_LATE_CPU_BIND_VALID_MASK": 1,
        "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING;": 1,
        "if (validate_ret)": 1,
        "late_ready_token.binding = late_plan.evidence.binding;": 1,
    }
    for token, count in exact_counts.items():
        require(additions.count(token) == count,
                f"patch contract count changed for {token!r}")
    parent.tokens(patch, [
        "!cpumask_test_cpu(cpu, &draft->target_cpus) ||",
        "cpumask_test_and_set_cpu(cpu, &indexed_targets)",
        "evidence->target_cpu[0] = 8;",
        "evidence->target_cpu[1] = 9;",
        "return !memcmp(binding->resolved_config_identity,",
        "ABI 4 deliberately publishes no mutation path",
        "draft->local_caps_planned ||",
    ], "format-patch safety contract")

    patch_0092 = (repo / PATCH_0092).read_text()
    boot = parent.function(parent.patch_postimage(
        parent.patch_sections(patch_0092)["arch/arm64/kernel/mt6797_psci.c"]
    ), "mt6797_psci_cpu_boot")
    disable = parent.function(parent.patch_postimage(
        parent.patch_sections(patch_0092)["arch/arm64/kernel/mt6797_psci.c"]
    ), "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot,
            "boot veto changed")
    require("return false;" in disable, "disable veto changed")
    require("PARTIAL_PER_TARGET_PLAN_BOUNDARY" in
            (repo / EXPERIMENT / "README.md").read_text(),
            "experiment claim is missing")
    require("A41 per-target capability planning" in
            (repo / "docs/ROADMAP.md").read_text(), "roadmap milestone is missing")
    return list(REPOSITORY_CHECKS)


def validate_source_files(root: Path) -> None:
    parent = load_parent(default_repo())
    require = parent.require
    header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    core = (root / "arch/arm64/kernel/cpufeature.c").read_text()
    lifecycle = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    mt = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    parent.tokens(header, [
        "#define ARM64_LATE_CPU_PLAN_ABI\t\t4",
        "ARM64_LATE_CPU_BLOCK_EFFECT_PLAN",
        "ARM64_LATE_CPU_BLOCK_PLAN_VALIDATION",
        "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
        "ARM64_LATE_CPU_BINDING_NONE",
        "ARM64_LATE_CPU_BINDING_FIXTURE",
        "ARM64_LATE_CPU_BINDING_RUNTIME",
        "ARM64_LATE_CPU_BIND_VALID_MASK",
        "struct arm64_late_cpu_target_plan",
        "target[ARM64_LATE_CPU_MAX_TARGETS]",
        "unsigned int target);",
    ], "ABI 4 schema")

    planner = parent.function(core, "arm64_plan_late_cpu_capabilities")
    classifier = parent.function(core, "classify_late_cpu_cap")
    parent.tokens(planner, [
        "cpumask_weight(&draft->target_cpus) != profile->target_count",
        "cpu = draft->evidence.target_cpu[target]",
        "cpu >= nr_cpu_ids",
        "!cpumask_test_cpu(cpu, &draft->target_cpus)",
        "cpumask_test_and_set_cpu(cpu, &indexed_targets)",
        "!cpumask_equal(&indexed_targets, &draft->target_cpus)",
        "target >= profile->target_count",
        "draft->target[target].classified_local_caps",
        "draft->target[target].local_caps",
        "if (!all_classified)",
        "if (any_present)",
        "draft->target_local_caps",
    ], "per-target core planner")
    require(planner.index("cpumask_test_and_set_cpu") <
            planner.index("classify_late_cpu_cap(cap"),
            "target mapping is not validated before classification")
    require(planner.count("draft->target[target].classified_local_caps") == 3 and
            planner.count("draft->target[target].local_caps") == 2,
            "per-target planner bitmap use changed")
    require(classifier.count("&draft->evidence, target") == 2,
            "match-list classification collapsed the target index")
    require(not re.search(r"\btarget\s*=", classifier),
            "classifier rewrites the validated target index")

    binding = parent.function(lifecycle, "late_profile_runtime_binding_complete")
    parent.tokens(binding, [
        "ARM64_LATE_CPU_BINDING_RUNTIME",
        "ARM64_LATE_CPU_BIND_VALID_MASK",
        "resolved_config_identity", "running_config_identity",
        "built_image_identity", "running_image_identity",
        "expected_cmdline_identity", "running_cmdline_identity",
    ], "runtime binding guard")
    require(binding.count("!memcmp(") == 3,
            "runtime binding equality checks changed")
    parent.tokens(binding, [
        "return !memcmp(binding->resolved_config_identity,\n"
        "\t\t       binding->running_config_identity,",
        "!memcmp(binding->built_image_identity,\n"
        "\t\t       binding->running_image_identity,",
        "!memcmp(binding->expected_cmdline_identity,\n"
        "\t\t       binding->running_cmdline_identity,",
    ], "runtime binding identity pairs")
    require(binding.count("return ") == 2 and
            binding.index("return false;") < binding.index("return !memcmp("),
            "runtime binding control flow changed")
    prepare = parent.function(lifecycle, "arm64_prepare_late_cpu_profile")
    parent.tokens(prepare, [
        "!late_profile_runtime_binding_complete(&draft.evidence.binding)",
        "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
        "if (plan_ret)", "ARM64_LATE_CPU_BLOCK_CAP_INVENTORY",
        "if (validate_ret)", "ARM64_LATE_CPU_BLOCK_PLAN_VALIDATION",
    ], "lifecycle blockers")
    require(prepare.index("late_profile_runtime_binding_complete") <
            prepare.index("arm64_plan_late_cpu_capabilities"),
            "runtime binding is checked after planning")
    commit = parent.function(lifecycle, "arm64_commit_late_cpu_profile")
    require(commit.count(
        'panic("late CPU profile commit implementation is unavailable")'
    ) == 1,
            "commit panic changed")
    finalize = parent.function(lifecycle, "arm64_finalize_late_cpu_profile_user")
    parent.tokens(finalize, [
        "late_ready_token.binding = late_plan.evidence.binding",
        "late_ready_token.target_cpu, late_plan.evidence.target_cpu",
    ], "READY provenance copy")

    profile_prepare = parent.function(mt, "mt6797_a72_profile_prepare")
    profile_validate = parent.function(mt, "mt6797_a72_validate_cap_plan")
    profile_classify = parent.function(mt, "mt6797_a72_classify_local_cap")
    expected_only = parent.function(mt, "mt6797_a72_evidence_is_expected_only")
    binding_empty = parent.function(mt, "mt6797_a72_binding_empty")
    parent.tokens(profile_prepare, [
        "evidence->target_cpu[0] = 8", "evidence->target_cpu[1] = 9",
        "return -EAGAIN;",
    ], "MT6797 prepare")
    parent.tokens(profile_classify, [
        "evidence->target_cpu[target] != 8 + target",
        "evidence->expected_target_mpidr[target] != 0x200 + target",
        "evidence->expected_target_midr[target] != MIDR_CORTEX_A72",
    ], "MT6797 target classifier")
    parent.tokens(expected_only, [
        "evidence->target_cpu[0] != 8", "evidence->target_cpu[1] != 9",
        "!mt6797_a72_binding_empty(&evidence->binding)",
    ], "expected-only evidence")
    parent.tokens(binding_empty, [
        "!binding->valid", "!binding->origin", "resolved_config_identity",
        "running_config_identity", "built_image_identity",
        "running_image_identity", "expected_cmdline_identity",
        "running_cmdline_identity",
    ], "empty binding")
    parent.tokens(profile_validate, [
        "for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)",
        "plan->target[target].classified_local_caps",
        "plan->target[target].local_caps",
        "ARRAY_SIZE(mt6797_a72_present_caps)",
        "ARRAY_SIZE(mt6797_a72_absent_caps)",
        "ARRAY_SIZE(mt6797_a72_unresolved_caps)",
        "plan->local_caps_planned", "return -EAGAIN;",
    ], "per-target profile validator")
    require("return 0;" not in profile_validate and
            profile_validate.count("return -EAGAIN;") == 1 and
            profile_validate.rstrip().endswith("return -EAGAIN;\n}"),
            "partial profile validator gained a success path")
    require(parent.array_symbols(mt, "mt6797_a72_present_caps") ==
            tuple(parent.PRESENT.values()), "present census changed")
    require(parent.array_symbols(mt, "mt6797_a72_absent_caps") ==
            tuple(parent.ABSENT.values()), "absent census changed")
    require(parent.array_symbols(mt, "mt6797_a72_unresolved_caps") ==
            tuple(parent.UNRESOLVED.values()), "unresolved census changed")
    parent.tokens(mt, [
        "0xf073150a6bbfb6af", "0x1d4262f4b7545341",
        "0x18181ee40284d60a", "0x59aa1068740d118d",
        "0x4dfe301404e0d972", "0x342311b51e9c9674",
        "0xd7ec3bc5198912fb", "0x2ec7f6167f72fb3e",
        "ARM64_LATE_CPU_BLOCK_EFFECT_PLAN",
        "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
        '"mt6797-a53-a72-a41-v4"',
    ], "MT6797 identities and blockers")


def run_git(root: Path, args: list[str], *, binary: bool = False):
    result = subprocess.run(
        ["git", *args], cwd=root, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=not binary,
    )
    return result.stdout


def validate_source_application(repo: Path, source_root: Path) -> None:
    repo = repo.resolve()
    source_root = source_root.resolve()
    parent = load_parent(repo)
    require = parent.require
    require((source_root / ".git").exists(), "source root is not a Git repository")
    require(run_git(source_root, ["rev-parse", f"{PARENT}^{{tree}}"]).strip() ==
            PARENT_TREE, "source parent tree changed")
    require(run_git(source_root, ["rev-parse", f"{SOURCE}^{{tree}}"]).strip() ==
            SOURCE_TREE, "source result tree changed")
    require(run_git(source_root, ["rev-parse", f"{SOURCE}^"]).strip() == PARENT,
            "source commit parent changed")
    require(run_git(source_root, ["rev-parse", "HEAD"]).strip() == SOURCE,
            "source checkout is not at the pinned commit")
    require(not run_git(source_root, ["status", "--porcelain"]).strip(),
            "source checkout is not clean")
    diff = run_git(source_root, ["diff", f"{PARENT}..{SOURCE}"], binary=True)
    require(hashlib.sha256(diff).hexdigest() == SOURCE_DIFF_SHA256,
            "source diff identity changed")
    changed = run_git(source_root, ["diff", "--name-only", f"{PARENT}..{SOURCE}"])
    require(tuple(changed.splitlines()) == CHANGED_PATHS,
            "source changed-path set changed")

    checkpatch = subprocess.run(
        [
            str(source_root / "scripts/checkpatch.pl"), "--strict", "--no-tree",
            "--show-types", "--ignore=MISSING_SIGN_OFF", str((repo / PATCH).resolve()),
        ],
        cwd=source_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    require(checkpatch.returncode == 0 and
            "0 errors, 0 warnings, 0 checks" in checkpatch.stdout,
            "strict format-patch check failed")
    checkincludes = subprocess.run(
        [str(source_root / "scripts/checkincludes.pl"), *CHANGED_PATHS],
        cwd=source_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    require(checkincludes.returncode == 0 and
            "No duplicate includes found." in checkincludes.stdout,
            "duplicate-include check failed")
    for script in (repo / EXPERIMENT / "scripts").glob("*.py"):
        compile(script.read_text(), str(script), "exec")

    sections = parent.patch_sections((repo / PATCH).read_text())
    with tempfile.TemporaryDirectory(prefix="gemini-a41-per-target-") as temporary:
        scratch = Path(temporary)
        for path, section in sections.items():
            index = re.search(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)", section, re.M)
            require(index is not None, f"{path}: patch index is missing")
            parent_blob = run_git(source_root, ["show", f"{PARENT}:{path}"], binary=True)
            actual_parent = run_git(source_root, ["rev-parse", f"{PARENT}:{path}"]).strip()
            require(actual_parent.startswith(index.group(1)),
                    f"{path}: patch preimage changed")
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(parent_blob)
        command = [
            "git", "apply", "--whitespace=error-all", str((repo / PATCH).resolve())
        ]
        result = subprocess.run(command, cwd=scratch, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        require(result.returncode == 0,
                f"patch application failed: {result.stderr.strip()}")
        for path in sections:
            expected = run_git(source_root, ["show", f"{SOURCE}:{path}"], binary=True)
            require((scratch / path).read_bytes() == expected,
                    f"{path}: applied postimage differs from source commit")
        validate_source_files(scratch)


def default_repo() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo())
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--skip-frozen-evidence", action="store_true")
    args = parser.parse_args(argv)
    print("validation=a41-per-target-plan-offline")
    try:
        checks = validate_repository(
            args.repo_root,
            skip_frozen_evidence=args.skip_frozen_evidence,
        )
        validate_source_application(args.repo_root, args.source_root)
        checks.extend(SOURCE_CHECKS)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError,
            subprocess.CalledProcessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    for check in checks:
        print(f"PASS {check}")
    print(f"patch_sha256={PATCH_SHA256}")
    print(f"series_sha256={SERIES_SHA256}")
    print(f"patchset_sha256={PATCHSET_SHA256}")
    print(f"source_state_sha256={SOURCE_STATE_SHA256}")
    print(f"config_sha256={CONFIG_SHA256}")
    print("target0=CPU8:34-classified:4-present:6-unresolved")
    print("target1=CPU9:34-classified:4-present:6-unresolved")
    print("implementation_state=PARTIAL_PER_TARGET_PLAN_BOUNDARY")
    print("a41_complete=no")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print("build_authorized=no")
    print("device_action_authorized=no")
    print(f"RESULT PASS {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
