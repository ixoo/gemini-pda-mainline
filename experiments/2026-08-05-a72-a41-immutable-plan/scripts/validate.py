#!/usr/bin/env python3
"""Validate the exact source-only A41 immutable-plan boundary."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Iterable, Sequence


sys.dont_write_bytecode = True


EXPERIMENT_REL = Path("experiments/2026-08-05-a72-a41-immutable-plan")
PREVIOUS_EXPERIMENT_REL = Path(
    "experiments/2026-08-05-a72-a41-canonical-planner"
)
PREVIOUS_VALIDATOR = PREVIOUS_EXPERIMENT_REL / "scripts/validate.py"
PREVIOUS_VALIDATOR_SHA256 = (
    "adecebe14d3cfd49b6f6c608c2f0f9f3bf09a34244ee3828f5f2c06e6eaf1612"
)

PATCH_0092 = Path(
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
)
PATCH_0148 = Path(
    "patches/v7.1.3/0148-arm64-add-a-fail-closed-late-CPU-profile-lifecycle.patch"
)
PATCH_0149 = Path(
    "patches/v7.1.3/0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch"
)
PATCH_0150 = Path(
    "patches/v7.1.3/0150-arm64-add-read-only-late-CPU-capability-planner.patch"
)
PATCH_0151 = Path(
    "patches/v7.1.3/0151-arm64-split-late-CPU-evidence-from-commit-receipt.patch"
)
CANONICAL_SERIES = Path("patches/series")
SELECTED_SERIES = Path("patches/series-a72-reject-gate-a41-immutable-plan")
SELECTED_FRAGMENT = Path("configs/gemini-a72-a41-immutable-plan.fragment")
MANIFEST = Path("kernel/manifest.json")
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-immutable-plan"
)
EXPECTED_PROFILE_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    str(SELECTED_FRAGMENT),
)

EXPECTED_PATCH_SHA256 = (
    "f85f02103974b56fbb5f4c94c76fb1fd73184b72b170fe8a1240bdfb5b1f9e1f"
)
EXPECTED_SERIES_SHA256 = (
    "617d2d4c16822bd77ee74d4ce8f50dafd5a95ad1787a753b4bb6a0b887584b05"
)
EXPECTED_PATCHSET_SHA256 = (
    "bd2a98a26989b787e070b219eb310092aa78d4d55eada7f251ce405f9587b030"
)
EXPECTED_SOURCE_STATE_SHA256 = (
    "bf192fa874aea9838cece3f58eec0bba2a18dc43bfe094ad9f6d635b9809ca32"
)
EXPECTED_CONFIG_INPUT_SHA256 = (
    "91694455fdc124725704ea5f0cfdeecbd9e51829d20021f328714aca76b2edb8"
)
EXPECTED_SOURCE_PARENT_IDENTITY = (
    "a1573b40b7b8f5a8a87f7a2b9a431090bf714ed52c79cf1e93c78d28ce633c56"
)
EXPECTED_PATCH_PARENT = "4c0300398ae77c99faca19bb6333868e1f70b299"
EXPECTED_PATCH_PARENT_TREE = "f29f66ee14829fca4a452d4a390ad6f23556b64e"
EXPECTED_PATCH_COMMIT = "9257e46ea3fd8da4766cfd0dba4b15af56cf0d6a"
EXPECTED_PATCH_TREE = "30c9cf493dda6501620e0713e657184566e5f339"
EXPECTED_DIFF_SHA256 = (
    "efb8fc57f27609efbf9a6d87eec29c11da8b0d70b1683b6603e225241d8e052c"
)
EXPECTED_PROFILE_COUNT = 57
EXPECTED_MUTATION_COUNT = 55

EXPECTED_PATCH_INDEXES = {
    "arch/arm64/include/asm/late_cpu_profile.h": ("45f7fa222", "79446800e"),
    "arch/arm64/kernel/cpufeature.c": ("134d782be", "0ce805c3c"),
    "arch/arm64/kernel/late_cpu_profile.c": ("0e3f7bae7", "afabf66fe"),
    "arch/arm64/kernel/mt6797_psci.c": ("f01f6c4f7", "1b6d589ba"),
}

EXPECTED_TSV_SHA256 = {
    "blockers.tsv":
        "94ef2fc9de11911d082a0e39a028c24ef4e427a68e5b6ae64605e15647bef8ac",
    "capability-census.tsv":
        "25bc93ef4b0b57a2b60a0999093fa98da1f7ad715ff4f4ac89a89dc0c4af31c6",
    "evidence-audit.tsv":
        "b170c25e68071d62df96e2d150a5687245ec10e697afcaeacee3d4070007aff8",
    "implementation.tsv":
        "bc4e3946ce170672e4f457e2c523c5ab90d9a90a1d6990c76364f7a5d286b362",
    "unresolved-effects.tsv":
        "2be0f65bb7169b2e7045190116de2b8124078c5820f4dd3e86a52020300c453e",
}

EXPECTED_EXPERIMENT_FILES = {
    Path("README.md"),
    Path("DESIGN.md"),
    Path("scripts/validate.py"),
    Path("scripts/test_mutations.py"),
    Path("results/blockers.tsv"),
    Path("results/evidence-audit.tsv"),
    Path("results/capability-census.tsv"),
    Path("results/unresolved-effects.tsv"),
    Path("results/implementation.tsv"),
    Path("results/kernel-static-review-20260805.txt"),
    Path("results/offline-validation-20260805.txt"),
    Path("results/mutation-validation-20260805.txt"),
}

EXPECTED_BLOCKERS = (
    (0, "ARM64_LATE_CPU_BLOCK_REGISTRATION", "core", "conditional"),
    (1, "ARM64_LATE_CPU_BLOCK_TOPOLOGY", "profile", "conditional"),
    (2, "ARM64_LATE_CPU_BLOCK_CONFIGURATION", "profile", "blocked"),
    (3, "ARM64_LATE_CPU_BLOCK_CAP_INVENTORY", "core", "blocked"),
    (4, "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA1", "profile", "blocked"),
    (5, "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA2", "profile", "blocked"),
    (6, "ARM64_LATE_CPU_BLOCK_ID_REGISTERS", "profile", "blocked"),
    (7, "ARM64_LATE_CPU_BLOCK_CACHE_TYPE", "profile", "blocked"),
    (8, "ARM64_LATE_CPU_BLOCK_ASID", "profile", "blocked"),
    (9, "ARM64_LATE_CPU_BLOCK_GRANULE", "profile", "blocked"),
    (10, "ARM64_LATE_CPU_BLOCK_VA_MODE", "profile", "blocked"),
    (11, "ARM64_LATE_CPU_BLOCK_GIC", "profile", "blocked"),
    (12, "ARM64_LATE_CPU_BLOCK_HWCAP", "profile", "blocked"),
    (13, "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS", "profile", "blocked"),
    (14, "ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY", "profile", "blocked"),
    (15, "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3", "profile", "blocked"),
)

EXPECTED_IMPLEMENTATION = {
    "implementation_state": "PARTIAL_IMMUTABLE_PLAN_BOUNDARY",
    "a41_complete": "no",
    "plan_abi": "3",
    "source_parent_identity": EXPECTED_SOURCE_PARENT_IDENTITY,
    "config_input_identity": EXPECTED_CONFIG_INPUT_SHA256,
    "compiled_local_cap_count": "40",
    "static_present_count": "4",
    "static_absent_count": "30",
    "evidence_dependent_count": "6",
    "fallible_evidence": "separate",
    "immutable_plan": "separate",
    "architecture_receipt": "separate",
    "ready_token": "separate",
    "full_target_register_image": "described",
    "typed_effect_count": "6",
    "firmware_workaround_count": "3",
    "canonical_plan_identity": "unavailable",
    "profile_classifier": "all_unresolved",
    "profile_validate_plan": "-EAGAIN",
    "profile_prepare": "-EAGAIN",
    "architecture_commit": "mutation_unavailable",
    "plan_frozen_reachable": "no",
    "committed_reachable": "no",
    "ready_reachable": "no",
    "cpu_boot_veto": "-EAGAIN",
    "cpu_disable_veto": "false",
    "maxcpus": "8",
    "boot_candidate": "false",
    "build_authorized": "no",
    "device_action_authorized": "no",
    "hardware_support_claim": "none",
}

AARCH32_FIELDS = (
    "id_dfr0", "id_dfr1",
    "id_isar0", "id_isar1", "id_isar2", "id_isar3",
    "id_isar4", "id_isar5", "id_isar6",
    "id_mmfr0", "id_mmfr1", "id_mmfr2", "id_mmfr3",
    "id_mmfr4", "id_mmfr5",
    "id_pfr0", "id_pfr1", "id_pfr2",
    "mvfr0", "mvfr1", "mvfr2",
)
AARCH64_FIELDS = (
    "ctr", "cntfrq", "dczid", "midr", "revidr", "aidr", "gmid",
    "smidr", "mpamidr", "id_aa64dfr0", "id_aa64dfr1",
    "id_aa64isar0", "id_aa64isar1", "id_aa64isar2", "id_aa64isar3",
    "id_aa64mmfr0", "id_aa64mmfr1", "id_aa64mmfr2", "id_aa64mmfr3",
    "id_aa64mmfr4", "id_aa64pfr0", "id_aa64pfr1", "id_aa64pfr2",
    "id_aa64zfr0", "id_aa64smfr0", "id_aa64fpfr0",
)
EFFECT_FIELDS = (
    "ctr_mismatch.required",
    "ctr_mismatch.target_mask",
    "ctr_mismatch.trap_ctr_el0",
    "ctr_mismatch.alternative",
    "spectre_v2.required",
    "spectre_v2.target_mask",
    "spectre_v2.mitigation_state",
    "spectre_v2.conduit",
    "spectre_v2.callback",
    "spectre_v2.hyp_vector",
    "spectre_v2.alternative",
    "spectre_v4.required",
    "spectre_v4.target_mask",
    "spectre_v4.mitigation_state",
    "spectre_v4.method",
    "spectre_v4.conduit",
    "spectre_v4.policy",
    "spectre_v4.firmware_alternative",
    "bhb.required",
    "bhb.target_mask",
    "bhb.method",
    "bhb.loop_count",
    "bhb.system_method",
    "bhb.mitigation_state",
    "bhb.vector_template",
    "bhb.alternative",
    "bhb.v2_non_vulnerable",
    "compat_aes_clear",
    "speculative_at_finalization",
)


class ValidationError(RuntimeError):
    """A fixed source-contract invariant did not hold."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_tokens(text: str, tokens: Iterable[str], scope: str) -> None:
    for token in tokens:
        require(token in text, "{}: missing {!r}".format(scope, token))


def ordered(text: str, tokens: Sequence[str], scope: str) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        require(position >= 0, "{}: missing ordered token {!r}".format(scope, token))
        require(position > cursor, "{}: out-of-order token {!r}".format(scope, token))
        cursor = position


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def safe_relative(value: str, label: str) -> Path:
    pure = PurePosixPath(value)
    require(
        not pure.is_absolute() and ".." not in pure.parts,
        "{} is not a safe relative path".format(label),
    )
    return Path(*pure.parts)


def series_entries(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def is_subsequence(selected: Sequence[str], canonical: Sequence[str]) -> bool:
    iterator = iter(canonical)
    return all(any(item == candidate for candidate in iterator) for item in selected)


def config_input_hash(repo: Path, profile_name: str, profile: dict) -> str:
    lines = [
        "profile={}".format(profile_name),
        "base={}".format(profile["base"]),
    ]
    for fragment in profile["fragments"]:
        path = repo / fragment
        require(path.is_file(), "missing profile fragment {}".format(fragment))
        lines.append("{}  {}".format(sha256_file(path), fragment))
    return sha256_bytes(("\n".join(lines) + "\n").encode())


def patchset_hash(repo: Path, series_relative: Path) -> str:
    series_path = repo / series_relative
    lines = ["{}  {}".format(sha256_file(series_path), series_relative)]
    for entry in series_entries(series_path.read_text()):
        path = series_path.parent / entry
        require(path.is_file(), "selected patch is missing: {}".format(entry))
        lines.append("{}  {}".format(sha256_file(path), entry))
    return sha256_bytes(("\n".join(lines) + "\n").encode())


def source_state_hash(repo: Path, series_relative: Path) -> str:
    manifest = json.loads((repo / MANIFEST).read_text())
    kernel = manifest["kernel"]
    material = "{}\n{}\n{}\n".format(
        kernel["version"],
        kernel["sha256"],
        patchset_hash(repo, series_relative),
    )
    return sha256_bytes(material.encode())


def digest_u64_literals(digest: str) -> tuple[str, ...]:
    require(bool(re.fullmatch(r"[0-9a-f]{64}", digest)), "invalid digest")
    return tuple(
        "0x" + digest[index:index + 16]
        for index in range(0, len(digest), 16)
    )


def load_previous_validator(repo: Path) -> ModuleType:
    path = repo / PREVIOUS_VALIDATOR
    require(path.is_file(), "previous planner validator is missing")
    require(
        sha256_file(path) == PREVIOUS_VALIDATOR_SHA256,
        "previous planner validator identity changed",
    )
    spec = importlib.util.spec_from_file_location("a41_previous_validator", path)
    require(spec is not None and spec.loader is not None, "cannot load previous validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def section_added(section: str) -> str:
    return "\n".join(
        line[1:]
        for line in section.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def section_postview(section: str) -> str:
    lines: list[str] = []
    for line in section.splitlines():
        if line.startswith(("+++", "---", "diff --git", "index ", "@@")):
            continue
        if line.startswith("+") or line.startswith(" "):
            lines.append(line[1:])
    return "\n".join(lines)


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(reader.fieldnames is not None, "{} has no header".format(path))
        rows = list(reader)
    return list(reader.fieldnames), rows


def macro_bit_definitions(text: str, prefix: str) -> list[tuple[int, str]]:
    found = re.findall(
        r"^#define\s+(" + re.escape(prefix) + r"[A-Z0-9_]+)"
        r"\s+BIT(?:_ULL)?\((\d+)\)",
        text,
        flags=re.MULTILINE,
    )
    return [(int(bit), name) for name, bit in found]


def extract_c_block(text: str, marker: str) -> str:
    start = text.find(marker)
    require(start >= 0, "missing C block {}".format(marker))
    brace = text.find("{", start)
    require(brace >= 0, "missing opening brace for {}".format(marker))
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValidationError("unterminated C block {}".format(marker))


def validate_bounded_archive(repo: Path, check_frozen_evidence: bool) -> None:
    experiment = repo / EXPERIMENT_REL
    require(experiment.is_dir() and not experiment.is_symlink(), "experiment is missing")
    actual = {
        path.relative_to(experiment)
        for path in experiment.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    required_without_transcripts = EXPECTED_EXPERIMENT_FILES - {
        Path("results/offline-validation-20260805.txt"),
        Path("results/mutation-validation-20260805.txt"),
    }
    require(
        required_without_transcripts <= actual,
        "experiment archive is incomplete",
    )
    if check_frozen_evidence:
        require(actual == EXPECTED_EXPERIMENT_FILES, "experiment residue changed")
    else:
        require(actual <= EXPECTED_EXPERIMENT_FILES, "unexpected experiment residue")

    bounded = [
        repo / PATCH_0151,
        repo / SELECTED_SERIES,
        repo / SELECTED_FRAGMENT,
    ]
    bounded.extend(experiment / relative for relative in actual)
    personal = ("/" + "Users/", "/" + "home/", "C:\\" + "Users\\")
    private_key = "-----BEGIN " + "PRIVATE KEY-----"
    credential = re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)"
        r"\s*[:=]\s*[\"'][^\"'\n]{4,}"
    )
    for path in bounded:
        require(path.is_file() and not path.is_symlink(), "bounded path is not regular")
        relative = path.relative_to(repo)
        require("artifacts" not in relative.parts, "artifacts path entered archive")
        text = path.read_text()
        require(
            not any(marker in text for marker in personal),
            "personal absolute path entered archive",
        )
        require(private_key not in text, "private key entered archive")
        require(not credential.search(text), "credential entered archive")

    for document in (experiment / "README.md", experiment / "DESIGN.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text()):
            if target.startswith(("http://", "https://", "#")):
                continue
            path_value = target.split("#", 1)[0]
            if (
                not check_frozen_evidence
                and path_value in {
                    "results/offline-validation-20260805.txt",
                    "results/mutation-validation-20260805.txt",
                }
            ):
                continue
            require(
                (document.parent / path_value).resolve().exists(),
                "broken experiment link {}".format(target),
            )

    index = (repo / "experiments/README.md").read_text()
    roadmap = (repo / "docs/ROADMAP.md").read_text()
    require(str(EXPERIMENT_REL.name) in index, "experiment index entry is missing")
    require(str(EXPERIMENT_REL.name) in roadmap, "roadmap milestone link is missing")


def validate_patch_and_manifest(repo: Path, previous: ModuleType, pin_hashes: bool) -> None:
    patch_text = (repo / PATCH_0151).read_text()
    require(
        patch_text.startswith(
            "From {} Mon Sep 17 00:00:00 2001\n".format(EXPECTED_PATCH_COMMIT)
        ),
        "patch commit identity changed",
    )
    require_tokens(
        patch_text,
        (
            "From: Gemini Mainline Project <noreply@invalid>",
            "Subject: [PATCH] arm64: split late-CPU evidence from commit receipt",
            "This experiment-only change has no certifying sign-off and is not\n"
            "submission-ready.",
        ),
        "patch metadata",
    )
    require("Signed-off-by:" not in patch_text, "synthetic sign-off entered patch")
    if pin_hashes:
        require(sha256_file(repo / PATCH_0151) == EXPECTED_PATCH_SHA256,
                "patch identity changed")

    sections = previous.patch_sections(patch_text)
    require(set(sections) == set(EXPECTED_PATCH_INDEXES), "patch path set changed")
    for path, expected in EXPECTED_PATCH_INDEXES.items():
        require(
            previous.parse_index(sections[path]) == expected,
            "{} patch pre/post image changed".format(path),
        )

    canonical = series_entries((repo / CANONICAL_SERIES).read_text())
    selected = series_entries((repo / SELECTED_SERIES).read_text())
    terminal = [
        str(path.relative_to("patches"))
        for path in (PATCH_0092, PATCH_0148, PATCH_0149, PATCH_0150, PATCH_0151)
    ]
    require(len(selected) == 93, "selected series entry count changed")
    require(selected[-5:] == terminal, "selected terminal patch order changed")
    require(is_subsequence(selected, canonical), "selected series is not canonical")
    positions = [canonical.index(entry) for entry in terminal[1:]]
    require(
        all(right == left + 1 for left, right in zip(positions, positions[1:])),
        "canonical A41 patch order changed",
    )
    if pin_hashes:
        require(
            sha256_file(repo / SELECTED_SERIES) == EXPECTED_SERIES_SHA256,
            "selected series identity changed",
        )
        require(
            patchset_hash(repo, SELECTED_SERIES) == EXPECTED_PATCHSET_SHA256,
            "selected patchset identity changed",
        )
        require(
            source_state_hash(repo, SELECTED_SERIES) == EXPECTED_SOURCE_STATE_SHA256,
            "selected source-state identity changed",
        )

    manifest = json.loads((repo / MANIFEST).read_text())
    config = manifest["config"]
    profiles = config["profiles"]
    require(config["default_profile"] == "full", "default profile changed")
    require(len(profiles) == EXPECTED_PROFILE_COUNT, "profile inventory changed")
    fallback = manifest.get("patch_series")
    for name, profile in profiles.items():
        require(
            bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name)),
            "unsafe profile name {}".format(name),
        )
        series_value = profile.get("patch_series", fallback)
        path = safe_relative(series_value, "profile series")
        require(path.parts[0] == "patches", "profile series escaped patches")
        entries = series_entries((repo / path).read_text())
        require(
            is_subsequence(entries, canonical),
            "profile {} is not a canonical subsequence".format(name),
        )

    require(PROFILE in profiles, "immutable-plan profile is missing")
    profile = profiles[PROFILE]
    require(profile.get("base") == "defconfig", "profile base changed")
    require(profile.get("patch_series") == str(SELECTED_SERIES),
            "profile series selection changed")
    require(
        tuple(profile.get("fragments", ())) == EXPECTED_PROFILE_FRAGMENTS,
        "profile fragment order changed",
    )
    for name, other in profiles.items():
        if name == PROFILE:
            continue
        require(
            other.get("patch_series") != str(SELECTED_SERIES),
            "selected series leaked into {}".format(name),
        )
        require(
            str(SELECTED_FRAGMENT) not in other.get("fragments", ()),
            "selected fragment leaked into {}".format(name),
        )

    fragment = (repo / SELECTED_FRAGMENT).read_text()
    assignments = [
        line.strip()
        for line in fragment.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        assignments == [
            "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
            'CONFIG_LOCALVERSION="-gemini-a41-immutable-blocked"',
        ],
        "selected fragment settings changed",
    )
    require(
        "architecture-owned mutation implementation remain unavailable" in fragment,
        "fragment misstates the commit boundary",
    )
    require("CONFIG_CMDLINE" not in "\n".join(assignments),
            "selected fragment changes command line")
    require(
        "maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(),
        "inherited maxcpus=8 guard changed",
    )
    require(
        config_input_hash(repo, PROFILE, profile) == EXPECTED_CONFIG_INPUT_SHA256,
        "configuration-input identity changed",
    )


def validate_evidence_tables(repo: Path, pin_hashes: bool) -> None:
    results = repo / EXPERIMENT_REL / "results"
    for name, expected in EXPECTED_TSV_SHA256.items():
        if pin_hashes:
            require(sha256_file(results / name) == expected,
                    "{} identity changed".format(name))

    fields, rows = read_tsv(results / "blockers.tsv")
    require(
        fields == ["bit", "symbol", "owner", "current_state", "abi3_binding"],
        "blocker table header changed",
    )
    require(len(rows) == 16, "blocker table row count changed")
    actual = [
        (int(row["bit"]), row["symbol"], row["owner"], row["current_state"])
        for row in rows
    ]
    require(actual == list(EXPECTED_BLOCKERS), "blocker table changed")

    fields, audit = read_tsv(results / "evidence-audit.tsv")
    require(
        fields == [
            "bit", "symbol", "owner", "current_state",
            "strongest_exact_repo_citations", "what_it_proves",
            "exact_remaining_gap", "existing_evidence_can_close",
        ],
        "evidence audit header changed",
    )
    require(len(audit) == 16, "evidence audit row count changed")
    for expected, row in zip(EXPECTED_BLOCKERS, audit):
        bit, symbol, owner, _state = expected
        require(
            (int(row["bit"]), row["symbol"], row["owner"]) ==
            (bit, symbol, owner),
            "evidence audit ordering changed",
        )
        require(
            row["existing_evidence_can_close"].startswith("no"),
            "existing evidence was promoted without proof",
        )
    cap_row = audit[3]
    require_tokens(
        "\t".join(cap_row.values()),
        ("all 40", "UNRESOLVED", "future evaluator input"),
        "capability-inventory evidence",
    )
    require_tokens(
        "\t".join(audit[15].values()),
        ("workaround-3", "WA3", "BHB method"),
        "WA3 evidence",
    )

    fields, census = read_tsv(results / "capability-census.tsv")
    require(
        fields == [
            "slot", "symbol", "type", "guard", "matcher", "state", "basis",
            "evidence_needed", "effect_class", "early_a53_relation",
        ],
        "capability census header changed",
    )
    require(len(census) == 40, "capability census count changed")
    slots = [int(row["slot"]) for row in census]
    require(len(slots) == len(set(slots)), "capability census duplicates a slot")
    states = Counter(row["state"] for row in census)
    require(
        states == Counter({"PRESENT": 4, "ABSENT": 30, "UNRESOLVED": 6}),
        "capability census partition changed",
    )
    present = {int(row["slot"]) for row in census if row["state"] == "PRESENT"}
    unresolved = {
        int(row["slot"]) for row in census if row["state"] == "UNRESOLVED"
    }
    require(present == {9, 66, 94, 121}, "static PRESENT set changed")
    require(unresolved == {33, 36, 69, 79, 81, 82},
            "evidence-dependent set changed")
    by_slot = {int(row["slot"]): row for row in census}
    for slot in (9, 66):
        require(
            "not newly required" in by_slot[slot]["early_a53_relation"],
            "AMU/HW_DBM was promoted to a new effect",
        )
    require(
        "CSV2.3" in by_slot[82]["evidence_needed"]
        or "CSV2" in by_slot[82]["evidence_needed"],
        "BHB state lost target CSV2 evidence",
    )

    fields, unresolved_rows = read_tsv(results / "unresolved-effects.tsv")
    require(
        fields == [
            "slot", "symbol", "capability_state_rule",
            "capability_state_evidence", "effect_or_method_evidence",
            "early_a53_relation", "commit_or_validation_semantics",
        ],
        "unresolved-effect header changed",
    )
    require(
        [int(row["slot"]) for row in unresolved_rows] ==
        [33, 36, 69, 79, 81, 82],
        "unresolved-effect set changed",
    )
    bhb = unresolved_rows[-1]
    require(
        "CSV2" in bhb["capability_state_rule"]
        and "loop k=8" not in bhb["capability_state_rule"],
        "BHB state/method separation changed",
    )
    require_tokens(
        "\t".join(bhb.values()),
        ("CSV2", "WA3", "loop k=8", "method"),
        "BHB state/method separation",
    )

    fields, markers = read_tsv(results / "implementation.tsv")
    require(fields == ["key", "value", "basis"],
            "implementation table header changed")
    values = {row["key"]: row["value"] for row in markers}
    require(len(values) == len(markers), "implementation marker duplicated")
    require(values == EXPECTED_IMPLEMENTATION, "implementation markers changed")


def validate_patch_source_contract(repo: Path, previous: ModuleType) -> None:
    patch_text = (repo / PATCH_0151).read_text()
    sections = previous.patch_sections(patch_text)
    header = section_postview(
        sections["arch/arm64/include/asm/late_cpu_profile.h"]
    )
    cpufeature = section_postview(sections["arch/arm64/kernel/cpufeature.c"])
    framework = section_postview(
        sections["arch/arm64/kernel/late_cpu_profile.c"]
    )
    platform = section_postview(sections["arch/arm64/kernel/mt6797_psci.c"])
    added = "\n".join((header, cpufeature, framework, platform))

    require_tokens(
        header,
        (
            "#define ARM64_LATE_CPU_PLAN_ABI\t\t3",
            "struct arm64_late_cpu_evidence",
            "struct arm64_late_cpu_plan",
            "struct arm64_late_cpu_receipt",
            "struct arm64_late_cpu_ready_token",
            "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3",
            "ARM64_LATE_CPU_TARGET_CAP_WA3_VALID",
            "ARM64_LATE_CPU_TARGET_METHOD_BHB_VALID",
            "struct arm64_late_cpu_target_cap_evidence",
            "struct arm64_late_cpu_target_method_evidence",
            "struct arm64_late_cpu_system_cap_evidence",
            "expected_elf_hwcap[3]",
            "expected_compat_hwcap",
            "expected_compat_hwcap2",
        ),
        "ABI 3 header",
    )
    ordered(
        header,
        (
            "ARM64_LATE_CPU_PROFILE_NONE",
            "ARM64_LATE_CPU_PROFILE_REGISTERED",
            "ARM64_LATE_CPU_PROFILE_BLOCKED",
            "ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
            "ARM64_LATE_CPU_PROFILE_COMMITTED",
            "ARM64_LATE_CPU_PROFILE_SYSTEM_VERIFIED",
            "ARM64_LATE_CPU_PROFILE_READY",
        ),
        "ABI 3 state order",
    )
    extract_c_block(header, "struct arm64_late_cpu_evidence {")
    effect_schema = extract_c_block(header, "struct arm64_late_cpu_effect_plan {")
    receipt_schema = extract_c_block(header, "struct arm64_late_cpu_receipt {")
    ready_schema = extract_c_block(header, "struct arm64_late_cpu_ready_token {")
    require_tokens(
        effect_schema,
        (
            "u8 trap_ctr_el0;",
            "u8 callback;",
            "u8 hyp_vector;",
            "u8 firmware_alternative;",
            "u8 loop_count;",
            "u8 vector_template;",
            "u8 compat_aes_clear;",
            "u8 speculative_at_finalization;",
        ),
        "typed effect schema",
    )
    require_tokens(
        receipt_schema,
        (
            "u64 plan_identity[ARM64_LATE_CPU_ID_WORDS];",
            "struct arm64_late_cpu_effect_plan committed;",
            "u8 commit_complete;",
            "u8 strict_caps_verified;",
            "u8 alternatives_finalized;",
            "u8 user_hwcaps_finalized;",
        ),
        "receipt schema",
    )
    require_tokens(
        ready_schema,
        (
            "u64 plan_identity[ARM64_LATE_CPU_ID_WORDS];",
            "u64 source_parent_identity[ARM64_LATE_CPU_ID_WORDS];",
            "u64 config_input_identity[ARM64_LATE_CPU_ID_WORDS];",
            "u64 evidence_identity[ARM64_LATE_CPU_ID_WORDS];",
            "struct arm64_late_cpu_effect_plan committed;",
        ),
        "READY token schema",
    )
    for field in AARCH32_FIELDS:
        require(
            re.search(r"\bu32\s+{};".format(re.escape(field)), header) is not None,
            "AArch32 register field {} is missing".format(field),
        )
    for field in AARCH64_FIELDS:
        require(
            re.search(r"\bu64\s+{};".format(re.escape(field)), header) is not None,
            "AArch64 register field {} is missing".format(field),
        )
    require_tokens(
        header,
        (
            "u64 clidr_el1;",
            "u64 ctr_effective;",
            "u64 icc_sre_el1;",
            "u64 icc_idr0_el1;",
            "u64 ich_vtr_el2;",
            "s32 ich_vtr_status;",
            "s32 smccc_wa1;",
            "s32 smccc_wa2;",
            "s32 smccc_wa3;",
            "u16 asid_bits;",
            "u8 page_shift;",
            "u8 va_bits;",
            "u8 hyp_available;",
            "u8 gic_sre_usable;",
        ),
        "target evidence schema",
    )

    blockers = macro_bit_definitions(header, "ARM64_LATE_CPU_BLOCK_")
    require(
        (15, "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3") in blockers,
        "ABI WA3 blocker definition changed",
    )
    require(
        macro_bit_definitions(header, "ARM64_LATE_CPU_TARGET_CAP_") ==
        [
            (0, "ARM64_LATE_CPU_TARGET_CAP_MIDR_VALID"),
            (1, "ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID"),
            (2, "ARM64_LATE_CPU_TARGET_CAP_CTR_VALID"),
            (3, "ARM64_LATE_CPU_TARGET_CAP_GIC_VALID"),
            (4, "ARM64_LATE_CPU_TARGET_CAP_HYP_VALID"),
            (5, "ARM64_LATE_CPU_TARGET_CAP_WA1_VALID"),
            (6, "ARM64_LATE_CPU_TARGET_CAP_WA2_VALID"),
            (7, "ARM64_LATE_CPU_TARGET_CAP_WA3_VALID"),
            (8, "ARM64_LATE_CPU_TARGET_CAP_ASID_VALID"),
            (9, "ARM64_LATE_CPU_TARGET_CAP_GRANULE_VALID"),
            (10, "ARM64_LATE_CPU_TARGET_CAP_VA_VALID"),
        ],
        "target capability validity mask changed",
    )
    require(
        macro_bit_definitions(header, "ARM64_LATE_CPU_TARGET_METHOD_") ==
        [
            (0, "ARM64_LATE_CPU_TARGET_METHOD_CONDUIT_VALID"),
            (1, "ARM64_LATE_CPU_TARGET_METHOD_V2_VALID"),
            (2, "ARM64_LATE_CPU_TARGET_METHOD_V4_VALID"),
            (3, "ARM64_LATE_CPU_TARGET_METHOD_BHB_VALID"),
        ],
        "target method validity mask changed",
    )

    require_tokens(
        cpufeature,
        (
            "late_cpu_effect_plan_empty",
            "arm64_commit_late_cpu_profile();",
            "case ARM64_MISMATCHED_CACHE_TYPE:",
            "case ARM64_SPECTRE_V2:",
            "case ARM64_SPECTRE_V4:",
            "case ARM64_SPECTRE_BHB:",
            "The exhaustive evaluator owns these typed effects.",
            "draft->effects.compat_aes_clear = 1;",
            "draft->effects.speculative_at_finalization = 1;",
        ),
        "cpufeature ABI 3 boundary",
    )
    for field in EFFECT_FIELDS:
        require(
            "effects->{}".format(field) in cpufeature,
            "effect emptiness check omits {}".format(field),
        )
    require_tokens(
        framework,
        (
            "static struct arm64_late_cpu_plan late_plan __ro_after_init;",
            "static struct arm64_late_cpu_receipt late_receipt __ro_after_init",
            "static struct arm64_late_cpu_ready_token late_ready_token __ro_after_init;",
            "late_profile_effects_match",
            "late_profile_receipt_identity_matches",
            "late_profile_plan_has_identity",
            "arm64_commit_late_cpu_profile",
            "late CPU profile commit implementation is unavailable",
            "smp_store_release(&late_receipt.state",
            "smp_load_acquire(&late_receipt.state)",
        ),
        "core ABI 3 transaction",
    )
    ordered(
        framework,
        (
            "late_profile.prepare",
            "evidence.abi != ARM64_LATE_CPU_PLAN_ABI",
            "arm64_plan_late_cpu_capabilities",
            "late_profile.validate_plan",
            "ret || plan_ret || validate_ret || draft.evidence.blocker_mask",
            "late_profile_block",
            "late_profile_plan_has_identity",
            "late_plan = draft;",
            "memcpy(late_receipt.plan_identity",
            "ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
        ),
        "prepare/freeze transaction",
    )
    commit = extract_c_block(
        framework, "void __init arm64_commit_late_cpu_profile"
    )
    require_tokens(
        commit,
        (
            "state == ARM64_LATE_CPU_PROFILE_NONE",
            "state == ARM64_LATE_CPU_PROFILE_BLOCKED",
            "state != ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
            "late CPU profile commit implementation is unavailable",
        ),
        "architecture commit implementation",
    )
    require(
        "state == ARM64_LATE_CPU_PROFILE_BLOCKED" in commit,
        "architecture commit BLOCKED return changed",
    )
    verify = extract_c_block(
        framework, "void __init arm64_verify_late_cpu_profile_system"
    )
    require(
        verify.count("late_profile_receipt_identity_matches") >= 2,
        "system verification lost bracketing identity checks",
    )
    finalize = extract_c_block(
        framework, "void __init arm64_finalize_late_cpu_profile_user"
    )
    require(
        "smp_store_release(&late_receipt.state" in finalize,
        "READY publication lost release-store",
    )
    accessor = extract_c_block(
        framework, "arm64_get_late_cpu_ready_token(void)"
    )
    require_tokens(
        accessor,
        ("smp_load_acquire(&late_receipt.state)", "return &late_ready_token;"),
        "READY accessor",
    )
    require("late_plan" not in accessor, "READY accessor exposes the plan")
    for field in EFFECT_FIELDS:
        require(
            "left->{}".format(field) in framework and
            "right->{}".format(field) in framework,
            "receipt effect comparison omits {}".format(field),
        )
    require(
        not re.search(r"(?:draft->|late_plan\.)identity\s*\[[^\]]+\]\s*=", added),
        "plan identity gained a writer",
    )
    require("memcpy(draft->identity" not in added, "draft identity gained a writer")
    require("memcpy(late_plan.identity" not in added,
            "published plan identity gained a writer")
    require(
        not re.search(r"late_receipt\.commit_complete\s*=", added),
        "commit completion gained a writer",
    )
    require(
        "ARM64_LATE_CPU_PROFILE_COMMITTED);" not in added,
        "COMMITTED publication became reachable",
    )
    require(
        not re.search(r"late_receipt\.committed(?:\.|\s*=)", added),
        "receipt committed effects gained a writer",
    )

    require_tokens(
        platform,
        (
            "return ARM64_LATE_CPU_CAP_UNRESOLVED;",
            "Never bless a partial census as a frozen capability plan.",
            "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA1",
            "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA2",
            "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3",
            "return -EAGAIN;",
        ) + digest_u64_literals(EXPECTED_SOURCE_PARENT_IDENTITY)
          + digest_u64_literals(EXPECTED_CONFIG_INPUT_SHA256),
        "MT6797 fail-closed profile",
    )
    classifier = extract_c_block(
        platform, "mt6797_a72_classify_local_cap"
    )
    require(
        classifier.count("return ARM64_LATE_CPU_CAP_UNRESOLVED;") == 1
        and classifier.count("return ") == 1,
        "profile classifier is no longer all-unresolved",
    )
    validator = extract_c_block(
        platform, "mt6797_a72_validate_cap_plan"
    )
    require(
        validator.count("return -EAGAIN;") == 1,
        "profile validator no longer rejects",
    )
    profile_prepare = extract_c_block(
        platform, "mt6797_a72_profile_prepare"
    )
    require(
        "return -EAGAIN;" in profile_prepare,
        "profile preparation no longer rejects",
    )

    forbidden = (
        "system_cpucaps",
        "elf_hwcap |=",
        "compat_elf_hwcap |=",
        "max_bhb_k =",
        "spectre_v2_state =",
        "spectre_v4_state =",
        "cpu_psci_ops.cpu_boot(",
        "psci_ops.cpu_on(",
        "draft->effects.bhb.required =",
    )
    for token in forbidden:
        require(token not in added, "live mutation entered patch: {}".format(token))


def validate_offline_tools(repo: Path) -> None:
    scripts = [
        repo / EXPERIMENT_REL / "scripts/validate.py",
        repo / EXPERIMENT_REL / "scripts/test_mutations.py",
    ]
    forbidden_imports = {
        "socket", "urllib", "http", "requests", "ftplib", "paramiko",
    }
    forbidden_commands = {
        "ssh", "nc", "netcat", "curl", "wget", "scp", "rsync",
        "build-kernel", "dev-vm",
    }
    for path in scripts:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                require(
                    not any(alias.name.split(".")[0] in forbidden_imports
                            for alias in node.names),
                    "offline script imports a network module",
                )
            if isinstance(node, ast.ImportFrom):
                require(
                    (node.module or "").split(".")[0] not in forbidden_imports,
                    "offline script imports a network module",
                )
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    require(
                        node.func.id not in {"eval", "exec", "compile"},
                        "offline script contains dynamic execution",
                    )
                if isinstance(node.func, ast.Attribute):
                    require(
                        node.func.attr not in {"Popen", "system", "popen"},
                        "offline script contains an unsafe process call",
                    )
                require(
                    not any(
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value
                        for keyword in node.keywords
                    ),
                    "offline script enables a shell",
                )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and node.args
            ):
                command_literals = {
                    value.value
                    for value in ast.walk(node.args[0])
                    if isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                }
                require(
                    not command_literals.intersection(forbidden_commands),
                    "offline script contains a forbidden command",
                )


def mutation_case_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    function = next(
        (
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "mutations"
        ),
        None,
    )
    require(function is not None, "mutation suite has no mutations function")
    returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
    require(
        len(returns) == 1 and isinstance(returns[0].value, ast.List),
        "mutation suite case list changed",
    )
    names: list[str] = []
    for element in returns[0].value.elts:
        require(
            isinstance(element, ast.Call)
            and isinstance(element.func, ast.Name)
            and element.func.id == "Mutation"
            and element.args
            and isinstance(element.args[0], ast.Constant)
            and isinstance(element.args[0].value, str),
            "mutation suite case shape changed",
        )
        names.append(element.args[0].value)
    require(len(names) == EXPECTED_MUTATION_COUNT, "mutation count changed")
    require(len(names) == len(set(names)), "mutation names are duplicated")
    return names


def validate_frozen_evidence(repo: Path) -> None:
    experiment = repo / EXPERIMENT_REL
    validator = experiment / "scripts/validate.py"
    mutation_suite = experiment / "scripts/test_mutations.py"
    offline = (
        experiment / "results/offline-validation-20260805.txt"
    ).read_text().splitlines()
    expected_stages = [
        "PASS previous-planner-baseline",
        "PASS bounded-archive",
        "PASS patch-manifest-identities",
        "PASS evidence-tables",
        "PASS abi3-source-contract",
        "PASS offline-tool-boundary",
        "PASS source-application",
    ]
    require(offline[:7] == expected_stages, "offline stage transcript changed")
    require_tokens(
        "\n".join(offline),
        (
            "patch_0151_sha256=" + EXPECTED_PATCH_SHA256,
            "selected_series_sha256=" + EXPECTED_SERIES_SHA256,
            "selected_patchset_sha256=" + EXPECTED_PATCHSET_SHA256,
            "selected_source_state_sha256=" + EXPECTED_SOURCE_STATE_SHA256,
            "config_inputs_sha256=" + EXPECTED_CONFIG_INPUT_SHA256,
            "source_parent_commit=" + EXPECTED_PATCH_PARENT,
            "source_commit=" + EXPECTED_PATCH_COMMIT,
            "source_tree=" + EXPECTED_PATCH_TREE,
            "validator_sha256=" + sha256_file(validator),
            "implementation_state=PARTIAL_IMMUTABLE_PLAN_BOUNDARY",
            "a41_complete=no",
            "build_authorized=no",
            "device_action_authorized=no",
            "RESULT PASS 7/7",
        ),
        "offline transcript",
    )

    names = mutation_case_names(mutation_suite)
    mutation = (
        experiment / "results/mutation-validation-20260805.txt"
    ).read_text().splitlines()
    expected_lines = [
        "PASS mutation {:02d} {}".format(index, name)
        for index, name in enumerate(names, 1)
    ]
    require(
        mutation[:len(expected_lines)] == expected_lines,
        "mutation transcript case list changed",
    )
    require_tokens(
        "\n".join(mutation),
        (
            "validator_sha256=" + sha256_file(validator),
            "mutation_suite_sha256=" + sha256_file(mutation_suite),
            "mutation_count={}".format(EXPECTED_MUTATION_COUNT),
            "RESULT PASS {0}/{0}".format(EXPECTED_MUTATION_COUNT),
        ),
        "mutation transcript",
    )


def validate_repository(
    repo: Path,
    *,
    pin_hashes: bool = True,
    check_frozen_evidence: bool = True,
) -> list[str]:
    repo = repo.resolve()
    previous = load_previous_validator(repo)
    try:
        previous.validate_repository(
            repo,
            pin_hashes=True,
            check_frozen_evidence=True,
        )
    except Exception as error:
        raise ValidationError("previous planner baseline failed: {}".format(error)) from error
    completed = ["previous-planner-baseline"]

    validate_bounded_archive(repo, check_frozen_evidence)
    if check_frozen_evidence:
        validate_frozen_evidence(repo)
    completed.append("bounded-archive")

    validate_patch_and_manifest(repo, previous, pin_hashes)
    completed.append("patch-manifest-identities")

    validate_evidence_tables(repo, pin_hashes)
    completed.append("evidence-tables")

    validate_patch_source_contract(repo, previous)
    completed.append("abi3-source-contract")

    validate_offline_tools(repo)
    completed.append("offline-tool-boundary")
    return completed


def run_git(source_root: Path, args: Sequence[str], *, binary: bool = False):
    result = subprocess.run(
        [
            "git", "--no-pager", "--no-replace-objects",
            "-C", str(source_root), *args,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    )
    require(
        result.returncode == 0,
        "git {} failed: {}".format(
            " ".join(args),
            result.stderr if not binary else result.stderr.decode(errors="replace"),
        ),
    )
    return result.stdout


def validate_applied_source(tree: Path) -> None:
    header = (tree / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    cpufeature = (tree / "arch/arm64/kernel/cpufeature.c").read_text()
    framework = (tree / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    platform = (tree / "arch/arm64/kernel/mt6797_psci.c").read_text()

    require(
        macro_bit_definitions(header, "ARM64_LATE_CPU_BLOCK_") ==
        [(bit, symbol) for bit, symbol, _owner, _state in EXPECTED_BLOCKERS],
        "applied ABI blocker definitions changed",
    )

    states = extract_c_block(header, "enum arm64_late_cpu_profile_state")
    ordered(
        states,
        (
            "ARM64_LATE_CPU_PROFILE_NONE",
            "ARM64_LATE_CPU_PROFILE_REGISTERED",
            "ARM64_LATE_CPU_PROFILE_BLOCKED",
            "ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
            "ARM64_LATE_CPU_PROFILE_COMMITTED",
            "ARM64_LATE_CPU_PROFILE_SYSTEM_VERIFIED",
            "ARM64_LATE_CPU_PROFILE_READY",
        ),
        "profile state order",
    )
    aarch32 = extract_c_block(
        header, "struct arm64_late_cpu_aarch32_register_image"
    )
    aarch64 = extract_c_block(header, "struct arm64_late_cpu_register_image")
    ordered(aarch32, [" {};" .format(field) for field in AARCH32_FIELDS],
            "AArch32 register order")
    ordered(aarch64, [" {};" .format(field) for field in AARCH64_FIELDS],
            "AArch64 register order")

    prepare = extract_c_block(framework, "void __init arm64_prepare_late_cpu_profile")
    ordered(
        prepare,
        (
            "late_profile.prepare",
            "evidence.abi != ARM64_LATE_CPU_PLAN_ABI",
            "arm64_plan_late_cpu_capabilities",
            "late_profile.validate_plan",
            "ret || plan_ret || validate_ret || draft.evidence.blocker_mask",
            "late_profile_block",
            "late_profile_plan_has_identity",
            "late_plan = draft;",
            "memcpy(late_receipt.plan_identity",
            "ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
        ),
        "prepare/freeze transaction",
    )
    commit = extract_c_block(framework, "void __init arm64_commit_late_cpu_profile")
    require_tokens(
        commit,
        (
            "ARM64_LATE_CPU_PROFILE_NONE",
            "ARM64_LATE_CPU_PROFILE_BLOCKED",
            "ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
            "late_profile_plan_has_identity",
            "late CPU profile commit implementation is unavailable",
        ),
        "architecture commit",
    )
    for forbidden in (
        "late_profile.",
        "__set_bit",
        "system_cpucaps",
        "commit_complete =",
        "committed =",
        "ARM64_LATE_CPU_PROFILE_COMMITTED);",
    ):
        require(forbidden not in commit,
                "architecture commit contains mutation {}".format(forbidden))

    verify = extract_c_block(
        framework, "void __init arm64_verify_late_cpu_profile_system"
    )
    finalize = extract_c_block(
        framework, "void __init arm64_finalize_late_cpu_profile_user"
    )
    for body, label in ((verify, "system verification"), (finalize, "user verification")):
        require(body.count("late_profile_receipt_identity_matches") >= 2,
                "{} lost bracketing identity checks".format(label))
        require(body.count("late_profile_effects_match") >= 1,
                "{} lost effect checks".format(label))
    require(finalize.count("late_profile_effects_match") >= 3,
            "READY publication lost effect bracketing")

    accessor = extract_c_block(
        framework, "arm64_get_late_cpu_ready_token(void)"
    )
    require_tokens(
        accessor,
        ("smp_load_acquire(&late_receipt.state)", "return &late_ready_token;"),
        "READY accessor",
    )
    require("late_plan" not in accessor, "READY accessor exposes the plan")

    setup = extract_c_block(cpufeature, "static void __init setup_system_capabilities")
    ordered(
        setup,
        (
            "arm64_commit_late_cpu_profile();",
            "update_cpu_capabilities(SCOPE_SYSTEM);",
            "enable_cpu_capabilities(SCOPE_ALL & ~SCOPE_BOOT_CPU);",
            "apply_alternatives_all();",
        ),
        "applied commit timing",
    )
    classifier = extract_c_block(
        platform, "mt6797_a72_classify_local_cap"
    )
    require(
        classifier.count("return ARM64_LATE_CPU_CAP_UNRESOLVED;") == 1
        and classifier.count("return ") == 1,
        "profile classifier is no longer all-unresolved",
    )
    validator = extract_c_block(platform, "mt6797_a72_validate_cap_plan")
    require(validator.count("return -EAGAIN;") == 1,
            "profile validator no longer rejects")
    profile_prepare = extract_c_block(platform, "mt6797_a72_profile_prepare")
    require("return -EAGAIN;" in profile_prepare,
            "profile preparation no longer rejects")
    boot = extract_c_block(platform, "static int mt6797_psci_cpu_boot")
    disable = extract_c_block(platform, "mt6797_psci_cpu_can_disable")
    require(
        "return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot,
        "A72 boot veto changed",
    )
    require("return false;" in disable, "A72 disable veto changed")

    all_source = "\n".join((header, cpufeature, framework, platform))
    require(
        not re.search(r"(?:draft->|late_plan\.)identity\s*\[[^\]]+\]\s*=",
                      all_source),
        "applied source writes plan identity",
    )
    require("memcpy(draft->identity" not in all_source,
            "applied source writes draft identity")
    require("memcpy(late_plan.identity" not in all_source,
            "applied source writes published plan identity")
    require(
        not re.search(r"late_receipt\.commit_complete\s*=", framework),
        "applied source writes commit_complete",
    )
    require(
        "smp_store_release(&late_receipt.state,\n"
        "\t\t\t  ARM64_LATE_CPU_PROFILE_COMMITTED)" not in framework,
        "applied source publishes COMMITTED",
    )


def validate_source_application(
    repo: Path,
    source_root: Path,
    previous: ModuleType,
) -> None:
    source_root = source_root.resolve()
    require((source_root / ".git").exists(), "source root is not a Git repository")
    commit = run_git(source_root, ["rev-parse", "--verify",
                                  EXPECTED_PATCH_COMMIT + "^{commit}"]).strip()
    parent = run_git(source_root, ["rev-parse", "--verify",
                                  EXPECTED_PATCH_PARENT + "^{commit}"]).strip()
    require(commit == EXPECTED_PATCH_COMMIT, "source commit is absent")
    require(parent == EXPECTED_PATCH_PARENT, "source parent is absent")
    require(
        run_git(source_root, ["rev-parse", commit + "^{tree}"]).strip() ==
        EXPECTED_PATCH_TREE,
        "source tree changed",
    )
    require(
        run_git(source_root, ["rev-parse", parent + "^{tree}"]).strip() ==
        EXPECTED_PATCH_PARENT_TREE,
        "source parent tree changed",
    )
    actual_parent = run_git(
        source_root, ["rev-parse", commit + "^"]
    ).strip()
    require(actual_parent == parent, "source commit parent changed")

    patch_text = (repo / PATCH_0151).read_text()
    sections = previous.patch_sections(patch_text)
    with tempfile.TemporaryDirectory(prefix="gemini-a41-abi3-validate-") as temp:
        scratch = Path(temp)
        for source_path, section in sections.items():
            blob = run_git(
                source_root,
                ["cat-file", "blob", "{}:{}".format(parent, source_path)],
                binary=True,
            )
            old, _new = previous.parse_index(section)
            require(git_blob_sha1(blob).startswith(old),
                    "{} parent blob changed".format(source_path))
            destination = scratch / source_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blob)

        check = subprocess.run(
            [
                "git", "--no-pager", "--no-replace-objects", "apply",
                "--check", "--whitespace=error-all", str((repo / PATCH_0151).resolve()),
            ],
            cwd=scratch,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(check.returncode == 0,
                "patch applicability failed: {}".format(check.stderr.strip()))
        apply = subprocess.run(
            [
                "git", "--no-pager", "--no-replace-objects", "apply",
                "--whitespace=error-all", str((repo / PATCH_0151).resolve()),
            ],
            cwd=scratch,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(apply.returncode == 0,
                "patch application failed: {}".format(apply.stderr.strip()))
        for source_path, section in sections.items():
            _old, new = previous.parse_index(section)
            data = (scratch / source_path).read_bytes()
            require(git_blob_sha1(data).startswith(new),
                    "{} applied blob changed".format(source_path))
            committed = run_git(
                source_root,
                ["cat-file", "blob", "{}:{}".format(commit, source_path)],
                binary=True,
            )
            require(data == committed,
                    "{} differs from committed postimage".format(source_path))
        validate_applied_source(scratch)


def git_version() -> str:
    result = subprocess.run(
        ["git", "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(result.returncode == 0, "git version probe failed")
    return result.stdout.strip()


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--skip-frozen-evidence", action="store_true")
    args = parser.parse_args(argv)

    try:
        completed = validate_repository(
            args.repo_root,
            pin_hashes=True,
            check_frozen_evidence=not args.skip_frozen_evidence,
        )
        previous = load_previous_validator(args.repo_root.resolve())
        if args.source_root is not None:
            validate_source_application(
                args.repo_root.resolve(),
                args.source_root,
                previous,
            )
            completed.append("source-application")
        for stage in completed:
            print("PASS {}".format(stage))
        print("patch_0151_sha256={}".format(EXPECTED_PATCH_SHA256))
        print("selected_series_sha256={}".format(EXPECTED_SERIES_SHA256))
        print("selected_patchset_sha256={}".format(EXPECTED_PATCHSET_SHA256))
        print("selected_source_state_sha256={}".format(
            EXPECTED_SOURCE_STATE_SHA256
        ))
        print("config_inputs_sha256={}".format(EXPECTED_CONFIG_INPUT_SHA256))
        print("source_parent_commit={}".format(EXPECTED_PATCH_PARENT))
        print("source_commit={}".format(EXPECTED_PATCH_COMMIT))
        print("source_tree={}".format(EXPECTED_PATCH_TREE))
        print("diff_sha256={}".format(EXPECTED_DIFF_SHA256))
        print("validator_sha256={}".format(sha256_file(Path(__file__))))
        print("python_version={}".format(sys.version.split()[0]))
        print("git_version={}".format(git_version()))
        print("profile_count={}".format(EXPECTED_PROFILE_COUNT))
        print("compiled_local_caps=40")
        print("static_present=4")
        print("static_absent=30")
        print("evidence_dependent=6")
        print("implementation_state=PARTIAL_IMMUTABLE_PLAN_BOUNDARY")
        print("a41_complete=no")
        print("build_authorized=no")
        print("device_action_authorized=no")
        print("RESULT PASS {0}/{0}".format(len(completed)))
        return 0
    except (OSError, ValueError, ValidationError) as error:
        print("RESULT FAIL {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
