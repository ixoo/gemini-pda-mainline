#!/usr/bin/env python3
"""Validate the generated protected-readback retained call ledger."""

from __future__ import annotations

import argparse
from pathlib import Path


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

    ledger = (
        root / "fs/pstore/gemini_protected_readback_ledger.c"
    ).read_text()
    kconfig = (root / "fs/pstore/Kconfig").read_text()
    makefile = (root / "fs/pstore/Makefile").read_text()
    ram = (root / "fs/pstore/ram.c").read_text()
    header = (root / "include/linux/pstore_ram.h").read_text()
    observer = (
        root / "drivers/soc/mediatek/mt6797-protected-readback-observer.c"
    ).read_text()

    for token in (
        "GEMINI_PRB_RESERVE_BASE\t\t0x44410000ULL",
        "GEMINI_PRB_RESERVE_SIZE\t\t0x000e0000ULL",
        "GEMINI_PRB_LEDGER_BASE\t\t0x444bb000ULL",
        "GEMINI_PRB_SLOT_COUNT\t\t4",
        "GEMINI_PRB_FIRST_OWNED_SLOT\t2",
        "GEMINI_PRB_SIGNATURE\t\t0x43474244",
        "checkpoint=before-clock slot=173 crc32=08f2fe56",
        "checkpoint=after-clock slot=174 crc32=e477a18e",
        'of_find_node_by_path("/reserved-memory/ramoops@44410000")',
        'strcmp(model, "MT6797X")',
        'of_property_read_u32(node, "record-size", &value)',
        'of_property_read_u32(node, "console-size", &value)',
        'of_property_read_u32(node, "ftrace-size", &value)',
        'of_property_read_u32(node, "pmsg-size", &value)',
        'of_property_read_u32(node, "mem-type", &value)',
        'of_property_read_bool(node, "no-map")',
        "memcpy_toio((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE",
        "gemini_prb_prefix_valid(ledger, checkpoint)",
    ):
        require(token in ledger, f"ledger token: {token}")

    require(ledger.count("gemini_prb_records[]") == 1, "one record table")
    require(ledger.count("checkpoint=") == 2, "exact two record payloads")
    require(ledger.count("writel(len,") == 2, "metadata-only retained writes")
    require(ledger.count("memcpy_toio(") == 1, "one bounded writer body")
    require(ledger.count("ioremap_wc(") == 1, "one bounded mapping")
    require(ledger.count("iounmap(") == 1, "mapping always released")
    require("memset" not in ledger and "clear" not in ledger,
            "no clear or repair path")

    writer = body(
        ledger,
        "static bool gemini_prb_write",
        "static bool gemini_prb_exact_dt",
    )
    require(
        writer.index("gemini_prb_slot_empty")
        < writer.index("memcpy_toio")
        < writer.index("wmb();")
        < writer.index("writel(len,")
        < writer.index("\tmb();")
        < writer.index("readl(slot)"),
        "empty-check then payload-before-metadata and full readback",
    )
    require("for (i = 0; i < len; i++)" in writer,
            "full payload readback")

    checkpoint = body(
        ledger,
        "bool gemini_protected_readback_ledger_checkpoint",
        "\n}",
    )
    require("checkpoint > 1" in checkpoint, "only two checkpoint ordinals")
    require("checkpoint == 0 && gemini_prb_armed" in checkpoint,
            "first checkpoint cannot repeat")
    require("checkpoint == 1 && !gemini_prb_armed" in checkpoint,
            "second checkpoint requires first")
    require("!gemini_prb_exact_dt()" in checkpoint,
            "DT fingerprint before mapping or write")

    for token in (
        "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER",
        "depends on PSTORE_RAM=y",
        "depends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y",
        "depends on !PSTORE_GEMINI_PRE_RAMOOPS_LEDGER",
        "depends on !PSTORE_GEMINI_ARM64_ENTRY_LEDGER",
        "default n",
    ):
        require(token in kconfig, f"Kconfig token: {token}")
    require("CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER" in makefile,
            "ledger object selected")
    require(
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER" in ram
        and 'of_machine_is_compatible("planet,gemini-pda")' in ram,
        "isolated Gemini ramoops skip",
    )
    require(
        "bool gemini_protected_readback_ledger_checkpoint" in header
        and "return true;" in header,
        "typed API and no-op unselected stub",
    )

    probe = body(
        observer,
        "static int mt6797_readback_observer_probe",
        "static const struct of_device_id",
    )
    before = "gemini_protected_readback_ledger_checkpoint(0)"
    clock = "mt6797_dvfsp_clock_backend_read("
    after = "gemini_protected_readback_ledger_checkpoint(1)"
    bigidvfs = "mt6797_bigidvfs_backend_read("
    require(probe.count(before) == 1, "one before-clock checkpoint")
    require(probe.count(after) == 1, "one after-clock checkpoint")
    require(probe.count(clock) == 1, "one protected-clock read")
    require(probe.count(bigidvfs) == 1, "one BigiDVFS read")
    require(
        probe.index(before) < probe.index(clock) < probe.index(after)
        < probe.index(bigidvfs),
        "checkpoint and protected-read ordering",
    )
    first_gate = probe[probe.index(before):probe.index(clock)]
    second_gate = probe[probe.index(after):probe.index(bigidvfs)]
    require("goto put_bigidvfs;" in first_gate,
            "first ledger failure stops before clock")
    require("goto put_bigidvfs;" in second_gate,
            "second ledger failure stops before BigiDVFS")

    added = ledger + observer
    for forbidden in (
        "arm_smccc_smc(",
        "MT6797_BIGIDVFS_FID_WRITE",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops",
        "watchdog",
        "kernel_restart(",
        "emergency_restart(",
        "schedule_work(",
        "msleep(",
    ):
        require(forbidden not in added, f"forbidden new effect: {forbidden}")

    print("source_validation=pass")
    print("retained_slot_count=2")
    print("retained_maximum_writes=2")
    print("retained_slots=173,174")
    print("protected_reads=clock-1,bigidvfs-1")
    print("checkpoint_order=before-clock,after-clock,bigidvfs")
    print("payload_before_metadata=yes")
    print("full_readback=yes")
    print("retry=none")
    print("normal_mainline_ramoops=skipped-on-exact-Gemini-only")
    print("cpu_requests=0")
    print("owner_registration=0")


if __name__ == "__main__":
    main()
