#!/usr/bin/env python3
"""Validate the manual raw-entry write qualification definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PATCH_REL = "patches/v7.1.3/0332-pstore-qualify-Gemini-manual-raw-entry-write.patch"
FRAGMENT_REL = "configs/gemini-manual-checkpoint-raw-write.fragment"
PROFILE = "da921x-manual-checkpoint-raw-write"
PARENT = "da921x-manual-checkpoint-stage-control"
SYMBOL = "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def validate_patch_text(patch: str) -> None:
    required = (
        f"config {SYMBOL}",
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER",
        "default n",
        "readl(slot) == ~0U",
        "readl((u8 __iomem *)slot + 4) == ~0U",
        "readl((u8 __iomem *)slot + 8) == ~0U",
        "memcpy_toio((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE, record, len)",
        "writel(len, (u8 __iomem *)slot + 4)",
        "writel(len, (u8 __iomem *)slot + 8)",
        "writel(GEMINI_PRB_SIGNATURE, slot)",
        "if (checkpoint != 0 || gemini_prb_armed)",
        "second = false;",
        "GEMINI_MANUAL_RAW_WRITE_QUALIFICATION_LIVE_V1",
        '"bigidvfs=%u cpu=%u\\n"',
        "first, gemini_prb_stage, first, 0, 0, 0, 0",
    )
    for token in required:
        require(token in patch, f"required patch token missing: {token}")
    require(patch.index("memcpy_toio(") < patch.index("writel(len, (u8 __iomem *)slot + 4)"), "payload is not first")
    require(patch.index("writel(len, (u8 __iomem *)slot + 4)") < patch.index("writel(len, (u8 __iomem *)slot + 8)"), "start is not before size")
    require(patch.index("writel(len, (u8 __iomem *)slot + 8)") < patch.index("writel(GEMINI_PRB_SIGNATURE, slot)"), "signature is not last")
    added = added_lines(patch)
    for forbidden in (
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_",
        "psci_ops.cpu_on",
        "cpu_up(",
        "regulator_enable(",
        "i2c_transfer(",
        "kernel_restart(",
        "emergency_restart(",
    ):
        require(forbidden not in added, f"forbidden action added: {forbidden}")
    require("Signed-off-by:" not in patch, "synthetic patch gained a sign-off")


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    patch_path = ROOT / PATCH_REL
    patch = patch_path.read_text(encoding="utf-8")
    base_writer = (ROOT / "patches/v7.1.3/0323-pstore-add-Gemini-protected-readback-call-ledger.patch").read_text(encoding="utf-8")
    stage_patch = (ROOT / "patches/v7.1.3/0328-pstore-report-Gemini-manual-checkpoint-stage.patch").read_text(encoding="utf-8")
    fragment = (ROOT / FRAGMENT_REL).read_text(encoding="utf-8")
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity changed")
    require(contract["patch"]["path"] == PATCH_REL, "contract patch path changed")
    require(hashlib.sha256(patch_path.read_bytes()).hexdigest() == contract["patch"]["sha256"], "patch identity changed")
    validate_patch_text(patch)
    for token in (
        "readl(slot) != GEMINI_PRB_SIGNATURE",
        "readl((u8 __iomem *)slot + 4) != len",
        "readl((u8 __iomem *)slot + 8) != len",
        "readb((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE + i)",
        'GEMINI_PRB_SET_STAGE("metadata-readback-refused")',
        'GEMINI_PRB_SET_STAGE("payload-readback-refused")',
        'GEMINI_PRB_SET_STAGE("success")',
    ):
        require(token in base_writer + stage_patch, f"inherited full-readback gate missing: {token}")
    require("late_initcall(gemini_protected_readback_manual_control_init);" in (ROOT / "patches/v7.1.3/0327-pstore-add-Gemini-manual-checkpoint-control.patch").read_text(encoding="utf-8"), "proven late initcall missing")

    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles and PARENT in profiles, "profile missing")
    require(profiles[PROFILE]["patch_series"] == "patches/series", "profile series changed")
    require(
        profiles[PROFILE]["fragments"]
        == profiles[PARENT]["fragments"] + [FRAGMENT_REL],
        "profile is not the exact parent plus qualification fragment",
    )
    require(series[-1] == PATCH_REL.removeprefix("patches/"), "patch is not canonical tail")
    require(series.count(PATCH_REL.removeprefix("patches/")) == 1, "patch series count changed")

    for line in (
        f"CONFIG_{SYMBOL}=y",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL is not set",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL is not set",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER is not set",
        'CONFIG_LOCALVERSION="-gemini-checkpoint-raw-write"',
    ):
        require(line in fragment.splitlines(), f"fragment gate missing: {line}")
    parent_fragments = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in profiles[PARENT]["fragments"]
    )
    for line in (
        "# CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND is not set",
        "# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set",
        "# CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set",
    ):
        require(line in parent_fragments, f"parent veto missing: {line}")

    print("validation=manual-checkpoint-raw-write-qualification-definition")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print("retained_record_commits_maximum=1")
    print("commit_order=payload,start,size,signature")
    print("full_local_readback=true")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
