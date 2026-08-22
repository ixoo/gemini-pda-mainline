#!/usr/bin/env python3
"""Validate the exact manual-checkpoint mapping-control definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
PROFILE = "da921x-manual-checkpoint-map-control"
PARENT = "da921x-manual-checkpoint-prefix-control"
PATCH = "v7.1.3/0330-pstore-compare-Gemini-ramoops-mapping-models.patch"
FRAGMENT = "configs/gemini-manual-checkpoint-map-control.fragment"
MODE = "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL"
EXPERIMENT = "experiments/2026-08-22-mainline-manual-checkpoint-map-control"
PATCH_SHA256 = "a8c1f85ee511fc6ea4ec8b0075b92ec32d85aaa3cd619558a4827558d9085e53"
EXPECTED_FRAGMENT = """# Read-only comparison of the parallel ledger map and ramoops mapping model.
# The mode bypasses the prefix predicate and retained writer completely.
CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL=y
CONFIG_LOCALVERSION="-gemini-checkpoint-map"
"""
REASONS = (
    "ramoops-empty-parallel-all-ones",
    "both-empty",
    "views-match-other",
    "views-differ",
    "ramoops-map-unavailable",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def changed_lines(text: str, prefix: str) -> list[str]:
    excluded = "+++" if prefix == "+" else "---"
    return [
        line[1:]
        for line in text.splitlines()
        if line.startswith(prefix)
        and not line.startswith(excluded)
        and line != "-- "
    ]


def validate_hunk_counts(text: str) -> None:
    lines = text.splitlines()
    hunks = 0
    for index, line in enumerate(lines):
        match = re.match(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@", line)
        if not match:
            continue
        hunks += 1
        expected_old = int(match.group(1) or "1")
        expected_new = int(match.group(2) or "1")
        actual_old = 0
        actual_new = 0
        for body_line in lines[index + 1:]:
            if (body_line.startswith("@@ ") or body_line.startswith("diff --git ")
                    or body_line == "-- "):
                break
            require(bool(body_line), "unprefixed blank line in patch hunk")
            require(body_line[0] in " +-\\", "invalid patch-hunk prefix")
            if body_line[0] in " -":
                actual_old += 1
            if body_line[0] in " +":
                actual_new += 1
        require(actual_old == expected_old, "old hunk count changed")
        require(actual_new == expected_new, "new hunk count changed")
    require(hunks == 8, "patch hunk inventory changed")


def validate_patch(text: str) -> None:
    header, separator, _body = text.partition("\n\n")
    require(bool(separator), "patch header terminator changed")
    unfolded = " ".join(line.strip() for line in header.splitlines())
    require(
        "Subject: [PATCH] pstore: compare Gemini ramoops mapping models"
        in unfolded,
        "patch subject changed",
    )
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
        in text,
        "synthetic experiment author changed",
    )
    require("Signed-off-by:" not in text, "synthetic certification added")
    paths = tuple(
        match.group(1)
        for match in re.finditer(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE)
    )
    require(
        paths
        == (
            "fs/pstore/Kconfig",
            "fs/pstore/gemini_protected_readback_ledger.c",
            "fs/pstore/ram_core.c",
            "fs/pstore/ram_internal.h",
        ),
        "patch path inventory changed",
    )
    validate_hunk_counts(text)

    additions = changed_lines(text, "+")
    removals = changed_lines(text, "-")
    require(len(additions) == 123, "patch addition count changed")
    require(
        removals
        == ["#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL"],
        "patch removal inventory changed",
    )
    added = "\n".join(additions)
    require(added.count(f"config {MODE}") == 1, "map mode declaration changed")
    require(
        added.count('bool "Gemini manual checkpoint ramoops mapping control"') == 1,
        "map mode prompt changed",
    )
    require(added.count("\tdefault n") == 1, "map mode is not uniquely default off")
    require(
        added.count(
            "\tdepends on "
            "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y"
        )
        == 1,
        "map mode parent dependency changed",
    )
    require(added.count(f"#ifdef CONFIG_{MODE}") == 5,
            "map mode compile-time guards changed")
    require(
        added.count("#include \"ram_internal.h\"") == 1,
        "internal persistent-RAM interface changed",
    )
    require(added.count("persistent_ram_vmap(start, sizeof(*buffer),") == 1,
            "ramoops mapping model changed")
    require(added.count("MEM_TYPE_WCOMBINE") == 1,
            "ramoops mapping protection changed")
    require(added.count("pfn_valid(start >> PAGE_SHIFT)") == 1,
            "valid-PFN gate changed")
    require(added.count("READ_ONCE(buffer->sig)") == 1,
            "signature snapshot changed")
    require(added.count("atomic_read(&buffer->start)") == 1,
            "start snapshot changed")
    require(added.count("atomic_read(&buffer->size)") == 1,
            "size snapshot changed")
    require(added.count("vunmap(vaddr - offset_in_page(start))") == 1,
            "ramoops-model unmap changed")
    require(added.count("readl(") == 3, "parallel read count changed")
    require("readb(" not in added, "map control gained payload reads")
    require(
        added.count("if (checkpoint == 0) {") == 1
        and added.count("gemini_prb_capture_map_control(ledger);") == 1
        and added.count('GEMINI_PRB_SET_STAGE("map-control-observed");') == 1
        and added.count("goto out;") == 1,
        "no-write control branch changed",
    )
    require(
        text.index("gemini_prb_capture_map_control(ledger);")
        < text.index("if (!gemini_prb_prefix_valid(ledger, checkpoint))"),
        "map control no longer precedes the prefix predicate",
    )
    require(
        added.count(
            "!defined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL)"
        )
        == 1,
        "parent prefix marker was not suppressed",
    )
    for reason in REASONS:
        require(
            added.count(f'gemini_prb_map_reason = "{reason}";') == 1,
            f"mapping result inventory changed: {reason}",
        )
    require(added.count("GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_V1") == 1,
            "live map marker changed")
    require(
        added.count(
            "%s r=171 p=%llx why=%s rh=%08x/%u/%u ph=%08x/%u/%u "
            "rr=%u pr=3 w=0\\n"
        )
        == 1,
        "live map output schema changed",
    )
    for forbidden in (
        "\tmemcpy_toio(",
        "\twritel(",
        "\twriteb(",
        "\tioremap(",
        "\tioremap_wc(",
        "platform_driver_register(",
        "persistent_ram_new(",
        "gemini_prb_write(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "clk_prepare_enable(",
        "i2c_transfer(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
        "kernel_restart(",
        "schedule_delayed_work(",
    ):
        require(forbidden not in added, f"map patch added forbidden effect: {forbidden}")


def main() -> None:
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    profiles = manifest["config"]["profiles"]
    parent = profiles[PARENT]
    profile = profiles[PROFILE]
    require(profile["base"] == parent["base"] == "defconfig", "profile base changed")
    require(
        profile["patch_series"] == manifest["patch_series"] == "patches/series",
        "profile does not use canonical series",
    )
    require(
        profile["fragments"] == parent["fragments"] + [FRAGMENT],
        "profile is not exact parent plus one fragment",
    )
    fragment = ROOT / FRAGMENT
    require(fragment.is_file() and not fragment.is_symlink(), "map fragment is unsafe")
    require(fragment.read_text(encoding="utf-8") == EXPECTED_FRAGMENT,
            "map fragment changed")
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()
    require(series[-1] == PATCH, "map patch is not canonical tip")
    require(series.count(PATCH) == 1 and len(series) == len(set(series)),
            "canonical series duplicate changed")
    patch_path = ROOT / "patches" / PATCH
    require(patch_path.is_file() and not patch_path.is_symlink(), "map patch is unsafe")
    patch_text = patch_path.read_text(encoding="utf-8")
    require(
        hashlib.sha256(patch_text.encode("utf-8")).hexdigest() == PATCH_SHA256,
        "exact map patch hash changed",
    )
    validate_patch(patch_text)

    contract = json.loads((ROOT / EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
    require(contract["profile"]["name"] == PROFILE, "contract profile changed")
    require(contract["profile"]["parent"] == PARENT, "contract parent changed")
    require(contract["patch"]["sha256"] == PATCH_SHA256, "contract patch hash changed")
    require(contract["runtime_oracle"]["reason_values"] == list(REASONS),
            "contract result inventory changed")
    scope = contract["scope"]
    require(scope["retained_ram_writes"] == 0, "retained write scope changed")
    require(scope["retained_header_reads_maximum"] == 6,
            "header read ceiling changed")
    require(scope["retained_payload_reads"] == 0, "payload read scope changed")
    require(scope["normal_ramoops_registration"] is False,
            "ramoops registration scope changed")
    require(scope["pstore_record_scan"] is False, "pstore scan scope changed")
    require(scope["protected_clock_reads"] == 0 and scope["bigidvfs_reads"] == 0,
            "protected read scope changed")
    require(scope["cpu_on"] is False and scope["cpu_off"] is False,
            "CPU scope changed")
    require(scope["boot_candidate"] is False, "definition became a boot candidate")

    print("validation=mainline-manual-checkpoint-map-control-definition")
    print(f"profile={PROFILE}")
    print(f"profile_fragments={len(profile['fragments'])}")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print(f"fixed_map_results={len(REASONS)}")
    print("parallel_header_reads=3")
    print("ramoops_model_header_reads_maximum=3")
    print("retained_writes=0")
    print("normal_ramoops_registration=false")
    print("protected_calls=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
