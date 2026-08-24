#!/usr/bin/env python3
"""Validate the A72 early-initcall retained-ledger source state."""

from __future__ import annotations

import argparse
from pathlib import Path
import zlib


MODE = "CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER"
PARENT_MODE = "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    root = parser.parse_args().source_root.resolve()
    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    ledger = (root / "fs/pstore/gemini_protected_readback_ledger.c").read_text(
        encoding="utf-8"
    )
    observer = (
        root / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    ).read_text(encoding="utf-8")

    mode = kconfig.split(
        "config PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER", 1
    )[1].split("config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER", 1)[0]
    for token in (
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "depends on !PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER",
        "depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",
        "depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER",
        "Commit record 1 from pure initcall and record 2 from core initcall",
        "one fixed refusal marker",
        "exact DT, map, and raw-header gates",
        "at most two short retained write attempts",
        "CPU request, reset, reboot, or power",
    ):
        require(token in mode, f"Kconfig contract: {token}")
    require(mode.count("default n") == 1, "mode defaults off")

    require(ledger.count(f"defined({MODE})") == 3,
            "mode in base and two raw-write conditionals")
    require(ledger.count(f"#ifdef {MODE}") == 2,
            "one record branch and one early-init branch")
    require(ledger.count(f"#elif defined({PARENT_MODE})") == 1,
            "parent record branch retained")

    records = ledger.split(f"#ifdef {MODE}", 1)[1].split(
        f"#elif defined({PARENT_MODE})", 1
    )[0]
    expected = (
        ("pure-init", "commit", 1, "03d9627f"),
        ("core-init", "commit", 2, "57dd63b5"),
        ("pure-init", "primary-refused", 2, "5767e326"),
    )
    require(records.count("GEMINI_A72_EARLY_INIT_V1") == 3,
            "three fixed record identities")
    require(records.count("token=GAEI-20260824-A") == 3,
            "three exact tokens")
    for checkpoint, outcome, slot, checksum in expected:
        line = (
            "GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A "
            f"checkpoint={checkpoint} outcome={outcome} slot={slot}"
        )
        require(
            f"checkpoint={checkpoint} outcome={outcome} slot={slot} "
            f"crc32={checksum}\\n" in records,
            f"record identity: {checkpoint}/{outcome}",
        )
        require(f"{zlib.crc32(line.encode()):08x}" == checksum,
                f"record CRC: {checkpoint}/{outcome}")
    require(records.count("static const char gemini_prb_refusal_record[]") == 1,
            "one fixed refusal record")

    early = ledger.split(
        "static bool gemini_a72_pure_refusal_checkpoint(void)", 1
    )[1].split(f"#ifdef {PARENT_MODE}", 1)[0]
    for token in (
        "if (!gemini_prb_exact_dt())",
        "ioremap_wc(GEMINI_PRB_LEDGER_BASE,",
        "slot = (u8 __iomem *)ledger + GEMINI_PRB_SLOT_SIZE;",
        "if (gemini_prb_slot_available(slot))",
        "gemini_prb_write(slot, gemini_prb_refusal_record)",
        "iounmap(ledger);",
        "gemini_protected_readback_ledger_checkpoint(0)",
        "gemini_a72_pure_refusal_checkpoint() ? -EAGAIN : -EIO",
        "pure_initcall(gemini_a72_pure_initcall_checkpoint);",
        "gemini_protected_readback_ledger_checkpoint(1)",
        "core_initcall(gemini_a72_core_initcall_checkpoint);",
    ):
        require(token in early, f"early-init path: {token}")
    require(early.count("gemini_prb_write(") == 1,
            "one bounded fallback writer call")
    require(early.count("gemini_protected_readback_ledger_checkpoint(") == 2,
            "two ordered primary checkpoint calls")
    require(early.index("pure_initcall(") < early.index("core_initcall("),
            "source declares pure before core")
    require(early.index("gemini_prb_slot_available(slot)") <
            early.index("gemini_prb_write(slot, gemini_prb_refusal_record)"),
            "fallback raw precondition precedes write")
    require(early.index("gemini_prb_exact_dt()") < early.index("ioremap_wc("),
            "fallback exact DT gate precedes mapping")
    require("for (" not in early and "while (" not in early,
            "fallback has no retry loop")

    observer_init = observer.split(
        "static int __init mt6797_a72_physical_source_init(void)", 1
    )[1].split("device_initcall(mt6797_a72_physical_source_init);", 1)[0]
    guard = observer_init.index(f"defined({MODE})")
    parent = observer_init.index(f"defined({PARENT_MODE})")
    suppression = observer_init.index("return 0;", parent)
    registration = observer_init.index("platform_driver_register(")
    require(guard < parent < suppression < registration,
            "both initcall modes suppress observer registration")
    require(observer_init.count("return 0;") == 1,
            "one shared observer suppression return")
    require(observer.count(MODE) == 1,
            "new mode does not alter probe or capture")

    added_path = records + early + observer_init[guard:suppression + 9]
    for forbidden in (
        "platform_driver_register(",
        "kvzalloc",
        "get_device(",
        "mt6797_a72_platform_state_snapshot(",
        "mt6797_a72_provider_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "regmap_write(",
        "i2c_transfer(",
        "cpu_up(",
        "cpu_down(",
        "arm_smccc_smc(",
        "kernel_restart(",
        "orderly_poweroff(",
    ):
        require(forbidden not in added_path,
                f"forbidden enabled-path action: {forbidden}")

    print("validation=a72-early-initcall-ledger-source")
    print("retained_checkpoints=pure-init,core-init")
    print("fallback=pure-init-primary-refused")
    print("retained_write_attempts_maximum=2")
    print("observer_registrations=0")
    print("allocations=0")
    print("source_lookups=0")
    print("provider_transactions=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
