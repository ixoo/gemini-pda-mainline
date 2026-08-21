#!/usr/bin/env python3
"""Validate the generated MT6797 A72 platform-state source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    wdt = (root / "drivers/watchdog/mtk_wdt.c").read_text()
    driver = (root / "drivers/soc/mediatek/mt6797-a72-platform-state.c").read_text()
    header = (root / "include/linux/soc/mediatek/mt6797-a72-platform-state.h").read_text()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text()
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text()
    dtsi = (root / "arch/arm64/boot/dts/mediatek/mt6797.dtsi").read_text()
    gemini = (root / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts").read_text()
    binding = (root / (
        "Documentation/devicetree/bindings/soc/mediatek/"
        "mediatek,mt6797-a72-platform-state.yaml"
    )).read_text()

    status_start = wdt.index("static int toprgu_reset_status")
    status_end = wdt.index("static int toprgu_reset_assert", status_start)
    status = wdt[status_start:status_end]
    for token in (
        "spin_lock_irqsave(&data->lock, flags)",
        "readl(data->wdt_base + WDT_SWSYSRST)",
        "spin_unlock_irqrestore(&data->lock, flags)",
        "return !!(value & BIT(id))",
    ):
        require(token in status, f"TOPRGU status token: {token}")
    require(".status = toprgu_reset_status" in wdt,
            "TOPRGU reset-status callback registered")
    for forbidden in ("writel(", "toprgu_reset_update", "udelay", "msleep"):
        require(forbidden not in status, f"TOPRGU status effect: {forbidden}")

    for token in (
        "config MTK_MT6797_A72_PLATFORM_STATE",
        "default-off read-only source",
        "performs no register write or polling",
    ):
        require(token in kconfig, f"Kconfig token: {token}")
    require("default y" not in kconfig.split(
        "config MTK_MT6797_A72_PLATFORM_STATE", 1)[1].split("config ", 1)[0],
        "platform-state source remains default-off")
    require(
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE) += "
        "mt6797-a72-platform-state.o" in makefile,
        "platform-state object registration",
    )

    for token in (
        "#define MT6797_SPM_CPU_PWR_STATUS\t\t0x188",
        "#define MT6797_SPM_CPU_PWR_STATUS_2ND\t\t0x18c",
        "#define MT6797_SPM_MP2_CPUSYS_PWR_CON\t\t0x218",
        "#define MT6797_SPM_MP2_CPU0_PWR_CON\t\t0x240",
        "#define MT6797_SPM_MP2_CPU1_PWR_CON\t\t0x244",
        "#define MT6797_SPM_CPU_EXT_BUCK_ISO\t\t0x290",
        "#define MT6797_MCUCFG_MP2_SYNC_DCM\t\t0x274",
        "#define MT6797_CCI_STATUS\t\t\t0x000c",
        "#define MT6797_CCI_MP2_PORT_CONTROL\t\t0x6000",
        "reset_control_status(source->pwrap_reset)",
        "mt6797_state_read_once(source, &first)",
        "mt6797_state_read_once(source, &second)",
        "ret = -EBUSY",
        "ret = -EAGAIN",
        "*snapshot = second",
        "snapshot->valid = true",
        "EXPORT_SYMBOL_GPL(mt6797_a72_platform_state_snapshot)",
    ):
        require(token in driver, f"driver token: {token}")
    require(driver.count("mt6797_state_read_once(source, &first)") == 1,
            "single first sample")
    require(driver.count("mt6797_state_read_once(source, &second)") == 1,
            "single second sample")
    require(driver.index("*snapshot = (struct mt6797_a72_platform_state){}") <
            driver.index("dev_get_drvdata(dev)"),
            "destination cleared before lookup")
    for forbidden in (
        "writel(", "writeb(", "writew(", "regmap_write(",
        "reset_control_assert(", "reset_control_deassert(",
        "readl_poll", "regmap_read_poll", "while (", "for (",
        "psci", "cpu_up(", "cpu_down(", "A34",
    ):
        require(forbidden not in driver, f"forbidden driver effect: {forbidden}")

    for token in (
        "struct mt6797_a72_platform_state",
        "u32 cci_mp2_port_control;",
        "u32 cci_status_before;",
        "u32 cci_status_after;",
        "bool pwrap_reset_asserted;",
        "bool valid;",
        "return -EOPNOTSUPP;",
    ):
        require(token in header, f"header token: {token}")

    for token in (
        "a72_platform_state: a72-platform-state@10222000",
        '<0 0x10390000 0 0x10000>',
        'reg-names = "mcucfg", "cci";',
        'status = "disabled";',
    ):
        require(token in dtsi, f"DTS token: {token}")
    require("a72_power: a72-power@10222000" not in dtsi,
            "stale duplicate unit address removed")
    require("/delete-node/ &a72_power;" not in gemini,
            "stale Gemini deletion removed")

    for token in (
        "mediatek,mt6797-a72-platform-state",
        "minItems: 2",
        "maxItems: 2",
        "- const: mcucfg",
        "- const: cci",
        "const: pwrap",
        "additionalProperties: false",
    ):
        require(token in binding, f"binding token: {token}")

    print("source_validation=pass")
    print("toprgu_status=locked-read-only")
    print("platform_samples=2-no-loop")
    print("cci_mp2_port_offset=0x6000")
    print("cci_global_status_offset=0x000c")
    print("hardware_write=none")
    print("a34_caller=none")
    print("cpu_on=false")


if __name__ == "__main__":
    main()
