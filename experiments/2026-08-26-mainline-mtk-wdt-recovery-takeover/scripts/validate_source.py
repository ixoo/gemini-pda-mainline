#!/usr/bin/env python3
"""Validate generated MT6797 watchdog recovery-takeover source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    kconfig = (root / "drivers/watchdog/Kconfig").read_text(encoding="utf-8")
    source = (root / "drivers/watchdog/mtk_wdt.c").read_text(encoding="utf-8")
    header = (root / "include/linux/mtk_wdt.h").read_text(encoding="utf-8")

    require(kconfig.count(
        "config MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER\n") == 1,
        "production Kconfig")
    for token in (
        "MTK_WDT_RECOVERY_TIMEOUT_MS 15000U",
        "struct mtk_wdt_recovery_result",
        "mtk_wdt_recovery_takeover(struct device *dev",
    ):
        require(token in header, f"header token: {token}")
    for token in (
        "timeout_ms != MTK_WDT_RECOVERY_TIMEOUT_MS",
        "owner->owned = true;",
        "ops->write(context, WDT_LENGTH",
        "ops->write(context, WDT_MODE",
        "ops->write(context, WDT_RST, WDT_RST_RELOAD)",
        "WDT_LENGTH_TIMEOUT_MASK",
        "WDT_MODE_RECOVERY_MASK",
        "recovery_takeover = true",
        "if (!mtk_wdt->recovery_supported)",
        "EXPORT_SYMBOL_GPL(mtk_wdt_recovery_takeover)",
        "if (mtk_wdt->recovery.owned)",
        "return -EBUSY;",
    ):
        require(token in source, f"source token: {token}")
    require(source.count("mtk_wdt_mutation_begin(mtk_wdt, &flags)") == 5,
            "five competing operation gates")
    require(source.index("owner->owned = true;") <
            source.index("ops->write(context, WDT_LENGTH"),
            "ownership before first write")
    require(source.index("ops->write(context, WDT_LENGTH") <
            source.index("ops->write(context, WDT_MODE") <
            source.index("ops->write(context, WDT_RST"),
            "exact write order")
    require(source.count("mtk_wdt_recovery_takeover(") == 1,
            "definition only; no production caller")
    require("recovery_release" not in source + header, "no release API")
    require("psci_" not in source and "cpu_up(" not in source,
            "no CPU operation")
    require("pstore" not in source, "no retained write")

    if args.phase == "tests":
        require(kconfig.count(
            "config MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER_KUNIT_TEST\n") == 1,
            "test Kconfig")
        require(source.count("KUNIT_CASE(mtk_wdt_recovery_") == 5,
                "five focused cases")
        for token in (
            '"mtk-wdt-recovery-takeover"',
            "mtk_wdt_recovery_success_test",
            "mtk_wdt_recovery_rejections_test",
            "mtk_wdt_recovery_one_shot_test",
            "mtk_wdt_recovery_length_fault_test",
            "mtk_wdt_recovery_mode_fault_test",
            "MTK_WDT_RECOVERY_TEST_WRITES 3",
        ):
            require(token in source, f"test token: {token}")
        test_region = source[source.index(
            "#if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER_KUNIT_TEST)"
        ):source.index("module_param(timeout")]
        for token in ("ioread32", "iowrite32", "platform_device", "msleep",
                      "udelay", "watchdog_register"):
            require(token not in test_region,
                    f"hardware-free test token: {token}")
    else:
        require("RECOVERY_TAKEOVER_KUNIT_TEST\n\tbool" not in kconfig,
                "tests absent from production phase")
        require("mtk_wdt_recovery_success_test" not in source,
                "test source absent")

    print(f"source_phase={args.phase}")
    print("recovery_timeout_ms=15000")
    print("competing_operation_gates=5")
    print("production_callers=0")
    print("physical_watchdog_calls=0")
    print("device_action=none")
    print("source_validation=pass")


if __name__ == "__main__":
    main()
