#!/usr/bin/env python3
"""Validate the guarded physical-source candidate definition."""

from __future__ import annotations

import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PROFILE = "a72-physical-source-candidate"
KUNIT_PROFILE = "a72-physical-source-kunit"
FRAGMENT = "configs/gemini-a72-physical-source-candidate.fragment"
MODULE_FRAGMENT = "configs/gemini-da921x-provider-modules-control.fragment"
DTB = "dtbs/mediatek/mt6797-gemini-pda-a72-physical-source.dtb"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
    fragment = (ROOT / FRAGMENT).read_text(encoding="utf-8").splitlines()
    profiles = manifest["config"]["profiles"]

    require(PROFILE in profiles and KUNIT_PROFILE in profiles,
            "candidate or KUnit profile absent")
    candidate = profiles[PROFILE]
    kunit = profiles[KUNIT_PROFILE]
    expected = kunit["fragments"][:-1]
    expected.insert(expected.index("configs/gemini-da921x-provider-owner-refusal.fragment"),
                    MODULE_FRAGMENT)
    expected.append(FRAGMENT)
    require(candidate["base"] == "defconfig", "candidate base changed")
    require(candidate["patch_series"] == "patches/series",
            "candidate patch series changed")
    require(candidate["fragments"] == expected,
            "candidate is not the isolated KUnit source composition plus module policy")
    require(manifest["patch_series"] == "patches/series",
            "canonical manifest series changed")

    required = (
        "CONFIG_MODULES=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y",
        "CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y",
        "CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y",
        "CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",
        "# CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR is not set",
        "# CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-physical-source"',
    )
    forbidden_modes = (
        "PSTORE_GEMINI_PRE_RAMOOPS_LEDGER",
        "PSTORE_GEMINI_ARM64_ENTRY_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL",
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL",
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL",
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL",
        "PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION",
        "PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",
        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
        "PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION",
        "PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION",
        "MTK_MT6797_PROTECTED_READBACK_OBSERVER",
    )
    for line in required:
        require(fragment.count(line) == 1, f"candidate gate absent or duplicated: {line}")
    for symbol in forbidden_modes:
        line = f"# CONFIG_{symbol} is not set"
        require(fragment.count(line) == 1,
                f"conflicting candidate mode not closed exactly once: {symbol}")

    candidate_contract = contract["candidate"]
    require(candidate_contract["profile"] == PROFILE, "contract profile changed")
    require(candidate_contract["dtb"] == DTB, "contract DTB changed")
    require(candidate_contract["retained_writes_maximum"] == 2,
            "retained-write ceiling changed")
    require(candidate_contract["clock_calls"] == 1 and
            candidate_contract["bigidvfs_calls"] == 1,
            "read-only call count changed")
    require(candidate_contract["bigidvfs_smc_reads"] == 8,
            "BigiDVFS SMC-read count changed")
    require(candidate_contract["provider_transactions"] == 0 and
            candidate_contract["publisher_calls"] == 0 and
            candidate_contract["owner_mutations"] == 0 and
            candidate_contract["cpu_requests"] == 0,
            "action path opened")
    require(candidate_contract["status"] in (
        "definition-pending-build",
        "build-passed-assembly-pending",
        "validated",
    ), "candidate lifecycle state changed")
    require(candidate_contract["boot_candidate"] is
            (candidate_contract["status"] == "validated"),
            "candidate promotion does not match its validated lifecycle state")

    print("validation=a72-physical-source-candidate-definition")
    print(f"profile={PROFILE}")
    print(f"dtb={DTB}")
    print("retained_records=1,2")
    print("retained_writes_maximum=2")
    print("platform_calls=1")
    print("provider_snapshots=1")
    print("clock_calls=1")
    print("bigidvfs_calls=1")
    print("bigidvfs_smc_reads=8")
    print("provider_transactions=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("device_access=none")
    print("hardware_write=none")
    print(f"boot_candidate={str(candidate_contract['boot_candidate']).lower()}")
    print("result=pass")


if __name__ == "__main__":
    main()
