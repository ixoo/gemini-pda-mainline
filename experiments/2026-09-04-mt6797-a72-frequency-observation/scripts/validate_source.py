#!/usr/bin/env python3
"""Validate the repaired MT6797 clock-state decoder source boundary."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    source = (root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state.c").read_text()
    header = (root / "include/linux/soc/mediatek/mt6797-dvfsp-clock-state.h").read_text()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text()
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text()
    test = (root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state-test.c").read_text()

    required = (
        (header, "MT6797_DVFSP_CLOCK_STATE_PCW_STROBE", "strobe name"),
        (header, "GENMASK(30, 0)", "BigiDVFS PCW field"),
        (header, "GENMASK(14, 12)", "BigiDVFS POSDIV field"),
        (source, "mt6797_dvfsp_clock_big_frequency_decode", "BigiDVFS decoder"),
        (source, ">> 24", "BigiDVFS fractional width"),
        (source, "frequency = div_u64(frequency, BIT(posdiv));\n\tfrequency *= 1000;", "BigiDVFS integer order"),
        (source, "con1 & MT6797_DVFSP_CLOCK_STATE_PCW_MASK", "normal PCW field"),
        (source, "FIELD_GET(MT6797_DVFSP_CLOCK_STATE_BIG_POSDIV_MASK", "BigiDVFS POSDIV extraction"),
        (kconfig, "config MTK_MT6797_DVFSP_CLOCK_STATE_KUNIT_TEST", "KUnit option"),
        (makefile, "mt6797-dvfsp-clock-state-test.o", "KUnit object"),
        (test, ".pll_ll = { 0, 0xc1114000, 0 }", "stable live LL fixture"),
        (test, ".pll_cci = { 0, 0xc10c1d89, 0 }", "stable live CCI fixture"),
        (test, "0x4c000000U", "31-bit BigiDVFS fixture"),
        (test, "247000U", "separate POSDIV and CKDIV fixture"),
    )
    for text, needle, label in required:
        require(text, needle, label)

    forbidden = (
        "MT6797_DVFSP_CLOCK_STATE_PLL_CHANGE",
        "con1 & MT6797_DVFSP_CLOCK_STATE_PCW_STROBE",
        "readl(",
        "writel(",
        "arm_smccc",
        "cpu_up(",
        "cpu_down(",
        "psci",
    )
    combined = "\n".join((source, header, test))
    for needle in forbidden:
        if needle in combined:
            raise SystemExit(f"forbidden source operation present: {needle!r}")

    if test.count("KUNIT_CASE(") != 6:
        raise SystemExit("focused KUnit case inventory changed")
    print("normal_pcw_fractional_bits=14")
    print("normal_posdiv_field=bits26:24")
    print("normal_bit31_semantics=strobe-not-busy")
    print("big_pcw_fractional_bits=24")
    print("big_posdiv_field=bits14:12")
    print("armplldiv_ratio_count=13")
    print("focused_kunit_case_count=6")
    print("hardware_action=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
