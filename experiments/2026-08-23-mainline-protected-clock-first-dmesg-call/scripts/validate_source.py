#!/usr/bin/env python3
"""Validate the first-dmesg protected-clock call-ledger source."""

from __future__ import annotations

import argparse
import zlib
from pathlib import Path


MODE = "CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def body(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    ledger = (
        root / "fs/pstore/gemini_protected_readback_ledger.c"
    ).read_text(encoding="utf-8")
    observer = (
        root / "drivers/soc/mediatek/mt6797-protected-readback-observer.c"
    ).read_text(encoding="utf-8")
    backend = (
        root / "drivers/soc/mediatek/mt6797-dvfsp-clock-backend.c"
    ).read_text(encoding="utf-8")

    mode = body(
        kconfig,
        "config PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION",
        "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER",
    )
    for token in (
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER=y",
        "depends on !PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION",
        "default n",
        "exactly one protected clock read and zero\n\t  BigiDVFS reads",
        "two-write ceiling",
        "no-clear/no-retry",
    ):
        require(token in mode, f"mode Kconfig: {token}")

    layout = body(
        ledger,
        "#define GEMINI_PRB_RESERVE_BASE",
        "#define GEMINI_PRB_HEADER_SIZE",
    )
    require(f"defined({MODE})" in layout, "mode selects first-dmesg layout")
    require("GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE" in layout,
            "ledger starts at first dmesg record")
    require("GEMINI_PRB_SLOT_COUNT\t\t2" in layout,
            "ledger owns exactly two records")
    require("GEMINI_PRB_FIRST_OWNED_SLOT\t0" in layout,
            "first owned record is record 1")

    records = body(
        ledger,
        f"#ifdef {MODE}",
        "#elif defined(CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION)",
    )
    expected = (
        ("before-clock", 1, "183854b2"),
        ("after-clock", 2, "d14b85aa"),
    )
    require(records.count("GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1") == 2,
            "two exact record identities")
    require(records.count("token=GPCF-20260823-A") == 2,
            "two exact record tokens")
    for checkpoint, slot, checksum in expected:
        line = (
            "GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 "
            f"token=GPCF-20260823-A checkpoint={checkpoint} slot={slot}"
        )
        require(f"checkpoint={checkpoint} slot={slot} crc32={checksum}" in records,
                f"record identity: {checkpoint}")
        actual = f"{zlib.crc32(line.encode()):08x}"
        require(actual == checksum, f"record crc32: {checkpoint}")

    raw_mode = body(
        observer,
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER",
        "#else\nstatic int mt6797_readback_observer_probe",
    )
    before = raw_mode.index("gemini_protected_readback_ledger_checkpoint(0)")
    call = raw_mode.index("mt6797_dvfsp_clock_backend_read(")
    after = raw_mode.index("gemini_protected_readback_ledger_checkpoint(1)")
    require(before < call < after, "checkpoints exactly bracket the clock call")
    require(raw_mode.count("mt6797_dvfsp_clock_backend_read(") == 1,
            "one protected clock call")
    require("mt6797_bigidvfs_backend_read(" not in raw_mode,
            "no BigiDVFS call")
    require("clock_calls=1 bigidvfs_calls=0" in raw_mode,
            "terminal call receipt")
    require("cpu_requests=0 owner_registration=0" in raw_mode,
            "terminal ownership and CPU closure")

    require(ledger.count("memcpy_toio(") == 1, "no second payload writer")
    require(ledger.count("bool gemini_protected_readback_ledger_checkpoint(") == 1,
            "no second checkpoint implementation")
    require("mt6797_dvfsp_cspm_execute(" in backend,
            "clock transaction uses the handoff-owned CSPM callback")
    require("CSPM owner=handoff" in backend, "single-owner backend retained")

    print("validation=protected-clock-first-dmesg-call-source")
    print("retained_records=1,2")
    print("retained_maximum_writes=2")
    print("protected_clock_reads=1")
    print("bigidvfs_reads=0")
    print("new_writer=0")
    print("new_call_site=0")
    print("cpu_requests=0")
    print("owner_registration=0")
    print("result=pass")


if __name__ == "__main__":
    main()
