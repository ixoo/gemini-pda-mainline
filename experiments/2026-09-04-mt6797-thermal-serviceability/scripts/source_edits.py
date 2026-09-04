#!/usr/bin/env python3
"""Apply deterministic MT6797 thermal serviceability DT edits."""

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


def add_reset(root: Path) -> None:
    dtsi = root / "arch/arm64/boot/dts/mediatek/mt6797.dtsi"
    replace_once(
        dtsi,
        '\t\tclock-names = "therm", "auxadc";\n'
        "\t\tmediatek,auxadc = <&auxadc>;\n",
        '\t\tclock-names = "therm", "auxadc";\n'
        "\t\tresets = <&infrasys MT6797_INFRA_THERM_CTRL_RST>;\n"
        "\t\tmediatek,auxadc = <&auxadc>;\n",
    )


def serviceability_dts() -> str:
    return dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /*
     * Copyright (c) 2026 Julien Etienne
     */

    #include "mt6797-gemini-pda.dts"

    / {
    \tmodel = "Planet Computers Gemini PDA (thermal serviceability)";

    \tthermal-zones {
    \t\tsoc-thermal {
    \t\t\tpolling-delay-passive = <0>;
    \t\t\tpolling-delay = <1000>;
    \t\t\tthermal-sensors = <&thermal>;
    \t\t};
    \t};
    };

    &thermal {
    \tstatus = "okay";
    };
    """)


def add_serviceability_variant(root: Path) -> None:
    mediatek = root / "arch/arm64/boot/dts/mediatek"
    variant = mediatek / "mt6797-gemini-pda-thermal-serviceability.dts"
    if variant.exists():
        raise SystemExit(f"refusing to overwrite existing path: {variant}")
    variant.write_text(serviceability_dts(), encoding="utf-8")
    replace_once(
        mediatek / "Makefile",
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda.dtb\n",
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda.dtb\n"
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda-thermal-serviceability.dtb\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("reset", "variant"), required=True)
    args = parser.parse_args()
    if args.phase == "reset":
        add_reset(args.source_root)
    else:
        add_serviceability_variant(args.source_root)


if __name__ == "__main__":
    main()
