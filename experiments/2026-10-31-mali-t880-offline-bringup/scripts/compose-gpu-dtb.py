#!/usr/bin/env python3
"""Compose an offline GPU bring-up DTB from a base mainline DTB.

This only mutates a copy of the DTB. It enables mfgsys, i2c7, the RT5735
regulator and the GPU, adds the bus clock and a fixed 1.0 V regulator range,
sets the MFG 52 MHz mux parent and the 520 MHz core rate, and leaves
OPP/devfreq/reset/IOMMU policy out. The result is for offline validation and a
later reviewed runtime candidate, not for deployment.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(f"{' '.join(cmd)}: {result.stderr.strip()}")


def get_int(dtb: str, path: str, prop: str) -> int:
    result = subprocess.run(
        ["fdtget", "-t", "x", dtb, path, prop],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise SystemExit(f"missing {path}:{prop}: {result.stderr.strip()}")
    return int(result.stdout.split()[0], 16)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--gpu-path", default="/gpu@13040000")
    parser.add_argument("--mfgsys-path", default="/syscon@13000000")
    parser.add_argument("--infrasys-path", default="/syscon@10001000")
    parser.add_argument("--topckgen-path", default="/topckgen@10000000")
    parser.add_argument("--scpsys-path", default="/power-controller@10006000")
    parser.add_argument("--watchdog-path", default="/watchdog@10007000")
    parser.add_argument("--i2c7-path", default="/i2c@11010000")
    parser.add_argument("--regulator-path", default="/i2c@11010000/regulator@1c")
    args = parser.parse_args()

    shutil.copyfile(args.input, args.output)
    dtb = args.output

    mfgsys = get_int(dtb, args.mfgsys_path, "phandle")
    infrasys = get_int(dtb, args.infrasys_path, "phandle")
    topckgen = get_int(dtb, args.topckgen_path, "phandle")
    watchdog = get_int(dtb, args.watchdog_path, "phandle")
    regulator = get_int(dtb, args.regulator_path, "phandle")

    run(["fdtput", "-t", "s", dtb, args.mfgsys_path, "status", "okay"])
    run(["fdtput", "-t", "s", dtb, args.i2c7_path, "status", "okay"])
    run(["fdtput", "-t", "s", dtb, args.regulator_path, "status", "okay"])
    run(["fdtput", "-t", "u", dtb, args.regulator_path, "regulator-min-microvolt", "1000000"])
    run(["fdtput", "-t", "u", dtb, args.regulator_path, "regulator-max-microvolt", "1000000"])
    run(["fdtput", "-t", "u", dtb, args.regulator_path, "regulator-enable-ramp-delay", "350"])
    run(["fdtput", "-t", "u", dtb, args.regulator_path, "regulator-settling-time-up-us", "350"])
    run(["fdtput", "-t", "u", dtb, args.regulator_path, "regulator-ramp-delay", "4000"])

    run(["fdtput", "-t", "u", dtb, args.gpu_path, "clocks", str(mfgsys), "1", str(infrasys), "83"])
    run(["fdtput", "-t", "s", dtb, args.gpu_path, "clock-names", "core", "bus"])
    run(["fdtput", "-t", "u", dtb, args.gpu_path, "mali-supply", str(regulator)])
    # MT6797_TOPRGU_MFG_SW_RST = 2. The provider is the MT6797 watchdog.
    run(["fdtput", "-t", "u", dtb, args.gpu_path, "resets", str(watchdog), "2"])
    # CLK_MFG_BG3D = 1. Panfrost does not set a rate without an OPP table.
    run(["fdtput", "-t", "u", dtb, args.gpu_path, "assigned-clocks", str(mfgsys), "1"])
    run(["fdtput", "-t", "u", dtb, args.gpu_path, "assigned-clock-rates", "520000000"])
    # The vendor selects univpll2_d8 (52 MHz) for the SCPSYS MFG preclock.
    # CLK_TOP_MUX_MFG_52M = 34, CLK_TOP_UNIVPLL2_D8 = 64.
    run(["fdtput", "-t", "u", dtb, args.scpsys_path, "assigned-clocks", str(topckgen), "34"])
    run(["fdtput", "-t", "u", dtb, args.scpsys_path, "assigned-clock-parents", str(topckgen), "64"])
    run(["fdtput", "-t", "s", dtb, args.gpu_path, "status", "okay"])

    print(f"composed {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
