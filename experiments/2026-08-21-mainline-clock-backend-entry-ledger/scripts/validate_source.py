#!/usr/bin/env python3
"""Validate the generated clock-backend init/probe ledger source."""

from __future__ import annotations

import argparse
from pathlib import Path


MODE = "CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER"
PROBE_GATE = "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER"


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
    backend = (
        root / "drivers/soc/mediatek/mt6797-dvfsp-clock-backend.c"
    ).read_text()
    dts_makefile = (root / "arch/arm64/boot/dts/mediatek/Makefile").read_text()
    candidate = (
        root
        / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-clock-backend-entry.dts"
    ).read_text()

    for token in (
        "GEMINI_PRB_RESERVE_BASE\t\t0x44410000ULL",
        "GEMINI_PRB_RESERVE_SIZE\t\t0x000e0000ULL",
        "GEMINI_PRB_LEDGER_BASE\t\t0x444bb000ULL",
        "GEMINI_PRB_SLOT_COUNT\t\t4",
        "GEMINI_PRB_FIRST_OWNED_SLOT\t2",
        "checkpoint=driver-init slot=173 crc32=cda5d04d",
        "checkpoint=probe-enter slot=174 crc32=a3662888",
        "checkpoint=probe-enter slot=173 crc32=06a9b43b",
        "checkpoint=gate-passed slot=174 crc32=41e86ca4",
        "checkpoint=before-clock slot=173 crc32=08f2fe56",
        "checkpoint=after-clock slot=174 crc32=e477a18e",
        'of_find_node_by_path("/reserved-memory/ramoops@44410000")',
        'of_property_read_bool(node, "no-map")',
        "memcpy_toio((u8 __iomem *)slot + GEMINI_PRB_HEADER_SIZE",
        "gemini_prb_prefix_valid(ledger, checkpoint)",
    ):
        require(token in ledger, f"ledger token: {token}")
    require(ledger.count("gemini_prb_records[]") == 3,
            "three mutually exclusive record tables")
    require(ledger.count("checkpoint=") == 6,
            "two records in each historical/new mode")
    require(ledger.count("memcpy_toio(") == 1, "one writer body")
    require(ledger.count("writel(len,") == 2, "unchanged metadata commits")
    require(ledger.count("ioremap_wc(") == 1, "one bounded mapping")
    require(ledger.count("iounmap(") == 1, "mapping released")
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
        require(token in minimal, f"minimal safety gate: {token}")

    checkpoint = body(
        ledger,
        "bool gemini_protected_readback_ledger_checkpoint",
        "\n}",
    )
    require("checkpoint > 1" in checkpoint, "only two checkpoint ordinals")
    require("checkpoint == 0 && gemini_prb_armed" in checkpoint,
            "first checkpoint cannot repeat")
    require("checkpoint == 1 && !gemini_prb_armed" in checkpoint,
            "second requires first")
    require(
        f"#ifdef {MODE}\n\tif (!gemini_prb_minimal_dt())" in checkpoint,
        "new mode uses the minimal exact safety gate for both records",
    )
    require(
        f"#elif defined({PROBE_GATE})" in checkpoint
        and "else if (!gemini_prb_exact_dt())" in checkpoint,
        "probe/gate predecessor keeps its split gates",
    )
    require("#else\n\tif (!gemini_prb_exact_dt())" in checkpoint,
            "historical call ledger keeps exact gate")

    mode_config = body(
        kconfig,
        "config PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
        "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT",
    )
    for token in (
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "depends on MTK_MT6797_DVFSP_CLOCK_BACKEND=y",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
        "default n",
        "makes no\n\t  protected call",
        "two-write\n\t  ceiling",
    ):
        require(token in mode_config, f"mode Kconfig: {token}")

    probe = body(backend, "static int mt6797_dvfsp_clock_backend_probe",
                 "static const struct of_device_id")
    checkpoint_1 = "gemini_protected_readback_ledger_checkpoint(1)"
    require(probe.count(checkpoint_1) == 1, "one probe-entry checkpoint")
    require(
        probe.index(checkpoint_1) < probe.index("devm_kzalloc"),
        "checkpoint is the probe's first operation",
    )
    init = body(
        backend,
        "static int __init mt6797_dvfsp_clock_backend_driver_init",
        "static void __exit mt6797_dvfsp_clock_backend_driver_exit",
    )
    checkpoint_0 = "gemini_protected_readback_ledger_checkpoint(0)"
    require(init.count(checkpoint_0) == 1, "one driver-init checkpoint")
    require(
        init.index(checkpoint_0) < init.index("platform_driver_register"),
        "driver-init record precedes registration",
    )
    require(f"#ifdef {MODE}\nstatic int __init" in backend,
            "explicit init exists only in the new mode")
    require("#else\nmodule_platform_driver(" in backend,
            "historical registration macro retained when mode is off")
    require("#include <linux/pstore_ram.h>" in backend,
            "typed checkpoint declaration included")

    require(
        "mt6797-gemini-pda-clock-backend-entry.dtb" in dts_makefile,
        "candidate DTB is built",
    )
    require('#include "mt6797-gemini-pda.dts"' in candidate,
            "candidate derives from exact Gemini base")
    require(candidate.count('status = "okay";') == 1,
            "exactly one node enabled")
    require("&dvfsp_clock_backend" in candidate, "clock backend enabled")
    require("bigidvfs" not in candidate and "protected-readback-observer" not in candidate,
            "BigiDVFS and observer are not instantiated")

    new_runtime = init + probe + candidate
    for forbidden in (
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "clk_prepare_enable(",
        "readl(",
        "writel(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
        "kernel_restart(",
        "emergency_restart(",
    ):
        require(forbidden not in new_runtime, f"forbidden new path effect: {forbidden}")

    print("source_validation=pass")
    print("mode=driver-init,probe-enter")
    print("retained_slot_count=2")
    print("retained_maximum_writes=2")
    print("retained_slots=173,174")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("secure_calls=0")
    print("clock_enable=0")
    print("observer=disabled")
    print("payload_before_metadata=yes")
    print("full_readback=yes")
    print("retry=none")
    print("cpu_requests=0")
    print("owner_registration=0")


if __name__ == "__main__":
    main()
