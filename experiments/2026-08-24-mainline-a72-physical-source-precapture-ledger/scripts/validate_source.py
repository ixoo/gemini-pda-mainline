#!/usr/bin/env python3
"""Validate the A72 physical-source pre-capture ledger source state."""

from __future__ import annotations

import argparse
from pathlib import Path
import zlib


MODE = "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"


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
        root
        / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    ).read_text(encoding="utf-8")

    mode = kconfig.split(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER", 1
    )[1].split("config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER", 1)[0]
    for token in (
        'bool "Gemini A72 physical-source pre-capture ledger"',
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
        "depends on !PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
        "depends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER",
        "default n",
    ):
        require(token in mode, f"Kconfig mode token: {token}")
    physical = kconfig.split(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER", 1
    )[1].split(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER", 1
    )[0]
    require(
        "depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"
        in physical,
        "reciprocal physical-ledger exclusion",
    )

    records = ledger.split(
        "#ifdef CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER", 1
    )[1].split(
        "#elif defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER)", 1
    )[0]
    expected = (
        ("probe-enter", 1, "b8f6c566"),
        ("sources-held", 2, "9e7fd3e6"),
    )
    require(records.count("GEMINI_A72_PRECAPTURE_V1") == 2, "two records")
    require(records.count("token=GAPC-20260824-A") == 2, "two tokens")
    for checkpoint, slot, checksum in expected:
        line = (
            "GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A "
            f"checkpoint={checkpoint} slot={slot}"
        )
        require(
            f'checkpoint={checkpoint} slot={slot} crc32={checksum}\\n' in records,
            f"record identity: {checkpoint}",
        )
        require(
            f"{zlib.crc32(line.encode()):08x}" == checksum,
            f"record CRC: {checkpoint}",
        )
    require(
        ledger.count(
            "#if defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER) ||"
        )
        == 2,
        "two raw first-dmesg conditionals",
    )
    require(ledger.count("memcpy_toio(") == 1, "single retained writer")
    require(
        ledger.count("bool gemini_protected_readback_ledger_checkpoint(") == 1,
        "single checkpoint implementation",
    )

    probe = observer.split(
        "mt6797_a72_physical_source_probe(struct platform_device *pdev)", 1
    )[1]
    checkpoint_0 = "gemini_protected_readback_ledger_checkpoint(0)"
    checkpoint_1 = "gemini_protected_readback_ledger_checkpoint(1)"
    allocation = "snapshot = kvzalloc_obj(*snapshot)"
    platform = 'get_device(dev, "mediatek,platform-state")'
    clock = 'get_device(dev, "mediatek,clock-backend")'
    bigidvfs = 'get_device(dev, "mediatek,bigidvfs-backend")'
    capture = "mt6797_a72_physical_source_run(&context"
    require(probe.count(f"#ifdef {MODE}") == 2, "two mode call-site guards")
    require(probe.count(checkpoint_0) == 1, "one probe-entry checkpoint")
    require(probe.count(checkpoint_1) == 1, "one sources-held checkpoint")
    require(
        probe.index(checkpoint_0) < probe.index(allocation) < probe.index(platform),
        "probe-entry precedes allocation and source acquisition",
    )
    require(
        probe.index(platform)
        < probe.index(clock)
        < probe.index(bigidvfs)
        < probe.index(checkpoint_1)
        < probe.index(capture),
        "sources-held boundary order",
    )
    between = probe[probe.index(checkpoint_1):probe.index(capture)]
    for token in (
        'dev_info(dev, "pre-capture ledger complete; capture disabled\\n")',
        "ret = 0;",
        "goto put_bigidvfs;",
    ):
        require(token in between, f"pre-capture stop token: {token}")
    require(probe.count("goto put_bigidvfs;") >= 2, "reference cleanup path")
    require(probe.count("kvfree(snapshot);") == 1, "snapshot cleanup")
    require(observer.count("mt6797_bigidvfs_backend_read") == 1,
            "no new BigiDVFS call")
    require(observer.count("mt6797_a72_provider_snapshot") == 1,
            "no new provider call")
    require(observer.count("mt6797_dvfsp_clock_backend_read") == 1,
            "no new clock call")
    require("cpu_up(" not in observer and "cpu_down(" not in observer,
            "no CPU request")

    print("validation=a72-physical-source-precapture-source")
    print("retained_checkpoints=probe-enter,sources-held")
    print("retained_writes_maximum=2")
    print("capture_calls_in_precapture_path=0")
    print("provider_transactions=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
