#!/usr/bin/env python3
"""Validate the generated MediaTek watchdog boot-status source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_region(text: str, start: str, end: str) -> str:
    require(text.count(start) == 1, f"unique start marker: {start}")
    require(text.count(end) == 1, f"unique end marker: {end}")
    return text.split(start, 1)[1].split(end, 1)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    driver = (root / "drivers/watchdog/mtk_wdt.c").read_text()
    kconfig = (root / "drivers/watchdog/Kconfig").read_text()
    header = (root / "include/linux/mtk_wdt.h").read_text()

    for token in (
        "config CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE",
        "config CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST",
    ):
        require(token not in kconfig, f"malformed Kconfig symbol: {token}")
    for token in (
        "config MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE",
        "depends on MEDIATEK_WATCHDOG=y",
        "config MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST",
        "select MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE",
    ):
        require(token in kconfig, f"Kconfig token: {token}")

    require("#define WDT_STATUS\t\t0x0c" in driver,
            "raw status offset")
    require(".has_boot_status = true" in driver,
            "MT6797-only capture capability")
    require(driver.count("readl(mtk_wdt->wdt_base + WDT_STATUS)") == 1,
            "exactly one production raw-status read")
    probe_prefix = driver.split("irq = platform_get_irq_optional", 1)[0]
    require("mtk_wdt_capture_boot_status" in probe_prefix,
            "capture precedes IRQ and watchdog initialization")
    require(driver.index("readl(mtk_wdt->wdt_base + WDT_STATUS)") <
            driver.index("mtk_wdt_init(&mtk_wdt->wdt_dev)"),
            "capture precedes mtk_wdt_init")
    require("EXPORT_SYMBOL_GPL(mtk_wdt_boot_status_snapshot)" in driver,
            "typed snapshot API exported")

    helper = added_region(
        driver,
        "static void\nmtk_wdt_capture_boot_status",
        "#endif\n\n/**\n * toprgu_reset_sw_en_unlocked()",
    )
    for token in (
        "READ_ONCE(status->valid)",
        "smp_load_acquire(&status->valid)",
        "WRITE_ONCE(status->raw, raw)",
        "smp_store_release(&status->valid, true)",
        "return -ENODATA",
        "return -ENODEV",
    ):
        require(token in helper, f"snapshot helper token: {token}")
    for forbidden in ("writel(", "iowrite", "mtk_wdt_init(",
                      "watchdog_", "reset_control", "psci", "cpu_"):
        require(forbidden not in helper,
                f"snapshot helper effect token: {forbidden}")

    require(driver.count("KUNIT_CASE(mtk_wdt_boot_status_") == 4,
            "four focused KUnit cases")
    for case in ("invalid", "exact", "every_bit", "immutable"):
        require(f"mtk_wdt_boot_status_{case}_test" in driver,
                f"KUnit case: {case}")
    test_region = driver.split(
        "#if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST)",
        2)[-1]
    for forbidden in ("readl(", "writel(", "ioread", "iowrite",
                      "platform_device", "watchdog_start", "watchdog_stop"):
        require(forbidden not in test_region,
                f"hardware token in focused tests: {forbidden}")

    for token in (
        "struct mtk_wdt_boot_status",
        "u32 raw;",
        "bool valid;",
        "mtk_wdt_boot_status_snapshot",
        "return -EOPNOTSUPP;",
    ):
        require(token in header, f"public header token: {token}")
    for forbidden in ("reset_provenance", "platform_reset", "external_reset",
                      "safe_reset", "cpu8", "A34"):
        require(forbidden not in driver + header,
                f"forbidden classifier/lifecycle token: {forbidden}")

    print("source_validation=pass")
    print("status_reads=1")
    print("capture_order=before-mtk_wdt_init")
    print("kunit_cases=4")
    print("reset_classifier=none")
    print("a34_caller=none")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
