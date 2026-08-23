#!/usr/bin/env python3
"""Validate the first-dmesg raw-write qualification definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PATCH_REL = "patches/v7.1.3/0333-pstore-qualify-Gemini-first-dmesg-raw-write.patch"
FRAGMENT_REL = "configs/gemini-first-dmesg-raw-write.fragment"
PROFILE = "da921x-first-dmesg-raw-write"
PARENT = "da921x-manual-checkpoint-stage-control"
SYMBOL = "PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION"


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
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER",
        "default n",
        "#define GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE",
        "#define GEMINI_PRB_SLOT_COUNT\t\t1",
        "#define GEMINI_PRB_FIRST_OWNED_SLOT\t0",
        "GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260822-B",
        "checkpoint=manual-first slot=1 crc32=7785e4ce",
        "defined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION)",
        "if (checkpoint != 0 || gemini_prb_armed)",
        "second = false;",
        "GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1",
        "first, gemini_prb_stage, first, 1, GEMINI_PRB_LEDGER_BASE",
        "0, 0, 0, 0",
    )
    for token in required:
        require(token in patch, f"required patch token missing: {token}")
    require(patch.count("#define GEMINI_PRB_SLOT_COUNT\t\t1") == 1,
            "one-slot definition count changed")
    require(patch.count("checkpoint=manual-first slot=1") == 1,
            "record-1 payload count changed")
    added = added_lines(patch)
    for forbidden in (
        "default y",
        "0x444bf000",
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
    inherited_writer = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "patches/v7.1.3/0323-pstore-add-Gemini-protected-readback-call-ledger.patch",
            "patches/v7.1.3/0328-pstore-report-Gemini-manual-checkpoint-stage.patch",
            "patches/v7.1.3/0331-pstore-accept-Gemini-raw-entry-ledger.patch",
            "patches/v7.1.3/0332-pstore-qualify-Gemini-manual-raw-entry-write.patch",
        )
    )
    fragment = (ROOT / FRAGMENT_REL).read_text(encoding="utf-8")
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity changed")
    require(contract["patch"]["path"] == PATCH_REL, "contract patch path changed")
    require(hashlib.sha256(patch_path.read_bytes()).hexdigest() == contract["patch"]["sha256"],
            "patch identity changed")
    require(contract["ledger"]["owned_records"] == [1], "owned record changed")
    require(contract["ledger"]["owned_addresses"] == ["0x44410000"],
            "owned address changed")
    require(contract["ledger"]["maximum_logical_record_commits"] == 1,
            "logical write ceiling changed")
    require(contract["ledger"]["console_ring_touched"] is False,
            "console exclusion changed")
    validate_patch_text(patch)

    for token in (
        "memcpy_toio((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE, record, len)",
        "writel(len, (u8 __iomem *)slot + 4)",
        "writel(len, (u8 __iomem *)slot + 8)",
        "writel(GEMINI_PRB_SIGNATURE, slot)",
        "readl(slot) != GEMINI_PRB_SIGNATURE",
        "readl((u8 __iomem *)slot + 4) != len",
        "readl((u8 __iomem *)slot + 8) != len",
        "readb((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE + i)",
        'GEMINI_PRB_SET_STAGE("metadata-readback-refused")',
        'GEMINI_PRB_SET_STAGE("payload-readback-refused")',
        'GEMINI_PRB_SET_STAGE("success")',
    ):
        require(token in inherited_writer, f"inherited writer gate missing: {token}")
    require(inherited_writer.index("memcpy_toio(") < inherited_writer.index(
        "writel(len, (u8 __iomem *)slot + 4)"), "payload is not first")
    require(inherited_writer.index("writel(len, (u8 __iomem *)slot + 4)") <
            inherited_writer.index("writel(len, (u8 __iomem *)slot + 8)"),
            "start is not before size")
    require(inherited_writer.index("writel(len, (u8 __iomem *)slot + 8)") <
            inherited_writer.index("writel(GEMINI_PRB_SIGNATURE, slot)"),
            "signature is not last")
    require("late_initcall(gemini_protected_readback_manual_control_init);" in
            (ROOT / "patches/v7.1.3/0327-pstore-add-Gemini-manual-checkpoint-control.patch").read_text(encoding="utf-8"),
            "proven late initcall missing")

    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles and PARENT in profiles, "profile missing")
    require(profiles[PROFILE]["patch_series"] == "patches/series", "profile series changed")
    require(profiles[PROFILE]["fragments"] ==
            profiles[PARENT]["fragments"] + [FRAGMENT_REL],
            "profile is not the exact parent plus qualification fragment")
    require(series[-1] == PATCH_REL.removeprefix("patches/"),
            "patch is not canonical tail")
    require(series.count(PATCH_REL.removeprefix("patches/")) == 1,
            "patch series count changed")

    for line in (
        f"CONFIG_{SYMBOL}=y",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION is not set",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL is not set",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL is not set",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER is not set",
        'CONFIG_LOCALVERSION="-gemini-checkpoint-first-dmesg"',
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

    audit = ROOT / contract["foundation"]["source_audit"]
    audit_text = audit.read_text(encoding="utf-8")
    for token in (
        "record_173_sparse_reachability=unreachable-after-earlier-empty-dmesg-zones",
        "record_1_header=444247430000000000000000",
        "selected_successor_location=record-1-at-0x44410000",
        "console_zone_relocation=not-selected-live-ring-is-nonempty-and-owned-by-normal-console",
    ):
        require(token in audit_text, f"source-audit gate missing: {token}")

    print("validation=first-dmesg-raw-write-qualification-definition")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print("owned_record=1")
    print("owned_address=0x44410000")
    print("retained_record_commits_maximum=1")
    print("commit_order=payload,start,size,signature")
    print("full_local_readback=true")
    print("console_ring_touched=false")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
