#!/usr/bin/env python3
"""Validate the exact source-only A41 canonical-planner contract."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


EXPERIMENT_REL = Path("experiments/2026-08-05-a72-a41-canonical-planner")
PATCH_0092 = Path("patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch")
PATCH_0148 = Path(
    "patches/v7.1.3/0148-arm64-add-a-fail-closed-late-CPU-profile-lifecycle.patch"
)
PATCH_0149 = Path(
    "patches/v7.1.3/0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch"
)
PATCH_0150 = Path(
    "patches/v7.1.3/0150-arm64-add-read-only-late-CPU-capability-planner.patch"
)
PATCHES = (PATCH_0092, PATCH_0148, PATCH_0149, PATCH_0150)

CANONICAL_SERIES = Path("patches/series")
PLANNER_SERIES = Path("patches/series-a72-reject-gate-a41-planner")
PRE_A41_SERIES = Path("patches/series-a72-reject-gate")
PLANNER_FRAGMENT = Path("configs/gemini-a72-a41-planner.fragment")
MANIFEST = Path("kernel/manifest.json")
PLANNER_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-planner"
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
    str(PLANNER_FRAGMENT),
)

EXPECTED_PATCH_SHA256 = {
    PATCH_0092: "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5",
    PATCH_0148: "953a990c6c9f0f91822b9923a2adf6ebf71e326ea5c570dd133c4178059750fb",
    PATCH_0149: "3c0911601d73ba73cce6a122d62df4e4f0273aeb9474e81c871aba2214feadc0",
    PATCH_0150: "d9244d9f3815092b492608cd7882e471bd5026dc15f5ed4afe32ad94961dd427",
}
EXPECTED_PATCH_COMMITS = {
    PATCH_0148: "5ba594da7b561ceed4d8b060bf12a3bfa3bcbe23",
    PATCH_0149: "08eb3392a57d30922cd06a4af0e55ee49628cdce",
    PATCH_0150: "4c0300398ae77c99faca19bb6333868e1f70b299",
}
EXPECTED_CANONICAL_PREFIX_SHA256 = (
    "ecca97afbb79a45399a622b6db68a1e6fb243202fdc195983171b24be64c4045"
)
EXPECTED_PLANNER_SERIES_SHA256 = (
    "50025a818157b395a8ee8980c279463876b94734da8a120c695b7c6d01690e05"
)
EXPECTED_PATCHSET_SHA256 = (
    "5ce33180a753e2c386986c200563bf46c773cb9ec171916a9121e5e2a7cfbaa5"
)
EXPECTED_SOURCE_STATE_SHA256 = (
    "a1573b40b7b8f5a8a87f7a2b9a431090bf714ed52c79cf1e93c78d28ce633c56"
)
EXPECTED_CONFIG_INPUT_SHA256 = (
    "528b2bbdea4df1e872d4671e73a788d0ecf3469d1ba24d6335ed158a1b8f63cf"
)
EXPECTED_SOURCE_PARENT_SHA256 = (
    "2ef15df475d00e5ae0f85a1f25866cd4267a407af974b5c8cf992ad2e15e0a9b"
)
EXPECTED_PRE_A41_PATCHSET_SHA256 = (
    "ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd"
)

EXPECTED_BASE_COMMIT = "df9447fb8be9b03a643b00111dd25f6ce62be719"
EXPECTED_BASE_TREE = "265ffcaf56d7ec453e0dd017f19a5373a13960ba"
EXPECTED_ARM64_NCAPS = 130
EXPECTED_PLANNER_SOURCE_TREE = "f29f66ee14829fca4a452d4a390ad6f23556b64e"
EXPECTED_BASE_BLOBS = {
    "arch/arm64/Kconfig": "10c69474f276197062f5cf6bb1affcfe1a3efd5f",
    "arch/arm64/Kconfig.platforms": "72c812e76b0b115b2d59c199df5fc56060cb9da7",
    "arch/arm64/include/asm/cpu_ops.h": "a444c8915e886397d9cf117b0b6982fbd453d806",
    "arch/arm64/kernel/Makefile": "ef1f74332272b3d02d679b7797b7c8d3ea5bacdc",
    "arch/arm64/kernel/cpu_errata.c": "4b0d5d9328972f0a3dd9d5ddf04cb1bfb0bb173a",
    "arch/arm64/kernel/cpu_ops.c": "b773e4dbe349b07545ace8920579ab2322cfd976",
    "arch/arm64/kernel/cpufeature.c": "6d53bb15cf7bb48e926330c7ff0c93c0c14b14c2",
    "arch/arm64/kernel/mt6797_psci.c": "2777a3ee0fa11ac666106b0351c7cdb87a386c73",
    "arch/arm64/kernel/smp.c": "1aa324104afb440951e0b5da1bd9d6ad84aa2f72",
}
NEW_SOURCE_PATHS = {
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/late_cpu_profile.c",
}
EXPECTED_0150_PATHS = {
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/cpu_errata.c",
    "arch/arm64/kernel/cpufeature.c",
    "arch/arm64/kernel/late_cpu_profile.c",
    "arch/arm64/kernel/mt6797_psci.c",
}
EXPECTED_0150_INDEXES = {
    "arch/arm64/include/asm/late_cpu_profile.h": ("1215abfdf", "45f7fa222"),
    "arch/arm64/kernel/cpu_errata.c": ("4b0d5d932", "6816b59a8"),
    "arch/arm64/kernel/cpufeature.c": ("6d53bb15c", "134d782be"),
    "arch/arm64/kernel/late_cpu_profile.c": ("c611c2846", "0e3f7bae7"),
    "arch/arm64/kernel/mt6797_psci.c": ("45ef7a6c9", "f01f6c4f7"),
}

EXPECTED_CAPABILITIES = (
    "ARM64_SPECTRE_BHB",
    "ARM64_WORKAROUND_1742098",
    "ARM64_WORKAROUND_SPECULATIVE_AT",
)
EXPECTED_EFFECTS = (
    "ARM64_LATE_CPU_EFFECT_BHB_MAX_K",
    "ARM64_LATE_CPU_EFFECT_BHB_SYSTEM_LOOP",
    "ARM64_LATE_CPU_EFFECT_BHB_MITIGATION_STATE",
    "ARM64_LATE_CPU_EFFECT_BHB_VECTOR_TEMPLATE",
    "ARM64_LATE_CPU_EFFECT_BHB_ALTERNATIVE",
    "ARM64_LATE_CPU_EFFECT_BHB_V2_DEPENDENCY",
    "ARM64_LATE_CPU_EFFECT_COMPAT_AES_CLEAR",
    "ARM64_LATE_CPU_EFFECT_SPEC_AT_FINALIZATION",
)
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
)
EXPECTED_PROFILE_BLOCKERS = {
    symbol
    for bit, symbol, owner, status in EXPECTED_BLOCKERS
    if owner == "profile" and status == "blocked"
}
EXPECTED_FOUNDATION_BLOCKERS = EXPECTED_PROFILE_BLOCKERS | {
    "ARM64_LATE_CPU_BLOCK_CAP_INVENTORY"
}
EXPECTED_IMPLEMENTATION_MARKERS = {
    "implementation_state": "PARTIAL_READ_ONLY_PLANNER",
    "a41_complete": "no",
    "source_parent_identity": "pre_a41_non_circular",
    "config_input_identity": "exact_selected_input_digest",
    "canonical_slot_traversal": "implemented",
    "descriptor_structure_guard": "implemented",
    "live_target_match_callbacks": "invoked_no",
    "midr_all_versions_helper": "implemented",
    "deterministic_target_cap_count": "3",
    "deterministic_required_cap_count": "3",
    "planned_bhb_method": "ARM64_LATE_CPU_BHB_LOOP",
    "planned_bhb_k": "8",
    "planned_effect_count": "8",
    "remaining_local_classification": "unresolved",
    "cap_inventory_owner": "core",
    "profile_prepare_result": "-EAGAIN",
    "profile_commit": "absent",
    "production_ready_reachable": "no",
    "production_cpu_on_path": "absent",
    "current_cpu_boot_veto": "required",
    "current_cpu_disable_veto": "required",
    "boot_candidate": "false",
    "build_authorized": "no",
    "device_action_authorized": "no",
    "hardware_support_claim": "none",
}
EXPECTED_CAPABILITY_CLASSES = (
    ("canonical_slots", "all surviving non-null cpucap_ptrs", "structurally validated"),
    ("deterministic_target", "local", "BHB 1742098 speculative-AT"),
    (
        "conditional_local",
        "local",
        "Spectre-v2 Spectre-v4 CTR KPTI and other predicates",
    ),
    ("strict_boot", "boot", "exact equality unproven"),
    ("boot_feature", "boot", "target may not miss finalized true state"),
    ("system_feature", "system", "target may not miss finalized true state"),
    ("native_hwcap", "userspace", "complete bitmap unproven"),
    ("compat_hwcap", "userspace", "complete bitmap plus AES fixup unproven"),
)
GENERATED_RESULTS = {
    "results/offline-validation-20260805.txt",
    "results/mutation-validation-20260805.txt",
}
EXPECTED_TSV_SHA256 = {
    "implementation.tsv": "34b76afdbc410c9c6ad425f9c494e0b5bfa009bdbd9651d5955623a6cef5477e",
    "blockers.tsv": "9341b8a7035063f108676365bc28c86440083343bd93b2a4e66d98f9f3d27f1b",
    "effects.tsv": "2c249366af9e23416c0f5479658dbd4c029a970205ddab18f7f61c480181366a",
    "capability-classes.tsv": "03bf0bbed73f4ce38bd4720afd108cd7287e3c470560765623ea35ece9222c43",
}
EXPECTED_MUTATION_COUNT = 69


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
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def series_entries(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def canonical_prefix_hash(path: Path, terminal_entry: str) -> str:
    """Hash the historical canonical prefix while allowing later append-only work."""

    data = path.read_bytes()
    marker = (terminal_entry + "\n").encode()
    require(data.count(marker) == 1, "canonical terminal patch occurrence changed")
    end = data.index(marker) + len(marker)
    return sha256_bytes(data[:end])


def is_subsequence(candidate: Sequence[str], canonical: Sequence[str]) -> bool:
    cursor = 0
    for entry in canonical:
        if cursor < len(candidate) and candidate[cursor] == entry:
            cursor += 1
    return cursor == len(candidate)


def safe_relative(value: str, scope: str) -> PurePosixPath:
    path = PurePosixPath(value)
    require(value and not path.is_absolute(), "{} is unsafe: {}".format(scope, value))
    require(not any(char.isspace() for char in value), "{} is unsafe: {}".format(scope, value))
    require(
        all(part not in ("", ".", "..") for part in path.parts),
        "{} is unsafe: {}".format(scope, value),
    )
    return path


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


def patch_header(patch: str) -> str:
    marker = patch.find("diff --git ")
    require(marker >= 0, "format-patch has no diff")
    return patch[:marker]


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
    result: list[str] = []
    in_hunk = False
    for line in section.splitlines():
        if line.startswith("@@ "):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith((" ", "+")) and not line.startswith("+++"):
            result.append(line[1:])
    return "\n".join(result)


def extract_c_function(text: str, name: str) -> str:
    match = re.search(r"\b{}\s*\([^;]*?\)\s*\{{".format(re.escape(name)), text, re.DOTALL)
    require(match is not None, "missing function {}".format(name))
    brace = text.find("{", match.start())
    depth = 0
    for cursor in range(brace, len(text)):
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : cursor + 1]
    raise ValidationError("unterminated function {}".format(name))


def extract_c_initializer(text: str, name: str) -> str:
    match = re.search(r"\b{}\s*\[\s*\]\s*=\s*\{{".format(re.escape(name)), text)
    require(match is not None, "missing source array {}".format(name))
    brace = text.find("{", match.start())
    depth = 0
    for cursor in range(brace, len(text)):
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : cursor + 1]
    raise ValidationError("unterminated source array {}".format(name))


def c_entry_containing(initializer: str, token: str) -> str:
    require(initializer.count(token) == 1, "source binding occurrence changed: {}".format(token))
    position = initializer.find(token)
    stack: list[int] = []
    enclosing: list[tuple[int, int]] = []
    for cursor, character in enumerate(initializer):
        if character == "{":
            stack.append(cursor)
        elif character == "}":
            require(bool(stack), "source initializer braces are malformed")
            start = stack.pop()
            if start < position < cursor:
                enclosing.append((start, cursor))
    require(enclosing, "source binding entry is malformed: {}".format(token))
    start, end = max(enclosing, key=lambda pair: pair[0])
    return initializer[start : end + 1]


def initializer_elements(initializer: str) -> list[str]:
    """Split the outer initializer on commas not nested in C delimiters."""

    outer = initializer.find("{")
    require(outer >= 0 and initializer.endswith("}"), "source initializer is malformed")
    content = initializer[outer + 1 : -1]
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    content = re.sub(r"//[^\n]*", "", content)
    content = re.sub(r"^\s*#.*$", "", content, flags=re.MULTILINE)
    elements: list[str] = []
    start = 0
    round_depth = square_depth = brace_depth = 0
    quote = ""
    escaped = False
    for cursor, character in enumerate(content):
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
            continue
        if character in ("'", '"'):
            quote = character
        elif character == "(":
            round_depth += 1
        elif character == ")":
            round_depth -= 1
        elif character == "[":
            square_depth += 1
        elif character == "]":
            square_depth -= 1
        elif character == "{":
            brace_depth += 1
        elif character == "}":
            brace_depth -= 1
        elif character == "," and not (round_depth or square_depth or brace_depth):
            element = content[start:cursor].strip()
            if element:
                elements.append(element)
            start = cursor + 1
        require(
            round_depth >= 0 and square_depth >= 0 and brace_depth >= 0,
            "source initializer delimiters are malformed",
        )
    tail = content[start:].strip()
    if tail:
        elements.append(tail)
    require(not (round_depth or square_depth or brace_depth or quote), "source initializer is unterminated")
    return elements


def validate_bounded_initializer(initializer: str, name: str) -> None:
    elements = initializer_elements(initializer)
    require(elements and re.fullmatch(r"\{\s*\}", elements[-1]), "source list sentinel missing: {}".format(name))
    require(
        0 < len(elements) - 1 < EXPECTED_ARM64_NCAPS,
        "source list bound changed: {}".format(name),
    )


def validate_capability_source_tables(cpu_errata: str, cpufeature: str) -> None:
    """Validate exact bounded list sentinels and their canonical parent bindings."""

    errata_table = extract_c_initializer(cpu_errata, "arm64_errata")
    features_table = extract_c_initializer(cpufeature, "arm64_features")
    require(
        initializer_elements(errata_table)
        and re.fullmatch(r"\{\s*\}", initializer_elements(errata_table)[-1]),
        "arm64_errata final sentinel missing",
    )
    require(
        initializer_elements(features_table)
        and re.fullmatch(r"\{\s*\}", initializer_elements(features_table)[-1]),
        "arm64_features final sentinel missing",
    )

    local_lists = {
        "erratum_843419_list": "ARM64_WORKAROUND_843419",
        "qcom_erratum_1003_list": "ARM64_WORKAROUND_QCOM_FALKOR_E1003",
        "arm64_repeat_tlbi_list": "ARM64_WORKAROUND_REPEAT_TLBI",
    }
    for name, capability in local_lists.items():
        initializer = extract_c_initializer(cpu_errata, name)
        validate_bounded_initializer(initializer, name)
        entry = c_entry_containing(errata_table, ".match_list = {},".format(name))
        ordered(
            entry,
            [
                ".capability = {},".format(capability),
                ".matches = cpucap_multi_entry_cap_matches,",
                ".match_list = {},".format(name),
            ],
            "canonical list binding {}".format(name),
        )

    target_lists = {
        "erratum_speculative_at_list": (
            "ARM64_WORKAROUND_SPECULATIVE_AT",
            "ERRATA_MIDR_RANGE_LIST(erratum_speculative_at_list)",
        ),
        "broken_aarch32_aes": (
            "ARM64_WORKAROUND_1742098",
            "CAP_MIDR_RANGE_LIST(broken_aarch32_aes)",
        ),
    }
    for name, (capability, binding) in target_lists.items():
        initializer = extract_c_initializer(cpu_errata, name)
        validate_bounded_initializer(initializer, name)
        require(
            initializer.count("MIDR_ALL_VERSIONS(MIDR_CORTEX_A72)") == 1,
            "exact A72 all-versions row changed: {}".format(name),
        )
        entry = c_entry_containing(errata_table, binding)
        require(
            ".capability = {},".format(capability) in entry,
            "target MIDR list binding changed: {}".format(name),
        )

    nested_entry = c_entry_containing(
        features_table, ".capability = ARM64_HAS_NESTED_VIRT,"
    )
    match_list = re.search(
        r"\.match_list\s*=\s*\(const struct arm64_cpu_capabilities\s*\[\]\)\s*\{",
        nested_entry,
    )
    require(match_list is not None, "nested-virtualization match list binding changed")
    brace = nested_entry.find("{", match_list.start())
    depth = 0
    nested_initializer = ""
    for cursor in range(brace, len(nested_entry)):
        if nested_entry[cursor] == "{":
            depth += 1
        elif nested_entry[cursor] == "}":
            depth -= 1
            if depth == 0:
                nested_initializer = nested_entry[brace : cursor + 1]
                break
    require(bool(nested_initializer), "nested-virtualization match list is unterminated")
    validate_bounded_initializer(nested_initializer, "nested-virtualization match_list")


def parse_index(section: str) -> tuple[str, str]:
    match = re.search(
        r"^index ([0-9a-f]+)\.\.([0-9a-f]+)(?: [0-7]{6})?$",
        section,
        flags=re.MULTILINE,
    )
    require(match is not None, "patch section lacks an index line")
    return match.group(1), match.group(2)


def read_tsv(path: Path, fields: Sequence[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(reader.fieldnames == list(fields), "{}: header changed".format(path.name))
        rows = list(reader)
    require(rows, "{}: table is empty".format(path.name))
    require(
        all(None not in row and all(value != "" for value in row.values()) for row in rows),
        "{}: malformed or empty cell".format(path.name),
    )
    return rows


def validate_bounded_new_paths(repo: Path) -> None:
    """Reject sensitive or non-reviewable residue in this experiment's new paths."""

    experiment = repo / EXPERIMENT_REL
    experiment_files = {
        Path("README.md"),
        Path("DESIGN.md"),
        Path("results/blockers.tsv"),
        Path("results/capability-classes.tsv"),
        Path("results/effects.tsv"),
        Path("results/implementation.tsv"),
        Path("results/kernel-static-review-20260805.txt"),
        Path("scripts/validate.py"),
        Path("scripts/test_mutations.py"),
    }
    experiment_files.update(Path(relative) for relative in GENERATED_RESULTS)
    actual_experiment_files = {
        path.relative_to(experiment)
        for path in experiment.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    require(
        actual_experiment_files <= experiment_files,
        "unexpected experiment residue: {}".format(
            sorted(str(path) for path in actual_experiment_files - experiment_files)
        ),
    )
    paths = [repo / PLANNER_FRAGMENT, repo / PLANNER_SERIES, repo / PATCH_0150]
    paths.extend(experiment / relative for relative in sorted(actual_experiment_files))
    personal_markers = ("/" + "Users/", "/" + "home/", "C:\\" + "Users\\")
    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    credential_assignment = re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret|credential)"
        r"\s*[:=]\s*[\"'][^\"'\n]{4,}"
    )
    private_identifier = re.compile(
        r"(?i)\b(?:imei|serial(?:_number)?)\s*[:=]\s*[\"']?[A-Za-z0-9-]{6,}"
    )

    def scan_text(text: str, label: object) -> None:
        require(
            not any(marker in text for marker in personal_markers),
            "personal absolute path in bounded new files: {}".format(label),
        )
        require(private_key_marker not in text, "private-key block in bounded new files: {}".format(label))
        require(not credential_assignment.search(text), "credential assignment in bounded new files: {}".format(label))
        require(not private_identifier.search(text), "private identifier in bounded new files: {}".format(label))

    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        require(not path.is_symlink(), "bounded new path is a symlink: {}".format(path))
        if not path.is_file():
            continue
        relative = path.relative_to(repo)
        require("artifacts" not in relative.parts, "artifacts path entered bounded new files")
        try:
            text = path.read_text()
        except UnicodeDecodeError as error:
            raise ValidationError("bounded new path is not reviewable text: {}".format(relative)) from error
        scan_text(text, relative)

    if (repo / ".git").exists():
        modified = (
            "docs/ROADMAP.md",
            "experiments/README.md",
            "kernel/manifest.json",
            "patches/series",
        )
        diff = subprocess.run(
            [
                "git",
                "--no-pager",
                "--no-replace-objects",
                "-C",
                str(repo),
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--unified=0",
                "HEAD",
                "--",
                *modified,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(diff.returncode == 0, "bounded added-line scan could not read Git diff")
        added_lines = "\n".join(
            line[1:]
            for line in diff.stdout.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        scan_text(added_lines, "modified-file added lines")


def mutation_case_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "mutations"
        ),
        None,
    )
    require(function is not None, "mutation suite has no mutations function")
    returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
    require(len(returns) == 1 and isinstance(returns[0].value, ast.List), "mutation suite return shape changed")
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
    require(len(names) == EXPECTED_MUTATION_COUNT, "mutation suite case count changed")
    require(len(names) == len(set(names)), "mutation suite contains duplicate case names")
    return names


def config_input_hash(repo: Path, profile_name: str, profile: dict) -> str:
    lines = ["profile={}".format(profile_name), "base={}".format(profile["base"])]
    for fragment in profile["fragments"]:
        path = repo / fragment
        require(path.is_file(), "missing profile fragment {}".format(fragment))
        lines.append("{}  {}".format(sha256_file(path), fragment))
    return sha256_bytes(("\n".join(lines) + "\n").encode())


def patchset_hash(repo: Path, series_relative: Path) -> str:
    series_path = repo / series_relative
    lines = ["{}  {}".format(sha256_file(series_path), series_relative)]
    for entry in series_entries(series_path.read_text()):
        patch_path = series_path.parent / entry
        require(patch_path.is_file(), "selected patch is missing: {}".format(entry))
        lines.append("{}  {}".format(sha256_file(patch_path), entry))
    return sha256_bytes(("\n".join(lines) + "\n").encode())


def source_state_hash(repo: Path, series_relative: Path) -> str:
    manifest = json.loads((repo / MANIFEST).read_text())
    kernel = manifest["kernel"]
    material = "{}\n{}\n{}\n".format(
        kernel["version"], kernel["sha256"], patchset_hash(repo, series_relative)
    )
    return sha256_bytes(material.encode())


def digest_u64_literals(digest: str) -> tuple[str, ...]:
    require(bool(re.fullmatch(r"[0-9a-f]{64}", digest)), "invalid SHA-256 digest")
    return tuple("0x" + digest[index : index + 16] for index in range(0, 64, 16))


def parse_definitions(text: str, prefix: str) -> list[tuple[int, str]]:
    definitions = re.findall(
        r"^#define\s+(" + re.escape(prefix) + r"[A-Z0-9_]+)\s+BIT_ULL\((\d+)\)",
        text,
        flags=re.MULTILINE,
    )
    return [(int(bit), symbol) for symbol, bit in definitions]


def validate_experiment_record(repo: Path, *, check_frozen_evidence: bool) -> None:
    experiment = repo / EXPERIMENT_REL
    required_files = {
        "README.md",
        "DESIGN.md",
        "results/blockers.tsv",
        "results/capability-classes.tsv",
        "results/effects.tsv",
        "results/implementation.tsv",
        "results/kernel-static-review-20260805.txt",
        "scripts/validate.py",
        "scripts/test_mutations.py",
    }
    if check_frozen_evidence:
        required_files.update(GENERATED_RESULTS)
    for relative in required_files:
        require((experiment / relative).is_file(), "missing experiment file {}".format(relative))

    readme = (experiment / "README.md").read_text()
    design = (experiment / "DESIGN.md").read_text()
    combined = readme + "\n" + design
    require_tokens(
        combined,
        [
            "PARTIAL_READ_ONLY_PLANNER",
            "a41_complete=no",
            "boot_candidate=false",
            "build_authorized=no",
            "device_action_authorized=no",
            "Every other compiled local predicate remains UNRESOLVED",
            "No such commit exists in patch 0150",
            EXPECTED_PATCH_COMMITS[PATCH_0150],
            EXPECTED_PATCH_SHA256[PATCH_0150],
            EXPECTED_PLANNER_SERIES_SHA256,
            EXPECTED_PATCHSET_SHA256,
            EXPECTED_SOURCE_STATE_SHA256,
            EXPECTED_CONFIG_INPUT_SHA256,
            EXPECTED_SOURCE_PARENT_SHA256,
            EXPECTED_BASE_COMMIT,
            EXPECTED_BASE_TREE,
            "surviving canonical arm64",
            "ARM64_NCAPS` loops cap iterations but cannot supply C object",
            "exact prepared Git source checkout",
            "no kernel build/output tree",
            "review and integrity attestation for the exact scripts",
            "not a protective sandbox for arbitrary modified Python",
        ],
        "experiment claim boundary",
    )
    require("/" + "Users/" not in combined, "personal absolute path in experiment docs")

    static_review = (experiment / "results/kernel-static-review-20260805.txt").read_text()
    require_tokens(
        static_review,
        [
            "source_base_commit=" + EXPECTED_BASE_COMMIT,
            "source_head_commit=" + EXPECTED_PATCH_COMMITS[PATCH_0150],
            "source_head_tree=" + EXPECTED_PLANNER_SOURCE_TREE,
            "source_diff_sha256=bd416e32c751263092d36228f5dd9234eecb5996b0f0a887f04695a5a89cff6f",
            "patch_0150_sha256=" + EXPECTED_PATCH_SHA256[PATCH_0150],
            "review_3_errors=1",
            "review_3_warnings=0",
            "review_3_checks=0",
            "review_3_lines=567",
            "review_3_expected_error=Missing Signed-off-by",
            "review_4_output=No duplicate includes found.",
            "review_7=git diff --check",
            "review_7_result=clean",
            "review_8=bounded new-file license and sensitive-data scan",
            "review_8_result=clean",
            "review_8_scope=planner patch series fragment experiment files and added lines in modified repository files",
            "review_8_license=project-authored validation and documentation; no vendored proprietary or submission-ready material",
            "compile_run=no",
            "build_run=no",
            "device_action_run=no",
            "RESULT=PASS_WITH_EXPECTED_EXPERIMENT_ONLY_SIGNOFF_EXCEPTION",
        ],
        "kernel static-review evidence",
    )

    for document in (experiment / "README.md", experiment / "DESIGN.md"):
        text = document.read_text()
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            clean = target.split("#", 1)[0]
            destination = (document.parent / clean).resolve()
            relative = str(destination.relative_to(experiment.resolve())) if destination.is_relative_to(experiment.resolve()) else ""
            if relative in GENERATED_RESULTS and not check_frozen_evidence:
                continue
            require(destination.exists(), "document link target is missing: {}".format(target))

    implementations = read_tsv(
        experiment / "results/implementation.tsv", ("key", "value", "evidence")
    )
    actual_markers = {row["key"]: row["value"] for row in implementations}
    require(len(actual_markers) == len(implementations), "duplicate implementation marker")
    require(
        actual_markers == EXPECTED_IMPLEMENTATION_MARKERS,
        "implementation claim boundary changed",
    )
    require(
        sha256_file(experiment / "results/implementation.tsv")
        == EXPECTED_TSV_SHA256["implementation.tsv"],
        "implementation.tsv full rows changed",
    )

    blockers = read_tsv(
        experiment / "results/blockers.tsv",
        ("bit", "symbol", "owner", "status", "evidence_needed"),
    )
    blocker_projection = [
        (int(row["bit"]), row["symbol"], row["owner"], row["status"])
        for row in blockers
    ]
    require(blocker_projection == list(EXPECTED_BLOCKERS), "blocker table changed")
    require(
        sha256_file(experiment / "results/blockers.tsv")
        == EXPECTED_TSV_SHA256["blockers.tsv"],
        "blockers.tsv full rows changed",
    )

    effects = read_tsv(
        experiment / "results/effects.tsv", ("bit", "symbol", "scope", "status")
    )
    effect_projection = [(int(row["bit"]), row["symbol"], row["status"]) for row in effects]
    require(
        effect_projection
        == [(bit, symbol, "planned-only") for bit, symbol in enumerate(EXPECTED_EFFECTS)],
        "effect table changed",
    )
    require(
        sha256_file(experiment / "results/effects.tsv")
        == EXPECTED_TSV_SHA256["effects.tsv"],
        "effects.tsv full rows changed",
    )

    classes = read_tsv(
        experiment / "results/capability-classes.tsv",
        ("class", "scope", "result", "closure"),
    )
    class_projection = [(row["class"], row["scope"], row["result"]) for row in classes]
    require(class_projection == list(EXPECTED_CAPABILITY_CLASSES), "capability class table changed")
    require(
        sha256_file(experiment / "results/capability-classes.tsv")
        == EXPECTED_TSV_SHA256["capability-classes.tsv"],
        "capability-classes.tsv full rows changed",
    )

    offline = experiment / "results/offline-validation-20260805.txt"
    if check_frozen_evidence:
        offline_lines = offline.read_text().splitlines()
        expected_offline: list[str | None] = [
            "PASS bounded-new-files",
            "PASS experiment-record",
            "PASS patch-identities",
            "PASS manifest-series",
            "PASS planner-source-contract",
            "PASS offline-boundary",
            "PASS sequential-source-application",
            "patch_0150_sha256=" + EXPECTED_PATCH_SHA256[PATCH_0150],
            "planner_series_sha256=" + EXPECTED_PLANNER_SERIES_SHA256,
            "planner_patchset_sha256=" + EXPECTED_PATCHSET_SHA256,
            "planner_source_state_sha256=" + EXPECTED_SOURCE_STATE_SHA256,
            "source_parent_sha256=" + EXPECTED_SOURCE_PARENT_SHA256,
            "config_inputs_sha256=" + EXPECTED_CONFIG_INPUT_SHA256,
            "source_base_commit=" + EXPECTED_BASE_COMMIT,
            "planner_source_commit=" + EXPECTED_PATCH_COMMITS[PATCH_0150],
            "planner_source_tree=" + EXPECTED_PLANNER_SOURCE_TREE,
            "validator_sha256=" + sha256_file(experiment / "scripts/validate.py"),
            None,
            None,
            "implementation_state=PARTIAL_READ_ONLY_PLANNER",
            "a41_complete=no",
            "build_authorized=no",
            "device_action_authorized=no",
            "RESULT PASS 7/7",
        ]
        require(len(offline_lines) == len(expected_offline), "frozen offline transcript line count changed")
        require(
            all(expected is None or offline_lines[index] == expected for index, expected in enumerate(expected_offline)),
            "frozen offline transcript structure changed",
        )
        require(
            bool(re.fullmatch(r"python_version=\d+\.\d+\.\d+", offline_lines[17])),
            "frozen offline transcript lacks an exact Python version",
        )
        require(
            bool(re.fullmatch(r"git_version=git version \S.*", offline_lines[18])),
            "frozen offline transcript lacks an exact Git version",
        )
    mutations = experiment / "results/mutation-validation-20260805.txt"
    if check_frozen_evidence:
        mutation_lines = mutations.read_text().splitlines()
        names = mutation_case_names(experiment / "scripts/test_mutations.py")
        expected_mutations: list[str | None] = [
            "PASS mutation {:02d} {}".format(index, name)
            for index, name in enumerate(names, 1)
        ]
        expected_mutations.extend(
            [
                "validator_sha256=" + sha256_file(experiment / "scripts/validate.py"),
                "mutation_suite_sha256=" + sha256_file(experiment / "scripts/test_mutations.py"),
                None,
                "baseline_static_checks=6",
                "mutation_count={}".format(EXPECTED_MUTATION_COUNT),
                "RESULT PASS {0}/{0}".format(EXPECTED_MUTATION_COUNT),
            ]
        )
        require(len(mutation_lines) == len(expected_mutations), "frozen mutation transcript line count changed")
        require(
            all(expected is None or mutation_lines[index] == expected for index, expected in enumerate(expected_mutations)),
            "frozen mutation transcript structure changed",
        )
        require(
            bool(
                re.fullmatch(
                    r"python_version=\d+\.\d+\.\d+",
                    mutation_lines[EXPECTED_MUTATION_COUNT + 2],
                )
            ),
            "frozen mutation transcript lacks an exact Python version",
        )


def validate_patch_identities(repo: Path, patches: dict[Path, str], pin_hashes: bool) -> None:
    if pin_hashes:
        for relative, expected in EXPECTED_PATCH_SHA256.items():
            require(sha256_file(repo / relative) == expected, "{} SHA-256 changed".format(relative.name))

    for relative, commit in EXPECTED_PATCH_COMMITS.items():
        match = re.match(r"From ([0-9a-f]{40}) ", patches[relative])
        require(match is not None, "{} missing format-patch identity".format(relative.name))
        require(match.group(1) == commit, "{} source commit changed".format(relative.stem[:4]))

    patch150 = patches[PATCH_0150]
    header = patch_header(patch150)
    require(
        header.count("Subject: [PATCH] arm64: add read-only late-CPU capability planner") == 1,
        "0150 subject changed",
    )
    require("Signed-off-by:" not in header, "0150 experiment patch gained a sign-off")
    require_tokens(
        re.sub(r"\s+", " ", header),
        [
            "This experiment-only change has no certifying sign-off",
            "no live capability, vector, alternative, HWCAP, or CPU path is changed",
        ],
        "0150 format-patch header",
    )
    sections = patch_sections(patch150)
    require(set(sections) == EXPECTED_0150_PATHS, "0150 changed-path set differs")
    for path, expected in EXPECTED_0150_INDEXES.items():
        require(parse_index(sections[path]) == expected, "0150 preimage changed for {}".format(path))


def validate_series_file(repo: Path, relative: Path, label: str) -> list[str]:
    safe_relative(str(relative), label)
    path = repo / relative
    require(path.is_file() and not path.is_symlink(), "{} is missing or not regular".format(label))
    entries = series_entries(path.read_text())
    require(entries, "{} selects no patches".format(label))
    require(len(entries) == len(set(entries)), "{} contains duplicate patches".format(label))
    for entry in entries:
        safe_relative(entry, "{} patch path".format(label))
        patch = path.parent / entry
        require(
            patch.is_file() and not patch.is_symlink(),
            "{} patch is missing or not regular: {}".format(label, entry),
        )
    return entries


def validate_series_and_manifest(repo: Path, pin_hashes: bool) -> None:
    canonical = validate_series_file(repo, CANONICAL_SERIES, "canonical series")
    selected = validate_series_file(repo, PLANNER_SERIES, "planner series")
    pre_a41 = validate_series_file(repo, PRE_A41_SERIES, "pre-A41 series")
    p92 = str(PATCH_0092.relative_to("patches"))
    p148 = str(PATCH_0148.relative_to("patches"))
    p149 = str(PATCH_0149.relative_to("patches"))
    p150 = str(PATCH_0150.relative_to("patches"))
    require(len(selected) == 92, "planner series entry count changed")
    require(selected[-4:] == [p92, p148, p149, p150], "planner terminal patch order changed")
    positions = [canonical.index(entry) if entry in canonical else -1 for entry in (p148, p149, p150)]
    require(
        positions[0] >= 0 and positions[1] == positions[0] + 1 and positions[2] == positions[1] + 1,
        "canonical planner patch order changed",
    )
    require(is_subsequence(selected, canonical), "planner series is not a canonical subsequence")
    require(is_subsequence(pre_a41, canonical), "pre-A41 series is not a canonical subsequence")
    if pin_hashes:
        require(
            canonical_prefix_hash(repo / CANONICAL_SERIES, p150)
            == EXPECTED_CANONICAL_PREFIX_SHA256,
            "canonical series prefix identity changed",
        )
        require(sha256_file(repo / PLANNER_SERIES) == EXPECTED_PLANNER_SERIES_SHA256, "planner series identity changed")
        require(patchset_hash(repo, PLANNER_SERIES) == EXPECTED_PATCHSET_SHA256, "planner patchset identity changed")
        require(source_state_hash(repo, PLANNER_SERIES) == EXPECTED_SOURCE_STATE_SHA256, "planner source-state identity changed")
        require(
            patchset_hash(repo, PRE_A41_SERIES) == EXPECTED_PRE_A41_PATCHSET_SHA256,
            "pre-A41 reject-gate patchset identity changed",
        )
        require(
            source_state_hash(repo, PRE_A41_SERIES) == EXPECTED_SOURCE_PARENT_SHA256,
            "pre-A41 source parent identity changed",
        )

    manifest = json.loads((repo / MANIFEST).read_text())
    config = manifest.get("config", {})
    profiles = config.get("profiles", {})
    require(config.get("default_profile") == "full", "default profile changed")
    require(isinstance(profiles, dict) and profiles, "manifest profiles are missing")
    require(config.get("default_profile") in profiles, "default profile is not selectable")
    fallback = manifest.get("patch_series")
    for name, profile in profiles.items():
        require(bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name)), "unsafe profile name {}".format(name))
        require(isinstance(profile, dict), "profile {} is not an object".format(name))
        series_value = profile.get("patch_series", fallback)
        require(isinstance(series_value, str), "profile {} has no patch series".format(name))
        series_path = safe_relative(series_value, "profile {} series".format(name))
        require(series_path.parts[0] == "patches", "profile {} series escapes patches".format(name))
        profile_entries = validate_series_file(repo, Path(series_value), "profile {} series".format(name))
        require(
            is_subsequence(profile_entries, canonical),
            "profile {} series is not a canonical subsequence".format(name),
        )

    require(PLANNER_PROFILE in profiles, "planner profile is missing")
    planner = profiles[PLANNER_PROFILE]
    require(planner.get("base") == "defconfig", "planner profile base changed")
    require(planner.get("patch_series") == str(PLANNER_SERIES), "planner series selection changed")
    require(tuple(planner.get("fragments", ())) == EXPECTED_PROFILE_FRAGMENTS, "planner fragment order changed")
    for name, profile in profiles.items():
        if name == PLANNER_PROFILE:
            continue
        require(profile.get("patch_series") != str(PLANNER_SERIES), "planner series leaked into profile {}".format(name))
        require(str(PLANNER_FRAGMENT) not in profile.get("fragments", []), "planner fragment leaked into profile {}".format(name))

    fragment = (repo / PLANNER_FRAGMENT).read_text()
    assignments = [
        line.strip()
        for line in fragment.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        assignments
        == [
            "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
            'CONFIG_LOCALVERSION="-gemini-a41-planner-blocked"',
        ],
        "planner fragment gained an unreviewed setting",
    )
    require("CONFIG_CMDLINE" not in "\n".join(assignments), "planner fragment changes the command line")
    require("maxcpus=" not in "\n".join(assignments), "planner fragment changes the CPU limit")
    require("maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(), "inherited maxcpus=8 guard changed")
    require(
        config_input_hash(repo, PLANNER_PROFILE, planner) == EXPECTED_CONFIG_INPUT_SHA256,
        "planner configuration-input identity changed",
    )


def macro_symbols(text: str, macro: str, terminator: str) -> set[str]:
    start = text.find("#define " + macro)
    end = text.find(terminator, start)
    require(start >= 0 and end > start, "missing macro {}".format(macro))
    return set(re.findall(r"ARM64_LATE_CPU_BLOCK_[A-Z0-9_]+", text[start:end]))


def validate_source_contract(patches: dict[Path, str]) -> None:
    p92 = patches[PATCH_0092]
    p148 = patches[PATCH_0148]
    p149 = patches[PATCH_0149]
    p150 = patches[PATCH_0150]
    sections148 = patch_sections(p148)
    sections149 = patch_sections(p149)
    sections150 = patch_sections(p150)

    header148 = added_source(sections148["arch/arm64/include/asm/late_cpu_profile.h"])
    blocker_defs = parse_definitions(header148, "ARM64_LATE_CPU_BLOCK_")
    require(
        blocker_defs == [(bit, symbol) for bit, symbol, _owner, _status in EXPECTED_BLOCKERS],
        "source blocker definitions changed",
    )

    header150 = patch_postimage_context(
        sections150["arch/arm64/include/asm/late_cpu_profile.h"]
    )
    require_tokens(
        header150,
        [
            "ARM64_LATE_CPU_ATTESTATION_ABI\t2",
            "ARM64_LATE_CPU_CAP_UNRESOLVED",
            "ARM64_LATE_CPU_CAP_ABSENT",
            "ARM64_LATE_CPU_CAP_PRESENT",
            "DECLARE_BITMAP(canonical_caps, ARM64_NCAPS)",
            "DECLARE_BITMAP(compiled_local_caps, ARM64_NCAPS)",
            "DECLARE_BITMAP(classified_local_caps, ARM64_NCAPS)",
            "DECLARE_BITMAP(early_local_caps, ARM64_NCAPS)",
            "DECLARE_BITMAP(target_local_caps, ARM64_NCAPS)",
            "DECLARE_BITMAP(required_local_caps, ARM64_NCAPS)",
            "DECLARE_BITMAP(conflicting_local_caps, ARM64_NCAPS)",
            "u64 planned_effects",
            "u8 local_caps_planned",
            "arm64_late_cpu_cap_uses_multi_entry_match",
            "(*classify_local_cap)",
            "int (*validate_plan)",
        ],
        "planner attestation schema",
    )
    ordered(
        header150,
        [
            "ARM64_LATE_CPU_CAP_UNRESOLVED",
            "ARM64_LATE_CPU_CAP_ABSENT",
            "ARM64_LATE_CPU_CAP_PRESENT",
        ],
        "capability tri-state order",
    )
    require(
        parse_definitions(header150, "ARM64_LATE_CPU_EFFECT_")
        == list(enumerate(EXPECTED_EFFECTS)),
        "effect definitions changed",
    )

    cpufeature = added_source(sections150["arch/arm64/kernel/cpufeature.c"])
    descriptor = extract_c_function(cpufeature, "validate_late_cpu_cap_descriptor")
    require_tokens(
        descriptor,
        [
            "cap->capability != slot",
            "switch (cap->type)",
            "if (!cap->match_list)",
            "cap->type & SCOPE_LOCAL_CPU",
            "!arm64_late_cpu_cap_uses_multi_entry_match(cap)",
            "i < ARM64_NCAPS",
            "if (!match->matches)",
            "if (match->match_list)",
            "return -E2BIG",
        ],
        "descriptor structure guard",
    )
    composite_types = tuple(re.findall(r"case\s+(ARM64_CPUCAP_[A-Z0-9_]+)\s*:", descriptor))
    require(
        composite_types
        == (
            "ARM64_CPUCAP_LOCAL_CPU_ERRATUM",
            "ARM64_CPUCAP_SYSTEM_FEATURE",
            "ARM64_CPUCAP_WEAK_LOCAL_CPU_FEATURE",
            "ARM64_CPUCAP_EARLY_LOCAL_CPU_FEATURE",
            "ARM64_CPUCAP_STRICT_BOOT_CPU_FEATURE",
            "ARM64_CPUCAP_BOOT_CPU_FEATURE",
        ),
        "descriptor exact composite types changed",
    )
    require(descriptor.count("continue;") == 0, "descriptor traversal gained an unaudited skip")

    classify = extract_c_function(cpufeature, "classify_late_cpu_cap")
    require(not re.search(r"(?:cap|match)->matches\s*\(", classify), "live target match callback added")
    require_tokens(
        classify,
        [
            "profile->classify_local_cap(cap, cap, draft)",
            "i < ARM64_NCAPS",
            "profile->classify_local_cap(cap, match, draft)",
            "case ARM64_LATE_CPU_CAP_UNRESOLVED",
            "unresolved = true",
            "case ARM64_LATE_CPU_CAP_ABSENT",
            "case ARM64_LATE_CPU_CAP_PRESENT",
            "present = true",
            "return -E2BIG",
        ],
        "tri-state fail-closed classification",
    )
    require_tokens(
        classify,
        [
            "*target_state = present ?",
            "ARM64_LATE_CPU_CAP_PRESENT :",
            "(unresolved ? ARM64_LATE_CPU_CAP_UNRESOLVED :",
        ],
        "canonical OR match-list classification",
    )
    require(
        not re.search(r"if\s*\(\s*i\s*==[^)]*\)\s*(?:\{\s*)?continue\s*;", classify),
        "match-member classification contains an unaudited skip",
    )
    require(classify.count("continue;") == 0, "match-member classification contains an unaudited skip")

    planner = extract_c_function(cpufeature, "arm64_plan_late_cpu_capabilities")
    require_tokens(
        planner,
        [
            "system_capabilities_finalized()",
            "cpus_have_cap(ARM64_ALWAYS_SYSTEM)",
            "for (i = 0; i < ARM64_NCAPS; i++)",
            "cpucap_ptrs[i]",
            "if (!cap)\n\t\t\tcontinue",
            "__set_bit(i, draft->canonical_caps)",
            "validate_late_cpu_cap_descriptor(cap, i)",
            "if (!(cap->type & SCOPE_LOCAL_CPU))",
            "__set_bit(i, draft->compiled_local_caps)",
            "cpus_have_cap(i)",
            "classify_late_cpu_cap(cap, draft, profile, &target_state)",
            "!bitmap_equal(draft->compiled_local_caps",
            "!bitmap_empty(draft->conflicting_local_caps, ARM64_NCAPS)",
            "draft->local_caps_planned = 1",
        ],
        "planner canonical traversal",
    )
    require(planner.count("return 0;") == 1, "planner gained an early success path")
    require(planner.count("continue;") == 6, "canonical planner traversal skip count changed")
    require(
        not re.search(r"if\s*\(\s*i\s*==[^)]*\)\s*(?:\{\s*)?continue\s*;", planner),
        "canonical planner traversal contains an unaudited slot skip",
    )
    for field in (
        "canonical_caps",
        "compiled_local_caps",
        "classified_local_caps",
        "early_local_caps",
        "target_local_caps",
        "required_local_caps",
        "conflicting_local_caps",
    ):
        require("bitmap_empty(draft->{}, ARM64_NCAPS)".format(field) in planner, "planner output guard missing {}".format(field))
    ordered(
        planner,
        [
            "__set_bit(i, draft->canonical_caps)",
            "validate_late_cpu_cap_descriptor(cap, i)",
            "if (!(cap->type & SCOPE_LOCAL_CPU))",
            "__set_bit(i, draft->compiled_local_caps)",
            "classify_late_cpu_cap(cap, draft, profile, &target_state)",
            "__set_bit(i, draft->classified_local_caps)",
        ],
        "planner canonical traversal",
    )
    ordered(
        planner,
        [
            "if (invalid)",
            "return -EINVAL",
            "if (incomplete ||",
            "return -EAGAIN",
            "if (!bitmap_empty(draft->conflicting_local_caps",
            "return -EINVAL",
            "draft->local_caps_planned = 1",
            "return 0",
        ],
        "planner classification completeness",
    )
    require(
        set(re.findall(r"ARM64_LATE_CPU_EFFECT_[A-Z0-9_]+", planner)) == set(EXPECTED_EFFECTS),
        "planner effect mapping changed",
    )
    require_tokens(
        planner,
        [
            "draft->bhb_method != ARM64_LATE_CPU_BHB_LOOP",
            "!draft->bhb_loop_count",
            "cpucap_late_cpu_optional(cap)",
            "cpucap_late_cpu_permitted(cap)",
        ],
        "planner capability policy",
    )
    required_tail = planner[planner.find("__set_bit(i, draft->required_local_caps)") :]
    require(
        tuple(re.findall(r"case\s+(ARM64_[A-Z0-9_]+)\s*:", required_tail))
        == EXPECTED_CAPABILITIES,
        "required capability allowlist changed",
    )

    errata = added_source(sections150["arch/arm64/kernel/cpu_errata.c"])
    match_guard = extract_c_function(
        errata, "arm64_late_cpu_cap_uses_multi_entry_match"
    )
    require_tokens(
        match_guard,
        ["return cap->matches == cpucap_multi_entry_cap_matches;"],
        "exact multi-entry callback guard",
    )
    require(
        bool(
            re.search(
                r"\{\s*return cap->matches == cpucap_multi_entry_cap_matches;\s*\}\s*$",
                match_guard,
            )
        ),
        "exact multi-entry callback guard changed",
    )
    midr = extract_c_function(errata, "arm64_late_cpu_midr_all_versions")
    require_tokens(
        midr,
        [
            "cap->matches == is_affected_midr_range",
            "if (cap->fixed_revs)",
            "cap->matches != is_affected_midr_range_list",
            "!cap->midr_range_list",
            "i < ARM64_NCAPS",
            "!range->rv_min && range->rv_max == rv_all",
            "ARM64_LATE_CPU_CAP_UNRESOLVED",
        ],
        "bounded exact MIDR classifier",
    )
    require("#ifdef CONFIG_ARM64_LATE_CPU_PROFILE" in errata, "MIDR helper is not configuration-bounded")

    platform = added_source(sections150["arch/arm64/kernel/mt6797_psci.c"])
    target_classifier = extract_c_function(platform, "mt6797_a72_classify_local_cap")
    require(
        not re.search(r"(?:cap|match)->matches\s*\(", target_classifier),
        "live target match callback added to selected profile",
    )
    require_tokens(
        target_classifier,
        [
            "case ARM64_SPECTRE_BHB",
            "match != cap",
            "attestation->bhb_method != ARM64_LATE_CPU_BHB_LOOP",
            "attestation->bhb_loop_count != 8",
            "case ARM64_WORKAROUND_1742098",
            "case ARM64_WORKAROUND_SPECULATIVE_AT",
            "arm64_late_cpu_midr_all_versions(match, MIDR_CORTEX_A72)",
            "default:\n\t\treturn ARM64_LATE_CPU_CAP_UNRESOLVED",
        ],
        "exact MT6797 target classifier",
    )
    plan_validator = extract_c_function(platform, "mt6797_a72_validate_cap_plan")
    expected_array = re.search(r"expected_caps\[\]\s*=\s*\{(.*?)\};", plan_validator, re.DOTALL)
    require(expected_array is not None, "exact plan expected-cap array is missing")
    require(
        tuple(re.findall(r"ARM64_[A-Z0-9_]+", expected_array.group(1))) == EXPECTED_CAPABILITIES,
        "exact expected capability set changed",
    )
    effects_assignment = re.search(r"expected_effects\s*=\s*(.*?);", plan_validator, re.DOTALL)
    require(effects_assignment is not None, "exact plan effect assignment is missing")
    require(
        tuple(re.findall(r"ARM64_LATE_CPU_EFFECT_[A-Z0-9_]+", effects_assignment.group(1)))
        == EXPECTED_EFFECTS,
        "exact expected effect set changed",
    )
    require_tokens(
        plan_validator,
        [
            "attestation->bhb_method != ARM64_LATE_CPU_BHB_LOOP",
            "attestation->bhb_loop_count != 8",
            "attestation->planned_effects != expected_effects",
            "bitmap_weight(attestation->target_local_caps, ARM64_NCAPS)",
            "bitmap_weight(attestation->required_local_caps, ARM64_NCAPS)",
            "bitmap_empty(attestation->conflicting_local_caps, ARM64_NCAPS)",
            "test_bit(cap, attestation->canonical_caps)",
            "test_bit(cap, attestation->compiled_local_caps)",
            "test_bit(cap, attestation->classified_local_caps)",
            "test_bit(cap, attestation->target_local_caps)",
            "test_bit(cap, attestation->required_local_caps)",
        ],
        "exact three-cap k=8 plan validation",
    )

    platform149 = added_source(sections149["arch/arm64/kernel/mt6797_psci.c"])
    foundation_symbols = macro_symbols(platform149, "MT6797_A72_PROFILE_BLOCKERS", "static bool")
    require(foundation_symbols == EXPECTED_FOUNDATION_BLOCKERS, "foundation blocker set changed")
    prepare149 = extract_c_function(platform149, "mt6797_a72_profile_prepare")
    require(
        prepare149.count("return -EAGAIN;") == 1 and "return 0;" not in prepare149,
        "selected profile no longer has a sole fail-closed return",
    )
    require(
        tuple(re.findall(r"__set_bit\((ARM64_[A-Z0-9_]+),\s*draft->required_local_caps", prepare149))
        == EXPECTED_CAPABILITIES,
        "foundation three-cap plan changed",
    )

    platform_post = patch_postimage_context(sections150["arch/arm64/kernel/mt6797_psci.c"])
    require_tokens(
        platform149,
        digest_u64_literals(EXPECTED_SOURCE_PARENT_SHA256),
        "non-circular source-parent identity",
    )
    require_tokens(
        platform_post,
        digest_u64_literals(EXPECTED_CONFIG_INPUT_SHA256),
        "selected configuration-input identity",
    )
    removed_platform = "\n".join(removed_source(sections150["arch/arm64/kernel/mt6797_psci.c"]))
    require(
        set(re.findall(r"ARM64_LATE_CPU_BLOCK_[A-Z0-9_]+", removed_platform))
        == {"ARM64_LATE_CPU_BLOCK_CAP_INVENTORY"},
        "post-planner profile blocker set changed",
    )
    require_tokens(
        removed_platform,
        [
            "ARM64_LATE_CPU_BLOCK_CAP_INVENTORY",
            "__set_bit(ARM64_SPECTRE_BHB, draft->required_local_caps)",
            "__set_bit(ARM64_WORKAROUND_1742098, draft->required_local_caps)",
            "__set_bit(ARM64_WORKAROUND_SPECULATIVE_AT",
        ],
        "core ownership migration",
    )
    initializer_start = platform_post.find("static const struct arm64_late_cpu_profile mt6797_a72_profile")
    initializer_end = platform_post.find("};", initializer_start)
    require(initializer_start >= 0 and initializer_end > initializer_start, "selected profile initializer is missing")
    initializer = platform_post[initializer_start : initializer_end + 2]
    require_tokens(
        initializer,
        [
            '.name = "mt6797-a53-a72-a41-v2"',
            ".classify_local_cap = mt6797_a72_classify_local_cap",
            ".validate_plan = mt6797_a72_validate_cap_plan",
            ".prepare = mt6797_a72_profile_prepare",
        ],
        "selected planner profile",
    )
    require(".verify_system" not in initializer and ".finalize_user" not in initializer and ".commit" not in initializer, "selected profile gained a production commit callback")

    framework = added_source(sections150["arch/arm64/kernel/late_cpu_profile.c"])
    framework_post = patch_postimage_context(sections150["arch/arm64/kernel/late_cpu_profile.c"])
    require_tokens(
        framework,
        [
            "plan_ret = arm64_plan_late_cpu_capabilities(&draft, &late_profile)",
            "validate_ret = late_profile.validate_plan(&draft)",
            "if (plan_ret || validate_ret)",
            "draft.blocker_mask |= ARM64_LATE_CPU_BLOCK_CAP_INVENTORY",
            "ret || plan_ret || validate_ret || draft.blocker_mask",
        ],
        "core CAP_INVENTORY ownership",
    )
    require(
        not re.search(r"blocker_mask\s*&=\s*~\s*ARM64_LATE_CPU_BLOCK_CAP_INVENTORY", framework_post + platform_post),
        "CAP_INVENTORY can be cleared outside the core plan result",
    )
    for field in (
        "canonical_caps",
        "compiled_local_caps",
        "classified_local_caps",
        "early_local_caps",
        "target_local_caps",
        "required_local_caps",
        "conflicting_local_caps",
        "planned_effects",
        "local_caps_planned",
    ):
        require(framework_post.count(field) >= 2, "planner identity guard missing {}".format(field))

    source92 = "\n".join(added_source(section) for section in patch_sections(p92).values())
    boot = extract_c_function(source92, "mt6797_psci_cpu_boot")
    disable = extract_c_function(source92, "mt6797_psci_cpu_can_disable")
    require(
        boot.count("return -EAGAIN;") == 1
        and "return 0;" not in boot
        and "cpu_psci_ops.cpu_boot" not in boot,
        "0092 boot veto changed",
    )
    require(
        disable.count("return false;") == 1 and "return true;" not in disable,
        "0092 disable veto changed",
    )

    lifecycle = added_source(sections148["arch/arm64/kernel/late_cpu_profile.c"])
    accessor = extract_c_function(lifecycle, "arm64_get_late_cpu_attestation")
    ordered(
        accessor,
        ["smp_load_acquire", "ARM64_LATE_CPU_PROFILE_READY", "return NULL", "return &late_attestation"],
        "READY accessor guard",
    )

    combined150 = "\n".join(added_source(section) for section in sections150.values())
    require(
        "ARM64_LATE_CPU_PROFILE_READY" not in combined150,
        "0150 publishes READY state directly",
    )
    forbidden = (
        "cpu_psci_ops.cpu_boot(",
        "psci_ops.cpu_on(",
        "invoke_psci_fn(",
        "update_cpu_capabilities(",
        "enable_cpu_capabilities(",
        "apply_alternatives",
        "max_bhb_k =",
        "spectre_bhb_state =",
        "this_cpu_set_vectors(",
        "write_sysreg(",
        "compat_elf_hwcap &=",
        "elf_hwcap &=",
        "system_cpucaps)",
    )
    for token in forbidden:
        require(token not in combined150, "live capability mutation added: {}".format(token))
    for call in re.findall(r"(?<![A-Za-z0-9_])(?:__)?set_bit\s*\(([^\n;]+)\)", cpufeature):
        require("draft->" in call, "live capability mutation added through set_bit")
    require("clear_bit(" not in combined150, "live capability clear added")


def validate_offline_boundary(repo: Path) -> None:
    script_paths = (
        repo / EXPERIMENT_REL / "scripts/validate.py",
        repo / EXPERIMENT_REL / "scripts/test_mutations.py",
    )
    scripts = "\n".join(path.read_text() for path in script_paths)
    forbidden = (
        "./scripts/" + "build-kernel",
        "./scripts/" + "dev-vm",
        'subprocess.run(["' + "ssh" + '"',
        'subprocess.run(["' + "nc" + '"',
        'subprocess.run(["' + "shutdown" + '"',
        'subprocess.run(["' + "reboot" + '"',
        "/dev/" + "mmc",
    )
    for token in forbidden:
        require(token not in scripts, "offline validator contains build/device action")

    allowed_imports = {
        "validate.py": {
            "__future__",
            "argparse",
            "ast",
            "csv",
            "hashlib",
            "json",
            "re",
            "subprocess",
            "sys",
            "tempfile",
            "pathlib",
            "typing",
        },
        "test_mutations.py": {
            "__future__",
            "importlib",
            "json",
            "shutil",
            "sys",
            "tempfile",
            "dataclasses",
            "pathlib",
            "typing",
        },
    }

    def command_shape(command: ast.List) -> tuple[str, ...]:
        shape: list[str] = []
        for element in command.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                shape.append(element.value)
            elif isinstance(element, ast.Starred) and isinstance(element.value, ast.Name):
                shape.append("*" + element.value.id)
            else:
                shape.append("<expr>")
        return tuple(shape)

    safe_prefix = ("git", "--no-pager", "--no-replace-objects")
    allowed_git_shapes = {
        safe_prefix
        + (
            "-C",
            "<expr>",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--unified=0",
            "HEAD",
            "--",
            "*modified",
        ),
        safe_prefix + ("-C", "<expr>", "rev-parse", "--verify", "<expr>"),
        safe_prefix + ("-C", "<expr>", "cat-file", "blob", "<expr>"),
        safe_prefix + ("-C", "<expr>", "cat-file", "-e", "<expr>"),
        safe_prefix
        + ("apply", "--check", "--whitespace=error-all", "<expr>"),
        safe_prefix + ("apply", "--whitespace=error-all", "<expr>"),
        ("git", "--version"),
    }
    for path in script_paths:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                require(
                    all(alias.asname is None for alias in node.names),
                    "offline validator contains an import alias",
                )
                modules = {alias.name.split(".", 1)[0] for alias in node.names}
                require(
                    modules <= allowed_imports[path.name],
                    "offline validator contains an unreviewed import",
                )
            elif isinstance(node, ast.ImportFrom):
                require(
                    all(alias.asname is None for alias in node.names),
                    "offline validator contains an import alias",
                )
                module = (node.module or "").split(".", 1)[0]
                require(
                    module in allowed_imports[path.name] and module != "subprocess",
                    "offline validator contains an unreviewed import",
                )
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "subprocess"
            ):
                require(
                    node.attr in {"run", "PIPE", "DEVNULL"},
                    "offline validator contains a disallowed subprocess operation",
                )
            if path.name == "test_mutations.py" and isinstance(node, ast.Name):
                require(node.id != "subprocess", "mutation harness may not use subprocess")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    require(
                        node.func.id not in {"exec", "eval", "__import__"},
                        "offline validator contains a dangerous dynamic call",
                    )
                elif isinstance(node.func, ast.Attribute):
                    require(
                        node.func.attr not in {"Popen", "system"},
                        "offline validator contains a dangerous process call",
                    )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            ):
                require(node.func.attr == "run", "offline validator contains a disallowed subprocess operation")
                require(node.args and isinstance(node.args[0], ast.List), "subprocess executable is not statically bounded")
                require(
                    command_shape(node.args[0]) in allowed_git_shapes,
                    "offline validator git command shape is not allowlisted",
                )
                require(
                    not any(keyword.arg == "shell" for keyword in node.keywords),
                    "offline validator subprocess may not use a shell",
                )
                shape = command_shape(node.args[0])
                if "apply" in shape:
                    cwd = [keyword for keyword in node.keywords if keyword.arg == "cwd"]
                    require(
                        len(cwd) == 1
                        and isinstance(cwd[0].value, ast.Name)
                        and cwd[0].value.id == "scratch",
                        "git apply is not statically confined to the scratch tree",
                    )


def validate_repository(
    repo: Path,
    *,
    pin_hashes: bool = True,
    check_frozen_evidence: bool = True,
) -> list[str]:
    """Run repository-only checks; intentionally exposed to the mutation suite."""

    repo = repo.resolve()
    patches = {relative: (repo / relative).read_text() for relative in PATCHES}
    completed: list[str] = []
    validate_bounded_new_paths(repo)
    completed.append("bounded-new-files")
    validate_experiment_record(repo, check_frozen_evidence=check_frozen_evidence)
    completed.append("experiment-record")
    validate_patch_identities(repo, patches, pin_hashes)
    completed.append("patch-identities")
    validate_series_and_manifest(repo, pin_hashes)
    completed.append("manifest-series")
    validate_source_contract(patches)
    completed.append("planner-source-contract")
    validate_offline_boundary(repo)
    completed.append("offline-boundary")
    return completed


def git_rev_parse(source_root: Path, revision: str) -> str:
    result = subprocess.run(
        [
            "git",
            "--no-pager",
            "--no-replace-objects",
            "-C",
            str(source_root),
            "rev-parse",
            "--verify",
            revision,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(result.returncode == 0, "git rev-parse failed: {}".format(result.stderr.strip()))
    return result.stdout.strip()


def git_cat_blob(source_root: Path, object_spec: str) -> bytes:
    result = subprocess.run(
        [
            "git",
            "--no-pager",
            "--no-replace-objects",
            "-C",
            str(source_root),
            "cat-file",
            "blob",
            object_spec,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(
        result.returncode == 0,
        "git cat-file blob failed: {}".format(result.stderr.decode(errors="replace").strip()),
    )
    return result.stdout


def git_object_exists(source_root: Path, object_spec: str) -> bool:
    result = subprocess.run(
        [
            "git",
            "--no-pager",
            "--no-replace-objects",
            "-C",
            str(source_root),
            "cat-file",
            "-e",
            object_spec,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def git_tool_version() -> str:
    result = subprocess.run(
        ["git", "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(result.returncode == 0, "git --version failed")
    return result.stdout.strip()


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
        "applied lifecycle order",
    )
    cpufeature = (tree / "arch/arm64/kernel/cpufeature.c").read_text()
    cpu_errata = (tree / "arch/arm64/kernel/cpu_errata.c").read_text()
    validate_capability_source_tables(cpu_errata, cpufeature)
    planner = extract_c_function(cpufeature, "arm64_plan_late_cpu_capabilities")
    require_tokens(
        planner,
        ["system_capabilities_finalized()", "cpus_have_cap(ARM64_ALWAYS_SYSTEM)", "return -EAGAIN;"],
        "applied planner fail-closed timing",
    )
    framework = (tree / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    prepare = extract_c_function(framework, "arm64_prepare_late_cpu_profile")
    ordered(
        prepare,
        [
            "late_profile.prepare",
            "arm64_plan_late_cpu_capabilities",
            "late_profile.validate_plan",
            "draft.blocker_mask |= ARM64_LATE_CPU_BLOCK_CAP_INVENTORY",
            "ret || plan_ret || validate_ret || draft.blocker_mask",
            "late_profile_block",
            "ARM64_LATE_CPU_PROFILE_PREPARED",
        ],
        "applied core plan transaction",
    )
    platform = (tree / "arch/arm64/kernel/mt6797_psci.c").read_text()
    require(
        macro_symbols(platform, "MT6797_A72_PROFILE_BLOCKERS", "static enum")
        == EXPECTED_PROFILE_BLOCKERS,
        "applied profile blocker set changed",
    )
    require("return -EAGAIN;" in extract_c_function(platform, "mt6797_a72_profile_prepare"), "applied profile lost -EAGAIN")
    boot = extract_c_function(platform, "mt6797_psci_cpu_boot")
    disable = extract_c_function(platform, "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot, "applied source lost boot veto")
    require("return false;" in disable, "applied source lost disable veto")


def validate_source_application(repo: Path, source_root: Path) -> None:
    source_root = source_root.resolve()
    require((source_root / ".git").exists(), "source root is not a Git repository")
    final_commit = git_rev_parse(
        source_root, "{}^{{commit}}".format(EXPECTED_PATCH_COMMITS[PATCH_0150])
    )
    require(final_commit == EXPECTED_PATCH_COMMITS[PATCH_0150], "final planner source commit is absent")
    final_tree = git_rev_parse(source_root, "{}^{{tree}}".format(final_commit))
    require(final_tree == EXPECTED_PLANNER_SOURCE_TREE, "final planner source tree changed")
    commit = git_rev_parse(source_root, "{}^{{commit}}".format(EXPECTED_BASE_COMMIT))
    require(commit == EXPECTED_BASE_COMMIT, "pinned source baseline is absent")
    tree_id = git_rev_parse(source_root, "{}^{{tree}}".format(commit))
    require(tree_id == EXPECTED_BASE_TREE, "pinned source baseline tree changed")

    patch_texts = {relative: (repo / relative).read_text() for relative in (PATCH_0148, PATCH_0149, PATCH_0150)}
    touched = set().union(*(set(patch_sections(text)) for text in patch_texts.values()))
    require(touched == set(EXPECTED_BASE_BLOBS) | NEW_SOURCE_PATHS, "sequential touched-path inventory changed")
    with tempfile.TemporaryDirectory(prefix="gemini-a41-planner-validate-") as temporary:
        scratch = Path(temporary)
        for source_path, expected_blob in EXPECTED_BASE_BLOBS.items():
            blob = git_cat_blob(source_root, "{}:{}".format(commit, source_path))
            require(git_blob_sha1(blob) == expected_blob, "{} baseline blob changed".format(source_path))
            destination = scratch / source_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blob)
        for source_path in NEW_SOURCE_PATHS:
            require(
                not git_object_exists(source_root, "{}:{}".format(commit, source_path)),
                "{} unexpectedly exists in baseline".format(source_path),
            )

        for relative in (PATCH_0148, PATCH_0149, PATCH_0150):
            sections = patch_sections(patch_texts[relative])
            for source_path, section in sections.items():
                old, _new = parse_index(section)
                current = scratch / source_path
                if set(old) == {"0"}:
                    require(not current.exists(), "{} new-file preimage exists".format(source_path))
                else:
                    require(current.is_file(), "{} preimage is missing".format(source_path))
                    require(git_blob_sha1(current.read_bytes()).startswith(old), "{} sequential preimage differs".format(source_path))
            patch_path = (repo / relative).resolve()
            check_result = subprocess.run(
                [
                    "git",
                    "--no-pager",
                    "--no-replace-objects",
                    "apply",
                    "--check",
                    "--whitespace=error-all",
                    str(patch_path),
                ],
                cwd=scratch,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            require(
                check_result.returncode == 0,
                "{} sequential applicability failed: {}".format(
                    relative.name, check_result.stderr.strip()
                ),
            )
            apply_result = subprocess.run(
                [
                    "git",
                    "--no-pager",
                    "--no-replace-objects",
                    "apply",
                    "--whitespace=error-all",
                    str(patch_path),
                ],
                cwd=scratch,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            require(
                apply_result.returncode == 0,
                "{} sequential application failed: {}".format(
                    relative.name, apply_result.stderr.strip()
                ),
            )
            for source_path, section in sections.items():
                _old, new = parse_index(section)
                current = scratch / source_path
                require(current.is_file(), "{} postimage is missing".format(source_path))
                require(git_blob_sha1(current.read_bytes()).startswith(new), "{} applied postimage differs".format(source_path))

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
        help="Git source repository containing the pinned baseline and final planner commit",
    )
    parser.add_argument(
        "--skip-frozen-evidence",
        action="store_true",
        help="bootstrap transcript capture without validating the output file being written",
    )
    args = parser.parse_args(argv)
    try:
        checks = validate_repository(
            args.repo_root,
            check_frozen_evidence=not args.skip_frozen_evidence,
        )
        validate_source_application(args.repo_root.resolve(), args.source_root)
        checks.append("sequential-source-application")
        git_version = git_tool_version()
    except (OSError, ValueError, json.JSONDecodeError, ValidationError) as error:
        print("FAIL {}".format(error), file=sys.stderr)
        return 1

    for check in checks:
        print("PASS {}".format(check))
    print("patch_0150_sha256={}".format(sha256_file(args.repo_root / PATCH_0150)))
    print("planner_series_sha256={}".format(sha256_file(args.repo_root / PLANNER_SERIES)))
    print("planner_patchset_sha256={}".format(EXPECTED_PATCHSET_SHA256))
    print("planner_source_state_sha256={}".format(EXPECTED_SOURCE_STATE_SHA256))
    print("source_parent_sha256={}".format(EXPECTED_SOURCE_PARENT_SHA256))
    print("config_inputs_sha256={}".format(EXPECTED_CONFIG_INPUT_SHA256))
    print("source_base_commit={}".format(EXPECTED_BASE_COMMIT))
    print("planner_source_commit={}".format(EXPECTED_PATCH_COMMITS[PATCH_0150]))
    print("planner_source_tree={}".format(EXPECTED_PLANNER_SOURCE_TREE))
    print("validator_sha256={}".format(sha256_file(Path(__file__))))
    print("python_version={}".format(sys.version.split()[0]))
    print("git_version={}".format(git_version))
    print("implementation_state=PARTIAL_READ_ONLY_PLANNER")
    print("a41_complete=no")
    print("build_authorized=no")
    print("device_action_authorized=no")
    print("RESULT PASS {}/{}".format(len(checks), len(checks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
