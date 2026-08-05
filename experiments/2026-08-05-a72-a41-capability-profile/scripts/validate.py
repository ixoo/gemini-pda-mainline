#!/usr/bin/env python3
"""Validate the exact partial, fail-closed A41 source contract."""

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


EXPERIMENT_REL = Path("experiments/2026-08-05-a72-a41-capability-profile")
PATCH_0092 = Path("patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch")
PATCH_0148 = Path(
    "patches/v7.1.3/0148-arm64-add-a-fail-closed-late-CPU-profile-lifecycle.patch"
)
PATCH_0149 = Path(
    "patches/v7.1.3/0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch"
)
A41_SERIES = Path("patches/series-a72-reject-gate-a41")
PRE_A41_SERIES = Path("patches/series-a72-reject-gate")
CANONICAL_SERIES = Path("patches/series")
A41_FRAGMENT = Path("configs/gemini-a72-a41.fragment")
MANIFEST = Path("kernel/manifest.json")

A41_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41"
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
    str(A41_FRAGMENT),
)

# These identities are updated only when the two reviewed format-patches change.
EXPECTED_PATCH_SHA256 = {
    PATCH_0092: "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5",
    PATCH_0148: "953a990c6c9f0f91822b9923a2adf6ebf71e326ea5c570dd133c4178059750fb",
    PATCH_0149: "3c0911601d73ba73cce6a122d62df4e4f0273aeb9474e81c871aba2214feadc0",
}
EXPECTED_PATCH_COMMITS = {
    PATCH_0148: "5ba594da7b561ceed4d8b060bf12a3bfa3bcbe23",
    PATCH_0149: "08eb3392a57d30922cd06a4af0e55ee49628cdce",
}
EXPECTED_CANONICAL_SERIES_SHA256 = (
    "21e2491fc8392fe53381dad63cb4258c2881875b5cb4b7ba9029bedec85fed37"
)
EXPECTED_A41_SERIES_SHA256 = (
    "50193ab6a7aaf1055a60936bf9647865a28d9b36750b6e6a49fd1f7811087c30"
)
EXPECTED_PRE_A41_PATCHSET_SHA256 = (
    "ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd"
)
EXPECTED_SOURCE_PARENT_IDENTITY = (
    "2ef15df475d00e5ae0f85a1f25866cd4267a407af974b5c8cf992ad2e15e0a9b"
)

EXPECTED_BASE_COMMIT = "df9447fb8be9b03a643b00111dd25f6ce62be719"
EXPECTED_BASE_TREE = "265ffcaf56d7ec453e0dd017f19a5373a13960ba"
EXPECTED_BASE_BLOBS = {
    "arch/arm64/Kconfig": "10c69474f276197062f5cf6bb1affcfe1a3efd5f",
    "arch/arm64/kernel/Makefile": "ef1f74332272b3d02d679b7797b7c8d3ea5bacdc",
    "arch/arm64/kernel/smp.c": "1aa324104afb440951e0b5da1bd9d6ad84aa2f72",
    "arch/arm64/Kconfig.platforms": "72c812e76b0b115b2d59c199df5fc56060cb9da7",
    "arch/arm64/include/asm/cpu_ops.h": (
        "a444c8915e886397d9cf117b0b6982fbd453d806"
    ),
    "arch/arm64/kernel/cpu_ops.c": "b773e4dbe349b07545ace8920579ab2322cfd976",
    "arch/arm64/kernel/mt6797_psci.c": (
        "2777a3ee0fa11ac666106b0351c7cdb87a386c73"
    ),
}
NEW_SOURCE_PATHS = {
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/late_cpu_profile.c",
}
EXPECTED_CHANGED_PATHS = {
    PATCH_0148: {
        "arch/arm64/Kconfig",
        "arch/arm64/include/asm/late_cpu_profile.h",
        "arch/arm64/kernel/Makefile",
        "arch/arm64/kernel/late_cpu_profile.c",
        "arch/arm64/kernel/smp.c",
    },
    PATCH_0149: {
        "arch/arm64/Kconfig.platforms",
        "arch/arm64/include/asm/cpu_ops.h",
        "arch/arm64/kernel/cpu_ops.c",
        "arch/arm64/kernel/mt6797_psci.c",
    },
}

EXPECTED_CAPABILITIES = (
    "ARM64_SPECTRE_BHB",
    "ARM64_WORKAROUND_1742098",
    "ARM64_WORKAROUND_SPECULATIVE_AT",
)
EXPECTED_BLOCKERS = (
    (0, "ARM64_LATE_CPU_BLOCK_REGISTRATION", "framework_guard"),
    (1, "ARM64_LATE_CPU_BLOCK_TOPOLOGY", "conditional_guard"),
    (2, "ARM64_LATE_CPU_BLOCK_CONFIGURATION", "mandatory_blocker"),
    (3, "ARM64_LATE_CPU_BLOCK_CAP_INVENTORY", "mandatory_blocker"),
    (4, "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA1", "mandatory_blocker"),
    (5, "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA2", "mandatory_blocker"),
    (6, "ARM64_LATE_CPU_BLOCK_ID_REGISTERS", "mandatory_blocker"),
    (7, "ARM64_LATE_CPU_BLOCK_CACHE_TYPE", "mandatory_blocker"),
    (8, "ARM64_LATE_CPU_BLOCK_ASID", "mandatory_blocker"),
    (9, "ARM64_LATE_CPU_BLOCK_GRANULE", "mandatory_blocker"),
    (10, "ARM64_LATE_CPU_BLOCK_VA_MODE", "mandatory_blocker"),
    (11, "ARM64_LATE_CPU_BLOCK_GIC", "mandatory_blocker"),
    (12, "ARM64_LATE_CPU_BLOCK_HWCAP", "mandatory_blocker"),
    (13, "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS", "mandatory_blocker"),
    (14, "ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY", "mandatory_blocker"),
)
MANDATORY_BLOCKERS = {
    symbol for _, symbol, kind in EXPECTED_BLOCKERS if kind == "mandatory_blocker"
}

EXPECTED_IMPLEMENTATION_MARKERS = {
    "implementation_state": "PARTIAL_FAIL_CLOSED",
    "a41_complete": "no",
    "framework_lifecycle": "implemented",
    "attestation_schema": "implemented",
    "profile_registration": "implemented",
    "independent_activation": "implemented",
    "non_circular_input_identities": "recorded_not_runtime_proof",
    "target_observation_validity": "explicit",
    "capability_inventory_enumerator": "not_implemented",
    "planned_capability_count": "3",
    "planned_capabilities": ",".join(EXPECTED_CAPABILITIES),
    "planned_bhb_method": "ARM64_LATE_CPU_BHB_LOOP",
    "planned_bhb_k": "8",
    "profile_commit": "unreachable_for_selected_profile",
    "production_ready_reachable": "no",
    "production_cpu_on_path": "absent",
    "production_capability_mutation_path": "absent",
    "a36_attestation_binding": "interface_only",
    "current_cpu_boot_veto": "required",
    "current_cpu_disable_veto": "required",
    "boot_candidate": "false",
    "build_authorized": "no",
    "device_action_authorized": "no",
    "hardware_support_claim": "none",
}


class ValidationError(RuntimeError):
    """A fixed experiment invariant did not hold."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob_sha1(data: bytes) -> str:
    header = "blob {}\0".format(len(data)).encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def ordered(text: str, tokens: Sequence[str], scope: str) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        require(position >= 0, "{}: missing ordered token {!r}".format(scope, token))
        require(position > cursor, "{}: out-of-order token {!r}".format(scope, token))
        cursor = position


def require_tokens(text: str, tokens: Iterable[str], scope: str) -> None:
    for token in tokens:
        require(token in text, "{}: missing {!r}".format(scope, token))


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


def patch_sections(patch: str) -> dict[str, str]:
    matches = list(
        re.finditer(r"^diff --git a/(\S+) b/(\S+)$", patch, flags=re.MULTILINE)
    )
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        require(match.group(1) == match.group(2), "patch renames are not permitted")
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(patch)
        path = match.group(1)
        require(path not in sections, "duplicate patch section for {}".format(path))
        sections[path] = patch[start:end]
    return sections


def added_source(section: str) -> str:
    return "\n".join(
        line[1:]
        for line in section.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def removed_source(section: str) -> list[str]:
    return [
        line[1:]
        for line in section.splitlines()
        if line.startswith("-")
        and not line.startswith("---")
        and not line.startswith("-- ")
    ]


def patch_postimage_context(section: str) -> str:
    """Return context plus additions from unified-diff hunks."""

    result: list[str] = []
    in_hunk = False
    for line in section.splitlines():
        if line.startswith("@@ "):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("diff --git "):
            break
        if line.startswith((" ", "+")) and not line.startswith("+++"):
            result.append(line[1:])
    return "\n".join(result)


def extract_c_function(text: str, name: str) -> str:
    match = re.search(r"\b{}\s*\([^;]*?\)\s*\{{".format(re.escape(name)), text, re.DOTALL)
    require(match is not None, "missing function {}".format(name))
    start = match.start()
    brace = text.find("{", match.start())
    depth = 0
    for cursor in range(brace, len(text)):
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
            if depth == 0:
                return text[start : cursor + 1]
    raise ValidationError("unterminated function {}".format(name))


def parse_index(section: str) -> tuple[str, str]:
    match = re.search(
        r"^index ([0-9a-f]+)\.\.([0-9a-f]+)(?: [0-7]{6})?$",
        section,
        flags=re.MULTILINE,
    )
    require(match is not None, "patch section lacks an index line")
    return match.group(1), match.group(2)


def config_input_hash(repo: Path, profile_name: str, profile: dict) -> str:
    lines = ["profile={}".format(profile_name), "base={}".format(profile["base"])]
    for fragment in profile["fragments"]:
        path = repo / fragment
        require(path.is_file(), "missing profile fragment {}".format(fragment))
        lines.append("{}  {}".format(sha256_file(path), fragment))
    return sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def patchset_hash(repo: Path, series_relative: Path) -> str:
    series_path = repo / series_relative
    series_data = series_path.read_bytes()
    lines = ["{}  {}".format(sha256_bytes(series_data), series_relative)]
    for entry in series_entries(series_data.decode("utf-8")):
        patch_path = series_path.parent / entry
        require(patch_path.is_file(), "pre-A41 patch is missing: {}".format(entry))
        lines.append("{}  {}".format(sha256_file(patch_path), entry))
    return sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def source_state_hash(repo: Path, series_relative: Path) -> str:
    manifest = json.loads((repo / MANIFEST).read_text())
    kernel = manifest["kernel"]
    material = "{}\n{}\n{}\n".format(
        kernel["version"], kernel["sha256"], patchset_hash(repo, series_relative)
    )
    return sha256_bytes(material.encode("utf-8"))


def digest_u64_literals(digest: str) -> tuple[str, ...]:
    require(bool(re.fullmatch(r"[0-9a-f]{64}", digest)), "invalid digest")
    return tuple("0x" + digest[index : index + 16] for index in range(0, 64, 16))


def read_tsv(path: Path, fieldnames: Sequence[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(reader.fieldnames == list(fieldnames), "{}: header changed".format(path.name))
        rows = list(reader)
    require(rows, "{}: table is empty".format(path.name))
    require(
        all(None not in row and all(value != "" for value in row.values()) for row in rows),
        "{}: malformed or empty cell".format(path.name),
    )
    return rows


def validate_experiment_record(repo: Path) -> None:
    experiment = repo / EXPERIMENT_REL
    expected_files = {
        "README.md",
        "DESIGN.md",
        "results/implementation.tsv",
        "results/blockers.tsv",
        "results/kernel-static-review-20260805.txt",
        "results/offline-validation-20260805.txt",
        "results/mutation-validation-20260805.txt",
        "scripts/validate.py",
        "scripts/test_mutations.py",
    }
    for relative in expected_files:
        require((experiment / relative).is_file(), "missing experiment file {}".format(relative))

    readme = (experiment / "README.md").read_text()
    design = (experiment / "DESIGN.md").read_text()
    static_review = (
        experiment / "results/kernel-static-review-20260805.txt"
    ).read_text()
    require_tokens(
        readme + "\n" + design,
        [
            "PARTIAL_FAIL_CLOSED",
            "A41 remains incomplete",
            "not a boot candidate",
            "../../docs/ROADMAP.md",
            "| Date(s) |",
            "| Investigator(s) |",
            "| Tracking issue |",
        ],
        "experiment claim boundary",
    )
    require("/Users/" not in readme + design, "personal absolute path in experiment docs")

    require_tokens(
        static_review,
        [
            "source_base_commit=" + EXPECTED_BASE_COMMIT,
            "source_head_commit=" + EXPECTED_PATCH_COMMITS[PATCH_0149],
            "source_diff_sha256=374a09a9f2d91d753bc3ed55ad5458c990848ab8c3d4f6df1be8f275f348d104",
            "command_2_errors=0",
            "command_2_warnings=1",
            "command_2_checks=0",
            "command_3_output=No duplicate includes found.",
            "patch_0148_expected_error=Missing Signed-off-by",
            "patch_0149_expected_error=Missing Signed-off-by",
            "compile_run=no",
            "build_run=no",
            "RESULT=PASS_WITH_EXPECTED_EXPERIMENT_ONLY_SIGNOFF_EXCEPTION",
        ],
        "kernel static-review evidence",
    )

    offline = (experiment / "results/offline-validation-20260805.txt").read_text()
    mutations = (experiment / "results/mutation-validation-20260805.txt").read_text()
    require_tokens(
        offline,
        [
            "patch_0148_sha256=" + EXPECTED_PATCH_SHA256[PATCH_0148],
            "patch_0149_sha256=" + EXPECTED_PATCH_SHA256[PATCH_0149],
            "implementation_state=PARTIAL_FAIL_CLOSED",
            "a41_complete=no",
            "RESULT PASS 16/16",
        ],
        "frozen offline transcript",
    )
    require_tokens(
        mutations,
        ["mutation_count=43", "RESULT PASS 43/43"],
        "frozen mutation transcript",
    )


def validate_patch_identities(repo: Path, patches: dict[Path, str], pin_hashes: bool) -> None:
    for relative, expected_paths in EXPECTED_CHANGED_PATHS.items():
        text = patches[relative]
        if pin_hashes:
            require(
                sha256_file(repo / relative) == EXPECTED_PATCH_SHA256[relative],
                "{}: SHA-256 changed".format(relative.name),
            )
        require(
            set(patch_sections(text)) == expected_paths,
            "{}: changed-path set differs".format(relative.name),
        )
        require("Signed-off-by:" not in text, "synthetic experiment patch gained a sign-off")

    for relative, commit in EXPECTED_PATCH_COMMITS.items():
        match = re.match(r"From ([0-9a-f]{40}) ", patches[relative])
        require(match is not None, "{}: missing format-patch identity".format(relative.name))
        require(match.group(1) == commit, "{}: source commit changed".format(relative.name))

    require(
        patches[PATCH_0148].count("Subject: [PATCH 148/149]") == 1,
        "0148 subject sequence changed",
    )
    require(
        patches[PATCH_0149].count("Subject: [PATCH 149/149]") == 1,
        "0149 subject sequence changed",
    )
    removed = removed_source(
        patch_sections(patches[PATCH_0149])["arch/arm64/kernel/mt6797_psci.c"]
    )
    require(
        removed == ["\treturn cpu_psci_ops.cpu_init(cpu);"],
        "0149 alters source beyond the reviewed cpu_init replacement",
    )


def validate_series_order(repo: Path, pin_hashes: bool) -> None:
    canonical_text = (repo / CANONICAL_SERIES).read_text()
    selected_text = (repo / A41_SERIES).read_text()
    if pin_hashes:
        require(
            sha256_bytes(canonical_text.encode()) == EXPECTED_CANONICAL_SERIES_SHA256,
            "canonical series identity changed",
        )
        require(
            sha256_bytes(selected_text.encode()) == EXPECTED_A41_SERIES_SHA256,
            "A41 series identity changed",
        )
    canonical = series_entries(canonical_text)
    selected = series_entries(selected_text)
    p92 = str(PATCH_0092.relative_to("patches"))
    p148 = str(PATCH_0148.relative_to("patches"))
    p149 = str(PATCH_0149.relative_to("patches"))
    require(len(selected) == 91, "A41 series entry count changed")
    require(selected[-3:] == [p92, p148, p149], "A41 terminal patch order changed")
    require(canonical[-2:] == [p148, p149], "canonical A41 patch order changed")
    require(is_subsequence(selected, canonical), "A41 series is not a canonical subsequence")
    require(len(selected) == len(set(selected)), "A41 series contains duplicates")
    for forbidden in ("0093-", "0111-", "a72-active", "cpu8-one-way"):
        require(
            not any(forbidden in entry for entry in selected),
            "A41 series includes active path {!r}".format(forbidden),
        )


def validate_manifest_isolation(repo: Path, patch149: str) -> None:
    manifest = json.loads((repo / MANIFEST).read_text())
    require(manifest["config"]["default_profile"] == "full", "default profile changed")
    profiles = manifest["config"]["profiles"]
    require(A41_PROFILE in profiles, "isolated A41 profile is missing")
    profile = profiles[A41_PROFILE]
    require(profile.get("base") == "defconfig", "A41 base configuration changed")
    require(profile.get("patch_series") == str(A41_SERIES), "A41 series selection changed")
    require(
        tuple(profile.get("fragments", ())) == EXPECTED_PROFILE_FRAGMENTS,
        "A41 fragment order changed",
    )

    for name, candidate in profiles.items():
        if name == A41_PROFILE:
            continue
        require(
            candidate.get("patch_series") != str(A41_SERIES),
            "A41 series leaked into profile {}".format(name),
        )
        require(
            str(A41_FRAGMENT) not in candidate.get("fragments", []),
            "A41 fragment leaked into profile {}".format(name),
        )

    fragment = (repo / A41_FRAGMENT).read_text()
    assignments = [
        line.strip()
        for line in fragment.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        assignments
        == [
            "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
            'CONFIG_LOCALVERSION="-gemini-a41-blocked"',
        ],
        "A41 fragment gained an unreviewed setting",
    )
    assignment_text = "\n".join(assignments)
    require("CONFIG_CMDLINE" not in assignment_text, "A41 fragment requests a CPU at boot")
    require("maxcpus=" not in assignment_text, "A41 fragment changes the inherited CPU limit")
    require(
        "maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(),
        "inherited maxcpus=8 guard changed",
    )

    kconfig = added_source(
        patch_sections(patch149)["arch/arm64/Kconfig.platforms"]
    )
    require_tokens(
        kconfig,
        [
            "config ARM64_MT6797_A72_CAPABILITY_PROFILE",
            'bool "Fail-closed MT6797 late Cortex-A72 capability profile"',
            "depends on ARCH_MEDIATEK && SMP",
            "select ARM64_LATE_CPU_PROFILE",
        ],
        "isolated A41 Kconfig option",
    )
    require(
        not re.search(r"^\s*default\s+y\b", kconfig, flags=re.MULTILINE),
        "A41 Kconfig option is not default-off",
    )

    digest = config_input_hash(repo, A41_PROFILE, profile)
    literals = digest_u64_literals(digest)
    source = added_source(
        patch_sections(patch149)["arch/arm64/kernel/mt6797_psci.c"]
    )
    require_tokens(source, literals, "A41 configuration identity")


def validate_patch_preimages(patches: dict[Path, str]) -> None:
    for relative in (PATCH_0148, PATCH_0149):
        for path, section in patch_sections(patches[relative]).items():
            old, new = parse_index(section)
            if path in NEW_SOURCE_PATHS:
                require(old == "0" * len(old), "{}: new-file preimage is not zero".format(path))
            else:
                expected = EXPECTED_BASE_BLOBS[path]
                require(expected.startswith(old), "{}: preimage blob changed".format(path))
            require(new != "0" * len(new), "{}: postimage blob is zero".format(path))


def validate_lifecycle(patch148: str) -> None:
    sections = patch_sections(patch148)
    smp = sections["arch/arm64/kernel/smp.c"]
    ordered(
        smp,
        [
            "hyp_mode_check();",
            "arm64_prepare_late_cpu_profile();",
            "setup_system_features();",
            "arm64_verify_late_cpu_profile_system();",
            "setup_user_features();",
            "arm64_finalize_late_cpu_profile_user();",
            "mark_linear_text_alias_ro();",
        ],
        "smp_cpus_done lifecycle",
    )

    lifecycle = added_source(sections["arch/arm64/kernel/late_cpu_profile.c"])
    prepare = extract_c_function(lifecycle, "arm64_prepare_late_cpu_profile")
    verify = extract_c_function(lifecycle, "arm64_verify_late_cpu_profile_system")
    finalize = extract_c_function(lifecycle, "arm64_finalize_late_cpu_profile_user")
    accessor = extract_c_function(lifecycle, "arm64_get_late_cpu_attestation")
    ordered(
        prepare,
        [
            "late_profile.prepare",
            "late_profile_core_matches",
            "ret || draft.blocker_mask",
            "late_profile_block",
            "return;",
            "ARM64_LATE_CPU_PROFILE_PREPARED",
        ],
        "prepare fail-closed transition",
    )
    require_tokens(
        verify,
        ["ARM64_LATE_CPU_PROFILE_BLOCKED", "ARM64_LATE_CPU_PROFILE_PREPARED"],
        "system finalizer",
    )
    require_tokens(
        finalize,
        ["ARM64_LATE_CPU_PROFILE_BLOCKED", "ARM64_LATE_CPU_PROFILE_SYSTEM_VERIFIED"],
        "user finalizer",
    )
    ordered(
        finalize,
        [
            "late_profile.finalize_user",
            "late_attestation.user_hwcaps_finalized = 1",
            "ARM64_LATE_CPU_PROFILE_READY",
        ],
        "READY publication",
    )
    ordered(
        accessor,
        [
            "smp_load_acquire",
            "ARM64_LATE_CPU_PROFILE_READY",
            "return NULL",
            "return &late_attestation",
        ],
        "attestation publication guard",
    )


def validate_registration_fail_closed(patch148: str, patch149: str) -> None:
    lifecycle = added_source(
        patch_sections(patch148)["arch/arm64/kernel/late_cpu_profile.c"]
    )
    prepare = extract_c_function(lifecycle, "arm64_prepare_late_cpu_profile")
    fault = prepare.find("late_profile_registration_fault")
    no_profile = prepare.find("if (!late_profile)")
    require(fault >= 0, "prepare does not inspect registration faults")
    require(
        no_profile < 0 or fault < no_profile,
        "invalid first registration is swallowed as no profile",
    )
    require_tokens(
        prepare,
        [
            "if (!late_profile_active && !late_profile_registration_fault)",
            "if (late_profile_registration_fault)",
            "ARM64_LATE_CPU_BLOCK_REGISTRATION",
        ],
        "invalid-first-registration handling",
    )

    platform = added_source(
        patch_sections(patch149)["arch/arm64/kernel/mt6797_psci.c"]
    )
    require_tokens(
        platform,
        [
            "arm64_activate_late_cpu_profile",
            "arm64_register_late_cpu_target",
            "mt6797_a72_profile",
            "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE",
            ".target_count = 2",
        ],
        "MT6797 registration",
    )
    cpu_ops = patch_postimage_context(
        patch_sections(patch149)["arch/arm64/kernel/cpu_ops.c"]
    )
    ordered(
        cpu_ops,
        [
            "if (!cpu)",
            "mt6797_activate_a72_capability_profile();",
            "cpu_read_enable_method(cpu)",
        ],
        "CPU0-independent profile activation",
    )
    require_tokens(
        prepare,
        ["cpumask_weight(&late_profile_targets)", "late_profile.target_count"],
        "complete target registration",
    )


def validate_callback_integrity(patch148: str) -> None:
    sections = patch_sections(patch148)
    header = added_source(sections["arch/arm64/include/asm/late_cpu_profile.h"])
    framework = added_source(sections["arch/arm64/kernel/late_cpu_profile.c"])
    core_match = extract_c_function(framework, "late_profile_core_matches")
    identity_match = extract_c_function(framework, "late_profile_identity_matches")
    prepare = extract_c_function(framework, "arm64_prepare_late_cpu_profile")
    verify = extract_c_function(framework, "arm64_verify_late_cpu_profile_system")
    finalize = extract_c_function(framework, "arm64_finalize_late_cpu_profile_user")

    require_tokens(
        header,
        [
            "int (*verify_system)(const struct arm64_late_cpu_attestation *attestation)",
            "int (*finalize_user)(const struct arm64_late_cpu_attestation *attestation)",
        ],
        "const finalizer callbacks",
    )
    require_tokens(
        core_match,
        [
            "draft->abi == ARM64_LATE_CPU_ATTESTATION_ABI",
            "draft->state == ARM64_LATE_CPU_PROFILE_REGISTERED",
            "memcmp(draft->profile_id, late_attestation.profile_id",
            "sizeof(draft->profile_id)",
            "cpumask_equal(&draft->target_cpus, &late_profile_targets)",
            "!draft->strict_caps_verified",
            "!draft->alternatives_finalized",
            "!draft->user_hwcaps_finalized",
        ],
        "prepare core-owned identity guard",
    )
    ordered(
        prepare,
        [
            "draft = late_attestation",
            "late_profile.prepare",
            "late_profile_core_matches(&draft)",
            "ret || draft.blocker_mask",
            "late_attestation = draft",
        ],
        "validate-before-copy prepare contract",
    )
    require_tokens(
        framework,
        [
            'pr_warn("%.*s blocked:',
            "ARM64_LATE_CPU_PROFILE_ID_LEN",
            "late_profile.name = late_attestation.profile_id",
        ],
        "bounded self-owned profile identity",
    )

    require_tokens(
        identity_match,
        [
            "memcmp(before->profile_id, after->profile_id",
            "before->blocker_mask == after->blocker_mask",
            "before->expected_elf_hwcap",
            "before->expected_compat_hwcap == after->expected_compat_hwcap",
            "before->expected_compat_hwcap2 == after->expected_compat_hwcap2",
            "before->strict_caps_verified == after->strict_caps_verified",
            "before->observed_target_registers_valid",
        ],
        "post-prepare immutable record guard",
    )
    ordered(
        verify,
        [
            "before = late_attestation",
            "draft = before",
            "late_profile.verify_system(&draft)",
            "draft.blocker_mask",
            "late_profile_identity_matches(&before, &draft)",
            "late_attestation = draft",
            "late_attestation.strict_caps_verified = 1",
            "late_attestation.alternatives_finalized = 1",
            "ARM64_LATE_CPU_PROFILE_SYSTEM_VERIFIED",
        ],
        "system callback transaction",
    )
    ordered(
        finalize,
        [
            "before = late_attestation",
            "draft = before",
            "late_profile.finalize_user(&draft)",
            "draft.blocker_mask",
            "late_profile_identity_matches(&before, &draft)",
            "!draft.strict_caps_verified",
            "!draft.alternatives_finalized",
            "late_attestation = draft",
            "late_attestation.user_hwcaps_finalized = 1",
            "ARM64_LATE_CPU_PROFILE_READY",
        ],
        "user callback transaction",
    )


def parse_blocker_definitions(header: str) -> list[tuple[int, str]]:
    definitions = re.findall(
        r"^#define\s+(ARM64_LATE_CPU_BLOCK_[A-Z0-9_]+)\s+BIT_ULL\((\d+)\)",
        header,
        flags=re.MULTILINE,
    )
    return [(int(bit), symbol) for symbol, bit in definitions]


def validate_blocker_model(repo: Path, patch148: str, patch149: str) -> None:
    header = added_source(
        patch_sections(patch148)["arch/arm64/include/asm/late_cpu_profile.h"]
    )
    expected_defs = [(bit, symbol) for bit, symbol, _ in EXPECTED_BLOCKERS]
    require(parse_blocker_definitions(header) == expected_defs, "source blocker set changed")

    rows = read_tsv(
        repo / EXPERIMENT_REL / "results/blockers.tsv",
        ("bit", "symbol", "profile_disposition", "evidence_status"),
    )
    actual_rows = [
        (int(row["bit"]), row["symbol"], row["profile_disposition"]) for row in rows
    ]
    require(actual_rows == list(EXPECTED_BLOCKERS), "blocker table is not exhaustive")

    platform = added_source(
        patch_sections(patch149)["arch/arm64/kernel/mt6797_psci.c"]
    )
    macro_start = platform.find("#define MT6797_A72_PROFILE_BLOCKERS")
    macro_end = platform.find("static bool", macro_start)
    require(macro_start >= 0 and macro_end > macro_start, "missing mandatory blocker macro")
    macro = platform[macro_start:macro_end]
    actual_mandatory = set(re.findall(r"ARM64_LATE_CPU_BLOCK_[A-Z0-9_]+", macro))
    require(actual_mandatory == MANDATORY_BLOCKERS, "mandatory blocker set changed")
    require_tokens(
        platform,
        [
            "draft->blocker_mask = MT6797_A72_PROFILE_BLOCKERS",
            "draft->blocker_mask |= ARM64_LATE_CPU_BLOCK_CONFIGURATION",
            "draft->blocker_mask |= ARM64_LATE_CPU_BLOCK_TOPOLOGY",
        ],
        "MT6797 blocker assignment",
    )
    require(
        not re.search(r"blocker_mask\s*(?:&=|\^=|=\s*0\s*;)", platform),
        "MT6797 source clears blocker evidence",
    )


def validate_planned_capabilities(patch149: str) -> None:
    platform = added_source(
        patch_sections(patch149)["arch/arm64/kernel/mt6797_psci.c"]
    )
    prepare = extract_c_function(platform, "mt6797_a72_profile_prepare")
    planned = tuple(
        re.findall(
            r"__set_bit\(\s*(ARM64_[A-Z0-9_]+)\s*,\s*"
            r"draft->required_local_caps\s*\)",
            prepare,
            flags=re.DOTALL,
        )
    )
    require(planned == EXPECTED_CAPABILITIES, "planned capability set/order changed")
    require(prepare.count("__set_bit(") == 3, "unexpected bitmap mutation in profile plan")
    require_tokens(
        prepare,
        [
            "draft->bhb_method = ARM64_LATE_CPU_BHB_LOOP",
            "draft->bhb_loop_count = 8",
            "draft->blocker_mask = MT6797_A72_PROFILE_BLOCKERS",
            "return -EAGAIN;",
        ],
        "deterministic MT6797 plan",
    )
    ordered(
        prepare,
        [
            "draft->bhb_method = ARM64_LATE_CPU_BHB_LOOP",
            "draft->bhb_loop_count = 8",
            "draft->blocker_mask = MT6797_A72_PROFILE_BLOCKERS",
            "return -EAGAIN;",
        ],
        "plan-before-block order",
    )


def validate_production_path_absence(patch148: str, patch149: str) -> None:
    framework = added_source(
        patch_sections(patch148)["arch/arm64/kernel/late_cpu_profile.c"]
    )
    platform = added_source(
        patch_sections(patch149)["arch/arm64/kernel/mt6797_psci.c"]
    )
    combined = framework + "\n" + platform
    forbidden = (
        "cpu_psci_ops.cpu_boot(",
        "psci_ops.cpu_on(",
        "invoke_psci_fn(",
        "system_cpucaps",
        "cpu_hwcaps",
        "update_cpu_capabilities(",
        "setup_cpu_features(",
        "apply_alternatives",
        "max_bhb_k =",
        "spectre_bhb_state =",
        "this_cpu_write(bp_hardening_data",
        "elf_hwcap |=",
        "compat_elf_hwcap |=",
    )
    for token in forbidden:
        require(token not in combined, "production mutation path added: {}".format(token))

    initializer = platform[
        platform.find("static const struct arm64_late_cpu_profile mt6797_a72_profile") :
    ]
    initializer = initializer[: initializer.find("};") + 2]
    require(".prepare = mt6797_a72_profile_prepare" in initializer, "profile prepare missing")
    require(".verify_system" not in initializer, "selected profile gained a system commit")
    require(".finalize_user" not in initializer, "selected profile gained a user commit")

    prepare = extract_c_function(platform, "mt6797_a72_profile_prepare")
    require("return -EAGAIN;" in prepare, "selected profile can report preparation success")
    generic_prepare = extract_c_function(framework, "arm64_prepare_late_cpu_profile")
    require(
        "ret || draft.blocker_mask" in generic_prepare,
        "framework can publish PREPARED with failed or blocked evidence",
    )
    for finalizer in (
        extract_c_function(framework, "arm64_verify_late_cpu_profile_system"),
        extract_c_function(framework, "arm64_finalize_late_cpu_profile_user"),
    ):
        require(
            "ARM64_LATE_CPU_PROFILE_BLOCKED" in finalizer,
            "BLOCKED does not short-circuit a finalizer",
        )

    # Generic callbacks may not erase blockers or change the immutable plan and
    # then advance the state. The exact helper names are part of the contract.
    require_tokens(
        framework,
        ["late_profile_identity_matches", "late_attestation.blocker_mask"],
        "post-callback integrity checks",
    )
    require(
        framework.count("late_profile_identity_matches") >= 2,
        "both lifecycle callbacks must recheck immutable identity",
    )


def validate_veto_preservation(repo: Path, patch0092: str, patch149: str, pin_hashes: bool) -> None:
    if pin_hashes:
        require(
            sha256_file(repo / PATCH_0092) == EXPECTED_PATCH_SHA256[PATCH_0092],
            "0092 veto patch identity changed",
        )
    source = "\n".join(added_source(section) for section in patch_sections(patch0092).values())
    boot = extract_c_function(source, "mt6797_psci_cpu_boot")
    disable = extract_c_function(source, "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot, "0092 boot veto changed")
    require("cpu_psci_ops.cpu_boot" not in boot, "0092 delegates to normal PSCI boot")
    require("return false;" in disable, "0092 disable veto changed")
    p149_diff = patch_sections(patch149)["arch/arm64/kernel/mt6797_psci.c"]
    for line in removed_source(p149_diff):
        require("cpu_boot" not in line and "cpu_can_disable" not in line, "0149 removes a veto")


def validate_identity_and_lifetime(
    repo: Path, patch148: str, patch149: str, pin_hashes: bool
) -> None:
    framework = added_source(
        patch_sections(patch148)["arch/arm64/kernel/late_cpu_profile.c"]
    )
    platform = added_source(
        patch_sections(patch149)["arch/arm64/kernel/mt6797_psci.c"]
    )
    dangling = (
        re.search(
            r"static const struct arm64_late_cpu_profile \*late_profile\s+__ro_after_init",
            framework,
        )
        and re.search(
            r"struct arm64_late_cpu_profile mt6797_a72_profile\s+__initconst",
            platform,
        )
    )
    require(not dangling, "permanent profile pointer aliases freed init memory")
    require_tokens(
        framework,
        [
            "late_profile_identity_matches",
            "late_profile_core_matches",
            "late_profile.name = late_attestation.profile_id",
        ],
        "immutable lifecycle identity",
    )

    header = added_source(
        patch_sections(patch148)["arch/arm64/include/asm/late_cpu_profile.h"]
    )
    require_tokens(
        header,
        [
            "source_parent_identity",
            "config_input_identity",
            "expected_target_mpidr",
            "expected_target_midr",
            "observed_target_midr",
            "observed_target_revidr",
            "observed_target_registers_valid",
            "smccc_wa1_valid",
            "smccc_wa2_valid",
        ],
        "parent/expected/observed attestation schema",
    )
    require_tokens(
        platform,
        digest_u64_literals(EXPECTED_SOURCE_PARENT_IDENTITY),
        "pre-A41 source parent identity",
    )
    if pin_hashes:
        computed_patchset = patchset_hash(repo, PRE_A41_SERIES)
        require(
            computed_patchset == EXPECTED_PRE_A41_PATCHSET_SHA256,
            "pre-A41 reject-gate patchset identity changed",
        )
        require(
            source_state_hash(repo, PRE_A41_SERIES)
            == EXPECTED_SOURCE_PARENT_IDENTITY,
            "pre-A41 source parent identity changed",
        )

    manifest = json.loads((repo / MANIFEST).read_text())
    digest = config_input_hash(repo, A41_PROFILE, manifest["config"]["profiles"][A41_PROFILE])
    require_tokens(platform, digest_u64_literals(digest), "current configuration identity")


def validate_markers(repo: Path) -> None:
    rows = read_tsv(
        repo / EXPERIMENT_REL / "results/implementation.tsv",
        ("key", "value", "evidence"),
    )
    require(len(rows) == len(EXPECTED_IMPLEMENTATION_MARKERS), "marker count changed")
    actual = {row["key"]: row["value"] for row in rows}
    require(len(actual) == len(rows), "duplicate implementation marker")
    require(actual == EXPECTED_IMPLEMENTATION_MARKERS, "implementation claim boundary changed")


def validate_offline_boundary(repo: Path) -> None:
    scripts = "\n".join(
        (repo / EXPERIMENT_REL / relative).read_text()
        for relative in ("scripts/validate.py", "scripts/test_mutations.py")
    )
    forbidden = (
        "./scripts/build" + "-kernel",
        "./scripts/dev" + "-vm",
        '["s' + 'sh"',
        '["n' + 'c"',
        '["shut' + 'down"',
        '["re' + 'boot"',
        "/d" + "ev/mmc",
    )
    for token in forbidden:
        require(
            token not in scripts,
            "offline validator contains device/build action {!r}".format(token),
        )


def validate_repository(repo: Path, *, pin_hashes: bool = True) -> list[str]:
    """Run repository-only checks; exposed for the mutation suite."""

    repo = repo.resolve()
    patches = {
        relative: (repo / relative).read_text()
        for relative in (PATCH_0092, PATCH_0148, PATCH_0149)
    }
    completed: list[str] = []
    validate_experiment_record(repo)
    completed.append("experiment-record")
    validate_patch_identities(repo, patches, pin_hashes)
    completed.append("patch-identities")
    validate_series_order(repo, pin_hashes)
    completed.append("series-order")
    validate_manifest_isolation(repo, patches[PATCH_0149])
    completed.append("manifest-isolation")
    validate_patch_preimages(patches)
    completed.append("patch-preimages")
    validate_lifecycle(patches[PATCH_0148])
    completed.append("lifecycle-order")
    validate_registration_fail_closed(patches[PATCH_0148], patches[PATCH_0149])
    completed.append("registration-fail-closed")
    validate_callback_integrity(patches[PATCH_0148])
    completed.append("callback-integrity")
    validate_blocker_model(repo, patches[PATCH_0148], patches[PATCH_0149])
    completed.append("blocker-model")
    validate_planned_capabilities(patches[PATCH_0149])
    completed.append("planned-capabilities")
    validate_production_path_absence(patches[PATCH_0148], patches[PATCH_0149])
    completed.append("production-path-absence")
    validate_veto_preservation(
        repo, patches[PATCH_0092], patches[PATCH_0149], pin_hashes
    )
    completed.append("veto-preservation")
    validate_identity_and_lifetime(
        repo, patches[PATCH_0148], patches[PATCH_0149], pin_hashes
    )
    completed.append("identity-and-lifetime")
    validate_markers(repo)
    completed.append("partial-markers")
    validate_offline_boundary(repo)
    completed.append("offline-boundary")
    return completed


def run_git(source_root: Path, arguments: Sequence[str], *, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    )
    require(
        result.returncode == 0,
        "git {} failed: {}".format(arguments[0], result.stderr.strip()),
    )
    return result.stdout


def validate_applied_source(tree: Path) -> None:
    smp = (tree / "arch/arm64/kernel/smp.c").read_text()
    ordered(
        extract_c_function(smp, "smp_cpus_done"),
        [
            "arm64_prepare_late_cpu_profile();",
            "setup_system_features();",
            "arm64_verify_late_cpu_profile_system();",
            "setup_user_features();",
            "arm64_finalize_late_cpu_profile_user();",
        ],
        "applied smp lifecycle",
    )
    platform = (tree / "arch/arm64/kernel/mt6797_psci.c").read_text()
    boot = extract_c_function(platform, "mt6797_psci_cpu_boot")
    disable = extract_c_function(platform, "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot, "applied source lost boot veto")
    require(
        "cpu_psci_ops.cpu_boot" not in boot,
        "applied boot path delegates to PSCI",
    )
    require("return false;" in disable, "applied source lost disable veto")
    require(".cpu_boot\t= mt6797_psci_cpu_boot" in platform, "boot veto is not installed")
    require(
        ".cpu_can_disable = mt6797_psci_cpu_can_disable" in platform,
        "disable veto is not installed",
    )


def validate_source_application(repo: Path, source_root: Path) -> None:
    source_root = source_root.resolve()
    require((source_root / ".git").exists(), "source root is not a Git repository")
    commit = run_git(source_root, ["rev-parse", EXPECTED_BASE_COMMIT]).strip()
    require(commit == EXPECTED_BASE_COMMIT, "pinned source baseline is absent")
    tree = run_git(source_root, ["rev-parse", "{}^{{tree}}".format(commit)]).strip()
    require(tree == EXPECTED_BASE_TREE, "pinned source baseline tree changed")

    patch_texts = {
        relative: (repo / relative).read_text() for relative in (PATCH_0148, PATCH_0149)
    }
    with tempfile.TemporaryDirectory(prefix="gemini-a41-validate-") as temporary:
        scratch = Path(temporary)
        for source_path, expected_blob in EXPECTED_BASE_BLOBS.items():
            blob = run_git(
                source_root,
                ["show", "{}:{}".format(commit, source_path)],
                binary=True,
            )
            require(
                git_blob_sha1(blob) == expected_blob,
                "{}: baseline blob changed".format(source_path),
            )
            destination = scratch / source_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blob)

        for source_path in NEW_SOURCE_PATHS:
            probe = subprocess.run(
                [
                    "git",
                    "-C",
                    str(source_root),
                    "cat-file",
                    "-e",
                    "{}:{}".format(commit, source_path),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            require(probe.returncode != 0, "{} unexpectedly exists in baseline".format(source_path))

        for relative in (PATCH_0148, PATCH_0149):
            patch_path = (repo / relative).resolve()
            for arguments in (
                ["apply", "--check", "--whitespace=error-all", str(patch_path)],
                ["apply", "--whitespace=error-all", str(patch_path)],
            ):
                result = subprocess.run(
                    ["git", *arguments],
                    cwd=scratch,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                require(
                    result.returncode == 0,
                    "{} sequential applicability failed: {}".format(
                        relative.name, result.stderr.strip()
                    ),
                )

        for relative, text in patch_texts.items():
            for source_path, section in patch_sections(text).items():
                _, expected_post = parse_index(section)
                actual_post = git_blob_sha1((scratch / source_path).read_bytes())
                require(
                    actual_post.startswith(expected_post),
                    "{}: applied postimage differs from patch index".format(source_path),
                )
        validate_applied_source(scratch)


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Git source repository containing the pinned pre-0148 baseline",
    )
    args = parser.parse_args(argv)
    try:
        checks = validate_repository(args.repo_root)
        validate_source_application(args.repo_root.resolve(), args.source_root)
        checks.append("sequential-source-application")
    except (OSError, ValueError, json.JSONDecodeError, ValidationError) as error:
        print("FAIL {}".format(error), file=sys.stderr)
        return 1

    for check in checks:
        print("PASS {}".format(check))
    manifest = json.loads((args.repo_root / MANIFEST).read_text())
    profile = manifest["config"]["profiles"][A41_PROFILE]
    print("patch_0148_sha256={}".format(sha256_file(args.repo_root / PATCH_0148)))
    print("patch_0149_sha256={}".format(sha256_file(args.repo_root / PATCH_0149)))
    print("config_inputs_sha256={}".format(config_input_hash(args.repo_root, A41_PROFILE, profile)))
    print("implementation_state=PARTIAL_FAIL_CLOSED")
    print("a41_complete=no")
    print("build_authorized=no")
    print("device_action_authorized=no")
    print("RESULT PASS {}/{}".format(len(checks), len(checks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
