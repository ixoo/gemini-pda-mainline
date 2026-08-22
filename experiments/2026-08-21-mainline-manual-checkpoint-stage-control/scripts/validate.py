#!/usr/bin/env python3
"""Validate the exact manual-checkpoint live-stage definition."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
PROFILE = "da921x-manual-checkpoint-stage-control"
PARENT = "da921x-manual-checkpoint-control"
PATCH = "v7.1.3/0328-pstore-report-Gemini-manual-checkpoint-stage.patch"
FRAGMENT = "configs/gemini-manual-checkpoint-stage-control.fragment"
MODE = "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL"
EXPECTED_FRAGMENT = """# Decision-bearing live refusal stage for the exact manual checkpoint call.
# The parent retains the two-write ceiling and every clock/protected/CPU veto.
CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y
CONFIG_LOCALVERSION="-gemini-checkpoint-stage"
"""
STAGES = (
    "call-entry",
    "sequence-refused",
    "dt-refused",
    "map-refused",
    "prefix-refused",
    "write-precondition-refused",
    "metadata-readback-refused",
    "payload-readback-refused",
    "success",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


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
    require(hunks == 7, "patch hunk inventory changed")


def validate_patch(text: str) -> None:
    header, separator, _body = text.partition("\n\n")
    require(bool(separator), "patch header terminator changed")
    unfolded = " ".join(line.strip() for line in header.splitlines())
    require("Subject: [PATCH] pstore: report Gemini manual checkpoint stage" in unfolded,
            "patch subject changed")
    require("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
            "synthetic experiment author changed")
    require("Signed-off-by:" not in text, "synthetic certification added")
    paths = tuple(
        match.group(1)
        for match in re.finditer(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE)
    )
    require(paths == ("fs/pstore/Kconfig",
                      "fs/pstore/gemini_protected_readback_ledger.c"),
            "patch path inventory changed")
    validate_hunk_counts(text)

    added = added_lines(text)
    require(added.count(f"config {MODE}") == 1, "stage mode declaration changed")
    require(added.count('bool "Gemini manual checkpoint live failure stage"') == 1,
            "stage mode prompt changed")
    require(added.count("\tdefault n") == 1, "stage mode is not uniquely default off")
    require(added.count(
        "\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y") == 1,
        "stage mode parent dependency changed")
    require(added.count(f"#ifdef CONFIG_{MODE}") == 2,
            "stage compile-time guards changed")
    require(added.count("#define GEMINI_PRB_SET_STAGE(stage) ((void)(stage))") == 1,
            "disabled stage setter gained behavior")
    for stage in STAGES:
        require(added.count(f'GEMINI_PRB_SET_STAGE("{stage}")') == 1,
                f"stage inventory changed: {stage}")
    require(added.count("GEMINI_MANUAL_CHECKPOINT_STAGE_V1") == 1,
            "live stage marker changed")
    for field in (
        "first=%u second=%u stage=%s writes=%u protected=%u cpu=%u",
        "first, second, gemini_prb_stage, first + second, 0, 0",
    ):
        require(added.count(field) == 1, f"stage output changed: {field}")
    for forbidden in (
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "clk_prepare_enable(",
        "i2c_transfer(",
        "regmap_write(",
        "writel(",
        "memcpy_toio(",
        "cpu_up(",
        "cpu_down(",
        "kernel_restart(",
        "schedule_delayed_work(",
    ):
        require(forbidden not in added, f"stage patch added forbidden effect: {forbidden}")


def main() -> None:
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    profiles = manifest["config"]["profiles"]
    parent = profiles[PARENT]
    profile = profiles[PROFILE]
    require(profile["base"] == parent["base"] == "defconfig", "profile base changed")
    require(profile["patch_series"] == manifest["patch_series"] == "patches/series",
            "profile does not use canonical series")
    require(profile["fragments"] == parent["fragments"] + [FRAGMENT],
            "profile is not exact parent plus one fragment")
    fragment = ROOT / FRAGMENT
    require(fragment.is_file() and not fragment.is_symlink(), "stage fragment is unsafe")
    require(fragment.read_text(encoding="utf-8") == EXPECTED_FRAGMENT,
            "stage fragment changed")
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()
    require(series[-1] == PATCH, "stage patch is not canonical tip")
    require(series.count(PATCH) == 1 and len(series) == len(set(series)),
            "canonical series duplicate changed")
    patch_path = ROOT / "patches" / PATCH
    require(patch_path.is_file() and not patch_path.is_symlink(), "stage patch is unsafe")
    validate_patch(patch_path.read_text(encoding="utf-8"))

    contract = json.loads((ROOT / "experiments/2026-08-21-mainline-manual-checkpoint-stage-control/contract.json").read_text(encoding="utf-8"))
    require(contract["profile"]["name"] == PROFILE, "contract profile changed")
    require(contract["runtime_oracle"]["stage_values"] == list(STAGES[1:]),
            "contract stage decisions changed")
    require(contract["scope"]["retained_ram_maximum_writes"] == 2,
            "write ceiling changed")
    require(contract["scope"]["new_retained_writes"] == 0,
            "stage mode added retained writes")
    require(contract["scope"]["protected_clock_reads"] == 0,
            "protected read scope changed")
    require(contract["scope"]["cpu_on"] is False and
            contract["scope"]["cpu_off"] is False, "CPU scope changed")
    require(contract["scope"]["boot_candidate"] is False,
            "prebuild definition was promoted")

    print("validation=mainline-manual-checkpoint-stage-control-prebuild")
    print(f"profile={PROFILE}")
    print(f"profile_fragments={len(profile['fragments'])}")
    print(f"canonical_patch_count={len(series)}")
    print(f"fixed_stage_values={len(STAGES) - 1}")
    print("retained_maximum_writes=2")
    print("new_retained_writes=0")
    print("protected_calls=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
