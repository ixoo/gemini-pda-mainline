#!/usr/bin/env python3
"""Validate the exact manual-checkpoint live prefix-reason definition."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
PROFILE = "da921x-manual-checkpoint-prefix-control"
PARENT = "da921x-manual-checkpoint-stage-control"
PATCH = "v7.1.3/0329-pstore-report-Gemini-manual-checkpoint-prefix-reason.patch"
FRAGMENT = "configs/gemini-manual-checkpoint-prefix-control.fragment"
MODE = "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL"
EXPERIMENT = "experiments/2026-08-21-mainline-manual-checkpoint-prefix-control"
EXPECTED_FRAGMENT = """# Read-only live reason for the first rejected manual-checkpoint prefix header.
# The parent stage oracle, write ceiling, and clock/protected/CPU vetoes remain.
CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y
CONFIG_LOCALVERSION="-gemini-checkpoint-prefix"
"""
REASONS = (
    "bad-signature",
    "nonzero-start",
    "nonzero-size",
    "unstable-or-other",
    "exact-record-refused",
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
    require(hunks == 4, "patch hunk inventory changed")


def validate_patch(text: str) -> None:
    header, separator, _body = text.partition("\n\n")
    require(bool(separator), "patch header terminator changed")
    unfolded = " ".join(line.strip() for line in header.splitlines())
    require(
        "Subject: [PATCH] pstore: report Gemini manual checkpoint prefix reason"
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
        paths == ("fs/pstore/Kconfig", "fs/pstore/gemini_protected_readback_ledger.c"),
        "patch path inventory changed",
    )
    validate_hunk_counts(text)

    additions = changed_lines(text, "+")
    removals = changed_lines(text, "-")
    require(len(additions) == 73, "patch addition count changed")
    require(
        removals
        == ["\t\t\tif (!gemini_prb_slot_exact(slot, gemini_prb_records[0]))"],
        "historical predicate deletion changed",
    )
    added = "\n".join(additions)
    require(added.count(f"config {MODE}") == 1, "prefix mode declaration changed")
    require(
        added.count('bool "Gemini manual checkpoint live prefix reason"') == 1,
        "prefix mode prompt changed",
    )
    require(added.count("\tdefault n") == 1, "prefix mode is not uniquely default off")
    require(
        added.count(
            "\tdepends on "
            "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y"
        )
        == 1,
        "prefix mode parent dependency changed",
    )
    require(added.count(f"#ifdef CONFIG_{MODE}") == 2, "compile-time guards changed")
    require(
        added.count("static void gemini_prb_capture_prefix(") == 1
        and added.count("static inline void gemini_prb_capture_prefix(") == 1,
        "enabled or disabled capture path changed",
    )
    require(added.count("readl(") == 3, "bounded header-read count changed")
    require("readb(" not in added, "prefix capture gained payload reads")
    require(
        added.count(
            "if (!gemini_prb_slot_exact(slot, gemini_prb_records[0])) {"
        )
        == 1,
        "exact-record predicate changed",
    )
    require(
        text.count("\t\t} else if (!gemini_prb_slot_empty(slot)) {") == 1,
        "empty-slot predicate changed",
    )
    require(
        added.count("gemini_prb_capture_prefix(checkpoint, i, false,") == 1
        and added.count("gemini_prb_capture_prefix(checkpoint, i, true, slot);") == 1,
        "post-refusal capture call inventory changed",
    )
    for field in (
        "gemini_prb_prefix_checkpoint = checkpoint;",
        "gemini_prb_prefix_slot_index = slot_index;",
        "gemini_prb_prefix_signature = signature;",
        "gemini_prb_prefix_start = start;",
        "gemini_prb_prefix_size = size;",
    ):
        require(added.count(field) == 1, f"captured field changed: {field}")
    for reason in REASONS:
        require(
            added.count(f'gemini_prb_prefix_reason = "{reason}";') == 1,
            f"prefix reason inventory changed: {reason}",
        )
    require(added.count("GEMINI_MANUAL_CHECKPOINT_PREFIX_V1") == 1,
            "live prefix marker changed")
    require(
        added.count('%s cp=%u slot=%u why=%s hdr=%08x/%u/%u reads=3\\n') == 1,
        "live prefix output schema changed",
    )
    for forbidden in (
        "memcpy_toio(",
        "writel(",
        "writeb(",
        "ioremap(",
        "ioremap_wc(",
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
        require(forbidden not in added, f"prefix patch added forbidden effect: {forbidden}")


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
    require(fragment.is_file() and not fragment.is_symlink(), "prefix fragment is unsafe")
    require(
        fragment.read_text(encoding="utf-8") == EXPECTED_FRAGMENT,
        "prefix fragment changed",
    )
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()
    require(series[-1] == PATCH, "prefix patch is not canonical tip")
    require(
        series.count(PATCH) == 1 and len(series) == len(set(series)),
        "canonical series duplicate changed",
    )
    patch_path = ROOT / "patches" / PATCH
    require(patch_path.is_file() and not patch_path.is_symlink(), "prefix patch is unsafe")
    validate_patch(patch_path.read_text(encoding="utf-8"))

    contract = json.loads((ROOT / EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
    require(contract["profile"]["name"] == PROFILE, "contract profile changed")
    require(contract["profile"]["parent"] == PARENT, "contract parent changed")
    require(contract["runtime_oracle"]["reason_values"] == list(REASONS),
            "contract reason inventory changed")
    require(
        contract["runtime_oracle"]["accepted_first_call_reason_values"]
        == list(REASONS[:4]),
        "accepted first-call reason inventory changed",
    )
    require(contract["runtime_oracle"]["required_stage"] == "prefix-refused",
            "required parent stage changed")
    scope = contract["scope"]
    require(scope["retained_ram_maximum_writes"] == 2, "write ceiling changed")
    require(scope["new_retained_writes"] == 0, "prefix mode added retained writes")
    require(scope["new_retained_header_reads"] == 3, "capture read count changed")
    require(scope["new_payload_reads"] == 0, "capture gained payload reads")
    require(scope["protected_clock_reads"] == 0, "protected read scope changed")
    require(scope["cpu_on"] is False and scope["cpu_off"] is False,
            "CPU scope changed")
    require(scope["boot_candidate"] is False, "prebuild definition became a candidate")

    print("validation=mainline-manual-checkpoint-prefix-control-definition")
    print(f"profile={PROFILE}")
    print(f"profile_fragments={len(profile['fragments'])}")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print(f"fixed_prefix_reasons={len(REASONS)}")
    print("post_refusal_header_reads=3")
    print("new_retained_writes=0")
    print("protected_calls=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
