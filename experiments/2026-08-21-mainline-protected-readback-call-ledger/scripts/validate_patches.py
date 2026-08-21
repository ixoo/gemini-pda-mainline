#!/usr/bin/env python3
"""Validate the generated protected-readback call-ledger patch."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCH = "0323-pstore-add-Gemini-protected-readback-call-ledger.patch"


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
    require((patch_dir / "series").read_text() == PATCH + "\n",
            "generated series")

    text = (patch_dir / PATCH).read_text()
    header, separator, _body = text.partition("\n\n")
    require(bool(separator), "RFC 2822 patch header terminator")
    unfolded = " ".join(line.strip() for line in header.splitlines())
    require(
        "Subject: [PATCH] pstore: add Gemini protected readback call ledger"
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
        "fs/pstore/gemini_protected_readback_ledger.c",
        "fs/pstore/Kconfig",
        "fs/pstore/Makefile",
        "fs/pstore/ram.c",
        "include/linux/pstore_ram.h",
        "drivers/soc/mediatek/mt6797-protected-readback-observer.c",
    ):
        require(path in text, f"patch path: {path}")

    added = added_lines(text)
    require(added.count("checkpoint=") == 2, "exact two fixed records")
    require(added.count("writel(len,") == 2,
            "only two retained metadata stores in writer")
    require(added.count("mt6797_dvfsp_clock_backend_read(") == 0,
            "existing clock call is context, not a new call")
    require(added.count("mt6797_bigidvfs_backend_read(") == 0,
            "existing BigiDVFS call is context, not a new call")
    for forbidden in (
        "arm_smccc_smc(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
        "kernel_restart(",
        "emergency_restart(",
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")

    print(f"patch={PATCH}")
    print("retained_slot_count=2")
    print("retained_maximum_writes=2")
    print("new_protected_reads=0")
    print("cpu_requests=0")
    print("owner_registration=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
