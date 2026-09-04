#!/usr/bin/env python3
"""Validate the exact MT6797 infracfg reset repair source contract."""

from __future__ import annotations

import argparse
from pathlib import Path


def require_once(text: str, needle: str, label: str) -> None:
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"{label}: expected once, found {count}: {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"{label}: forbidden text remains: {needle!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root
    clock = root / "drivers/clk/mediatek"

    binding = (root / "include/dt-bindings/reset/mt6797-resets.h").read_text()
    driver = (clock / "clk-mt6797.c").read_text()
    descriptor = (clock / "clk-mt6797-reset.h").read_text()
    reset_c = (clock / "reset.c").read_text()
    reset_h = (clock / "reset.h").read_text()
    kconfig = (clock / "Kconfig").read_text()
    makefile = (clock / "Makefile").read_text()
    test = (clock / "clk-mt6797-reset-test.c").read_text()

    require_once(binding, "#define MT6797_INFRA_THERM_CTRL_RST\t0", "binding")
    require_once(binding, "#define MT6797_INFRA_PMIC_WRAP_RST\t1", "binding")
    for old in (
        "MT6797_INFRA_USB_TOP_RST",
        "MT6797_INFRA_SSUSB_TOP_RST",
        "MT6797_INFRA_SPM_RST",
        "MT6797_INFRA_SCP_RST",
    ):
        reject(binding, old, "binding")

    require_once(driver, '#include "clk-mt6797-reset.h"', "driver")
    reject(driver, ".version = MTK_RST_SIMPLE", "driver")
    reject(driver, "\t0x124,\n\t0x128,", "driver")

    for needle in (
        "INFRA_RST0_SET_OFFSET",
        "INFRA_RST2_SET_OFFSET",
        "[MT6797_INFRA_THERM_CTRL_RST] = 0 * RST_NR_PER_BANK",
        "[MT6797_INFRA_PMIC_WRAP_RST] = 1 * RST_NR_PER_BANK",
        ".version = MTK_RST_SET_CLR",
        ".rst_idx_map = infra_rst_idx_map",
        ".rst_idx_map_nr = ARRAY_SIZE(infra_rst_idx_map)",
    ):
        require_once(descriptor, needle, "descriptor")
    reject(descriptor, "INFRA_RST1_SET_OFFSET", "descriptor")

    for needle in (
        "mtk_reset_xlate_index(const struct mtk_clk_rst_desc *desc",
        "if (!desc->rst_idx_map || index >= desc->rst_idx_map_nr)",
        "mtk_reset_set_clr_reg(const struct mtk_clk_rst_desc *desc",
        "if (bank >= desc->rst_bank_nr)",
        "*reg = desc->rst_bank_ofs[bank] + (deassert ? 0x4 : 0);",
        "*mask = BIT(id % RST_NR_PER_BANK);",
    ):
        require_once(reset_h, needle, "reset header")
    require_once(
        reset_c,
        "ret = mtk_reset_set_clr_reg(data->desc, id, deassert, &reg, &mask);",
        "reset core",
    )
    require_once(
        reset_c,
        "return mtk_reset_xlate_index(data->desc, reset_spec->args[0]);",
        "reset core",
    )
    reject(reset_c, "unsigned int deassert_ofs = deassert ? 0x4 : 0;", "reset core")

    require_once(kconfig, "config COMMON_CLK_MT6797_RESET_KUNIT_TEST", "Kconfig")
    require_once(
        makefile,
        "obj-$(CONFIG_COMMON_CLK_MT6797_RESET_KUNIT_TEST) += clk-mt6797-reset-test.o",
        "Makefile",
    )
    require_once(test, '.name = "mt6797-infracfg-reset-translation"', "KUnit")
    if test.count("KUNIT_CASE(") != 6:
        raise SystemExit("KUnit: expected exactly six cases")
    for needle in ("0x120U", "0x124U", "0x140U", "0x144U", "-EINVAL"):
        if needle not in test:
            raise SystemExit(f"KUnit: missing transaction assertion {needle}")

    print("production_translation=2")
    print("quarantined_rst1=yes")
    print("kunit_cases=6")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
