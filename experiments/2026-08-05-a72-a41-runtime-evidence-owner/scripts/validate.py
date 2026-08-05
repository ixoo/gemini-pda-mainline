#!/usr/bin/env python3
"""Validate the fail-closed ABI-6 late-CPU evidence ownership boundary."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

sys.dont_write_bytecode = True


EXPERIMENT = Path("experiments/2026-08-05-a72-a41-runtime-evidence-owner")
PATCH = Path(
    "patches/v7.1.3/0155-arm64-separate-late-CPU-runtime-evidence-ownership.patch"
)
PATCH_0092 = Path(
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
)
SERIES = Path("patches/series-a72-reject-gate-a41-runtime-evidence-owner")
PARENT_SERIES = Path("patches/series-a72-reject-gate-a41-six-row-fixture")
CANONICAL_SERIES = Path("patches/series")
FRAGMENT = Path("configs/gemini-a72-a41-runtime-evidence-owner.fragment")
MANIFEST = Path("kernel/manifest.json")
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-runtime-evidence-owner"
)

# BEGIN CENTRALIZED IDENTITY PINS / PLACEHOLDER BLOCK
# Keep every freeze-sensitive identity here. A not-yet-frozen value must be a
# visibly marked PLACEHOLDER_* string (or -1 for a count); normal validation
# rejects unresolved pins. All values below were resolved on 2026-08-05.
PLACEHOLDER_PREFIX = "PLACEHOLDER_"
PATCH_SHA256 = "bc52553d645d9d33c77e6b31e630be2243b8cb3984729422fc0ef0a7d5d45928"
SERIES_SHA256 = "04a20ca7ac3d979c8334ab419baed203d80c2d1c183b3a00cd44eb095293455f"
PATCHSET_SHA256 = "ff75286cf2372fac435f5e4aae284411df8b7b9db1b167258927a707da070477"
SOURCE_STATE_SHA256 = "c22cfc0af5aa41ca03ce1e13844866d559eac09a08718191b8857e50078f9092"
PARENT_SOURCE_STATE_SHA256 = (
    "2750c74f4c2c5c5ce0c07b90e57489fe6d412ec57fec7618b70a327623d5c058"
)
CONFIG_SHA256 = "7b875e34f11c7c6d007124aacc3e1e013acc41cc1628913a94cfddf0be8d7a74"
PARENT = "57d36fd59821b7de2fd81c938414e7f3c5a54229"
PARENT_TREE = "253625b12d09411997e1877a58ffd843f417ad7d"
SOURCE = "bcfb60248633bec2cdb6ab70540d5807d305c4e7"
SOURCE_TREE = "b23bf9e6332c865ef15606a41f11e75262e06fbf"
SOURCE_DIFF_SHA256 = "05da768b323e56d581f79f20943bfe7ffbc940c25145a90a2c9aea0ba80e049c"
PROFILE_COUNT = 61
SERIES_ENTRY_COUNT = 97
CANONICAL_ENTRY_COUNT = 144
# END CENTRALIZED IDENTITY PINS / PLACEHOLDER BLOCK

CHANGED_PATHS = (
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/late_cpu_profile.c",
    "arch/arm64/kernel/mt6797_psci.c",
    "arch/arm64/kernel/smp.c",
)

EXPECTED_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    str(FRAGMENT),
)

REQUIRED_EXPERIMENT_FILES = {
    "DESIGN.md",
    "README.md",
    "results/field-ownership.tsv",
    "results/implementation.tsv",
    "results/kernel-static-review-20260805.txt",
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
    "results/owner-oracle-validation-20260805.txt",
    "scripts/owner_oracle.py",
    "scripts/test_mutations.py",
    "scripts/test_owner_oracle.py",
    "scripts/validate.py",
}

REPOSITORY_CHECKS = (
    "experiment-safety",
    "manifest-profile",
    "configuration-identity",
    "all-profile-series-invariant",
    "selected-series-identity",
    "patch-provenance-and-inventory",
    "no-external-actions",
)

SOURCE_CHECKS = (
    "abi6-interface",
    "core-private-owner",
    "seal-order-and-publication",
    "profile-runtime-rejection",
    "profile-observation-rejection",
    "fixture-runtime-distinction",
    "prepare-validate-commit-vetoes",
    "boot-disable-vetoes",
    "source-identity-and-patch-application",
    "static-tooling",
)

REPOSITORY_MUTATIONS = (
    "repo-manifest-profile-missing",
    "repo-profile-series-substitution",
    "repo-fragment-policy-change",
    "repo-selected-series-duplicate",
    "repo-canonical-order-change",
    "repo-patch-source-change",
    "repo-patch-inventory-change",
    "repo-external-action-injection",
)

SOURCE_MUTATIONS = (
    "source-abi-downgrade",
    "source-seal-order-change",
    "source-late-seal-guard-polarity",
    "source-runtime-binding-completeness-polarity",
    "source-runtime-seal-state-polarity",
    "source-release-publication-loss",
    "source-acquire-consumption-loss",
    "source-private-record-export",
    "source-private-record-pointer-escape",
    "source-profile-runtime-rejection-loss",
    "source-profile-observation-rejection-loss",
    "source-observed-field-gap",
    "source-fixture-claims-runtime",
    "source-runtime-overlay-condition-change",
    "source-empty-runtime-blocker-loss",
    "source-profile-prepare-success",
    "source-profile-validator-success",
    "source-core-commit-blocker-loss",
    "source-core-commit-panic-loss",
    "source-cpu-boot-veto-loss",
    "source-cpu-disable-veto-loss",
)


class ValidationError(RuntimeError):
    """A repository or source contract was violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def unresolved_pins() -> tuple[str, ...]:
    values = {
        "PATCH_SHA256": PATCH_SHA256,
        "SERIES_SHA256": SERIES_SHA256,
        "PATCHSET_SHA256": PATCHSET_SHA256,
        "SOURCE_STATE_SHA256": SOURCE_STATE_SHA256,
        "PARENT_SOURCE_STATE_SHA256": PARENT_SOURCE_STATE_SHA256,
        "CONFIG_SHA256": CONFIG_SHA256,
        "PARENT": PARENT,
        "PARENT_TREE": PARENT_TREE,
        "SOURCE": SOURCE,
        "SOURCE_TREE": SOURCE_TREE,
        "SOURCE_DIFF_SHA256": SOURCE_DIFF_SHA256,
        "PROFILE_COUNT": PROFILE_COUNT,
        "SERIES_ENTRY_COUNT": SERIES_ENTRY_COUNT,
        "CANONICAL_ENTRY_COUNT": CANONICAL_ENTRY_COUNT,
    }
    return tuple(
        name
        for name, value in values.items()
        if (isinstance(value, str) and value.startswith(PLACEHOLDER_PREFIX))
        or (isinstance(value, int) and value < 0)
    )


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


def safe_relative_path(value: str, scope: str) -> Path:
    path = Path(value)
    require(value and not path.is_absolute(), f"{scope}: unsafe path {value!r}")
    require(
        not any(part in ("", ".", "..") for part in path.parts),
        f"{scope}: unsafe path {value!r}",
    )
    require(
        not any(character.isspace() for character in value),
        f"{scope}: whitespace in path {value!r}",
    )
    return path


def patch_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^diff --git a/(\S+) b/(\S+)$", text, re.MULTILINE))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        require(match.group(1) == match.group(2), "patch rename is not permitted")
        path = match.group(1)
        require(path not in result, f"duplicate patch section {path}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[path] = text[match.start() : end]
    return result


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def patch_postimage(section: str) -> str:
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


def braced_block(text: str, anchor: str) -> str:
    start = text.find(anchor)
    require(start >= 0, f"missing block anchor {anchor!r}")
    brace = text.find("{", start + len(anchor))
    require(brace >= 0, f"missing block body after {anchor!r}")
    depth = 0
    for cursor in range(brace, len(text)):
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
            if depth == 0:
                return text[start : cursor + 1]
    raise ValidationError(f"unterminated block after {anchor!r}")


def tokens(text: str, expected: Iterable[str], scope: str) -> None:
    for token in expected:
        require(token in text, f"{scope}: missing {token!r}")


def ordered(text: str, expected: Sequence[str], scope: str) -> None:
    cursor = -1
    for token in expected:
        position = text.find(token, cursor + 1)
        require(position >= 0, f"{scope}: missing {token!r}")
        require(position > cursor, f"{scope}: ordering changed at {token!r}")
        cursor = position


def validate_all_profile_series(
    repo: Path, manifest: dict, canonical: Sequence[str]
) -> None:
    fallback = manifest.get("patch_series")
    require(len(canonical) == len(set(canonical)), "canonical series has duplicates")
    require(
        len(canonical) == CANONICAL_ENTRY_COUNT,
        "canonical series entry count changed",
    )
    for entry in canonical:
        relative = safe_relative_path(entry, "canonical series")
        target = repo / CANONICAL_SERIES.parent / relative
        require(
            target.is_file() and not target.is_symlink(),
            f"canonical patch is missing or unsafe: {entry}",
        )
    for name, profile in manifest["config"]["profiles"].items():
        series_name = profile.get("patch_series", fallback)
        require(isinstance(series_name, str), f"profile {name}: series is missing")
        relative = safe_relative_path(series_name, f"profile {name}")
        require(relative.parts[0] == "patches", f"profile {name}: series left patches/")
        series_path = repo / relative
        require(
            series_path.is_file() and not series_path.is_symlink(),
            f"profile {name}: series is missing or unsafe",
        )
        entries = series_entries(series_path.read_text())
        require(entries, f"profile {name}: series is empty")
        require(
            len(entries) == len(set(entries)),
            f"profile {name}: series contains duplicates",
        )
        require(
            is_subsequence(entries, canonical),
            f"profile {name}: series is not a canonical-order subsequence",
        )
        for entry in entries:
            patch = series_path.parent / safe_relative_path(entry, f"profile {name}")
            require(
                patch.is_file() and not patch.is_symlink(),
                f"profile {name}: patch is missing or unsafe: {entry}",
            )


def validate_experiment_safety(repo: Path) -> None:
    root = repo / EXPERIMENT
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
        if "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    require(
        REQUIRED_EXPERIMENT_FILES <= actual,
        "required experiment file inventory is incomplete",
    )
    external_commands = tuple(
        word
        for word in (
            "cu" + "rl",
            "wg" + "et",
            "s" + "sh",
            "sc" + "p",
            "rsy" + "nc",
            "nc" + "at",
            "net" + "cat",
            "so" + "cat",
            "build" + "-kernel",
            "dev" + "-vm",
            "shut" + "down",
        )
    )
    external_pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?:"
        + "|".join(map(re.escape, external_commands))
        + r")(?![A-Za-z0-9_])"
    )
    for relative in sorted(actual):
        path = root / relative
        require(
            path.is_file() and not path.is_symlink(),
            f"experiment path is not a regular file: {relative}",
        )
        text = path.read_text()
        require(text.endswith("\n"), f"experiment file lacks final newline: {relative}")
        require(
            all(line == line.rstrip() for line in text.splitlines()),
            f"experiment file has trailing whitespace: {relative}",
        )
        require(
            ("/" + "Users/") not in text,
            f"experiment file exposes a personal host path: {relative}",
        )
        require(
            ("arti" + "facts/") not in text,
            f"experiment file refers to private artifacts: {relative}",
        )
        if relative.startswith("scripts/"):
            require(
                external_pattern.search(text) is None,
                f"experiment script contains an external action: {relative}",
            )
            validate_script_actions(relative, text)


def validate_script_actions(relative: str, text: str) -> None:
    """Allow only the validator's fixed local Git and kernel-tool subprocesses."""

    tree = ast.parse(text, filename=relative)
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    forbidden_imports = {
        "ftplib",
        "http",
        "paramiko",
        "requests",
        "smtplib",
        "socket",
        "telnetlib",
        "urllib",
    }
    subprocess_contexts: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            require(
                not roots.intersection(forbidden_imports),
                f"experiment script imports an external-action module: {relative}",
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            require(
                node.module.split(".", 1)[0] not in forbidden_imports,
                f"experiment script imports an external-action module: {relative}",
            )
        if not isinstance(node, ast.Call):
            continue
        require(
            not any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            ),
            f"experiment script enables a command shell: {relative}",
        )
        if isinstance(node.func, ast.Name):
            require(
                node.func.id not in {"eval", "exec", "__import__"},
                f"experiment script uses dynamic execution: {relative}",
            )
        if not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            continue
        require(
            node.func.attr == "run",
            f"experiment script uses an unapproved subprocess API: {relative}",
        )
        parent = parents.get(node)
        while parent is not None and not isinstance(
            parent, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            parent = parents.get(parent)
        subprocess_contexts.append(parent.name if parent is not None else "<module>")

    expected = (
        ["run_git"] + ["validate_source_application"] * 4
        if relative == "scripts/validate.py"
        else []
    )
    require(
        sorted(subprocess_contexts) == sorted(expected),
        f"experiment script subprocess inventory changed: {relative}",
    )


def validate_patch_contract(repo: Path, *, pin_hashes: bool) -> None:
    path = repo / PATCH
    patch = path.read_text()
    if pin_hashes:
        require(file_sha256(path) == PATCH_SHA256, "patch identity changed")
    source = re.match(r"From ([0-9a-f]{40}) ", patch)
    require(source is not None and source.group(1) == SOURCE, "patch source changed")
    metadata = patch.split("\n---\n", 1)[0]
    tokens(
        metadata,
        (
            "From: Gemini Mainline Project <noreply@invalid>",
            "Subject: [PATCH] arm64: separate late-CPU runtime evidence ownership",
            "This experiment-only change has no certifying sign-off and is not\n"
            "submission-ready.",
        ),
        "patch metadata",
    )
    require("Signed-off-by:" not in patch, "synthetic patch gained a sign-off")
    sections = patch_sections(patch)
    require(set(sections) == set(CHANGED_PATHS), "patch changed-path set changed")
    require(len(sections) == len(CHANGED_PATHS), "patch section count changed")

    additions = added_lines(patch)
    tokens(
        additions,
        (
            "#define ARM64_LATE_CPU_PLAN_ABI\t\t6",
            "void __init arm64_seal_late_cpu_runtime_evidence(void)",
            "arm64_seal_late_cpu_runtime_evidence();",
            '"mt6797-a53-a72-a41-v6"',
        ),
        "patch additions",
    )
    for forbidden in (
        "cpu_psci_ops.cpu_boot(cpu)",
        "ARM64_LATE_CPU_PROFILE_COMMITTED);",
        "ARM64_LATE_CPU_PROFILE_READY);",
        "plan->identity[0] =",
    ):
        require(forbidden not in additions, f"patch adds forbidden path {forbidden}")
    smp_postimage = patch_postimage(sections["arch/arm64/kernel/smp.c"])
    require(
        smp_postimage.count("arm64_seal_late_cpu_runtime_evidence();") == 1,
        "patch does not add one attributable architecture seal point",
    )


def validate_repository(
    repo: Path, *, pin_hashes: bool = True
) -> list[str]:
    repo = repo.resolve()
    if pin_hashes:
        require(not unresolved_pins(), f"unresolved identity pins: {unresolved_pins()}")
    validate_experiment_safety(repo)
    manifest = json.loads((repo / MANIFEST).read_text())
    profiles = manifest["config"]["profiles"]
    require(len(profiles) == PROFILE_COUNT, "manifest profile count changed")
    require(PROFILE in profiles, "runtime-evidence-owner profile is missing")
    profile = profiles[PROFILE]
    require(profile.get("base") == "defconfig", "profile base changed")
    require(profile.get("patch_series") == str(SERIES), "profile series changed")
    require(
        tuple(profile.get("fragments", ())) == EXPECTED_FRAGMENTS,
        "profile fragment sequence changed",
    )
    for name, candidate in profiles.items():
        if name == PROFILE:
            continue
        require(
            candidate.get("patch_series") != str(SERIES),
            f"runtime-owner series leaked into profile {name}",
        )
        require(
            str(FRAGMENT) not in candidate.get("fragments", ()),
            f"runtime-owner fragment leaked into profile {name}",
        )

    fragment_assignments = [
        line.strip()
        for line in (repo / FRAGMENT).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        fragment_assignments
        == [
            "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
            "CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE=y",
            'CONFIG_LOCALVERSION="-gemini-a41-owner-blocked"',
        ],
        "runtime-owner fragment gained an unreviewed setting",
    )
    require(
        "maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(),
        "inherited maxcpus=8 changed",
    )
    if pin_hashes:
        require(config_hash(repo, profile) == CONFIG_SHA256, "configuration identity changed")

    selected = series_entries((repo / SERIES).read_text())
    parent = series_entries((repo / PARENT_SERIES).read_text())
    canonical = series_entries((repo / CANONICAL_SERIES).read_text())
    validate_all_profile_series(repo, manifest, canonical)
    require(len(selected) == SERIES_ENTRY_COUNT, "selected series entry count changed")
    require(len(selected) == len(set(selected)), "selected series contains duplicates")
    require(selected[:-1] == parent, "selected series is not the exact parent plus ABI 6")
    require(selected[-1] == str(PATCH.relative_to("patches")), "selected series tail changed")
    require(is_subsequence(selected, canonical), "selected series lost canonical order")
    for forbidden in ("0093-", "a72-active", "cpu8-one-way"):
        require(
            not any(forbidden in entry for entry in selected),
            f"selected series contains active path {forbidden}",
        )
    if pin_hashes:
        require(file_sha256(repo / SERIES) == SERIES_SHA256, "selected series hash changed")
        require(patchset_hash(repo, SERIES) == PATCHSET_SHA256, "patchset identity changed")
        require(
            source_state_hash(repo, SERIES) == SOURCE_STATE_SHA256,
            "source-state identity changed",
        )
        require(
            source_state_hash(repo, PARENT_SERIES) == PARENT_SOURCE_STATE_SHA256,
            "parent source-state identity changed",
        )
    validate_patch_contract(repo, pin_hashes=pin_hashes)
    return list(REPOSITORY_CHECKS)


def validate_source_files(source_root: Path, *, repo: Path | None = None) -> None:
    source_root = source_root.resolve()
    source = {path: (source_root / path).read_text() for path in CHANGED_PATHS}
    header = source["arch/arm64/include/asm/late_cpu_profile.h"]
    core = source["arch/arm64/kernel/late_cpu_profile.c"]
    platform = source["arch/arm64/kernel/mt6797_psci.c"]
    smp = source["arch/arm64/kernel/smp.c"]

    tokens(
        header,
        (
            "#define ARM64_LATE_CPU_PLAN_ABI\t\t6",
            "Core-sealed runtime observations or an explicit profile fixture.",
            "Expected-only production input or an explicit FIXTURE; never RUNTIME.",
            "void __init arm64_seal_late_cpu_runtime_evidence(void);",
            "static inline void __init arm64_seal_late_cpu_runtime_evidence(void)",
        ),
        "ABI 6 header",
    )
    require(
        "extern struct arm64_late_cpu_evidence late_runtime_evidence" not in header,
        "private runtime record leaked through the header",
    )

    normalized_core = re.sub(r"\s+", " ", core)
    tokens(
        normalized_core,
        (
            "enum late_runtime_evidence_state { LATE_RUNTIME_EVIDENCE_OPEN, "
            "LATE_RUNTIME_EVIDENCE_SEALED_EMPTY, "
            "LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME, LATE_RUNTIME_EVIDENCE_FAULT, };",
            "static struct arm64_late_cpu_evidence late_runtime_evidence __initdata = "
            "{ .abi = ARM64_LATE_CPU_PLAN_ABI, };",
            "static u32 late_runtime_evidence_state __initdata;",
        ),
        "private runtime owner",
    )
    for other in (header, platform, smp):
        require(
            "late_runtime_evidence." not in other,
            "private runtime record is referenced outside its core owner",
        )

    seal = function(core, "arm64_seal_late_cpu_runtime_evidence")
    normalized_seal = re.sub(r"\s+", " ", seal)
    tokens(
        seal,
        (
            "READ_ONCE(late_runtime_evidence_state)",
            "state != LATE_RUNTIME_EVIDENCE_OPEN",
            "system_capabilities_finalized()",
            "cpus_have_cap(ARM64_ALWAYS_SYSTEM)",
            "late_runtime_evidence.abi != ARM64_LATE_CPU_PLAN_ABI",
            "late_runtime_evidence.binding.origin !=\n\t\t     ARM64_LATE_CPU_BINDING_NONE",
            "late_runtime_evidence.binding.origin !=\n\t\t     ARM64_LATE_CPU_BINDING_RUNTIME",
            "late_profile_runtime_binding_complete(&late_runtime_evidence.binding)",
            "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
            "LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME",
            "LATE_RUNTIME_EVIDENCE_SEALED_EMPTY",
            "smp_store_release(&late_runtime_evidence_state, state);",
        ),
        "runtime seal",
    )
    tokens(
        normalized_seal,
        (
            "if (state != LATE_RUNTIME_EVIDENCE_OPEN || "
            "system_capabilities_finalized() || "
            "cpus_have_cap(ARM64_ALWAYS_SYSTEM))",
            "late_runtime_evidence.binding.origin == "
            "ARM64_LATE_CPU_BINDING_RUNTIME && "
            "!late_profile_runtime_binding_complete(&late_runtime_evidence.binding)",
            "state = late_runtime_evidence.binding.origin == "
            "ARM64_LATE_CPU_BINDING_RUNTIME ? "
            "LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME : "
            "LATE_RUNTIME_EVIDENCE_SEALED_EMPTY;",
        ),
        "runtime seal polarity",
    )
    require(seal.count("smp_store_release(") == 3, "seal release-publication count changed")
    for forbidden in ("late_profile.prepare", "profile->", ".prepare("):
        require(forbidden not in seal, f"seal invokes profile-owned code: {forbidden}")
    require(
        re.search(r"late_runtime_evidence\.binding\.origin\s*=(?!=)", core) is None,
        "ABI 6 unexpectedly contains a runtime binding producer",
    )
    require(
        re.search(r"late_runtime_evidence\.observed_target_[a-z]+\[[^]]+\]\s*=(?!=)", core)
        is None,
        "ABI 6 unexpectedly contains a target observation producer",
    )
    require(
        re.search(r"\breturn\s+&late_runtime_evidence\b", core) is None,
        "private runtime record escaped through a pointer",
    )
    require(
        re.search(
            r"\bmem(?:cpy|move|set)\s*\(\s*&late_runtime_evidence(?:\b|\.)",
            core,
        )
        is None,
        "private runtime record gained a bulk writer",
    )

    empty = function(core, "late_profile_runtime_fields_empty")
    tokens(
        empty,
        (
            "late_profile_binding_empty(&evidence->binding)",
            "late_profile_identity_empty(evidence->evidence_identity)",
            "evidence->observed_target_mpidr[target]",
            "evidence->observed_target_midr[target]",
            "evidence->observed_target_revidr[target]",
            "memchr_inv(&evidence->target_cap[target]",
            "memchr_inv(&evidence->target_policy[target]",
            "memchr_inv(&evidence->system_cap",
        ),
        "profile observation rejection",
    )
    apply_runtime = function(core, "late_profile_apply_runtime_evidence")
    tokens(
        apply_runtime,
        (
            "evidence->binding = late_runtime_evidence.binding;",
            "late_runtime_evidence.evidence_identity",
            "late_runtime_evidence.observed_target_mpidr[target]",
            "late_runtime_evidence.observed_target_midr[target]",
            "late_runtime_evidence.observed_target_revidr[target]",
            "late_runtime_evidence.target_cap[target]",
            "late_runtime_evidence.target_policy[target]",
            "late_runtime_evidence.system_cap",
            "late_runtime_evidence.blocker_mask",
        ),
        "core runtime overlay",
    )
    for forbidden in (
        "expected_target_",
        "source_parent_identity",
        "config_input_identity",
        "target_cpu",
    ):
        require(forbidden not in apply_runtime, f"runtime overlay owns {forbidden}")

    prepare = function(core, "arm64_prepare_late_cpu_profile")
    ordered(
        prepare,
        (
            "runtime_state = smp_load_acquire(&late_runtime_evidence_state);",
            "ret = late_profile.prepare(&profile_evidence, &late_profile_targets);",
            "if (profile_evidence.binding.origin ==\n\t    ARM64_LATE_CPU_BINDING_RUNTIME)",
            "if (profile_evidence.binding.origin != ARM64_LATE_CPU_BINDING_NONE &&",
            "draft.evidence = profile_evidence;",
            "if (profile_evidence.binding.origin == ARM64_LATE_CPU_BINDING_NONE) {",
            "if (!late_profile_runtime_fields_empty(&profile_evidence)) {",
            "if (runtime_state == LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME)",
            "late_profile_apply_runtime_evidence(&draft.evidence);",
            "draft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH;",
            "if (ret || plan_ret || effect_ret || validate_ret ||",
            "late_plan = draft;",
        ),
        "prepare ownership and veto order",
    )
    tokens(
        prepare,
        (
            "runtime_state != LATE_RUNTIME_EVIDENCE_SEALED_EMPTY",
            "runtime_state != LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME",
            '"runtime evidence was not sealed"',
            '"profile declared runtime evidence"',
            '"profile declared an invalid evidence origin"',
            '"profile supplied runtime observations"',
            "ARM64_LATE_CPU_BINDING_FIXTURE",
            "late_profile_runtime_binding_complete(&draft.evidence.binding)",
            "draft.evidence.blocker_mask",
        ),
        "prepare fail-closed contract",
    )
    none_block = braced_block(
        prepare,
        "if (profile_evidence.binding.origin == ARM64_LATE_CPU_BINDING_NONE)",
    )
    require(
        none_block.count("late_profile_apply_runtime_evidence(&draft.evidence);") == 1,
        "runtime overlay escaped the NONE-origin branch",
    )
    require(
        "late_profile.prepare(&late_runtime_evidence" not in core,
        "profile callback received the private runtime record",
    )

    smp_done = function(smp, "smp_cpus_done")
    ordered(
        smp_done,
        (
            "hyp_mode_check();",
            "arm64_seal_late_cpu_runtime_evidence();",
            "arm64_prepare_late_cpu_profile();",
            "setup_system_features();",
        ),
        "architecture seal placement",
    )
    require(
        smp_done.count("arm64_seal_late_cpu_runtime_evidence();") == 1,
        "architecture seal call count changed",
    )

    tokens(
        platform,
        (
            '"mt6797-a53-a72-a41-v6"',
            "0x09c1750da0e98f35",
            "0x673ef55cf6389158",
            "0xe301a82bbd675634",
            "0x2fe28427cc4d6118",
            "ARM64_LATE_CPU_BLOCK_COMMIT_PATH",
        ),
        "MT6797 ABI 6 profile",
    )
    fixture = function(platform, "mt6797_a72_populate_fixture")
    require(
        "evidence->binding.origin = ARM64_LATE_CPU_BINDING_FIXTURE;" in fixture,
        "fixture lost its explicit origin",
    )
    require(
        "ARM64_LATE_CPU_BINDING_RUNTIME" not in fixture,
        "fixture is presented as runtime evidence",
    )
    expected_only = function(platform, "mt6797_a72_evidence_is_expected_only")
    tokens(
        expected_only,
        (
            "mt6797_a72_binding_empty(&evidence->binding)",
            "evidence->observed_target_mpidr[i]",
            "evidence->observed_target_midr[i]",
            "evidence->observed_target_revidr[i]",
            "evidence->target_cap[i].valid",
            "mt6797_a72_target_policy_empty(&evidence->target_policy[i])",
            "mt6797_a72_identity_empty(evidence->evidence_identity)",
            "return !evidence->system_cap.valid;",
        ),
        "expected-only profile input",
    )
    profile_prepare = function(platform, "mt6797_a72_profile_prepare")
    tokens(
        profile_prepare,
        (
            "mt6797_a72_populate_fixture(evidence);",
            "ARM64_LATE_CPU_BLOCK_CONFIGURATION",
            "ARM64_LATE_CPU_BLOCK_TOPOLOGY",
            "return -EAGAIN;",
        ),
        "profile prepare veto",
    )
    require(
        "observed_target_" not in profile_prepare,
        "production prepare directly writes observations",
    )
    require(
        profile_prepare.rstrip().endswith("return -EAGAIN;\n}"),
        "profile prepare final veto changed",
    )
    validator = function(platform, "mt6797_a72_validate_cap_plan")
    tokens(
        validator,
        (
            "plan->identity[i]",
            "Source-only fixture/expected evidence never publishes an identity.",
            "return -EAGAIN;",
        ),
        "profile validation veto",
    )
    require(
        validator.rstrip().endswith("return -EAGAIN;\n}"),
        "profile validator final veto changed",
    )
    require(
        re.search(r"plan->identity\s*\[[^]]+\]\s*=(?!=)", platform) is None,
        "profile writes a plan identity",
    )

    commit = function(core, "arm64_commit_late_cpu_profile")
    tokens(
        commit,
        (
            'panic("late CPU profile reached capability commit out of order")',
            'panic("late CPU profile commit implementation is unavailable")',
        ),
        "core commit veto",
    )
    require(
        "ARM64_LATE_CPU_PROFILE_COMMITTED" not in commit,
        "ABI 6 publishes a committed state",
    )

    boot = function(platform, "mt6797_psci_cpu_boot")
    require("return -EAGAIN;" in boot, "CPU boot veto changed")
    require("cpu_psci_ops.cpu_boot" not in boot, "CPU boot delegates to live PSCI")
    disable = function(platform, "mt6797_psci_cpu_can_disable")
    require("return false;" in disable, "CPU disable veto changed")

    if repo is not None:
        patch = (repo.resolve() / PATCH).read_text()
        require(
            set(patch_sections(patch)) == set(CHANGED_PATHS),
            "source validation patch inventory changed",
        )


def run_git(root: Path, args: Sequence[str], *, binary: bool = False):
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=not binary,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    error = result.stderr.decode() if binary else result.stderr
    require(result.returncode == 0, f"git {args[0]} failed: {error.strip()}")
    return result.stdout


def validate_source_application(repo: Path, source_root: Path) -> None:
    repo = repo.resolve()
    source_root = source_root.resolve()
    require((source_root / ".git").exists(), "source root is not a Git repository")
    require(
        run_git(source_root, ["rev-parse", f"{PARENT}^{{tree}}"] ).strip()
        == PARENT_TREE,
        "source parent tree changed",
    )
    require(
        run_git(source_root, ["rev-parse", f"{SOURCE}^{{tree}}"] ).strip()
        == SOURCE_TREE,
        "source result tree changed",
    )
    require(
        run_git(source_root, ["rev-parse", f"{SOURCE}^"]).strip() == PARENT,
        "source commit parent changed",
    )
    require(
        run_git(source_root, ["rev-parse", "HEAD"]).strip() == SOURCE,
        "source checkout is not at the pinned commit",
    )
    require(
        not run_git(source_root, ["status", "--porcelain"]).strip(),
        "source checkout is not clean",
    )
    require(
        not run_git(source_root, ["diff", "--check", f"{PARENT}..{SOURCE}"]).strip(),
        "source diff has whitespace errors",
    )
    diff = run_git(source_root, ["diff", f"{PARENT}..{SOURCE}"], binary=True)
    require(sha256(diff) == SOURCE_DIFF_SHA256, "source diff identity changed")
    changed = run_git(source_root, ["diff", "--name-only", f"{PARENT}..{SOURCE}"])
    require(tuple(changed.splitlines()) == CHANGED_PATHS, "source changed-path set changed")

    for strict in (False, True):
        arguments = [
            str(source_root / "scripts/checkpatch.pl"),
            *( ["--strict"] if strict else [] ),
            "--no-tree",
            "--show-types",
            "--ignore=MISSING_SIGN_OFF",
            str((repo / PATCH).resolve()),
        ]
        check = subprocess.run(
            arguments,
            cwd=source_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        clean_summary = re.search(r"total: 0 errors, 0 warnings", check.stdout)
        strict_summary = not strict or "0 checks" in check.stdout
        require(
            check.returncode == 0 and clean_summary and strict_summary,
            f"{'strict ' if strict else ''}checkpatch failed",
        )

    include_paths = [
        path
        for path in CHANGED_PATHS
        if path.endswith(".c")
    ]
    checkincludes = subprocess.run(
        [str(source_root / "scripts/checkincludes.pl"), *include_paths],
        cwd=source_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        checkincludes.returncode == 0
        and "No duplicate includes found." in checkincludes.stdout,
        "duplicate-include check failed",
    )
    for script in (repo / EXPERIMENT / "scripts").glob("*.py"):
        compile(script.read_text(), str(script), "exec")

    patch = (repo / PATCH).read_text()
    sections = patch_sections(patch)
    with tempfile.TemporaryDirectory(prefix="gemini-a41-owner-apply-") as temporary:
        scratch = Path(temporary)
        for path, section in sections.items():
            index = re.search(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)", section, re.M)
            require(index is not None, f"{path}: patch index is missing")
            parent_blob = run_git(source_root, ["show", f"{PARENT}:{path}"], binary=True)
            parent_oid = run_git(source_root, ["rev-parse", f"{PARENT}:{path}"]).strip()
            require(parent_oid.startswith(index.group(1)), f"{path}: patch preimage changed")
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(parent_blob)
        command = ["git", "apply", "--whitespace=error-all", str((repo / PATCH).resolve())]
        check = subprocess.run(
            [*command[:2], "--check", *command[2:]],
            cwd=scratch,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(check.returncode == 0, f"patch application check failed: {check.stderr.strip()}")
        applied = subprocess.run(
            command,
            cwd=scratch,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(applied.returncode == 0, f"patch application failed: {applied.stderr.strip()}")
        for path in sections:
            expected = run_git(source_root, ["show", f"{SOURCE}:{path}"], binary=True)
            require((scratch / path).read_bytes() == expected, f"{path}: postimage differs")
        validate_source_files(scratch, repo=repo)


def default_repo() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", "--repo-root", dest="repo", type=Path, default=default_repo()
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="skip freeze-sensitive hash pins while scaffolding; structural checks remain",
    )
    args = parser.parse_args(argv)
    print("validation=a41-runtime-evidence-owner-offline")
    try:
        checks = validate_repository(args.repo, pin_hashes=not args.allow_placeholders)
        if args.allow_placeholders and unresolved_pins():
            validate_source_files(args.source_root, repo=args.repo)
            checks.extend(SOURCE_CHECKS[:-2])
        else:
            validate_source_application(args.repo, args.source_root)
            checks.extend(SOURCE_CHECKS)
    except (
        OSError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    for check in checks:
        print(f"PASS {check}")
    print(f"patch_sha256={PATCH_SHA256}")
    print(f"series_sha256={SERIES_SHA256}")
    print(f"patchset_sha256={PATCHSET_SHA256}")
    print(f"source_state_sha256={SOURCE_STATE_SHA256}")
    print(f"config_sha256={CONFIG_SHA256}")
    print("implementation_state=ABI6_OWNER_BOUNDARY_BLOCKED")
    print("runtime_producer=absent")
    print("a41_complete=no")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print(f"RESULT PASS {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
