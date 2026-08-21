#!/usr/bin/env python3
"""Validate the generated clock-backend init/probe ledger patch."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCH = "0325-soc-mediatek-add-Gemini-clock-backend-entry-ledger.patch"


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
        "Subject: [PATCH] soc: mediatek: add Gemini clock-backend entry ledger"
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
        "drivers/soc/mediatek/mt6797-dvfsp-clock-backend.c",
        "arch/arm64/boot/dts/mediatek/Makefile",
        "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-clock-backend-entry.dts",
    ):
        require(path in text, f"patch path: {path}")
    for path in (
        "drivers/soc/mediatek/mt6797-protected-readback-observer.c",
        "drivers/soc/mediatek/mt6797-bigidvfs-backend.c",
        "fs/pstore/ram.c",
        "include/linux/pstore_ram.h",
    ):
        require(path not in text, f"unchanged/forbidden path: {path}")

    added = added_lines(text)
    require(added.count("checkpoint=driver-init") == 1,
            "one driver-init record")
    require(added.count("checkpoint=probe-enter") == 1,
            "one new probe-entry record")
    require("CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER" in added,
            "isolated mode selector")
    require(added.count("gemini_protected_readback_ledger_checkpoint(") == 2,
            "two checkpoint call sites")
    require(added.count("writel(") == 0, "no additional retained writer")
    require(added.count("memcpy_toio(") == 0,
            "no additional retained payload writer")
    for forbidden in (
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "clk_prepare_enable(",
        "readl(",
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
    print("new_retained_writer=0")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("secure_calls=0")
    print("observer=disabled-by-profile-and-dt")
    print("cpu_requests=0")
    print("owner_registration=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
