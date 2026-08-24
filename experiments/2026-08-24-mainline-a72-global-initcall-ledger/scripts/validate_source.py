#!/usr/bin/env python3
"""Validate the A72 global-initcall retained-ledger source state."""

from __future__ import annotations

import argparse
from pathlib import Path
import zlib


MODE = "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER"
OLD_MODE = "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"


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
        "config PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER", 1
    )[1].split("config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER", 1)[0]
    for token in (
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",
        "depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER",
        "Commit retained record 1 from a global subsys initcall",
        "from a later fs initcall",
        "Do not register the physical-source observer",
        "at most two short writes",
        "no observer registration, allocation,",
        "CPU request, reset, reboot, or power action",
    ):
        require(token in mode, f"Kconfig contract: {token}")
    require(mode.count("default n") == 1, "mode defaults off")

    require(ledger.count("#include <linux/errno.h>") == 1,
            "explicit errno include")
    require(ledger.count(f"defined({MODE})") == 3,
            "mode in base and two raw-write conditionals")
    require(ledger.count(f"#ifdef {MODE}") == 2,
            "one record branch and one initcall branch")

    records = ledger.split(f"#ifdef {MODE}", 1)[1].split(
        f"#elif defined({OLD_MODE})", 1
    )[0]
    expected = (
        ("subsys-init", 1, "cf2a6946"),
        ("fs-init", 2, "91ac2a49"),
    )
    require(records.count("GEMINI_A72_INITCALL_V1") == 2, "two records")
    require(records.count("token=GAIC-20260824-A") == 2, "two tokens")
    for checkpoint, slot, checksum in expected:
        line = (
            "GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A "
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
    require("GEMINI_A72_INIT_PROBE_V1" not in records,
            "predecessor records not selected")

    initcalls = ledger.split(
        "static int __init gemini_a72_subsys_initcall_checkpoint(void)", 1
    )[1].split(
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL", 1
    )[0]
    require(
        initcalls.count("gemini_protected_readback_ledger_checkpoint(0)") == 1,
        "one subsys checkpoint",
    )
    require(
        initcalls.count("gemini_protected_readback_ledger_checkpoint(1)") == 1,
        "one fs checkpoint",
    )
    require(
        initcalls.count("subsys_initcall(gemini_a72_subsys_initcall_checkpoint);")
        == 1,
        "one subsys initcall",
    )
    require(
        initcalls.count("fs_initcall(gemini_a72_fs_initcall_checkpoint);") == 1,
        "one fs initcall",
    )
    require(initcalls.count("? 0 : -EIO;") == 2,
            "writer refusal is an initcall error")
    require(
        initcalls.index("subsys_initcall(") < initcalls.index("fs_initcall("),
        "source declares the ordered boundaries clearly",
    )
    require(ledger.count("memcpy_toio(") == 1, "single retained writer")
    require(
        ledger.count("bool gemini_protected_readback_ledger_checkpoint(") == 1,
        "single checkpoint implementation",
    )

    observer_init = observer.split(
        "static int __init mt6797_a72_physical_source_init(void)", 1
    )[1].split("device_initcall(mt6797_a72_physical_source_init);", 1)[0]
    new_guard = observer_init.index(f"#ifdef {MODE}")
    new_return = observer_init.index("return 0;", new_guard)
    old_guard = observer_init.index(f"#ifdef {OLD_MODE}")
    registration = observer_init.index("platform_driver_register(")
    require(new_guard < new_return < old_guard < registration,
            "new mode exits before predecessor checkpoint and registration")
    require(observer_init.count(f"#ifdef {MODE}") == 1,
            "one observer suppression guard")
    require(observer.count("device_initcall(mt6797_a72_physical_source_init);") == 1,
            "historical explicit device initcall retained")
    require(observer.count("gemini_protected_readback_ledger_checkpoint(0)") == 1,
            "historical driver-init checkpoint retained")
    require(observer.count("gemini_protected_readback_ledger_checkpoint(1)") == 1,
            "historical probe checkpoint retained")
    require(observer.count(MODE) == 1, "new mode does not alter probe or capture")

    added_path = records + initcalls + observer_init[new_guard:old_guard]
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
        "kernel_restart(",
        "orderly_poweroff(",
    ):
        require(forbidden not in added_path, f"forbidden enabled-path action: {forbidden}")

    print("validation=a72-global-initcall-ledger-source")
    print("retained_checkpoints=subsys-init,fs-init")
    print("retained_writes_maximum=2")
    print("observer_registrations=0")
    print("allocations=0")
    print("source_lookups=0")
    print("capture_calls=0")
    print("provider_transactions=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
