#!/usr/bin/env python3
"""Validate the exact manual retained-checkpoint control and admission."""

from __future__ import annotations

import json
from pathlib import Path
import re
import zlib


ROOT = Path(__file__).resolve().parents[3]
PROFILE = "da921x-manual-checkpoint-control"
PARENT = "da921x-current-service-control"
PATCH = "v7.1.3/0327-pstore-add-Gemini-manual-checkpoint-control.patch"
FRAGMENT = "configs/gemini-manual-checkpoint-control.fragment"
MODE = "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL"
EXPECTED_FRAGMENT = """# Isolated manual exercise of the exact retained checkpoint writer on the
# runtime-proven current-tree serviceability base. The clock backend, observer,
# protected transports, DA921x action, and CPU8/CPU9 admission remain absent.
# CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER is not set
CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y
CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y
# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER is not set
# CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER is not set
# CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND is not set
# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set
# CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER is not set
# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set
CONFIG_LOCALVERSION="-gemini-checkpoint-ctl"
"""
RECORDS = (
    (
        "GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A "
        "checkpoint=manual-first slot=173",
        "9576f05d",
    ),
    (
        "GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A "
        "checkpoint=manual-second slot=174",
        "c90b9e18",
    ),
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
        match = re.match(
            r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@",
            line,
        )
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
            prefix = body_line[0]
            require(prefix in " +-\\", f"invalid patch-hunk prefix: {prefix!r}")
            if prefix in " -":
                actual_old += 1
            if prefix in " +":
                actual_new += 1
        require(actual_old == expected_old,
                f"old hunk count changed: {actual_old} != {expected_old}")
        require(actual_new == expected_new,
                f"new hunk count changed: {actual_new} != {expected_new}")
    require(hunks == 4, "patch hunk inventory changed")


def validate_patch(text: str) -> None:
    header, separator, _body = text.partition("\n\n")
    require(bool(separator), "patch header terminator changed")
    unfolded = " ".join(line.strip() for line in header.splitlines())
    require(
        "Subject: [PATCH] pstore: add Gemini manual checkpoint control" in unfolded,
        "patch subject changed",
    )
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
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

    added = added_lines(text)
    require(added.count(f"config {MODE}") == 1, "manual mode declaration changed")
    require(added.count('bool "Gemini protected-readback writer manual control"') == 1,
            "manual mode prompt changed")
    require(added.count("\tdefault n") == 1, "manual mode is not uniquely default off")
    for closure in (
        "depends on !MTK_MT6797_DVFSP_CLOCK_BACKEND",
        "depends on !MTK_MT6797_PROTECTED_READBACK_OBSERVER",
        "depends on !PSTORE_GEMINI_PRE_RAMOOPS_LEDGER",
        "depends on !PSTORE_GEMINI_ARM64_ENTRY_LEDGER",
    ):
        require(closure in added, f"manual-mode closure changed: {closure}")
    require(
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y" in added,
        "base-writer dependency did not admit the manual mode",
    )

    for body, expected_crc in RECORDS:
        prefix, checkpoint = body.split(" checkpoint=", 1)
        source_record = (
            f'"{prefix} "\n'
            f'\t"checkpoint={checkpoint} crc32={expected_crc}\\n"'
        )
        require(source_record in added, f"record source changed: {body}")
        actual_crc = f"{zlib.crc32(body.encode()) & 0xffffffff:08x}"
        require(actual_crc == expected_crc, f"record CRC calculation changed: {body}")
    require(added.count("checkpoint=manual-first") == 1, "first record count changed")
    require(added.count("checkpoint=manual-second") == 1, "second record count changed")
    require(added.count("gemini_protected_readback_ledger_checkpoint(0)") == 1,
            "first checkpoint call count changed")
    require(added.count("gemini_protected_readback_ledger_checkpoint(1)") == 1,
            "second checkpoint call count changed")
    require(
        "second = first && gemini_protected_readback_ledger_checkpoint(1);" in added,
        "second checkpoint is not gated by first-checkpoint success",
    )
    require(
        added.count("late_initcall(gemini_protected_readback_manual_control_init);") == 1,
        "manual call-site registration changed",
    )
    require(added.count("GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1") == 1,
            "live result marker count changed")
    require(added.count("\treturn 0;") == 1,
            "manual control no longer preserves serviceability")

    for forbidden in (
        "ioremap",
        "memcpy_toio",
        "writel(",
        "readl(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "clk_prepare_enable(",
        "i2c_transfer(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
        "kernel_restart(",
        "emergency_restart(",
        "schedule_delayed_work(",
        "while (",
        "for (",
    ):
        require(forbidden not in added, f"new call site added forbidden effect: {forbidden}")


def main() -> None:
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    profiles = manifest["config"]["profiles"]
    parent = profiles[PARENT]
    profile = profiles[PROFILE]
    require(profile["base"] == parent["base"] == "defconfig", "profile base changed")
    require(profile["patch_series"] == manifest["patch_series"] == "patches/series",
            "profile does not use the canonical series")
    require(profile["fragments"] == parent["fragments"] + [FRAGMENT],
            "profile is not the exact serviceability parent plus one fragment")

    fragment = ROOT / FRAGMENT
    require(fragment.is_file() and not fragment.is_symlink(), "manual fragment is unsafe")
    require(fragment.read_text(encoding="utf-8") == EXPECTED_FRAGMENT,
            "manual fragment contents changed")
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()
    require(series[-1] == PATCH, "manual patch is not the canonical tip")
    require(series.count(PATCH) == 1 and len(series) == len(set(series)),
            "canonical series duplicate changed")
    patch_path = ROOT / "patches" / PATCH
    require(patch_path.is_file() and not patch_path.is_symlink(), "manual patch is unsafe")
    validate_patch(patch_path.read_text(encoding="utf-8"))

    contract_path = ROOT / "experiments/2026-08-21-mainline-manual-checkpoint-control/contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    require(contract["profile"]["name"] == PROFILE, "contract profile changed")
    require(contract["ledger"]["maximum_writes"] == 2, "write ceiling changed")
    require(contract["ledger"]["new_writer"] is False, "new writer was introduced")
    require(contract["scope"]["protected_clock_reads"] == 0, "protected read scope changed")
    require(contract["scope"]["cpu_on"] is False and contract["scope"]["cpu_off"] is False,
            "CPU scope changed")
    require(contract["build"]["repository_commit"] ==
            "c1d59f3b1783f70e92b4ab27d11c5809f9722869",
            "admitted build commit changed")
    require(contract["candidate"]["padded_sha256"] ==
            "53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
            "admitted candidate changed")
    require(contract["candidate"]["lk_gates"] == "32-of-32",
            "LK gate result changed")
    require(contract["offline_validation"] == {
        "source_and_configuration_mutations_rejected": 13,
        "dt_mutations_rejected": 15,
        "live_runtime_mutations_rejected": 19,
        "retained_recovery_mutations_rejected": 9,
        "independent_raw_assemblies": "byte-identical",
        "independent_padding_constructions": "byte-identical",
        "device_access": False,
        "hardware_write": False,
    }, "offline admission evidence changed")
    require(contract["scope"]["boot_candidate"] is True,
            "exact offline-admitted candidate was demoted")
    runtime = contract["runtime"]
    require(runtime["physical_selections"] == 1,
            "runtime selection count changed")
    require(runtime["mainline_boot_id"] ==
            "517b88d0-9fb1-4fa5-9300-a57dac005041",
            "mainline runtime identity changed")
    require(runtime["classification"] ==
            "manual-checkpoint-first-refused-serviceable",
            "runtime classification changed")
    require(runtime["manual_first"] == 0 and runtime["manual_second"] == 0 and
            runtime["retained_writes"] == 0,
            "manual refusal result changed")
    require(runtime["protected_calls"] == 0 and runtime["cpu_requests"] == 0,
            "runtime safety result changed")
    require(runtime["post_return_boot2_sha256"] ==
            contract["candidate"]["padded_sha256"],
            "post-return boot2 identity changed")

    print("validation=mainline-manual-checkpoint-control-admission")
    print(f"profile={PROFILE}")
    print(f"profile_fragments={len(profile['fragments'])}")
    print(f"canonical_patch_count={len(series)}")
    print("retained_maximum_writes=2")
    print("new_retained_writer=0")
    print("protected_calls=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("runtime_result=manual-checkpoint-first-refused-serviceable")
    print("runtime_retained_writes=0")
    print("result=pass")


if __name__ == "__main__":
    main()
