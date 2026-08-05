#!/usr/bin/env python3
"""Validate the exact blocked A41 expected-A72 static census."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

sys.dont_write_bytecode = True


EXPERIMENT = Path("experiments/2026-08-05-a72-a41-static-census")
PATCH = Path("patches/v7.1.3/0152-arm64-classify-static-MT6797-late-CPU-capabilities.patch")
PATCH_0092 = Path("patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch")
SERIES = Path("patches/series-a72-reject-gate-a41-static-census")
PARENT_SERIES = Path("patches/series-a72-reject-gate-a41-immutable-plan")
CANONICAL_SERIES = Path("patches/series")
FRAGMENT = Path("configs/gemini-a72-a41-static-census.fragment")
MANIFEST = Path("kernel/manifest.json")
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-static-census"
)

PATCH_SHA256 = "61ff3351799c9313d89b4ab572f6511371e04f6c6f3625b3d730ad7d77b9abbf"
SERIES_SHA256 = "12b46a348af31ebbe506480716e2bb517044da095e5902b8bfb59622188e859f"
PATCHSET_SHA256 = "c06e83ea4491a28c18a5db9563497413984e578c9bdbb2ce6f3da35e2e115352"
SOURCE_STATE_SHA256 = "f073150a6bbfb6af1d4262f4b754534118181ee40284d60a59aa1068740d118d"
PARENT_SOURCE_STATE_SHA256 = "bf192fa874aea9838cece3f58eec0bba2a18dc43bfe094ad9f6d635b9809ca32"
CONFIG_SHA256 = "6fa24adaa512d804172b170b205f574b4d461b4263bc0d374c6499f78b7f3d7c"
PARENT = "9257e46ea3fd8da4766cfd0dba4b15af56cf0d6a"
PARENT_TREE = "30c9cf493dda6501620e0713e657184566e5f339"
SOURCE = "63e5d894150a5d5d1d897a639199a096815bb385"
SOURCE_TREE = "c3db9d87cf885b6e2313041e1e3b8b28ea8e98c1"
SOURCE_DIFF_SHA256 = "ab27efd5d334ac4fd18a41371db6efaf7d07bf5ead2df9991d612ba5ddcaf4c0"
CENSUS_SHA256 = "f7c323bfb0f94024b493bec1e40ffe44aa6963a27e1101ac53975971d145593b"
IMPLEMENTATION_SHA256 = "2c76610519029b680501f714cbfb3fe2b5cb9e4538b1658c7147d09035603cd8"
PROFILE_COUNT = 58
SERIES_ENTRY_COUNT = 94

EXPECTED_EXPERIMENT_FILES = {
    "DESIGN.md",
    "README.md",
    "results/implementation.tsv",
    "results/kernel-static-review-20260805.txt",
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
    "results/static-census.tsv",
    "scripts/test_mutations.py",
    "scripts/validate.py",
}
FROZEN_TRANSCRIPTS = {
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
}

CHANGED_PATHS = (
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/cpu_errata.c",
    "arch/arm64/kernel/cpufeature.c",
    "arch/arm64/kernel/mt6797_psci.c",
)

PRESENT = {
    9: "ARM64_HAS_AMU_EXTN",
    66: "ARM64_HW_DBM",
    94: "ARM64_WORKAROUND_1742098",
    121: "ARM64_WORKAROUND_SPECULATIVE_AT",
}
UNRESOLVED = {
    33: "ARM64_HAS_GICV5_LEGACY",
    36: "ARM64_HAS_ICH_HCR_EL2_TDIR",
    69: "ARM64_MISMATCHED_CACHE_TYPE",
    79: "ARM64_SPECTRE_V2",
    81: "ARM64_SPECTRE_V4",
    82: "ARM64_SPECTRE_BHB",
}
ABSENT = {
    47: "ARM64_HAS_BBML2_NOABORT",
    85: "ARM64_UNMAP_KERNEL_AT_EL0",
    87: "ARM64_WORKAROUND_843419",
    88: "ARM64_WORKAROUND_845719",
    89: "ARM64_WORKAROUND_858921",
    90: "ARM64_WORKAROUND_1418040",
    91: "ARM64_WORKAROUND_1463225",
    92: "ARM64_WORKAROUND_1508412",
    98: "ARM64_WORKAROUND_2077057",
    99: "ARM64_WORKAROUND_2457168",
    100: "ARM64_WORKAROUND_2645198",
    101: "ARM64_WORKAROUND_2658417",
    102: "ARM64_WORKAROUND_4193714",
    104: "ARM64_WORKAROUND_AMPERE_AC03_CPU_38",
    105: "ARM64_WORKAROUND_AMPERE_AC04_CPU_23",
    107: "ARM64_WORKAROUND_TSB_FLUSH_FAILURE",
    109: "ARM64_WORKAROUND_CAVIUM_23154",
    110: "ARM64_WORKAROUND_CAVIUM_27456",
    111: "ARM64_WORKAROUND_CAVIUM_30115",
    112: "ARM64_WORKAROUND_CAVIUM_TX2_219_PRFM",
    113: "ARM64_WORKAROUND_CAVIUM_TX2_219_TVM",
    114: "ARM64_WORKAROUND_CLEAN_CACHE",
    115: "ARM64_WORKAROUND_DEVICE_LOAD_ACQUIRE",
    116: "ARM64_WORKAROUND_NVIDIA_CARMEL_CNP",
    117: "ARM64_WORKAROUND_PMUV3_IMPDEF_TRAPS",
    118: "ARM64_WORKAROUND_QCOM_FALKOR_E1003",
    119: "ARM64_WORKAROUND_QCOM_ORYON_CNTVOFF",
    120: "ARM64_WORKAROUND_REPEAT_TLBI",
    122: "ARM64_WORKAROUND_SPECULATIVE_SSBS",
    123: "ARM64_WORKAROUND_SPECULATIVE_UNPRIV_LOAD",
}
ALL = {**PRESENT, **UNRESOLVED, **ABSENT}
REQUIRED = ("ARM64_WORKAROUND_1742098", "ARM64_WORKAROUND_SPECULATIVE_AT")


class ValidationError(RuntimeError):
    """A pinned invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def series_entries(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def is_subsequence(candidate: Sequence[str], canonical: Sequence[str]) -> bool:
    cursor = 0
    for entry in canonical:
        if cursor < len(candidate) and candidate[cursor] == entry:
            cursor += 1
    return cursor == len(candidate)


def patchset_hash(repo: Path, relative: Path) -> str:
    path = repo / relative
    lines = [f"{file_sha256(path)}  {relative}"]
    for entry in series_entries(path.read_text()):
        patch = path.parent / entry
        require(patch.is_file(), f"missing series patch {entry}")
        lines.append(f"{file_sha256(patch)}  {entry}")
    return sha256(("\n".join(lines) + "\n").encode())


def source_state_hash(repo: Path, relative: Path) -> str:
    kernel = json.loads((repo / MANIFEST).read_text())["kernel"]
    material = f"{kernel['version']}\n{kernel['sha256']}\n{patchset_hash(repo, relative)}\n"
    return sha256(material.encode())


def config_hash(repo: Path, profile: dict) -> str:
    lines = [f"profile={PROFILE}", f"base={profile['base']}"]
    for name in profile["fragments"]:
        lines.append(f"{file_sha256(repo / name)}  {name}")
    return sha256(("\n".join(lines) + "\n").encode())


def patch_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^diff --git a/(\S+) b/(\S+)$", text, re.MULTILINE))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        require(match.group(1) == match.group(2), "patch rename is not permitted")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1)] = text[match.start() : end]
    return result


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def patch_postimage(section: str) -> str:
    """Return context plus additions from a format-patch file section."""
    return "\n".join(
        line[1:]
        for line in section.splitlines()
        if line.startswith((" ", "+")) and not line.startswith("+++")
    )


def function(text: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", text, re.S)
    require(match is not None, f"missing function {name}")
    brace = text.find("{", match.start())
    depth = 0
    for cursor in range(brace, len(text)):
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : cursor + 1]
    raise ValidationError(f"unterminated function {name}")


def array_symbols(text: str, name: str) -> tuple[str, ...]:
    match = re.search(rf"\b{re.escape(name)}\[\].*?=\s*\{{(.*?)\n\}};", text, re.S)
    require(match is not None, f"missing array {name}")
    return tuple(re.findall(r"\bARM64_[A-Z0-9_]+\b", match.group(1)))


def tokens(text: str, expected: Iterable[str], scope: str) -> None:
    for token in expected:
        require(token in text, f"{scope}: missing {token!r}")


def safe_relative_path(value: str, scope: str) -> Path:
    path = Path(value)
    require(value and not path.is_absolute(), f"{scope}: unsafe path {value!r}")
    require(not any(part in ("", ".", "..") for part in path.parts),
            f"{scope}: unsafe path {value!r}")
    require(not any(character.isspace() for character in value),
            f"{scope}: whitespace in path {value!r}")
    return path


def validate_all_profile_series(repo: Path, manifest: dict,
                                canonical: Sequence[str]) -> None:
    fallback = manifest.get("patch_series")
    require(manifest["config"].get("default_profile") == "full",
            "default profile is no longer full")
    require(manifest["config"]["profiles"].get("full") == {
        "base": "defconfig",
        "fragments": ["configs/gemini.fragment"],
    }, "full profile changed")
    require(len(canonical) == len(set(canonical)),
            "canonical series contains duplicate entries")
    for entry in canonical:
        relative = safe_relative_path(entry, "canonical series")
        target = repo / CANONICAL_SERIES.parent / relative
        require(target.is_file() and not target.is_symlink(),
                f"canonical series patch is missing or unsafe: {entry}")
    for name, profile in manifest["config"]["profiles"].items():
        series_name = profile.get("patch_series", fallback)
        require(isinstance(series_name, str), f"profile {name}: series is missing")
        relative = safe_relative_path(series_name, f"profile {name}")
        require(relative.parts[0] == "patches", f"profile {name}: series left patches/")
        series_path = repo / relative
        require(series_path.is_file() and not series_path.is_symlink(),
                f"profile {name}: series is missing or unsafe")
        entries = series_entries(series_path.read_text())
        require(entries and len(entries) == len(set(entries)),
                f"profile {name}: series is empty or contains duplicates")
        require(is_subsequence(entries, canonical),
                f"profile {name}: series is not a canonical-order subsequence")
        for entry in entries:
            patch = series_path.parent / safe_relative_path(entry, f"profile {name}")
            require(patch.is_file() and not patch.is_symlink(),
                    f"profile {name}: selected patch is missing or unsafe: {entry}")


def validate_experiment_inventory(repo: Path, *, skip_frozen_evidence: bool) -> None:
    root = repo / EXPERIMENT
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    required = EXPECTED_EXPERIMENT_FILES - FROZEN_TRANSCRIPTS
    if skip_frozen_evidence:
        require(required <= actual <= EXPECTED_EXPERIMENT_FILES,
                "experiment file inventory changed")
    else:
        require(actual == EXPECTED_EXPERIMENT_FILES,
                "frozen experiment file inventory changed")
    for relative in actual:
        path = root / relative
        require(path.is_file() and not path.is_symlink(),
                f"experiment path is not a regular file: {relative}")
        text = path.read_text()
        require(("/" + "Users/") not in text,
                f"experiment file exposes a personal host path: {relative}")
        require(("arti" + "facts/") not in text,
                f"experiment file refers to private artifacts: {relative}")
        forbidden = tuple(
            word
            for word in (
                "cu" + "rl", "wg" + "et", "s" + "sh", "sc" + "p",
                "rsy" + "nc", "nc" + "at", "so" + "cat",
                "build" + "-kernel", "dev" + "-vm",
            )
        )
        if relative.startswith("scripts/"):
            require(not re.search(r"(?<![A-Za-z0-9_])(?:" +
                                  "|".join(map(re.escape, forbidden)) +
                                  r")(?![A-Za-z0-9_])", text),
                    f"experiment script contains an external action: {relative}")


def read_census(repo: Path) -> dict[int, tuple[str, str]]:
    path = repo / EXPERIMENT / "results/static-census.tsv"
    require(file_sha256(path) == CENSUS_SHA256, "static census identity changed")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(reader.fieldnames == ["slot", "symbol", "state", "basis"],
                "static census header changed")
        rows = list(reader)
    require(all(row["basis"] for row in rows), "static census contains an empty basis")
    result = {int(row["slot"]): (row["symbol"], row["state"]) for row in rows}
    require(len(result) == len(rows) == 40, "static census must contain 40 unique rows")
    return result


def validate_tables(repo: Path) -> None:
    expected = {
        **{slot: (symbol, "PRESENT") for slot, symbol in PRESENT.items()},
        **{slot: (symbol, "ABSENT") for slot, symbol in ABSENT.items()},
        **{slot: (symbol, "UNRESOLVED") for slot, symbol in UNRESOLVED.items()},
    }
    require(read_census(repo) == expected, "static census mapping changed")
    implementation = repo / EXPERIMENT / "results/implementation.tsv"
    require(file_sha256(implementation) == IMPLEMENTATION_SHA256,
            "implementation marker identity changed")
    with implementation.open(
        newline="", encoding="utf-8"
    ) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(reader.fieldnames == ["key", "value", "evidence"],
                "implementation marker header changed")
        rows = list(reader)
    require(len(rows) == len({row["key"] for row in rows}),
            "implementation marker keys are duplicated")
    require(all(row["evidence"] for row in rows),
            "implementation marker contains an empty evidence field")
    markers = {row["key"]: row["value"] for row in rows}
    wanted = {
        "implementation_state": "PARTIAL_STATIC_CAPABILITY_CENSUS",
        "a41_complete": "no",
        "plan_abi": "3",
        "source_parent_identity": PARENT_SOURCE_STATE_SHA256,
        "config_input_identity": CONFIG_SHA256,
        "compiled_local_cap_count": "40",
        "classified_local_cap_count": "34",
        "static_present_count": "4",
        "static_absent_count": "30",
        "evidence_dependent_count": "6",
        "required_local_caps": "94,121",
        "provisional_effects": "compat_aes_clear,speculative_at_finalization",
        "target_impl_override": "must_be_inactive",
        "kpti_state": "unforced_profile_static",
        "observed_target_midr": "absent",
        "resolved_running_config": "absent",
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
        "boot_candidate": "false",
        "build_authorized": "no",
        "device_action_authorized": "no",
    }
    require(markers == wanted,
            "implementation claim boundary changed")


def validate_repository(repo: Path, *, pin_hashes: bool = True,
                        skip_frozen_evidence: bool = False) -> list[str]:
    repo = repo.resolve()
    validate_experiment_inventory(repo, skip_frozen_evidence=skip_frozen_evidence)
    patch_path = repo / PATCH
    patch = patch_path.read_text()
    manifest = json.loads((repo / MANIFEST).read_text())
    profiles = manifest["config"]["profiles"]
    require(len(profiles) == PROFILE_COUNT, "manifest profile count changed")
    require(PROFILE in profiles, "static-census profile is missing")
    profile = profiles[PROFILE]
    require(profile.get("base") == "defconfig", "profile base changed")
    require(profile.get("patch_series") == str(SERIES), "profile series changed")
    require(profile.get("fragments", [])[-1] == str(FRAGMENT), "profile fragment changed")
    for name, candidate in profiles.items():
        if name != PROFILE:
            require(candidate.get("patch_series") != str(SERIES),
                    f"static series leaked into profile {name}")
            require(str(FRAGMENT) not in candidate.get("fragments", []),
                    f"static fragment leaked into profile {name}")
    fragment_assignments = [
        line.strip() for line in (repo / FRAGMENT).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(fragment_assignments == [
        "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
        'CONFIG_LOCALVERSION="-gemini-a41-static-blocked"',
    ], "static fragment gained an unreviewed setting")
    require("maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(),
            "inherited maxcpus=8 changed")
    require(config_hash(repo, profile) == CONFIG_SHA256, "configuration identity changed")

    selected_text = (repo / SERIES).read_text()
    selected = series_entries(selected_text)
    canonical = series_entries((repo / CANONICAL_SERIES).read_text())
    validate_all_profile_series(repo, manifest, canonical)
    require(len(selected) == SERIES_ENTRY_COUNT, "selected series entry count changed")
    require(len(selected) == len(set(selected)), "selected series contains duplicates")
    require(is_subsequence(selected, canonical), "selected series is not canonical-order")
    require(selected[-6:] == [
        "v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch",
        "v7.1.3/0148-arm64-add-a-fail-closed-late-CPU-profile-lifecycle.patch",
        "v7.1.3/0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch",
        "v7.1.3/0150-arm64-add-read-only-late-CPU-capability-planner.patch",
        "v7.1.3/0151-arm64-split-late-CPU-evidence-from-commit-receipt.patch",
        str(PATCH.relative_to("patches")),
    ], "selected series terminal order changed")
    for forbidden in ("0093-", "a72-active", "cpu8-one-way"):
        require(not any(forbidden in entry for entry in selected),
                f"selected series contains active path {forbidden}")
    if pin_hashes:
        require(file_sha256(repo / SERIES) == SERIES_SHA256, "selected series hash changed")
        require(patchset_hash(repo, SERIES) == PATCHSET_SHA256, "patchset identity changed")
        require(source_state_hash(repo, SERIES) == SOURCE_STATE_SHA256,
                "source-state identity changed")
        require(source_state_hash(repo, PARENT_SERIES) == PARENT_SOURCE_STATE_SHA256,
                "parent source-state identity changed")

    match = re.match(r"From ([0-9a-f]{40}) ", patch)
    require(match is not None and match.group(1) == SOURCE, "patch source commit changed")
    tokens(patch.split("\n---\n", 1)[0], [
        "From: Gemini Mainline Project <noreply@invalid>",
        "Subject: [PATCH] arm64: classify static MT6797 late-CPU capabilities",
        "This experiment-only change has no certifying sign-off and is not\n"
        "submission-ready.",
    ], "patch metadata")
    require("Signed-off-by:" not in patch, "synthetic patch gained a sign-off")
    sections = patch_sections(patch)
    require(set(sections) == set(CHANGED_PATHS), "patch changed-path set changed")
    require("arch/arm64/kernel/late_cpu_profile.c" not in sections,
            "static patch changes the profile publisher")
    if pin_hashes:
        require(file_sha256(patch_path) == PATCH_SHA256, "patch hash changed")
    additions = added_lines(patch)
    for forbidden in (
        "ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
        "ARM64_LATE_CPU_PROFILE_COMMITTED",
        "ARM64_LATE_CPU_PROFILE_READY",
        "late_plan =",
        "system_cpucaps",
        "apply_alternatives",
        "cpu_psci_ops.cpu_boot(",
        "return 0;",
    ):
        require(forbidden not in additions, f"static patch adds forbidden path {forbidden}")
    require(not re.search(r"identity\s*\[[^]]+\]\s*=", additions),
            "static patch writes plan identity")
    header_postimage = patch_postimage(sections[CHANGED_PATHS[0]])
    errata_postimage = patch_postimage(sections[CHANGED_PATHS[1]])
    feature_postimage = patch_postimage(sections[CHANGED_PATHS[2]])
    platform_postimage = patch_postimage(sections[CHANGED_PATHS[3]])
    override = function(errata_postimage, "arm64_late_cpu_target_impl_override_active")
    require("target_impl_cpu_num || target_impl_cpus" in override,
            "patch target implementation override guard weakened")
    erratum_state = function(errata_postimage, "arm64_late_cpu_erratum_state")
    require("arm64_late_cpu_target_impl_override_active()" in erratum_state,
            "patch erratum classifier lost target override guard")
    static_state = function(feature_postimage, "arm64_late_cpu_static_feature_state")
    require(re.search(r"supports_bbml2_noabort_list\s*,\s*model", static_state) is not None,
            "patch BBML2 source-owned list guard changed")
    require("!__kpti_forced" in static_state and
            "late_cpu_model_range_list_state(kpti_safe_list, model)" in
            re.sub(r"\s+", " ", static_state),
            "patch KPTI source-owned guard changed")
    kpti = function(platform_postimage, "mt6797_a72_kpti_policy_static")
    tokens(kpti, [
        "#ifdef CONFIG_CMDLINE_FORCE", "CONFIG_UNMAP_KERNEL_AT_EL0",
        "!IS_ENABLED(CONFIG_RANDOMIZE_BASE)",
        'strstr(CONFIG_CMDLINE, "nokaslr")',
        '!strstr(CONFIG_CMDLINE, "kpti=")',
        "!strcmp(saved_command_line, CONFIG_CMDLINE)",
    ], "patch KPTI policy")
    evidence = function(platform_postimage, "mt6797_a72_evidence_is_expected_only")
    normalized_evidence = re.sub(r"\s+", " ", evidence)
    tokens(normalized_evidence, [
        "memcmp(evidence->source_parent_identity, mt6797_a72_source_parent_identity,",
        "memcmp(evidence->config_input_identity, mt6797_a72_config_input_identity,",
        "(evidence->blocker_mask & MT6797_A72_PROFILE_BLOCKERS) != MT6797_A72_PROFILE_BLOCKERS",
        "~(MT6797_A72_PROFILE_BLOCKERS | ARM64_LATE_CPU_BLOCK_TOPOLOGY)",
        "!mt6797_a72_target_method_empty(&evidence->target_method[i])",
        "evidence->evidence_identity[i]",
    ], "patch expected-only evidence")
    tokens(platform_postimage, [
        "0xbf192fa874aea983", "0x9f6d635b9809ca32",
        "0x6fa24adaa512d804", "0x74c6499f78b7f3d7c",
    ], "patch identity pins")
    partial_validator = function(platform_postimage, "mt6797_a72_validate_cap_plan")
    require("return -EAGAIN;" in partial_validator,
            "patch partial validator can succeed")
    require("plan->identity[i]" in partial_validator,
            "patch partial validator lost empty plan-identity check")
    tokens(header_postimage, [
        "arm64_late_cpu_erratum_state",
        "arm64_late_cpu_static_feature_state",
        "arm64_late_cpu_target_impl_override_active",
    ], "patch classifier declarations")

    veto_additions = added_lines((repo / PATCH_0092).read_text())
    boot = function(veto_additions, "mt6797_psci_cpu_boot")
    disable = function(veto_additions, "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot,
            "inherited CPU boot veto changed")
    require("return false;" in disable, "inherited CPU disable veto changed")
    validate_tables(repo)
    if not skip_frozen_evidence:
        review = (repo / EXPERIMENT / "results/kernel-static-review-20260805.txt").read_text()
        tokens(review, [
            f"source_commit={SOURCE}",
            f"diff_sha256={SOURCE_DIFF_SHA256}",
            "git_diff_check=PASS",
            "checkincludes=PASS no_duplicate_includes",
            "checkpatch_diff=PASS errors=0 warnings=0 checks=0 lines=748",
            "build_performed=no",
            "device_accessed=no",
            "network_accessed=no",
        ], "frozen static review")
        offline = (repo / EXPERIMENT / "results/offline-validation-20260805.txt").read_text()
        tokens(offline, [
            "PASS manifest-config", "PASS series-identities",
            "PASS patch-application", "PASS veto-preservation",
            f"patch_sha256={PATCH_SHA256}",
            f"source_state_sha256={SOURCE_STATE_SHA256}",
            "implementation_state=PARTIAL_STATIC_CAPABILITY_CENSUS",
            "a41_complete=no", "build_authorized=no",
            "device_action_authorized=no", "build_performed=no",
            "device_accessed=no", "network_accessed=no", "RESULT PASS 7/7",
        ], "frozen offline validation")
        mutations = (repo / EXPERIMENT / "results/mutation-validation-20260805.txt").read_text()
        tokens(mutations, [
            "PASS patch-source-commit", "PASS synthetic-signoff",
            "PASS target-override-guard", "PASS kpti-force-guard",
            "PASS inherited-boot-veto", "PASS inherited-disable-veto",
            "PASS external-action", "PASS unexpected-residue",
            "build_performed=no", "device_accessed=no", "network_accessed=no",
        ], "frozen mutation validation")
        result = re.search(r"^RESULT PASS (\d+)/(\d+)$", mutations, re.MULTILINE)
        require(result is not None and result.group(1) == result.group(2) and
                int(result.group(1)) >= 20,
                "frozen mutation suite is incomplete")
    return ["manifest-config", "series-identities", "patch-identity", "claim-tables"]


def run_git(source: Path, args: Sequence[str], *, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(source), *args], check=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=not binary,
    )
    error = result.stderr.decode() if binary else result.stderr
    require(result.returncode == 0, f"git {args[0]} failed: {error.strip()}")
    return result.stdout


def validate_source_files(tree: Path) -> None:
    header = (tree / CHANGED_PATHS[0]).read_text()
    errata = (tree / CHANGED_PATHS[1]).read_text()
    features = (tree / CHANGED_PATHS[2]).read_text()
    platform = (tree / CHANGED_PATHS[3]).read_text()
    lifecycle = (tree / "arch/arm64/kernel/late_cpu_profile.c").read_text()

    expected_compiled = tuple(ALL[slot] for slot in sorted(ALL))
    require(array_symbols(platform, "mt6797_a72_compiled_caps") == expected_compiled,
            "compiled capability set/order changed")
    require(array_symbols(platform, "mt6797_a72_present_caps") ==
            tuple(PRESENT[slot] for slot in sorted(PRESENT)), "PRESENT set changed")
    require(array_symbols(platform, "mt6797_a72_absent_caps") ==
            tuple(ABSENT[slot] for slot in sorted(ABSENT)), "ABSENT set changed")
    require(array_symbols(platform, "mt6797_a72_unresolved_caps") ==
            tuple(UNRESOLVED[slot] for slot in sorted(UNRESOLVED)), "UNRESOLVED set changed")
    require(array_symbols(platform, "mt6797_a72_required_caps") == REQUIRED,
            "required capability set changed")

    override = function(errata, "arm64_late_cpu_target_impl_override_active")
    require("target_impl_cpu_num || target_impl_cpus" in override,
            "target implementation override guard weakened")
    erratum_state = function(errata, "arm64_late_cpu_erratum_state")
    require("arm64_late_cpu_target_impl_override_active()" in erratum_state,
            "erratum classifier lost target override guard")
    tokens(errata, [
        "for (i = 0; i < ARM64_NCAPS; i++, range++)",
        "return partial ? ARM64_LATE_CPU_CAP_UNRESOLVED",
        "cap->matches == is_kryo_midr",
        "cap->matches == needs_tx2_tvm_workaround",
        "cap->matches == has_impdef_pmuv3",
        "#ifdef CONFIG_ARM64_ERRATUM_4193714\nstatic enum arm64_late_cpu_cap_state __init\nlate_cpu_midr_range_state",
        "#ifdef CONFIG_ARM64_ERRATUM_4193714\n\tif (cap->matches == has_sme_dvmsync_erratum)",
    ], "erratum source guards")

    static_state = function(features, "arm64_late_cpu_static_feature_state")
    tokens(static_state, [
        "cap != match || cap->match_list",
        "arm64_late_cpu_target_impl_override_active()",
        "!__kpti_forced",
        "ARM64_LATE_CPU_CAP_PRESENT",
    ], "static feature guards")
    normalized_static_state = re.sub(r"\s+", " ", static_state)
    tokens(normalized_static_state, [
        "supports_bbml2_noabort_list, model",
        "late_cpu_model_range_list_state(kpti_safe_list, model)",
    ], "static feature source-owned lists")
    tokens(features, [
        "static const struct midr_range kpti_safe_list[]",
        "MIDR_ALL_VERSIONS(MIDR_CORTEX_A72)",
        "static const struct midr_range supports_bbml2_noabort_list[]",
    ], "source-owned allowlists")

    kpti = function(platform, "mt6797_a72_kpti_policy_static")
    tokens(kpti, [
        "#ifdef CONFIG_CMDLINE_FORCE",
        "CONFIG_UNMAP_KERNEL_AT_EL0",
        "!IS_ENABLED(CONFIG_RANDOMIZE_BASE)",
        'strstr(CONFIG_CMDLINE, "nokaslr")',
        '!strstr(CONFIG_CMDLINE, "kpti=")',
        "!strcmp(saved_command_line, CONFIG_CMDLINE)",
    ], "KPTI policy")
    config_gate = function(platform, "mt6797_a72_profile_config_gates_match")
    require("mt6797_a72_kpti_policy_static()" in config_gate,
            "config gate does not reuse exact KPTI policy")
    classifier = function(platform, "mt6797_a72_classify_local_cap")
    tokens(classifier, [
        "mt6797_a72_cap_descriptor_shape(cap, match)",
        "ARM64_HAS_GICV5_LEGACY",
        "ARM64_HAS_ICH_HCR_EL2_TDIR",
        "ARM64_MISMATCHED_CACHE_TYPE",
        "ARM64_SPECTRE_V2",
        "ARM64_SPECTRE_V4",
        "ARM64_SPECTRE_BHB",
        "return ARM64_LATE_CPU_CAP_UNRESOLVED;",
    ], "provisional classifier")

    validator = function(platform, "mt6797_a72_validate_cap_plan")
    tokens(validator, [
        "plan->local_caps_planned",
        "mt6797_a72_evidence_is_expected_only",
        "mt6797_a72_compiled_caps",
        "mt6797_a72_present_caps",
        "mt6797_a72_required_caps",
        "mt6797_a72_effects_are_provisional",
        "plan->identity[i]",
        "return -EINVAL;",
        "return -EAGAIN;",
    ], "partial validator")
    effects = function(platform, "mt6797_a72_effects_are_provisional")
    tokens(effects, [
        "!effects->ctr_mismatch.required",
        "!effects->spectre_v2.required",
        "!effects->spectre_v4.required",
        "!effects->bhb.required",
        "effects->compat_aes_clear == 1",
        "effects->speculative_at_finalization == 1",
    ], "provisional effects")
    evidence = function(platform, "mt6797_a72_evidence_is_expected_only")
    normalized_evidence = re.sub(r"\s+", " ", evidence)
    tokens(normalized_evidence, [
        "memcmp(evidence->source_parent_identity, mt6797_a72_source_parent_identity,",
        "memcmp(evidence->config_input_identity, mt6797_a72_config_input_identity,",
        "(evidence->blocker_mask & MT6797_A72_PROFILE_BLOCKERS) != MT6797_A72_PROFILE_BLOCKERS",
        "~(MT6797_A72_PROFILE_BLOCKERS | ARM64_LATE_CPU_BLOCK_TOPOLOGY)",
        "evidence->observed_target_mpidr[i]",
        "evidence->observed_target_midr[i]",
        "evidence->target_cap[i].valid",
        "!mt6797_a72_target_method_empty(&evidence->target_method[i])",
        "evidence->evidence_identity[i]",
        "!evidence->system_cap.valid",
    ], "expected-only evidence")
    tokens(platform, [
        "0xbf192fa874aea983", "0x9f6d635b9809ca32",
        "0x6fa24adaa512d804", "0x74c6499f78b7f3d7c",
        "ARM64_LATE_CPU_BLOCK_CONFIGURATION",
        "ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY",
        "ARM64_LATE_CPU_BLOCK_ID_REGISTERS",
    ], "identity and blocker pins")
    prepare = function(platform, "mt6797_a72_profile_prepare")
    require("return -EAGAIN;" in prepare, "profile prepare can succeed")
    boot = function(platform, "mt6797_psci_cpu_boot")
    disable = function(platform, "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot,
            "boot veto changed")
    require("return false;" in disable, "disable veto changed")
    tokens(lifecycle, [
        "if (plan_ret || validate_ret)",
        "ARM64_LATE_CPU_BLOCK_CAP_INVENTORY",
        'panic("late CPU profile commit implementation is unavailable")',
    ], "core fail-closed path")
    tokens(header, [
        "ARM64_LATE_CPU_TARGET_CAP_MIDR_VALID",
        "u64 identity[ARM64_LATE_CPU_ID_WORDS]",
    ], "evidence schema")


def validate_source_application(repo: Path, source_root: Path, *,
                                pin_source: bool = True) -> None:
    source_root = source_root.resolve()
    require((source_root / ".git").exists(), "source root is not a Git repository")
    require(run_git(source_root, ["rev-parse", f"{PARENT}^{{tree}}"]).strip() == PARENT_TREE,
            "source parent tree changed")
    require(run_git(source_root, ["rev-parse", f"{SOURCE}^{{tree}}"]).strip() == SOURCE_TREE,
            "source result tree changed")
    require(run_git(source_root, ["rev-parse", f"{SOURCE}^"]).strip() == PARENT,
            "source commit parent changed")
    if pin_source:
        require(run_git(source_root, ["rev-parse", "HEAD"]).strip() == SOURCE,
                "source checkout is not at the pinned commit")
        require(not run_git(source_root, ["status", "--porcelain"]).strip(),
                "source checkout is not clean")
        diff = run_git(source_root, ["diff", f"{PARENT}..{SOURCE}"], binary=True)
        require(sha256(diff) == SOURCE_DIFF_SHA256, "source diff identity changed")
        changed = run_git(source_root, ["diff", "--name-only", f"{PARENT}..{SOURCE}"])
        require(tuple(changed.splitlines()) == CHANGED_PATHS, "source changed-path set changed")

    patch_text = (repo / PATCH).read_text()
    sections = patch_sections(patch_text)
    with tempfile.TemporaryDirectory(prefix="gemini-a41-static-census-") as temporary:
        scratch = Path(temporary)
        for path, section in sections.items():
            index = re.search(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)", section, re.M)
            require(index is not None, f"{path}: patch index is missing")
            parent_blob = run_git(source_root, ["show", f"{PARENT}:{path}"], binary=True)
            actual_parent = run_git(source_root, ["rev-parse", f"{PARENT}:{path}"]).strip()
            require(actual_parent.startswith(index.group(1)), f"{path}: patch preimage changed")
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(parent_blob)
        result = subprocess.run(
            ["git", "apply", "--check", "--whitespace=error-all", str((repo / PATCH).resolve())],
            cwd=scratch, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        require(result.returncode == 0, f"patch application check failed: {result.stderr.strip()}")
        result = subprocess.run(
            ["git", "apply", "--whitespace=error-all", str((repo / PATCH).resolve())],
            cwd=scratch, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        require(result.returncode == 0, f"patch application failed: {result.stderr.strip()}")
        lifecycle_path = scratch / "arch/arm64/kernel/late_cpu_profile.c"
        lifecycle_path.parent.mkdir(parents=True, exist_ok=True)
        lifecycle_path.write_bytes(run_git(source_root, ["show", f"{SOURCE}:arch/arm64/kernel/late_cpu_profile.c"], binary=True))
        if pin_source:
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
    try:
        checks = validate_repository(
            args.repo_root, skip_frozen_evidence=args.skip_frozen_evidence
        )
        validate_source_application(args.repo_root.resolve(), args.source_root)
        checks.extend(["patch-application", "static-census-guards", "veto-preservation"])
    except (OSError, ValueError, json.JSONDecodeError, ValidationError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    for check in checks:
        print(f"PASS {check}")
    print(f"patch_sha256={PATCH_SHA256}")
    print(f"series_sha256={SERIES_SHA256}")
    print(f"patchset_sha256={PATCHSET_SHA256}")
    print(f"source_state_sha256={SOURCE_STATE_SHA256}")
    print(f"config_sha256={CONFIG_SHA256}")
    print("implementation_state=PARTIAL_STATIC_CAPABILITY_CENSUS")
    print("a41_complete=no")
    print("build_authorized=no")
    print("device_action_authorized=no")
    print(f"RESULT PASS {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
