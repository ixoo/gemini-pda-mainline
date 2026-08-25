#!/usr/bin/env python3
"""Validate generated A72 platform-snapshot observer source."""

from __future__ import annotations

import argparse
import zlib
from pathlib import Path


PHASES = ("ledger", "observer", "binding", "tests")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def section(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def validate_ledger(root: Path) -> None:
    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    ledger = (
        root / "fs/pstore/gemini_protected_readback_ledger.c"
    ).read_text(encoding="utf-8")
    mode = section(
        kconfig,
        "config PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER",
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",
    )
    for token in (
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "depends on MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y",
        "immediately before its first platform read",
        "one only after one stable",
        "signature-last",
        "no-retry protocol",
    ):
        require(token in mode, f"ledger Kconfig token: {token}")
    require(
        "MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y ||" in kconfig,
        "base ledger accepts platform observer",
    )

    layout = section(
        ledger, "#define GEMINI_PRB_RESERVE_BASE", "#define GEMINI_PRB_HEADER_SIZE"
    )
    require(
        "defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER)" in layout,
        "platform ledger selects first-dmesg layout",
    )
    require("GEMINI_PRB_SLOT_COUNT\t\t2" in layout, "two retained slots")
    require("GEMINI_PRB_FIRST_OWNED_SLOT\t0" in layout, "first slot index")

    records = section(
        ledger,
        "#ifdef CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER",
        "#elif defined(CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER)",
    )
    expected = (
        ("before-platform", 1, "a8bf2262"),
        ("after-platform", 2, "ca566ccf"),
    )
    require(
        records.count("GEMINI_A72_PLATFORM_SNAPSHOT_V1") == 2,
        "two platform-snapshot records",
    )
    require(records.count("token=GAPS-20260824-A") == 2, "two exact tokens")
    for checkpoint, slot, checksum in expected:
        line = (
            "GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A "
            f"checkpoint={checkpoint} slot={slot}"
        )
        require(
            f'"checkpoint={checkpoint} slot={slot} crc32={checksum}\\n"'
            in records,
            f"record identity: {checkpoint}",
        )
        require(
            f"{zlib.crc32(line.encode()):08x}" == checksum,
            f"record CRC: {checkpoint}",
        )
    require(
        ledger.count(
            "#if defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER) ||"
        )
        == 2,
        "raw all-ones and signature-last conditionals",
    )
    require(ledger.count("memcpy_toio(") == 1, "single retained writer")


def validate_observer(root: Path) -> None:
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text(encoding="utf-8")
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text(encoding="utf-8")
    observer = (
        root / "drivers/soc/mediatek/mt6797-a72-platform-snapshot-observer.c"
    ).read_text(encoding="utf-8")
    internal = (
        root
        / "drivers/soc/mediatek/mt6797-a72-platform-snapshot-observer-internal.h"
    ).read_text(encoding="utf-8")
    config = section(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER",
        "config MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER",
    )
    for token in (
        "depends on MTK_MT6797_A72_PLATFORM_STATE",
        "default n",
        "26 read-only register observations",
        "no DA921x provider, clock, BigiDVFS",
    ):
        require(token in config, f"observer Kconfig token: {token}")
    require(
        "CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER" in makefile,
        "observer Makefile wiring",
    )

    capture = section(
        observer,
        "int mt6797_platform_snapshot_capture(",
        "static struct device *",
    )
    order = (
        "ops->checkpoint(context, 0)",
        "ops->snapshot(context, platform, snapshot)",
        "snapshot->valid",
        "ops->checkpoint(context, 1)",
    )
    positions = [capture.index(token) for token in order]
    require(positions == sorted(positions), "checkpoint/snapshot/valid order")
    require(capture.count("ops->snapshot(") == 1, "one snapshot call")
    require(capture.count("ops->checkpoint(") == 2, "two checkpoints")
    require(capture.count("memset(snapshot, 0, sizeof(*snapshot));") == 2,
            "zero entry and every error")
    require("for (" not in capture and "while (" not in capture,
            "capture has no retry loop")

    probe = section(
        observer,
        "static int mt6797_a72_platform_snapshot_probe",
        "static const struct of_device_id",
    )
    require(probe.count("mt6797_platform_snapshot_capture(") == 1,
            "probe performs one capture")
    require(probe.count("put_device(platform)") == 1,
            "probe releases exact platform reference")
    require(
        probe.index("mt6797_platform_snapshot_capture(")
        < probe.index("put_device(platform)"),
        "reference retained through capture",
    )
    for forbidden in (
        "mt6797_a72_provider_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
    ):
        require(forbidden not in observer, f"forbidden operation: {forbidden}")
    for token in (
        "platform_calls=1 stable_samples=2",
        "register_observations=26 retained_writes=2 retries=0",
        "provider_snapshots=0 protected_clock_reads=0",
        "bigidvfs_reads=0 secure_calls=0 publisher_calls=0",
        "owner_mutations=0 cpu_requests=0",
    ):
        require(token in observer, f"terminal receipt: {token}")
    for token in (
        "struct mt6797_a72_platform_snapshot_observer_ops",
        "mt6797_platform_snapshot_capture",
    ):
        require(token in internal, f"injected interface: {token}")


def validate_binding(root: Path) -> None:
    binding = (
        root
        / "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-platform-snapshot-observer.yaml"
    ).read_text(encoding="utf-8")
    for token in (
        "mediatek,mt6797-a72-platform-snapshot-observer",
        "mediatek,platform-state:",
        "$ref: /schemas/types.yaml#/definitions/phandle",
        "additionalProperties: false",
    ):
        require(token in binding, f"binding token: {token}")
    require(binding.count("mediatek,platform-state") == 3,
            "one property, required entry, and example")


def validate_tests(root: Path) -> None:
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text(encoding="utf-8")
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text(encoding="utf-8")
    tests = (
        root / "drivers/soc/mediatek/mt6797-a72-platform-snapshot-observer-test.c"
    ).read_text(encoding="utf-8")
    config = section(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_SNAPSHOT_KUNIT_TEST",
        "config MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER",
    )
    for token in (
        "depends on KUNIT=y",
        "depends on MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER",
        "No MMIO, retained RAM, I2C, SMC",
    ):
        require(token in config, f"test Kconfig token: {token}")
    require(
        "CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_KUNIT_TEST" in makefile,
        "test Makefile wiring",
    )
    require(tests.count("KUNIT_CASE(") == 4, "four focused cases")
    for token in (
        "MT6797_PLATFORM_CHECKPOINT_0",
        "MT6797_PLATFORM_SNAPSHOT",
        "MT6797_PLATFORM_CHECKPOINT_1",
        "snapshot_ret = -EAGAIN",
        "snapshot_valid = false",
        'name = "mt6797-a72-platform-snapshot"',
    ):
        require(token in tests, f"focused test token: {token}")
    for forbidden in (
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "i2c_transfer(",
        "gemini_protected_readback_ledger_checkpoint(",
        "cpu_up(",
    ):
        require(forbidden not in tests, f"test physical operation: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validators = {
        "ledger": (validate_ledger,),
        "observer": (validate_ledger, validate_observer),
        "binding": (validate_ledger, validate_observer, validate_binding),
        "tests": (validate_ledger, validate_observer, validate_binding, validate_tests),
    }
    for validator in validators[args.phase]:
        validator(root)
    print(f"source_validation={args.phase}-pass")


if __name__ == "__main__":
    main()
