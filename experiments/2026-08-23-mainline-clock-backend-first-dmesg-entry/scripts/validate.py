#!/usr/bin/env python3
"""Validate the first-dmesg clock-backend entry definition."""

from __future__ import annotations

import hashlib
import json
import zlib
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PATCH_REL = "patches/v7.1.3/0334-pstore-qualify-Gemini-clock-entry-in-first-dmesg.patch"
FRAGMENT_REL = "configs/gemini-clock-backend-first-dmesg.fragment"
PROFILE = "da921x-clock-entry-first-dmesg"
PARENT = "da921x-current-service-control"
SYMBOL = "PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION"
PREFIX = "GEMINI_CLOCK_BACKEND_FIRST_DMESG_V1 token=GCBF-20260823-A"


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
        "depends on PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER=y",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER",
        "default n",
        "defined(CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION)",
        "#define GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE",
        "#define GEMINI_PRB_SLOT_COUNT\t\t2",
        "#define GEMINI_PRB_FIRST_OWNED_SLOT\t0",
        f"{PREFIX} ",
        "checkpoint=driver-init slot=1 crc32=6197fd57",
        "checkpoint=probe-enter slot=2 crc32=61636940",
        "GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1 ",
        "stage=driver-init writes=1 protected=0 bigidvfs=0 cpu=0",
        "stage=probe-enter writes=2 protected=0 bigidvfs=0 cpu=0",
        "stage=probe-complete writes=2 protected=0 bigidvfs=0 cpu=0",
    )
    for token in required:
        require(token in patch, f"required patch token missing: {token}")
    require(patch.count("#define GEMINI_PRB_SLOT_COUNT\t\t2") == 1,
            "two-slot definition count changed")
    require(patch.count("checkpoint=driver-init slot=1") == 1,
            "driver-init payload count changed")
    require(patch.count("checkpoint=probe-enter slot=2") == 1,
            "probe-enter payload count changed")
    added = added_lines(patch)
    for forbidden in (
        "default y",
        "0x444bf000",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_",
        "clk_prepare_enable(",
        "clk_enable(",
        "readl(",
        "writel(",
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
    fragment = (ROOT / FRAGMENT_REL).read_text(encoding="utf-8")
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity changed")
    require(contract["foundation"]["first_dmesg_evidence_commit"] ==
            "db28c2156a7a260f1d4e1bce0cbb865ff60053ea",
            "qualified foundation changed")
    require(contract["patch"]["path"] == PATCH_REL, "contract patch path changed")
    require(hashlib.sha256(patch_path.read_bytes()).hexdigest() ==
            contract["patch"]["sha256"], "patch identity changed")
    require(contract["ledger"]["owned_records"] == [1, 2], "owned records changed")
    require(contract["ledger"]["owned_addresses"] ==
            ["0x44410000", "0x44411000"], "owned addresses changed")
    require(contract["ledger"]["maximum_logical_record_commits"] == 2,
            "logical write ceiling changed")
    require(contract["ledger"]["console_ring_touched"] is False,
            "console exclusion changed")
    require(contract["scope"]["protected_clock_reads"] == 0,
            "protected-read scope opened")
    require(contract["scope"]["mapped_mmio_transactions"] == 0,
            "MMIO-transaction scope opened")
    require(contract["candidate"]["boot_candidate"] is False,
            "definition was promoted without admission")
    validate_patch_text(patch)

    for record in contract["ledger"]["records"]:
        marker = (f"{PREFIX} checkpoint={record['checkpoint']} "
                  f"slot={record['slot']}")
        require(len(("====0.000000-D\n" + marker +
                     f" crc32={record['crc32']}\n").encode()) == record["length"],
                f"record length changed: {record['checkpoint']}")
        require(f"{zlib.crc32(marker.encode()) & 0xffffffff:08x}" == record["crc32"],
                f"record CRC changed: {record['checkpoint']}")

    inherited = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "patches/v7.1.3/0323-pstore-add-Gemini-protected-readback-call-ledger.patch",
            "patches/v7.1.3/0325-soc-mediatek-add-Gemini-clock-backend-entry-ledger.patch",
            "patches/v7.1.3/0328-pstore-report-Gemini-manual-checkpoint-stage.patch",
            "patches/v7.1.3/0331-pstore-accept-Gemini-raw-entry-ledger.patch",
            "patches/v7.1.3/0332-pstore-qualify-Gemini-manual-raw-entry-write.patch",
            "patches/v7.1.3/0333-pstore-qualify-Gemini-first-dmesg-raw-write.patch",
        )
    }
    base = inherited["patches/v7.1.3/0323-pstore-add-Gemini-protected-readback-call-ledger.patch"]
    stages = inherited["patches/v7.1.3/0328-pstore-report-Gemini-manual-checkpoint-stage.patch"]
    raw = inherited["patches/v7.1.3/0332-pstore-qualify-Gemini-manual-raw-entry-write.patch"]
    calls = inherited["patches/v7.1.3/0325-soc-mediatek-add-Gemini-clock-backend-entry-ledger.patch"]
    for token in (
        "readl(slot) != GEMINI_PRB_SIGNATURE",
        "readl((u8 __iomem *)slot + 4) != len",
        "readl((u8 __iomem *)slot + 8) != len",
        "readb((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE + i)",
    ):
        require(token in base, f"inherited full-readback gate missing: {token}")
    for token in (
        'GEMINI_PRB_SET_STAGE("metadata-readback-refused")',
        'GEMINI_PRB_SET_STAGE("payload-readback-refused")',
        'GEMINI_PRB_SET_STAGE("success")',
    ):
        require(token in stages, f"inherited stage gate missing: {token}")
    order = (
        "memcpy_toio((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE, record, len)",
        "writel(len, (u8 __iomem *)slot + 4)",
        "writel(len, (u8 __iomem *)slot + 8)",
        "writel(GEMINI_PRB_SIGNATURE, slot)",
    )
    require(all(token in raw for token in order), "qualified raw writer is incomplete")
    require([raw.index(token) for token in order] ==
            sorted(raw.index(token) for token in order),
            "qualified writer order changed")
    require("if (!gemini_protected_readback_ledger_checkpoint(1))" in calls,
            "probe-entry checkpoint missing")
    require(calls.index("if (!gemini_protected_readback_ledger_checkpoint(1))") <
            calls.index("backend = devm_kzalloc"),
            "probe checkpoint is not the first probe operation")
    require("if (!gemini_protected_readback_ledger_checkpoint(0))" in calls,
            "driver-init checkpoint missing")
    require(calls.index("if (!gemini_protected_readback_ledger_checkpoint(0))") <
            calls.index("return platform_driver_register"),
            "driver-init checkpoint is not before registration")
    require("if (!gemini_prb_minimal_dt())" in calls,
            "exact clock-node DT gate missing")

    profiles = manifest["config"]["profiles"]
    additions = contract["profile"]["additional_fragments"]
    require(PROFILE in profiles and PARENT in profiles, "profile missing")
    require(profiles[PROFILE]["patch_series"] == "patches/series",
            "profile series changed")
    require(profiles[PROFILE]["fragments"] ==
            profiles[PARENT]["fragments"] + additions,
            "profile is not the exact serviceability parent plus three fragments")
    require(series[-1] == PATCH_REL.removeprefix("patches/"),
            "patch is not canonical tail")
    require(series.count(PATCH_REL.removeprefix("patches/")) == 1,
            "patch series count changed")

    for line in (
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER=y",
        f"CONFIG_{SYMBOL}=y",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION is not set",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION is not set",
        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER is not set",
        "# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set",
        "# CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER is not set",
        'CONFIG_LOCALVERSION="-gemini-clock-entry-first-dmesg"',
    ):
        require(line in fragment.splitlines(), f"fragment gate missing: {line}")
    combined_additions = "\n".join(
        (ROOT / path).read_text(encoding="utf-8") for path in additions
    )
    require("CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y" in combined_additions,
            "clock backend is not built in")
    for token in (
        "# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set",
        "# CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER is not set",
    ):
        require(token in combined_additions, f"backend veto missing: {token}")

    result = ROOT / contract["foundation"]["first_dmesg_result"]
    result_text = result.read_text(encoding="utf-8")
    for token in (
        "result=first-dmesg-cross-version-enumeration-pass",
        "pstore_exact_marker_count=1",
        "direct_record_1_exact_record_at_offset_12=true",
        "direct_record_2_header=444247430000000000000000",
        "next_branch=first-durable-pre-clock-backend-checkpoint-and-read-free-probe-entry",
    ):
        require(token in result_text, f"foundation evidence gate missing: {token}")

    print("validation=clock-backend-first-dmesg-entry-definition")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print("owned_records=1,2")
    print("owned_addresses=0x44410000,0x44411000")
    print("retained_record_commits_maximum=2")
    print("commit_order=payload,start,size,signature")
    print("full_local_readback=true")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("mapped_mmio_transactions=0")
    print("clock_enables=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
