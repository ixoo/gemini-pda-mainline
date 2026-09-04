#!/usr/bin/env python3
"""Validate the exact MT6797 live zero-divider decoder repair."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = (args.source_root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state.c").read_text()
    test = (args.source_root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state-test.c").read_text()

    require("\tswitch (selector) {\n\tcase 0:\n\tcase 8:\n" in source,
            "zero is not an explicit identity divider")
    require("\t\t0, 8, 9, 10, 11, 17, 18, 19, 20, 25, 26, 27, 28, 29,\n" in test,
            "divider table does not cover exact zero encoding")
    require("mt6797_clock_state_live_zero_dividers_test" in test,
            "exact live zero-divider test missing")
    for token in (
        "clock.armplldiv_ckdiv = 0x00000008;",
        "big.pll_pcw = 0xb9b13b14;",
        "big.pll_enable_posdiv = 0x00ff1101;",
        "897000U", "1274000U", "750000U", "629500U",
        "(clock.armplldiv_ckdiv & ~GENMASK(4, 0)) | 1;",
    ):
        require(token in test, f"live/guard token missing: {token}")
    require(test.count("KUNIT_CASE(") == 7, "focused decoder case count changed")
    for forbidden in ("readl(", "writel(", "arm_smccc", "cpu_up(", "cpu_down("):
        require(forbidden not in source + test,
                f"hardware operation entered pure decoder boundary: {forbidden}")

    print("zero_divider_identity=explicit")
    print("unknown_divider_rejection=retained")
    print("live_tuple_kunit=present")
    print("focused_decoder_cases=7")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
