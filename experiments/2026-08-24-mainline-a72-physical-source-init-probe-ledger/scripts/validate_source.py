#!/usr/bin/env python3
"""Validate the A72 observer init/probe ledger source state."""

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
        root / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    ).read_text(encoding="utf-8")

    mode = kconfig.split(
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER", 1
    )[1].split("config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER", 1)[0]
    for token in (
        "one retained record in its built-in",
        "init before driver registration",
        "one as the first probe operation",
        "Return before allocation or source lookup",
        "no overwrite, clear, retry, allocation, physical snapshot",
    ):
        require(token in mode, f"Kconfig contract: {token}")
    require("one after all three bound source devices" not in mode,
            "old source-held help absent")

    records = ledger.split(f"#ifdef {MODE}", 1)[1].split(
        "#elif defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER)", 1
    )[0]
    expected = (
        ("driver-init", 1, "85e5f336"),
        ("probe-enter", 2, "85116721"),
    )
    require(records.count("GEMINI_A72_INIT_PROBE_V1") == 2, "two records")
    require(records.count("token=GAIP-20260824-A") == 2, "two tokens")
    for checkpoint, slot, checksum in expected:
        line = (
            "GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A "
            f"checkpoint={checkpoint} slot={slot}"
        )
        require(
            f"checkpoint={checkpoint} slot={slot} crc32={checksum}\\n"
            in records,
            f"record identity: {checkpoint}",
        )
        require(
            f"{zlib.crc32(line.encode()):08x}" == checksum,
            f"record CRC: {checkpoint}",
        )
    require("GEMINI_A72_PRECAPTURE_V1" not in records, "old records absent")
    require("checkpoint=sources-held" not in records, "old checkpoint absent")
    require(ledger.count("memcpy_toio(") == 1, "single retained writer")
    require(
        ledger.count("bool gemini_protected_readback_ledger_checkpoint(") == 1,
        "single checkpoint implementation",
    )

    init = observer.split(
        "static int __init mt6797_a72_physical_source_init(void)", 1
    )[1].split("device_initcall(mt6797_a72_physical_source_init);", 1)[0]
    probe = observer.split(
        "mt6797_a72_physical_source_probe(struct platform_device *pdev)", 1
    )[1].split(
        "static const struct of_device_id mt6797_a72_physical_source_of_match[]",
        1,
    )[0]
    checkpoint_0 = "gemini_protected_readback_ledger_checkpoint(0)"
    checkpoint_1 = "gemini_protected_readback_ledger_checkpoint(1)"
    allocation = "snapshot = kvzalloc_obj(*snapshot)"
    platform = 'get_device(dev, "mediatek,platform-state")'
    clock = 'get_device(dev, "mediatek,clock-backend")'
    bigidvfs = 'get_device(dev, "mediatek,bigidvfs-backend")'
    require(init.count(f"#ifdef {MODE}") == 1, "one init guard")
    require(init.count(checkpoint_0) == 1, "one driver-init checkpoint")
    require(
        init.index(checkpoint_0) < init.index("platform_driver_register("),
        "driver-init checkpoint before registration",
    )
    require(probe.count(f"#ifdef {MODE}") == 1, "one probe guard")
    require(probe.count(checkpoint_1) == 1, "one probe-entry checkpoint")
    require(checkpoint_0 not in probe, "driver-init checkpoint absent from probe")
    require(
        probe.index(checkpoint_1)
        < probe.index("return 0;")
        < probe.index(allocation)
        < probe.index(platform)
        < probe.index(clock)
        < probe.index(bigidvfs),
        "experiment returns before allocation and source lookup",
    )
    require("sources-held ledger checkpoint" not in observer,
            "old source-held call site absent")
    require("put_bigidvfs:" not in observer,
            "obsolete experiment-only cleanup label absent")
    require("builtin_platform_driver(" not in observer,
            "implicit driver init replaced")
    require(observer.count("device_initcall(mt6797_a72_physical_source_init);") == 1,
            "one explicit built-in initcall")
    require(observer.count("mt6797_bigidvfs_backend_read") == 1,
            "no new BigiDVFS call")
    require(observer.count("mt6797_a72_provider_snapshot") == 1,
            "no new provider call")
    require(observer.count("mt6797_dvfsp_clock_backend_read") == 1,
            "no new clock call")
    require("cpu_up(" not in observer and "cpu_down(" not in observer,
            "no CPU request")

    print("validation=a72-physical-source-init-probe-source")
    print("retained_checkpoints=driver-init,probe-enter")
    print("retained_writes_maximum=2")
    print("allocations_in_enabled_path=0")
    print("source_lookups_in_enabled_path=0")
    print("capture_calls_in_enabled_path=0")
    print("provider_transactions=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
