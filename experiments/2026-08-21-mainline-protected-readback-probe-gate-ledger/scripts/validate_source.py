#!/usr/bin/env python3
"""Validate the generated Gemini probe/gate retained-ledger source."""

from __future__ import annotations

import argparse
from pathlib import Path


MODE = "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER"


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

    ledger = (root / "fs/pstore/gemini_protected_readback_ledger.c").read_text()
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
        "checkpoint=probe-enter slot=173 crc32=06a9b43b",
        "checkpoint=gate-passed slot=174 crc32=41e86ca4",
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

    require(ledger.count("gemini_prb_records[]") == 2,
            "one table in each exclusive mode")
    require(ledger.count("checkpoint=") == 4,
            "two old and two new fixed record payloads")
    require(ledger.count("writel(len,") == 2,
            "one unchanged metadata writer")
    require(ledger.count("memcpy_toio(") == 1, "one bounded writer body")
    require(ledger.count("ioremap_wc(") == 1, "one bounded mapping")
    require(ledger.count("iounmap(") == 1, "mapping always released")
    require("memset" not in ledger and "clear" not in ledger,
            "no clear or repair path")

    minimal = body(ledger, "static bool gemini_prb_minimal_dt",
                   "static bool gemini_prb_exact_dt")
    for token in (
        'of_machine_is_compatible("planet,gemini-pda")',
        'of_find_node_by_path("/reserved-memory/ramoops@44410000")',
        'of_device_is_compatible(node, "ramoops")',
        "resource.start == GEMINI_PRB_RESERVE_BASE",
        "resource_size(&resource) == GEMINI_PRB_RESERVE_SIZE",
        'of_property_read_bool(node, "no-map")',
        "of_node_put(node)",
    ):
        require(token in minimal, f"minimal entry gate: {token}")
    for forbidden in ("model", "record-size", "console-size", "ftrace-size",
                      "pmsg-size", "mem-type"):
        require(forbidden not in minimal,
                f"entry gate remains minimal: {forbidden}")

    exact = body(ledger, "static bool gemini_prb_exact_dt",
                 "static bool gemini_prb_prefix_valid")
    for token in (
        'strcmp(model, "MT6797X")',
        'of_property_read_u32(node, "record-size", &value)',
        'of_property_read_u32(node, "console-size", &value)',
        'of_property_read_u32(node, "ftrace-size", &value)',
        'of_property_read_u32(node, "pmsg-size", &value)',
        'of_property_read_u32(node, "mem-type", &value)',
    ):
        require(token in exact, f"complete second gate: {token}")

    writer = body(ledger, "static bool gemini_prb_write",
                  f"#ifdef {MODE}\nstatic bool gemini_prb_minimal_dt")
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
    require(f"#ifdef {MODE}" in checkpoint, "mode-specific DT gates")
    require("checkpoint == 0" in checkpoint and
            "!gemini_prb_minimal_dt()" in checkpoint,
            "entry checkpoint uses minimal safety gate")
    require("else if (!gemini_prb_exact_dt())" in checkpoint,
            "second checkpoint uses complete gate")
    require("#else\n\tif (!gemini_prb_exact_dt())" in checkpoint,
            "base call-ledger keeps complete gate for both records")

    mode_config = body(
        kconfig,
        "config PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
        "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT",
    )
    require("depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y"
            in mode_config, "mode depends on the isolated base ledger")
    require("default n" in mode_config, "mode remains opt-in")
    require("base\n\t  call-ledger behavior is unchanged" in mode_config,
            "historical behavior documented as unchanged")

    require("CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER" in makefile,
            "base ledger object remains selected")
    require(f"#ifdef {MODE}" not in makefile,
            "mode adds no second writer object")
    require("CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER" in ram,
            "isolated Gemini ramoops skip retained")
    require("bool gemini_protected_readback_ledger_checkpoint" in header,
            "base typed checkpoint API retained")

    probe = body(observer, "static int mt6797_readback_observer_probe",
                 "static const struct of_device_id")
    entry = "gemini_protected_readback_ledger_checkpoint(0)"
    gate = "gemini_protected_readback_ledger_checkpoint(1)"
    get_clock = "mt6797_readback_get_backend(dev,"
    clock = "mt6797_dvfsp_clock_backend_read("
    bigidvfs = "mt6797_bigidvfs_backend_read("
    require(probe.count(entry) == 2,
            "mode entry plus historical before-clock checkpoint")
    require(probe.count(gate) == 2,
            "mode gate plus historical after-clock checkpoint")
    require(probe.count(clock) == 1, "one protected-clock read")
    require(probe.count(bigidvfs) == 1, "one BigiDVFS read")
    require(
        probe.index(f"#ifdef {MODE}\n\tif (!{entry}")
        < probe.index(get_clock)
        < probe.index(f"#ifdef {MODE}\n\tif (!{gate}")
        < probe.index(clock)
        < probe.index(bigidvfs),
        "mode records entry then post-acquisition exact gate before reads",
    )
    require(f"#ifndef {MODE}\n\tif (!{gate}" in probe,
            "historical after-clock checkpoint retained when mode is off")
    require("goto put_bigidvfs;" in probe[
        probe.index(f"#ifdef {MODE}\n\tif (!{gate}"):
        probe.index(clock)
    ], "gate failure stops before clock")

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
    print("mode=probe-enter,gate-passed")
    print("retained_slot_count=2")
    print("retained_maximum_writes=2")
    print("retained_slots=173,174")
    print("protected_reads=clock-1,bigidvfs-1")
    print("payload_before_metadata=yes")
    print("full_readback=yes")
    print("retry=none")
    print("historical_call_ledger=unchanged-when-mode-off")
    print("cpu_requests=0")
    print("owner_registration=0")


if __name__ == "__main__":
    main()
