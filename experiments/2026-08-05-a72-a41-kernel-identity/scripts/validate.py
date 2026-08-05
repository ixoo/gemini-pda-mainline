#!/usr/bin/env python3
"""Validate the fail-closed ABI-7 Gemini A41 kernel-identity boundary."""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

sys.dont_write_bytecode = True

EXPERIMENT = Path("experiments/2026-08-05-a72-a41-kernel-identity")
PATCH_BUILDID = Path(
    "patches/v7.1.3/0156-lib-buildid-add-an-exact-GNU-note-parser.patch"
)
PATCH_ARM64 = Path(
    "patches/v7.1.3/0157-arm64-bind-late-CPU-profile-to-kernel-identity.patch"
)
SERIES = Path("patches/series-a72-reject-gate-a41-kernel-identity")
PARENT_SERIES = Path("patches/series-a72-reject-gate-a41-runtime-evidence-owner")
CANONICAL_SERIES = Path("patches/series")
FRAGMENT = Path("configs/gemini-a72-a41-kernel-identity.fragment")
MANIFEST = Path("kernel/manifest.json")
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-kernel-identity"
)

PLACEHOLDER_PREFIX = "PLACEHOLDER_"
PATCH_BUILDID_SHA256 = "4bdf4f1d264ab3a7a1debaf4a731df9d7edcf6fa292ab72ab0eaabe9c72597b6"
PATCH_ARM64_SHA256 = "e184e3c9e04bc51a75001d8dfcdde87ff333dfdab235cf7780dc89f491561950"
PATCH_BUILDID_COMMIT = "15d862a4fc495505104d1732b3c97f0ad0aa867c"
PATCH_ARM64_COMMIT = "22942d1697a9506132165ff8bfd30c92d5a5fe1e"
PATCHSET_SHA256 = "b048363e27e86326bf0fdd24af2d739d69658929b3de7e147634ecf266d134e5"
SOURCE_STATE_SHA256 = "1bafbcc101bb2094216fb1d25e33045984f50bd4d49d3c48b5ec3283664abcf3"
SOURCE_DIFF_SHA256 = "90e8ad3c3f9be58ef8f089f72f935e6f54aaa2473ada1145eebdb67a79593239"

SOURCE_PARENT = "bcfb60248633bec2cdb6ab70540d5807d305c4e7"
SOURCE_PARENT_TREE = "b23bf9e6332c865ef15606a41f11e75262e06fbf"
PATCH_BUILDID_TREE = "b065acbe5785436ac9b89164e31f6e64bf668bb9"
PATCH_ARM64_TREE = "c9d028016968c6f5b0439be23e26e55a175b7cbf"
SERIES_SHA256 = "d81fba3214e53bf3f05f4fde64e43f70638e863d04e01355e396a5990f21289d"
CANONICAL_SERIES_SHA256 = (
    "c00c6a21b47fd8610a918d1a951e95ad7f19519a5eee874d05fd2ab4152aeb27"
)
CONFIG_SHA256 = "4dca4e50ab039fbc60593e86d20d02e74e257dc6b5bb1afa94b38be6295b5203"
FRAGMENT_SHA256 = "5d2c34e1480acfbdba5b456ecc9d52ed94996e70e1b079e1928c4d95ebff2edf"
PROFILE_COUNT = 62
SERIES_ENTRY_COUNT = 99
CANONICAL_ENTRY_COUNT = 146

BUILDID_PATHS = (
    "include/linux/buildid.h",
    "lib/Kconfig.debug",
    "lib/Makefile",
    "lib/buildid.c",
    "lib/buildid_test.c",
)
ARM64_PATHS = (
    "arch/arm64/Kconfig",
    "arch/arm64/Kconfig.platforms",
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/late_cpu_profile.c",
    "arch/arm64/kernel/mt6797_psci.c",
    "arch/arm64/kernel/smp.c",
)
CHANGED_PATHS = BUILDID_PATHS + ARM64_PATHS
NEW_PATHS = frozenset({"lib/buildid_test.c"})

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
    "results/identity-oracle-validation-20260805.txt",
    "results/kernel-static-review-20260805.txt",
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
    "scripts/oracle.py",
    "scripts/test_mutations.py",
    "scripts/test_oracle.py",
    "scripts/validate.py",
}

REPOSITORY_CHECKS = (
    "experiment-safety",
    "manifest-profile",
    "configuration-identity",
    "all-profile-series-invariant",
    "selected-series-identity",
    "two-patch-provenance-and-inventory",
    "no-external-actions",
)
SOURCE_CHECKS = (
    "abi7-interface-and-kconfig",
    "exact-buildid-helper",
    "exact-buildid-kunit-contract",
    "core-private-identity-owner",
    "of-record-topology-and-allowlist",
    "identity-hash-and-endian-contract",
    "running-producer-bounds-and-cmdline",
    "atomic-collection-lifecycle",
    "seal-publication-and-polarity",
    "profile-cross-binding-and-overlay",
    "profile-observation-and-fixture-separation",
    "architecture-hook-order",
    "retained-commit-boot-disable-vetoes",
    "source-identity-application-and-static-tools",
)

REPOSITORY_MUTATIONS = (
    ("repo-manifest-profile-missing", "manifest-profile"),
    ("repo-profile-series-substitution", "manifest-profile"),
    ("repo-fragment-fixture-enable", "configuration-identity"),
    ("repo-selected-series-duplicate", "all-profile-series-invariant"),
    ("repo-canonical-order-change", "all-profile-series-invariant"),
    ("repo-patch-source-change", "two-patch-provenance-and-inventory"),
    ("repo-patch-inventory-change", "two-patch-provenance-and-inventory"),
    ("repo-external-action-injection", "no-external-actions"),
)
SOURCE_MUTATIONS = (
    ("source-abi-downgrade", "abi7-interface-and-kconfig"),
    ("source-kconfig-producer-loss", "abi7-interface-and-kconfig"),
    ("source-buildid-duplicate-loss", "exact-buildid-helper"),
    ("source-buildid-bounds-loss", "exact-buildid-helper"),
    ("source-buildid-zero-loss", "exact-buildid-helper"),
    ("source-buildid-alias-staging-loss", "exact-buildid-helper"),
    ("source-buildid-failure-zero-loss", "exact-buildid-helper"),
    ("source-buildid-kunit-wiring-loss", "exact-buildid-kunit-contract"),
    ("source-private-owner-export", "core-private-identity-owner"),
    ("source-of-name-loss", "of-record-topology-and-allowlist"),
    ("source-of-dynamic-property-loss", "of-record-topology-and-allowlist"),
    ("source-record-identity-polarity", "identity-hash-and-endian-contract"),
    ("source-digest-endian-loss", "identity-hash-and-endian-contract"),
    ("source-ikconfig-bound-loss", "running-producer-bounds-and-cmdline"),
    ("source-exact-helper-loss", "running-producer-bounds-and-cmdline"),
    ("source-cmdline-equality-loss", "running-producer-bounds-and-cmdline"),
    ("source-global-staging-loss", "atomic-collection-lifecycle"),
    ("source-late-collect-guard-polarity", "atomic-collection-lifecycle"),
    ("source-sealed-empty-polarity", "seal-publication-and-polarity"),
    ("source-sealed-identity-promotion", "seal-publication-and-polarity"),
    ("source-release-loss", "seal-publication-and-polarity"),
    ("source-acquire-loss", "profile-cross-binding-and-overlay"),
    ("source-crossbind-profile-loss", "profile-cross-binding-and-overlay"),
    ("source-crossbind-config-loss", "profile-cross-binding-and-overlay"),
    ("source-crossbind-target-loss", "profile-cross-binding-and-overlay"),
    ("source-overlay-condition-change", "profile-cross-binding-and-overlay"),
    ("source-overlay-scope-broadened", "profile-cross-binding-and-overlay"),
    ("source-profile-observation-rejection-loss", "profile-observation-and-fixture-separation"),
    ("source-fixture-claims-runtime", "profile-observation-and-fixture-separation"),
    ("source-collect-order-change", "architecture-hook-order"),
    ("source-profile-prepare-success", "retained-commit-boot-disable-vetoes"),
    ("source-profile-validator-success", "retained-commit-boot-disable-vetoes"),
    ("source-core-commit-blocker-loss", "retained-commit-boot-disable-vetoes"),
    ("source-core-commit-panic-loss", "retained-commit-boot-disable-vetoes"),
    ("source-cpu-boot-veto-loss", "retained-commit-boot-disable-vetoes"),
    ("source-cpu-disable-veto-loss", "retained-commit-boot-disable-vetoes"),
)


class ValidationError(RuntimeError):
    def __init__(self, check: str, message: str):
        super().__init__(f"[{check}] {message}")
        self.check = check


_ACTIVE_CHECK = "unscoped"


@contextlib.contextmanager
def checking(name: str) -> Iterator[None]:
    global _ACTIVE_CHECK
    previous = _ACTIVE_CHECK
    _ACTIVE_CHECK = name
    try:
        yield
    finally:
        _ACTIVE_CHECK = previous


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(_ACTIVE_CHECK, message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def unresolved_pins() -> tuple[str, ...]:
    values = {
        "PATCH_BUILDID_SHA256": PATCH_BUILDID_SHA256,
        "PATCH_ARM64_SHA256": PATCH_ARM64_SHA256,
        "PATCH_BUILDID_COMMIT": PATCH_BUILDID_COMMIT,
        "PATCH_ARM64_COMMIT": PATCH_ARM64_COMMIT,
        "PATCHSET_SHA256": PATCHSET_SHA256,
        "SOURCE_STATE_SHA256": SOURCE_STATE_SHA256,
        "SOURCE_DIFF_SHA256": SOURCE_DIFF_SHA256,
        "SOURCE_PARENT": SOURCE_PARENT,
        "SOURCE_PARENT_TREE": SOURCE_PARENT_TREE,
        "PATCH_BUILDID_TREE": PATCH_BUILDID_TREE,
        "PATCH_ARM64_TREE": PATCH_ARM64_TREE,
        "SERIES_SHA256": SERIES_SHA256,
        "CANONICAL_SERIES_SHA256": CANONICAL_SERIES_SHA256,
        "CONFIG_SHA256": CONFIG_SHA256,
        "FRAGMENT_SHA256": FRAGMENT_SHA256,
        "PROFILE_COUNT": str(PROFILE_COUNT),
        "SERIES_ENTRY_COUNT": str(SERIES_ENTRY_COUNT),
        "CANONICAL_ENTRY_COUNT": str(CANONICAL_ENTRY_COUNT),
    }
    return tuple(name for name, value in values.items() if value.startswith(PLACEHOLDER_PREFIX))


def tokens(text: str, expected: Iterable[str], scope: str) -> None:
    for token in expected:
        require(token in text, f"{scope}: missing {token!r}")


def ordered(text: str, expected: Sequence[str], scope: str) -> None:
    cursor = -1
    for token in expected:
        position = text.find(token, cursor + 1)
        require(position >= 0, f"{scope}: missing ordered token {token!r}")
        require(position > cursor, f"{scope}: out-of-order token {token!r}")
        cursor = position


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


def safe_relative_path(value: str, scope: str) -> Path:
    path = Path(value)
    require(value != "" and not path.is_absolute(), f"{scope}: unsafe path")
    require(not any(part in ("", ".", "..") for part in path.parts), f"{scope}: traversal")
    require(not any(character.isspace() for character in value), f"{scope}: whitespace")
    return path


def patchset_hash(repo: Path, series: Path) -> str:
    path = repo / series
    lines = [f"{file_sha256(path)}  {series}"]
    for entry in series_entries(path.read_text()):
        lines.append(f"{file_sha256(path.parent / entry)}  {entry}")
    return sha256(("\n".join(lines) + "\n").encode())


def source_state_hash(repo: Path, series: Path) -> str:
    kernel = json.loads((repo / MANIFEST).read_text())["kernel"]
    material = f"{kernel['version']}\n{kernel['sha256']}\n{patchset_hash(repo, series)}\n"
    return sha256(material.encode())


def config_hash(repo: Path, profile_name: str, profile: dict) -> str:
    lines = [f"profile={profile_name}", f"base={profile['base']}"]
    for name in profile["fragments"]:
        lines.append(f"{file_sha256(repo / name)}  {name}")
    return sha256(("\n".join(lines) + "\n").encode())


def patch_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^diff --git a/(\S+) b/(\S+)$", text, re.M))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        require(match.group(1) == match.group(2), "patch path changes name")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        require(match.group(1) not in sections, "patch repeats a path")
        sections[match.group(1)] = text[match.start():end]
    return sections


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def function(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", text, re.S)
    require(match is not None, f"function {name} is missing")
    start = text.rfind("\n", 0, match.start()) + 1
    brace = text.find("{", match.start())
    depth = 0
    for position in range(brace, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                return text[start:position + 1]
    raise ValidationError(_ACTIVE_CHECK, f"function {name} is unterminated")


def validate_script_actions(relative: str, text: str) -> None:
    tree = ast.parse(text, filename=relative)
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    forbidden_imports = {"ftplib", "http", "paramiko", "requests", "smtplib", "socket", "telnetlib", "urllib"}
    contexts: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            require(not roots & forbidden_imports, f"{relative}: external import")
        elif isinstance(node, ast.ImportFrom) and node.module:
            require(node.module.split(".", 1)[0] not in forbidden_imports, f"{relative}: external import")
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            require(node.func.id not in {"eval", "exec", "__import__"}, f"{relative}: dynamic execution")
        require(
            not any(
                keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                for keyword in node.keywords
            ),
            f"{relative}: shell enabled",
        )
        if not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            continue
        require(node.func.attr == "run", f"{relative}: unapproved subprocess API")
        parent = parents.get(node)
        while parent is not None and not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parent = parents.get(parent)
        contexts.append(parent.name if parent is not None else "<module>")
    expected = ["run_git", "run_local_tool", "run_oracle"] if relative == "scripts/validate.py" else []
    require(sorted(contexts) == sorted(expected), f"{relative}: subprocess inventory changed")


def validate_experiment_safety(repo: Path) -> None:
    root = repo / EXPERIMENT
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if (path.is_file() or path.is_symlink())
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    require(actual == REQUIRED_EXPERIMENT_FILES, "experiment file inventory changed")
    external_commands = (
        "c" + "url",
        "w" + "get",
        "s" + "sh",
        "s" + "cp",
        "r" + "sync",
        "n" + "cat",
        "net" + "cat",
        "so" + "cat",
    )
    forbidden = re.compile(
        r"(?<![A-Za-z0-9_])(?:" + "|".join(external_commands) + r")(?![A-Za-z0-9_])"
    )
    for relative in sorted(actual):
        path = root / relative
        require(path.is_file() and not path.is_symlink(), f"unsafe experiment path: {relative}")
        text = path.read_text()
        require(text.endswith("\n"), f"{relative}: missing final newline")
        require(all(line == line.rstrip() for line in text.splitlines()), f"{relative}: trailing whitespace")
        private_home = "/" + "Users/"
        artifact_tree = "artifacts" + "/"
        require(private_home not in text and artifact_tree not in text, f"{relative}: private path")
        if relative.startswith("scripts/"):
            require(forbidden.search(text) is None, f"{relative}: external action command")


def validate_manifest(repo: Path) -> None:
    manifest = json.loads((repo / MANIFEST).read_text())
    profiles = manifest["config"]["profiles"]
    require(len(profiles) == PROFILE_COUNT, "manifest profile count changed")
    require(PROFILE in profiles, "kernel-identity profile is missing")
    profile = profiles[PROFILE]
    require(profile.get("base") == "defconfig", "profile base changed")
    require(profile.get("patch_series") == str(SERIES), "profile series changed")
    require(tuple(profile.get("fragments", ())) == EXPECTED_FRAGMENTS, "profile fragments changed")
    for name, candidate in profiles.items():
        if name == PROFILE:
            continue
        require(candidate.get("patch_series") != str(SERIES), f"series leaked into {name}")
        require(str(FRAGMENT) not in candidate.get("fragments", ()), f"fragment leaked into {name}")


def validate_configuration(repo: Path, *, pin_hashes: bool) -> None:
    manifest = json.loads((repo / MANIFEST).read_text())
    profile = manifest["config"]["profiles"][PROFILE]
    fragment = (repo / FRAGMENT).read_text()
    required_lines = (
        "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
        "# CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE is not set",
        'CONFIG_LOCALVERSION="-gemini-a41-identity-blocked"',
    )
    for line in required_lines:
        require(fragment.count(line) == 1, f"fragment policy changed: {line}")
    require("CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE=y" not in fragment, "fixture enabled")
    require("maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(), "maxcpus=8 changed")
    if pin_hashes:
        require(file_sha256(repo / FRAGMENT) == FRAGMENT_SHA256, "fragment identity changed")
        require(config_hash(repo, PROFILE, profile) == CONFIG_SHA256, "configuration identity changed")


def validate_all_profile_series(repo: Path) -> None:
    manifest = json.loads((repo / MANIFEST).read_text())
    canonical = series_entries((repo / CANONICAL_SERIES).read_text())
    require(len(canonical) == CANONICAL_ENTRY_COUNT, "canonical series count changed")
    require(len(canonical) == len(set(canonical)), "canonical series has duplicates")
    fallback = manifest.get("patch_series")
    for name, profile in manifest["config"]["profiles"].items():
        series_name = profile.get("patch_series", fallback)
        require(isinstance(series_name, str), f"{name}: series missing")
        relative = safe_relative_path(series_name, name)
        require(relative.parts[0] == "patches", f"{name}: series outside patches")
        path = repo / relative
        require(path.is_file() and not path.is_symlink(), f"{name}: unsafe series")
        entries = series_entries(path.read_text())
        require(entries and len(entries) == len(set(entries)), f"{name}: duplicate/empty series")
        require(is_subsequence(entries, canonical), f"{name}: not canonical subsequence")
        for entry in entries:
            patch = path.parent / safe_relative_path(entry, name)
            require(patch.is_file() and not patch.is_symlink(), f"{name}: missing patch {entry}")


def validate_selected_series(repo: Path, *, pin_hashes: bool) -> None:
    selected = series_entries((repo / SERIES).read_text())
    parent = series_entries((repo / PARENT_SERIES).read_text())
    canonical = series_entries((repo / CANONICAL_SERIES).read_text())
    tails = [str(PATCH_BUILDID.relative_to("patches")), str(PATCH_ARM64.relative_to("patches"))]
    require(len(selected) == SERIES_ENTRY_COUNT, "selected series count changed")
    require(selected[:-2] == parent and selected[-2:] == tails, "selected series is not exact parent plus ABI7")
    require(is_subsequence(selected, canonical), "selected series lost canonical order")
    for forbidden in ("0093-", "a72-active", "cpu8-one-way"):
        require(not any(forbidden in entry for entry in selected), f"selected series contains {forbidden}")
    if pin_hashes:
        require(file_sha256(repo / SERIES) == SERIES_SHA256, "selected series hash changed")
        require(file_sha256(repo / CANONICAL_SERIES) == CANONICAL_SERIES_SHA256, "canonical series hash changed")
        require(patchset_hash(repo, SERIES) == PATCHSET_SHA256, "patchset identity changed")
        require(source_state_hash(repo, SERIES) == SOURCE_STATE_SHA256, "source-state identity changed")


def validate_patch_contracts(repo: Path, *, pin_hashes: bool) -> None:
    contracts = (
        (PATCH_BUILDID, PATCH_BUILDID_COMMIT, PATCH_BUILDID_SHA256, set(BUILDID_PATHS), "lib/buildid: add an exact GNU note parser"),
        (PATCH_ARM64, PATCH_ARM64_COMMIT, PATCH_ARM64_SHA256, set(ARM64_PATHS), "arm64: bind late-CPU profile to kernel identity"),
    )
    for path, commit, digest, changed, subject in contracts:
        text = (repo / path).read_text()
        match = re.match(r"From ([0-9a-f]{40}) ", text)
        require(match is not None and match.group(1) == commit, f"{path.name}: source commit changed")
        tokens(text.split("\n---\n", 1)[0], (
            "From: Gemini Mainline Project <noreply@invalid>",
            f"Subject: [PATCH] {subject}",
            "This experiment-only change has no certifying sign-off and is not\nsubmission-ready.",
        ), f"{path.name} metadata")
        require("Signed-off-by:" not in text, f"{path.name}: synthetic signoff added")
        require(set(patch_sections(text)) == changed, f"{path.name}: path inventory changed")
        if pin_hashes:
            require(file_sha256(repo / path) == digest, f"{path.name}: hash changed")
    additions = added_lines((repo / PATCH_ARM64).read_text())
    for forbidden in ("cpu_psci_ops.cpu_boot(cpu)", "ARM64_LATE_CPU_PROFILE_COMMITTED);", "ARM64_LATE_CPU_PROFILE_READY);"):
        require(forbidden not in additions, f"arm64 patch adds forbidden path {forbidden}")


def validate_no_external_actions(repo: Path) -> None:
    for relative in ("scripts/validate.py", "scripts/test_mutations.py", "scripts/oracle.py", "scripts/test_oracle.py"):
        validate_script_actions(relative, (repo / EXPERIMENT / relative).read_text())


def validate_repository(repo: Path, *, pin_hashes: bool = True) -> list[str]:
    repo = repo.resolve()
    if pin_hashes:
        require(not unresolved_pins(), f"unresolved identity pins: {unresolved_pins()}")
    operations: tuple[tuple[str, Callable[[], None]], ...] = (
        ("experiment-safety", lambda: validate_experiment_safety(repo)),
        ("manifest-profile", lambda: validate_manifest(repo)),
        ("configuration-identity", lambda: validate_configuration(repo, pin_hashes=pin_hashes)),
        ("all-profile-series-invariant", lambda: validate_all_profile_series(repo)),
        ("selected-series-identity", lambda: validate_selected_series(repo, pin_hashes=pin_hashes)),
        ("two-patch-provenance-and-inventory", lambda: validate_patch_contracts(repo, pin_hashes=pin_hashes)),
        ("no-external-actions", lambda: validate_no_external_actions(repo)),
    )
    for name, operation in operations:
        with checking(name):
            operation()
    return list(REPOSITORY_CHECKS)


def validate_source_files(source_root: Path, *, repo: Path | None = None) -> None:
    source_root = source_root.resolve()
    source = {path: (source_root / path).read_text() for path in CHANGED_PATHS}
    header = source["arch/arm64/include/asm/late_cpu_profile.h"]
    core = source["arch/arm64/kernel/late_cpu_profile.c"]
    platform = source["arch/arm64/kernel/mt6797_psci.c"]
    smp = source["arch/arm64/kernel/smp.c"]
    buildid = source["lib/buildid.c"]
    buildid_test = source["lib/buildid_test.c"]

    with checking("abi7-interface-and-kconfig"):
        tokens(header, (
            "#define ARM64_LATE_CPU_PLAN_ABI\t\t7",
            "ARM64_LATE_CPU_BIND_EXPECTED_CONFIG_VALID",
            "ARM64_LATE_CPU_BIND_EXPECTED_BUILD_ID_VALID",
            "void __init arm64_collect_late_cpu_runtime_identity(void);",
        ), "ABI7 header")
        require("resolved_config_identity" not in header and "built_image_identity" not in header, "old binding names remain")
        kconfig = source["arch/arm64/Kconfig"]
        tokens(kconfig, ("config ARM64_LATE_CPU_RUNTIME_IDENTITY", "depends on ARM64_LATE_CPU_PROFILE && OF && CMDLINE_FORCE", "select CRYPTO_LIB_SHA256", "select IKCONFIG"), "arm64 Kconfig")
        tokens(source["arch/arm64/Kconfig.platforms"], ("select ARM64_LATE_CPU_PROFILE", "select ARM64_LATE_CPU_RUNTIME_IDENTITY"), "platform Kconfig")

    with checking("exact-buildid-helper"):
        helper = function(buildid, "build_id_parse_buf_exact")
        tokens(helper, (
            "expected_size > BUILD_ID_SIZE_MAX",
            "check_add_overflow(nhdr.n_namesz, 3U, &name_size)",
            "check_add_overflow(nhdr.n_descsz, 3U, &desc_size)",
            "check_add_overflow(note_size, name_size, &note_size)",
            "check_add_overflow(note_size, desc_size, &note_size)",
            "note_size > buf_size - offset",
            "nhdr.n_type == BUILD_ID",
            "nhdr.n_namesz == sizeof(note_name)",
            "found || nhdr.n_descsz != expected_size",
            "!memchr_inv(desc, 0, expected_size)",
            "memcpy(parsed, found, expected_size);",
            "memset(build_id, 0, BUILD_ID_SIZE_MAX);",
        ), "exact build-ID helper")
        require(helper.count("memset(build_id, 0, BUILD_ID_SIZE_MAX);") == 2, "failure/success zeroing changed")
        require(buildid.count("int build_id_parse_buf_exact(") == 1, "exact helper count changed")

    with checking("exact-buildid-kunit-contract"):
        tokens(source["include/linux/buildid.h"], ("int build_id_parse_buf_exact", "u32 buf_size, u32 expected_size);"), "build-ID header")
        tokens(source["lib/Kconfig.debug"], ("config BUILDID_KUNIT_TEST", "depends on KUNIT=y"), "KUnit Kconfig")
        require("obj-$(CONFIG_BUILDID_KUNIT_TEST) += buildid_test.o" in source["lib/Makefile"], "KUnit object is not wired")
        for case in (
            "buildid_test_valid_with_neighbors", "buildid_test_short_valid_zero_padded",
            "buildid_test_rejected_candidates", "buildid_test_truncated_notes",
            "buildid_test_u32_size_overflow", "buildid_test_unaligned_input",
            "buildid_test_invalid_arguments", "buildid_test_success_output_alias",
            "buildid_test_failure_output_alias",
        ):
            require(buildid_test.count(f"KUNIT_CASE({case})") == 1, f"KUnit case missing: {case}")

    with checking("core-private-identity-owner"):
        tokens(core, (
            "static struct arm64_late_cpu_evidence late_runtime_evidence __initdata",
            "static struct late_runtime_identity late_runtime_identity __initdata;",
            "static u32 late_runtime_identity_state __initdata;",
        ), "private identity owner")
        for other in (header, platform, smp):
            require("late_runtime_identity." not in other and "late_runtime_evidence." not in other, "private owner leaked")
        require(re.search(r"\breturn\s+&late_runtime_(?:identity|evidence)\b", core) is None, "private pointer escaped")

    with checking("of-record-topology-and-allowlist"):
        parser = function(core, "late_runtime_parse_expected_record")
        tokens(parser, (
            'of_find_node_by_path("/")', 'of_find_node_by_path("/chosen")',
            'of_find_node_by_path("/chosen/gemini-late-cpu-provenance")',
            "chosen != of_chosen", "node->parent != chosen", "OF_DYNAMIC", "OF_DETACHED", "OF_OVERLAY",
            "for_each_child_of_node_scoped(node, child)", "for_each_compatible_node_scoped",
            "of_property_check_flag(property, OF_DYNAMIC)", 'strncmp(property->name, "running-"',
            "seen & BIT(index)", "seen != GENMASK(LATE_PROP_COUNT - 1, 0)",
            "late_runtime_hash_record(&record, record_digest)",
        ), "OF expected record parser")
        properties = (
            '"name"', '"compatible"', '"schema-version"', '"profile-id"', '"target-cpus"', '"target-mpidrs"',
            '"expected-ikconfig-identity"', '"expected-gnu-build-id-identity"', '"expected-cmdline-identity"',
            '"upstream-source-sha256"', '"patch-series-sha256"', '"config-inputs-sha256"',
            '"resolved-config-sha256"', '"package-image-sha256"', '"build-provenance-sha256"', '"record-identity"',
        )
        for prop in properties:
            require(core.count(prop) == 1, f"property table changed: {prop}")

    with checking("identity-hash-and-endian-contract"):
        tokens(core, (
            '"gemini-a41-runtime-binding-v1"', '"record"', '"ikconfig"', '"gnu-build-id"', '"cmdline"',
            "get_unaligned_be64(digest + i * sizeof(u64))", "cpu_to_be16(value)", "cpu_to_be32(value)", "cpu_to_be64(value)",
            "if (memcmp(record_digest, record.record_identity", "for (i = 0; i < LATE_RECORD_DIGEST_COUNT; i++)",
        ), "hash and endian contract")
        require("get_unaligned_le64(digest" not in core, "digest words became little-endian")

    with checking("running-producer-bounds-and-cmdline"):
        producer = function(core, "late_runtime_produce_running_identity")
        tokens(producer, (
            "kernel_config_data", "kernel_config_data_end", "LATE_RUNTIME_IKCONFIG_MAX",
            "__start_notes", "__stop_notes", "LATE_RUNTIME_NOTES_MAX",
            "build_id_parse_buf_exact(notes, build_id, notes_size", "BUILD_ID_SIZE_MAX",
            "saved_command_line_len != sizeof(CONFIG_CMDLINE) - 1",
            "memcmp(saved_command_line, CONFIG_CMDLINE, sizeof(CONFIG_CMDLINE))",
            "memzero_explicit(build_id, sizeof(build_id))",
        ), "running identity producer")

    with checking("atomic-collection-lifecycle"):
        collect = function(core, "arm64_collect_late_cpu_runtime_identity")
        tokens(collect, (
            "struct late_runtime_identity staged = {};", "LATE_RUNTIME_IDENTITY_UNCOLLECTED",
            "\n\t    system_capabilities_finalized() ||", "cpus_have_cap(ARM64_ALWAYS_SYSTEM)",
            "late_runtime_parse_expected_record(&staged)", "late_runtime_produce_running_identity(&staged)",
            "late_runtime_identity = staged;", "LATE_RUNTIME_IDENTITY_VERIFIED",
        ), "atomic collector")
        require(collect.count("late_runtime_identity = staged;") == 1, "collector publication count changed")
        require("late_runtime_parse_expected_record(&late_runtime_identity)" not in collect, "collector writes global during parse")

    with checking("seal-publication-and-polarity"):
        seal = function(core, "arm64_seal_late_cpu_runtime_evidence")
        tokens(seal, (
            "identity_state == LATE_RUNTIME_IDENTITY_UNCOLLECTED", "identity_state == LATE_RUNTIME_IDENTITY_FAILED",
            "!memchr_inv(&late_runtime_identity, 0", "state = LATE_RUNTIME_EVIDENCE_SEALED_EMPTY;",
            "identity_state == LATE_RUNTIME_IDENTITY_VERIFIED", "late_runtime_identity_complete(&late_runtime_identity)",
            "late_runtime_evidence.binding = late_runtime_identity.binding;", "state = LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY;",
            "smp_store_release(&late_runtime_evidence_state, state);",
        ), "identity seal")
        require("LATE_RUNTIME_EVIDENCE_SEALED_RUNTIME" not in seal, "seal can publish runtime")

    with checking("profile-cross-binding-and-overlay"):
        cross = function(core, "late_profile_identity_cross_bound")
        tokens(cross, (
            "strcmp(late_runtime_identity.profile_id, profile_id)",
            "\n\t    memcmp(late_runtime_identity.config_input_identity", "evidence->config_input_identity",
            "late_runtime_identity.target_cpu[target]", "evidence->target_cpu[target]",
            "late_runtime_identity.target_mpidr[target]", "evidence->expected_target_mpidr[target]",
            "!cpumask_test_cpu(late_runtime_identity.target_cpu[target]",
            "registered_targets))", "late_profile_runtime_binding_complete(&late_runtime_evidence.binding)",
        ), "profile cross-binding")
        prepare = function(core, "arm64_prepare_late_cpu_profile")
        ordered(prepare, (
            "runtime_state = smp_load_acquire(&late_runtime_evidence_state);",
            "ret = late_profile.prepare(&profile_evidence, &late_profile_targets);",
            "if (runtime_state == LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY)",
            "late_profile_identity_cross_bound",
            "draft.evidence.binding = late_runtime_evidence.binding;",
            "~ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
        ), "binding-only overlay")

    with checking("profile-observation-and-fixture-separation"):
        empty = function(core, "late_profile_runtime_fields_empty")
        tokens(empty, ("late_profile_binding_empty", "evidence_identity", "observed_target_mpidr", "observed_target_midr", "observed_target_revidr", "target_cap", "target_policy", "system_cap"), "profile observation rejection")
        prepare = function(core, "arm64_prepare_late_cpu_profile")
        tokens(prepare, (
            '"profile declared runtime evidence"', '"profile supplied runtime observations"',
            "if (!late_profile_runtime_fields_empty(&profile_evidence))", "ARM64_LATE_CPU_BINDING_FIXTURE",
        ), "profile origin rejection")
        fixture = function(platform, "mt6797_a72_populate_fixture")
        require("ARM64_LATE_CPU_BINDING_FIXTURE" in fixture and "ARM64_LATE_CPU_BINDING_RUNTIME" not in fixture, "fixture claims runtime")

    with checking("architecture-hook-order"):
        done = function(smp, "smp_cpus_done")
        ordered(done, ("hyp_mode_check();", "arm64_collect_late_cpu_runtime_identity();", "arm64_seal_late_cpu_runtime_evidence();", "arm64_prepare_late_cpu_profile();", "setup_system_features();"), "smp hook order")
        require(done.count("arm64_collect_late_cpu_runtime_identity();") == 1, "collector call count changed")

    with checking("retained-commit-boot-disable-vetoes"):
        core_prepare = function(core, "arm64_prepare_late_cpu_profile")
        ordered(core_prepare, (
            "~ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
            "draft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH;",
        ), "retained commit blocker")
        profile_prepare = function(platform, "mt6797_a72_profile_prepare")
        require(profile_prepare.rstrip().endswith("return -EAGAIN;\n}"), "profile prepare veto changed")
        validator = function(platform, "mt6797_a72_validate_cap_plan")
        require(validator.rstrip().endswith("return -EAGAIN;\n}"), "profile validator veto changed")
        commit = function(core, "arm64_commit_late_cpu_profile")
        tokens(commit, ('panic("late CPU profile reached capability commit out of order")', 'panic("late CPU profile commit implementation is unavailable")'), "commit veto")
        require("ARM64_LATE_CPU_PROFILE_COMMITTED" not in commit, "commit state became reachable")
        boot = function(platform, "mt6797_psci_cpu_boot")
        require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot, "CPU boot veto changed")
        disable = function(platform, "mt6797_psci_cpu_can_disable")
        require("return false;" in disable, "CPU disable veto changed")
        words = tuple(f"0x{CONFIG_SHA256[i:i + 16]}" for i in range(0, 64, 16))
        for word in words:
            require(word in platform, f"config-input word changed: {word}")

    if repo is not None:
        with checking("source-identity-application-and-static-tools"):
            buildid_patch = (repo.resolve() / PATCH_BUILDID).read_text()
            arm64_patch = (repo.resolve() / PATCH_ARM64).read_text()
            require(set(patch_sections(buildid_patch)) == set(BUILDID_PATHS), "build-ID patch inventory differs")
            require(set(patch_sections(arm64_patch)) == set(ARM64_PATHS), "arm64 patch inventory differs")


def run_git(root: Path, args: Sequence[str], *, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=root, text=not binary, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    error = result.stderr.decode() if binary else result.stderr
    require(result.returncode == 0, f"git {args[0]} failed: {error.strip()}")
    return result.stdout


def run_local_tool(arguments: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(arguments), cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def run_oracle(test: Path, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(test)], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def validate_source_application(repo: Path, source_root: Path) -> None:
    repo = repo.resolve()
    source_root = source_root.resolve()
    require((source_root / ".git").exists(), "source root is not a Git repository")
    identities = (
        (SOURCE_PARENT, SOURCE_PARENT_TREE),
        (PATCH_BUILDID_COMMIT, PATCH_BUILDID_TREE),
        (PATCH_ARM64_COMMIT, PATCH_ARM64_TREE),
    )
    for commit, tree in identities:
        require(run_git(source_root, ["rev-parse", f"{commit}^{{tree}}"] ).strip() == tree, f"source tree changed for {commit}")
    require(run_git(source_root, ["rev-parse", f"{PATCH_BUILDID_COMMIT}^"]).strip() == SOURCE_PARENT, "0156 parent changed")
    require(run_git(source_root, ["rev-parse", f"{PATCH_ARM64_COMMIT}^"]).strip() == PATCH_BUILDID_COMMIT, "0157 parent changed")
    require(run_git(source_root, ["rev-parse", "HEAD"]).strip() == PATCH_ARM64_COMMIT, "source checkout is not final commit")
    require(not run_git(source_root, ["status", "--porcelain"]).strip(), "source checkout is dirty")
    require(not run_git(source_root, ["diff", "--check", f"{SOURCE_PARENT}..{PATCH_ARM64_COMMIT}"]).strip(), "source diff whitespace errors")
    diff = run_git(source_root, ["diff", "--binary", f"{SOURCE_PARENT}..{PATCH_ARM64_COMMIT}"], binary=True)
    require(sha256(diff) == SOURCE_DIFF_SHA256, "source diff identity changed")
    changed = set(run_git(source_root, ["diff", "--name-only", f"{SOURCE_PARENT}..{PATCH_ARM64_COMMIT}"]).splitlines())
    require(changed == set(CHANGED_PATHS), "source changed-path set changed")
    parent_buildid = run_git(source_root, ["show", f"{SOURCE_PARENT}:lib/buildid.c"])
    helper_buildid = run_git(source_root, ["show", f"{PATCH_BUILDID_COMMIT}:lib/buildid.c"])
    require(
        function(parent_buildid, "build_id_parse_buf")
        == function(helper_buildid, "build_id_parse_buf"),
        "legacy build_id_parse_buf changed",
    )

    with tempfile.TemporaryDirectory(prefix="gemini-a41-identity-apply-") as temporary:
        scratch = Path(temporary)
        for path in CHANGED_PATHS:
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if path in NEW_PATHS:
                probe = run_local_tool(["git", "cat-file", "-e", f"{SOURCE_PARENT}:{path}"], source_root)
                require(probe.returncode != 0, f"new path existed in parent: {path}")
                continue
            target.write_bytes(run_git(source_root, ["show", f"{SOURCE_PARENT}:{path}"], binary=True))
        for patch, commit, paths in (
            (PATCH_BUILDID, PATCH_BUILDID_COMMIT, BUILDID_PATHS),
            (PATCH_ARM64, PATCH_ARM64_COMMIT, ARM64_PATHS),
        ):
            patch_path = str((repo / patch).resolve())
            for arguments in (("git", "apply", "--check", "--whitespace=error-all", patch_path), ("git", "apply", "--whitespace=error-all", patch_path)):
                result = run_local_tool(arguments, scratch)
                require(result.returncode == 0, f"{patch.name}: sequential apply failed: {result.stderr.strip()}")
            for path in paths:
                expected = run_git(source_root, ["show", f"{commit}:{path}"], binary=True)
                require((scratch / path).read_bytes() == expected, f"{patch.name}: postimage differs for {path}")
        validate_source_files(scratch, repo=repo)

    checkpatch = source_root / "scripts/checkpatch.pl"
    for patch in (PATCH_BUILDID, PATCH_ARM64):
        for strict in (False, True):
            args = [
                str(checkpatch), *(["--strict"] if strict else []),
                "--no-tree", "--show-types",
                "--ignore=MISSING_SIGN_OFF,FILE_PATH_CHANGES,AVOID_EXTERNS,CAMELCASE",
                str((repo / patch).resolve()),
            ]
            result = run_local_tool(args, source_root)
            require(result.returncode == 0 and re.search(r"total: 0 errors, 0 warnings", result.stdout) is not None, f"checkpatch failed for {patch.name}")
            require(not strict or "0 checks" in result.stdout, f"strict checkpatch checks for {patch.name}")
    c_paths = [path for path in CHANGED_PATHS if path.endswith(".c")]
    includes = run_local_tool([str(source_root / "scripts/checkincludes.pl"), *c_paths], source_root)
    require(includes.returncode == 0 and "No duplicate includes found." in includes.stdout, "duplicate include check failed")
    for script in (repo / EXPERIMENT / "scripts").glob("*.py"):
        compile(script.read_text(), str(script), "exec")
    oracle = run_oracle(repo / EXPERIMENT / "scripts/test_oracle.py", repo)
    require(oracle.returncode == 0 and "Ran 48 tests" in oracle.stderr and oracle.stderr.rstrip().endswith("OK"), "identity oracle failed")


def default_repo() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", "--repo-root", dest="repo", type=Path, default=default_repo())
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--allow-placeholders", action="store_true")
    args = parser.parse_args(argv)
    print("validation=a41-kernel-identity-offline")
    try:
        checks = validate_repository(args.repo, pin_hashes=not args.allow_placeholders)
        if args.allow_placeholders and unresolved_pins():
            validate_source_files(args.source_root, repo=args.repo)
            checks.extend(SOURCE_CHECKS[:-1])
        else:
            with checking("source-identity-application-and-static-tools"):
                validate_source_application(args.repo, args.source_root)
            checks.extend(SOURCE_CHECKS)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    for check in checks:
        print(f"PASS {check}")
    print(f"patch_0156_sha256={PATCH_BUILDID_SHA256}")
    print(f"patch_0157_sha256={PATCH_ARM64_SHA256}")
    print(f"series_sha256={SERIES_SHA256}")
    print(f"patchset_sha256={PATCHSET_SHA256}")
    print(f"source_state_sha256={SOURCE_STATE_SHA256}")
    print(f"config_sha256={CONFIG_SHA256}")
    print("implementation_state=ABI7_KERNEL_IDENTITY_BOUNDARY_BLOCKED")
    print("successful_seal_state=SEALED_IDENTITY")
    print("target_runtime_evidence=absent")
    print("a41_complete=no")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print(f"RESULT PASS {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
