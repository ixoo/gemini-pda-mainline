#!/usr/bin/env python3
"""Apply deterministic MT6797 A72 platform-state source changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: Path, source: Path) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def apply_watchdog(root: Path) -> None:
    driver = root / "drivers/watchdog/mtk_wdt.c"

    replace_once(
        driver,
        dedent("""\
        static int toprgu_reset_assert(struct reset_controller_dev *rcdev,
        \t\t\t       unsigned long id)
        {
        \treturn toprgu_reset_update(rcdev, id, true);
        }
        """),
        dedent("""\
        static int toprgu_reset_status(struct reset_controller_dev *rcdev,
        \t\t\t       unsigned long id)
        {
        \tstruct mtk_wdt_dev *data =
        \t\tcontainer_of(rcdev, struct mtk_wdt_dev, rcdev);
        \tunsigned long flags;
        \tu32 value;

        \tspin_lock_irqsave(&data->lock, flags);
        \tvalue = readl(data->wdt_base + WDT_SWSYSRST);
        \tspin_unlock_irqrestore(&data->lock, flags);

        \treturn !!(value & BIT(id));
        }

        static int toprgu_reset_assert(struct reset_controller_dev *rcdev,
        \t\t\t       unsigned long id)
        {
        \treturn toprgu_reset_update(rcdev, id, true);
        }
        """),
    )
    replace_once(
        driver,
        dedent("""\
        static const struct reset_control_ops toprgu_reset_ops = {
        \t.assert = toprgu_reset_assert,
        \t.deassert = toprgu_reset_deassert,
        \t.reset = toprgu_reset,
        };
        """),
        dedent("""\
        static const struct reset_control_ops toprgu_reset_ops = {
        \t.assert = toprgu_reset_assert,
        \t.deassert = toprgu_reset_deassert,
        \t.reset = toprgu_reset,
        \t.status = toprgu_reset_status,
        };
        """),
    )


def apply_platform(root: Path, experiment: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    makefile = root / "drivers/soc/mediatek/Makefile"
    dtsi = root / "arch/arm64/boot/dts/mediatek/mt6797.dtsi"
    gemini = root / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts"

    replace_once(
        kconfig,
        "config MTK_MT6797_DVFSP_HANDOFF\n",
        dedent("""\
        config MTK_MT6797_A72_PLATFORM_STATE
        \tbool "MediaTek MT6797 Cortex-A72 platform-state source"
        \tdepends on ARM64 && ARCH_MEDIATEK && OF
        \tdepends on RESET_CONTROLLER
        \tselect MFD_SYSCON
        \thelp
        \t  Build the default-off read-only source for the MT6797 Cortex-A72
        \t  SPM, TOPRGU PWRAP reset, MP2 DCM, and MP2 CCI state. It publishes
        \t  only a typed snapshot and performs no register write or polling.

        \t  A later transition owner must serialize snapshots against PSCI.
        \t  This source does not authorize CPU_ON or lifecycle publication.

        config MTK_MT6797_DVFSP_HANDOFF
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_POWER) += mt6797-a72-power.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_POWER) += mt6797-a72-power.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE) += mt6797-a72-platform-state.o\n",
    )
    replace_once(
        dtsi,
        dedent("""\
        \ta72_power: a72-power@10222000 {
        \t\tcompatible = "mediatek,mt6797-a72-power";
        \t\treg = <0 0x10222000 0 0x1000>;
        \t\tmediatek,spm = <&scpsys>;
        \t\tcpus = <&cpu8>, <&cpu9>;
        \t\tresets = <&watchdog MT6797_TOPRGU_PWRAP_SPI_CTL_RST>;
        \t\treset-names = "pwrap";
        \t\tstatus = "disabled";
        \t};
        """),
        dedent("""\
        \ta72_platform_state: a72-platform-state@10222000 {
        \t\tcompatible = "mediatek,mt6797-a72-platform-state";
        \t\treg = <0 0x10222000 0 0x1000>,
        \t\t      <0 0x10390000 0 0x10000>;
        \t\treg-names = "mcucfg", "cci";
        \t\tmediatek,spm = <&scpsys>;
        \t\tresets = <&watchdog MT6797_TOPRGU_PWRAP_SPI_CTL_RST>;
        \t\treset-names = "pwrap";
        \t\tstatus = "disabled";
        \t};
        """),
    )
    replace_once(gemini, "\n/delete-node/ &a72_power;\n", "\n")

    write_new(
        root / "drivers/soc/mediatek/mt6797-a72-platform-state.c",
        experiment / "source/mt6797-a72-platform-state.c",
    )
    write_new(
        root / "include/linux/soc/mediatek/mt6797-a72-platform-state.h",
        experiment / "source/mt6797-a72-platform-state.h",
    )
    write_new(
        root / (
            "Documentation/devicetree/bindings/soc/mediatek/"
            "mediatek,mt6797-a72-platform-state.yaml"
        ),
        experiment / "source/mediatek,mt6797-a72-platform-state.yaml",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--step", choices=("watchdog", "platform"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    experiment = Path(__file__).resolve().parents[1]

    if args.step == "watchdog":
        apply_watchdog(root)
    else:
        apply_platform(root, experiment)


if __name__ == "__main__":
    main()
