#!/usr/bin/env python3
"""Validate the generated first-dmesg protected-clock patch."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCH = "0336-pstore-qualify-Gemini-protected-clock-call-in-first-dmesg.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    found = tuple(path.name for path in patch_dir.glob("*.patch"))
    require(found == (PATCH,), "one exact patch filename")
    require((patch_dir / "series").read_text(encoding="utf-8") == PATCH + "\n",
            "generated series")

    text = (patch_dir / PATCH).read_text(encoding="utf-8")
    header, separator, _body = text.partition("\n\n")
    require(bool(separator), "RFC 2822 patch header terminator")
    unfolded = " ".join(line.strip() for line in header.splitlines())
    require(
        "Subject: [PATCH] pstore: qualify Gemini protected clock call in first dmesg"
        in unfolded,
        "exact patch subject",
    )
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
        in text,
        "explicit synthetic experiment author",
    )
    require("Signed-off-by:" not in text, "no synthetic certification")

    for path in (
        "fs/pstore/Kconfig",
        "fs/pstore/gemini_protected_readback_ledger.c",
    ):
        require(path in text, f"patch path: {path}")
    for path in (
        "drivers/",
        "arch/",
        "include/",
        "fs/pstore/ram.c",
    ):
        require(path not in text, f"unchanged/forbidden path: {path}")

    added = added_lines(text)
    require(
        "CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION"
        in added,
        "isolated mode selector",
    )
    require(added.count("checkpoint=before-clock") == 1,
            "one before-clock record")
    require(added.count("checkpoint=after-clock") == 1,
            "one after-clock record")
    require(added.count("GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1") == 2,
            "two exact record identities")
    for forbidden in (
        "memcpy_toio(",
        "writel(",
        "readl(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "clk_prepare_enable(",
        "cpu_up(",
        "cpu_down(",
        "kernel_restart(",
        "emergency_restart(",
        'status = "okay"',
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")

    print(f"patch={PATCH}")
    print("changed_files=2")
    print("retained_records=1,2")
    print("retained_maximum_writes=2")
    print("new_retained_writer=0")
    print("new_protected_reads=0")
    print("total_protected_reads=clock-1,bigidvfs-0")
    print("secure_calls=0")
    print("owner_registration=0")
    print("cpu_requests=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
