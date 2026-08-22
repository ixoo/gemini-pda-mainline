#!/usr/bin/env python3
"""Validate the exact protected-readback raw-entry ledger definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
PROFILE = "protected-readback-raw-entry-ledger"
PARENT = "protected-readback-call-ledger"
PATCH = "v7.1.3/0331-pstore-accept-Gemini-raw-entry-ledger.patch"
PATCH_SHA256 = "f312b82218f59da54026d1e90d39f75de1ad28ffaac9e7eb867219800a7260f2"
FRAGMENT = "configs/gemini-protected-readback-raw-entry-ledger.fragment"
MODE = "PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER"
EXPERIMENT = "experiments/2026-08-22-mainline-protected-readback-raw-entry-ledger"
EXPECTED_FRAGMENT = """# Exact raw-entry successor to the protected-readback two-record ledger.
# Normal ramoops remains skipped; one clock read is bracketed by two owned
# signature-last retained commits with full local readback and no retry.
CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER=y
CONFIG_LOCALVERSION=\"-gemini-protected-raw\"
"""


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


def main() -> None:
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    profiles = manifest["config"]["profiles"]
    parent = profiles[PARENT]
    profile = profiles[PROFILE]
    require(profile["base"] == parent["base"] == "defconfig", "profile base changed")
    require(profile["patch_series"] == "patches/series", "profile series changed")
    require(profile["fragments"] == parent["fragments"] + [FRAGMENT],
            "profile is not exact parent plus raw fragment")
    fragment = ROOT / FRAGMENT
    require(fragment.is_file() and not fragment.is_symlink(), "fragment is unsafe")
    require(fragment.read_text(encoding="utf-8") == EXPECTED_FRAGMENT,
            "fragment changed")

    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()
    require(series[-1] == PATCH, "raw-entry patch is not canonical tip")
    require(series.count(PATCH) == 1 and len(series) == len(set(series)),
            "canonical series duplicate changed")
    patch_path = ROOT / "patches" / PATCH
    require(patch_path.is_file() and not patch_path.is_symlink(), "patch is unsafe")
    text = patch_path.read_text(encoding="utf-8")
    require(hashlib.sha256(text.encode()).hexdigest() == PATCH_SHA256,
            "patch hash changed")
    require("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
            "synthetic author changed")
    require("Signed-off-by:" not in text, "synthetic certification added")
    require("Subject: [PATCH] pstore: accept Gemini raw entry ledger" in text,
            "patch subject changed")
    paths = tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))
    require(paths == (
        "fs/pstore/Kconfig",
        "drivers/soc/mediatek/mt6797-protected-readback-observer.c",
        "fs/pstore/gemini_protected_readback_ledger.c",
    ), "patch path inventory changed")

    added = "\n".join(changed_lines(text, "+"))
    require(added.count(f"config {MODE}") == 1, "mode declaration changed")
    require(added.count("\tdefault n") == 1, "mode is not uniquely default off")
    for dependency in (
        "PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "MTK_MT6797_PROTECTED_READBACK_OBSERVER=y",
        "!PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL",
        "!PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
        "!PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
    ):
        require(added.count(f"\tdepends on {dependency}") == 1,
                f"mode dependency changed: {dependency}")
    require(added.count(f"#ifdef CONFIG_{MODE}") == 3,
            "raw-mode positive guard count changed")
    require(added.count(f"#ifndef CONFIG_{MODE}") == 1,
            "raw-mode negative guard count changed")
    require(added.count("readl(slot) == ~0U") == 1, "raw signature gate changed")
    require(added.count("readl((u8 __iomem *)slot + 4) == ~0U") == 1,
            "raw start gate changed")
    require(added.count("readl((u8 __iomem *)slot + 8) == ~0U") == 1,
            "raw size gate changed")
    require(added.count("writel(GEMINI_PRB_SIGNATURE, slot)") == 1,
            "signature commit changed")
    require(text.index("writel(len, (u8 __iomem *)slot + 8)")
            < text.index("writel(GEMINI_PRB_SIGNATURE, slot)"),
            "signature is not after metadata")
    require(added.count("gemini_prb_slot_available(slot)") == 2,
            "raw availability use count changed")
    require(added.count("gemini_protected_readback_ledger_checkpoint(0)") == 1,
            "first checkpoint count changed")
    require(added.count("mt6797_dvfsp_clock_backend_read(&clock_backend->dev,") == 1,
            "protected clock call count changed")
    require(added.count("gemini_protected_readback_ledger_checkpoint(1)") == 1,
            "second checkpoint count changed")
    require('" state=complete attempts=1 clock_calls=1 bigidvfs_calls=0"' in added,
            "clock-only completion marker changed")
    for forbidden in (
        "mt6797_bigidvfs_backend_read(",
        "cpu_up(",
        "cpu_down(",
        "regmap_write(",
        "i2c_transfer(",
        "kernel_restart(",
        "schedule_delayed_work(",
        "platform_driver_register(",
        "persistent_ram_new(",
    ):
        require(forbidden not in added, f"patch added forbidden effect: {forbidden}")

    contract = json.loads((ROOT / EXPERIMENT / "contract.json").read_text())
    require(contract["patch"]["sha256"] == PATCH_SHA256, "contract hash changed")
    require(contract["profile"]["name"] == PROFILE, "contract profile changed")
    require(contract["profile"]["parent"] == PARENT, "contract parent changed")
    ledger = contract["ledger"]
    require(ledger["entry_records"] == [171, 172, 173, 174], "entry records changed")
    require(ledger["owned_records"] == [173, 174], "owned records changed")
    require(ledger["maximum_logical_record_commits"] == 2, "write ceiling changed")
    require(ledger["commit_order"] == ["payload", "start", "size", "signature"],
            "commit order changed")
    scope = contract["scope"]
    require(scope["normal_ramoops_registration"] is False, "ramoops owner opened")
    require(scope["protected_clock_reads_maximum"] == 1, "clock ceiling changed")
    require(scope["bigidvfs_reads"] == 0, "BigiDVFS action opened")
    require(scope["cpu_on"] is False and scope["cpu_off"] is False,
            "CPU scope opened")
    require(scope["boot_candidate"] is False, "definition became candidate")

    print("validation=protected-readback-raw-entry-ledger-definition")
    print(f"profile={PROFILE}")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print("raw_entry_header_reads=3-per-not-yet-owned-record")
    print("retained_record_commits_maximum=2")
    print("signature_last=true")
    print("full_local_readback=true")
    print("protected_clock_reads_maximum=1")
    print("bigidvfs_reads=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
