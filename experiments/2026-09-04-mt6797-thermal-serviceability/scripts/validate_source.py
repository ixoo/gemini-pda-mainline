#!/usr/bin/env python3
"""Validate the exact MT6797 thermal serviceability DT source contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def require_once(text: str, needle: str, label: str) -> None:
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"{label}: expected once, found {count}: {needle!r}")


def node(text: str, label: str) -> str:
    match = re.search(rf"\b{re.escape(label)}:\s+[^{{]+\{{(.*?)\n\t\}};", text, re.S)
    if not match:
        raise SystemExit(f"node not found: {label}")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    mediatek = args.source_root / "arch/arm64/boot/dts/mediatek"
    dtsi = (mediatek / "mt6797.dtsi").read_text(encoding="utf-8")
    board = (mediatek / "mt6797-gemini-pda.dts").read_text(encoding="utf-8")
    variant = (mediatek / "mt6797-gemini-pda-thermal-serviceability.dts").read_text(encoding="utf-8")
    makefile = (mediatek / "Makefile").read_text(encoding="utf-8")

    thermal = node(dtsi, "thermal")
    auxadc = node(dtsi, "auxadc")
    pwrap = node(dtsi, "pwrap")
    require_once(thermal, "resets = <&infrasys MT6797_INFRA_THERM_CTRL_RST>;", "thermal")
    require_once(thermal, 'status = "disabled";', "thermal")
    require_once(thermal, "mediatek,auxadc = <&auxadc>;", "thermal")
    if "reset-names" in thermal:
        raise SystemExit("thermal: reset-names is forbidden for unnamed acquisition")
    require_once(auxadc, 'status = "disabled";', "AUXADC")
    require_once(pwrap, "resets = <&infrasys MT6797_INFRA_PMIC_WRAP_RST>;", "PWRAP")

    require_once(variant, '#include "mt6797-gemini-pda.dts"', "variant")
    require_once(variant, 'model = "Planet Computers Gemini PDA (thermal serviceability)";', "variant")
    require_once(variant, "thermal-zones {", "variant")
    require_once(variant, "soc-thermal {", "variant")
    require_once(variant, "polling-delay-passive = <0>;", "variant")
    require_once(variant, "polling-delay = <1000>;", "variant")
    require_once(variant, "thermal-sensors = <&thermal>;", "variant")
    require_once(variant, "&thermal {", "variant")
    require_once(variant, 'status = "okay";', "variant")
    for forbidden in (
        "&auxadc", "trips {", "cooling-maps {", "cooling-device",
        "operating-points", "opp-table", "cpufreq", "cpu8", "cpu9",
        "interrupts =", "watchdog", "suspend",
    ):
        if forbidden in variant:
            raise SystemExit(f"variant: forbidden adjacent policy: {forbidden!r}")
    if "thermal-zones" in board:
        raise SystemExit("base board gained experiment-only thermal zone policy")
    board_thermal_match = re.search(r"&thermal \{(.*?)\n\};", board, re.S)
    if not board_thermal_match:
        raise SystemExit("base board thermal calibration override is absent")
    board_thermal = board_thermal_match.group(1)
    require_once(
        board_thermal,
        "nvmem-cells = <&mt6797_thermal_calibration>;",
        "base board thermal calibration",
    )
    require_once(
        board_thermal,
        'nvmem-cell-names = "calibration-data";',
        "base board thermal calibration",
    )
    if "status =" in board_thermal:
        raise SystemExit("base board gained experiment-only thermal enablement")
    require_once(
        makefile,
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda-thermal-serviceability.dtb",
        "Makefile",
    )

    print("thermal_reset=MT6797_INFRA_THERM_CTRL_RST")
    print("thermal_soc_status=disabled")
    print("thermal_variant_status=okay")
    print("thermal_zone_count=1")
    print("trip_count=0")
    print("cooling_map_count=0")
    print("standalone_auxadc_status=disabled")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
