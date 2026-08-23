#!/usr/bin/env python3
"""Validate the admitted first-dmesg protected-clock definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PATCH_REL = "patches/v7.1.3/0336-pstore-qualify-Gemini-protected-clock-call-in-first-dmesg.patch"
FRAGMENT_REL = "configs/gemini-protected-clock-first-dmesg-call.fragment"
PROFILE = "da921x-protected-clock-first-dmesg-call"
PARENT = "da921x-current-service-control"
EXTRA_FRAGMENTS = [
    "configs/gemini-dvfsp-clock-backend.fragment",
    "configs/gemini-dvfsp-bigidvfs-readonly.fragment",
    "configs/gemini-protected-readback-observer.fragment",
    "configs/gemini-protected-readback-call-ledger.fragment",
    "configs/gemini-protected-readback-raw-entry-ledger.fragment",
    FRAGMENT_REL,
]
PATCH_SHA256 = "97394ab84b4f0fc68f69388a8456a6f82321f2597405b9f23c253949ecf7033f"


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
    added = added_lines(patch)
    for path in (
        "fs/pstore/Kconfig",
        "fs/pstore/gemini_protected_readback_ledger.c",
    ):
        require(path in patch, f"required patch path missing: {path}")
    for forbidden_path in ("drivers/", "arch/", "include/", "fs/pstore/ram.c"):
        require(forbidden_path not in patch,
                f"forbidden patch path added: {forbidden_path}")
    require(patch.count("diff --git ") == 2, "patch must change exactly two files")
    require("Signed-off-by:" not in patch, "synthetic patch gained a sign-off")
    require(
        "CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION"
        in added,
        "isolated mode selector missing",
    )
    require(added.count("GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1") == 2,
            "two record identities required")
    require(added.count("token=GPCF-20260823-A") == 2,
            "two record tokens required")
    require(added.count("checkpoint=before-clock slot=1 crc32=183854b2") == 1,
            "before-clock record changed")
    require(added.count("checkpoint=after-clock slot=2 crc32=d14b85aa") == 1,
            "after-clock record changed")
    for forbidden in (
        "memcpy_toio(", "writel(", "readl(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(", "arm_smccc_smc(",
        "clk_prepare_enable(", "cpu_up(", "cpu_down(",
        "kernel_restart(", "emergency_restart(", 'status = "okay"',
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    patch_path = ROOT / PATCH_REL
    patch = patch_path.read_text(encoding="utf-8")
    fragment = (ROOT / FRAGMENT_REL).read_text(encoding="utf-8").splitlines()
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity changed")
    generation = contract["patch_generation"]
    require(generation["expected_patch"] == PATCH_REL, "contract patch path changed")
    require(generation["patch_sha256"] == PATCH_SHA256,
            "contract patch identity changed")
    require(hashlib.sha256(patch_path.read_bytes()).hexdigest() == PATCH_SHA256,
            "admitted patch bytes changed")
    require(generation["checkpatch"] == "0 errors, 0 warnings, 0 checks",
            "checkpatch result changed")
    require(generation["boot_candidate"] is False,
            "patch generation was promoted to a boot candidate")
    require(contract["offline_definition"]["profile"] == PROFILE,
            "offline profile identity changed")
    require(contract["offline_definition"]["candidate_bigidvfs_node"] == "disabled",
            "BigiDVFS DT closure changed")
    require(contract["scope"]["protected_clock_reads_maximum"] == 1,
            "clock-call ceiling changed")
    require(contract["scope"]["bigidvfs_reads"] == 0,
            "BigiDVFS-call closure changed")
    require(contract["scope"]["cpu_on"] is False and
            contract["scope"]["cpu_off"] is False,
            "CPU action scope opened")
    validate_patch_text(patch)

    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles and PARENT in profiles, "required profile missing")
    require(profiles[PROFILE]["patch_series"] == "patches/series",
            "profile patch series changed")
    require(profiles[PROFILE]["fragments"] ==
            profiles[PARENT]["fragments"] + EXTRA_FRAGMENTS,
            "profile is not the exact full-service parent plus isolated gate")
    require(series[-1] == PATCH_REL.removeprefix("patches/"),
            "protected-clock patch is not canonical tail")
    require(series.count(PATCH_REL.removeprefix("patches/")) == 1,
            "protected-clock patch series count changed")

    required_fragment = (
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER=y",
        "# CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER is not set",
        "# CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION is not set",
        "CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION=y",
        'CONFIG_LOCALVERSION="-gemini-clock-one-read"',
    )
    for line in required_fragment:
        require(line in fragment, f"fragment gate missing: {line}")

    foundation = ROOT / contract["foundation"]["coexistence_result"]
    require(hashlib.sha256(foundation.read_bytes()).hexdigest() ==
            contract["foundation"]["coexistence_result_sha256"],
            "runtime foundation changed")

    print("validation=protected-clock-first-dmesg-call-definition")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print("retained_records=1,2")
    print("retained_maximum_writes=2")
    print("protected_clock_reads=1")
    print("bigidvfs_reads=0")
    print("new_writer=0")
    print("new_call_site=0")
    print("cpu_requests=0")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
