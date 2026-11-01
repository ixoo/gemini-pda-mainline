#!/usr/bin/env python3
"""Validate the MT6797 GPU build configuration and DT contract.

Usage:
    ./validate-gpu-config.py --config .config --dtb board.dtb \
        [--expect disabled|enabled] [--gpu-path /soc/gpu@13040000]

The base patch keeps the GPU disabled. A bring-up composition may enable it;
--expect enabled requires the extra bus clock and okay status, while
--expect disabled requires status = "disabled".
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def fdtget(dtb: str, path: str, prop: str, kind: str) -> list[str]:
    result = subprocess.run(
        ["fdtget", "-t", kind, dtb, path, prop],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError(f"{path}:{prop} missing or unreadable")
    return result.stdout.split()


def config_value(path: str, symbol: str) -> str:
    want = f"CONFIG_{symbol}="
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith(want):
                return line[len(want):]
            if line == f"# CONFIG_{symbol} is not set":
                return "n"
    return "n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dtb", required=True)
    parser.add_argument("--expect", choices=("disabled", "enabled"), default="disabled")
    parser.add_argument("--gpu-path", default="/gpu@13040000")
    parser.add_argument("--mfgsys-path", default="/syscon@13000000")
    parser.add_argument("--infrasys-path", default="/syscon@10001000")
    parser.add_argument("--topckgen-path", default="/topckgen@10000000")
    parser.add_argument("--scpsys-path", default="/power-controller@10006000")
    parser.add_argument("--watchdog-path", default="/watchdog@10007000")
    parser.add_argument("--regulator-path", default="/i2c@11010000/regulator@1c")
    args = parser.parse_args()

    errors: list[str] = []

    required = {
        "DRM": ("y", "m"),
        "DRM_PANFROST": ("y", "m"),
        "PM_DEVFREQ": ("y",),
        "PM_OPP": ("y",),
        "MTK_SCPSYS": ("y",),
        "COMMON_CLK_MT6797_MFGSYS": ("y",),
        "REGULATOR_RT5735": ("y", "m"),
        "I2C_MT65XX": ("y", "m"),
    }
    for symbol, accepted in required.items():
        value = config_value(args.config, symbol)
        if value not in accepted:
            errors.append(f"config {symbol}={value}; expected {'/'.join(accepted)}")

    try:
        compat = " ".join(fdtget(args.dtb, args.gpu_path, "compatible", "s"))
        if "mediatek,mt6797-mali" not in compat or "arm,mali-t880" not in compat:
            errors.append(f"unexpected GPU compatible: {compat}")

        reg = [int(v, 16) for v in fdtget(args.dtb, args.gpu_path, "reg", "x")]
        if reg[:2] != [0, 0x13040000] or reg[2:] != [0, 0x4000]:
            errors.append(f"unexpected GPU reg: {[hex(v) for v in reg]}")

        irq = [int(v, 16) for v in fdtget(args.dtb, args.gpu_path, "interrupts", "x")]
        if irq != [0, 0x108, 0x8, 0, 0x107, 0x8, 0, 0x106, 0x8]:
            errors.append(f"unexpected GPU interrupts: {[hex(v) for v in irq]}")

        names = fdtget(args.dtb, args.gpu_path, "interrupt-names", "s")
        if names != ["job", "mmu", "gpu"]:
            errors.append(f"unexpected interrupt-names: {names}")

        clocks = [int(v, 16) for v in fdtget(args.dtb, args.gpu_path, "clocks", "x")]
        clock_names = fdtget(args.dtb, args.gpu_path, "clock-names", "s")
        if clock_names[:1] != ["core"]:
            errors.append(f"missing core clock name: {clock_names}")
        if len(clocks) < 2:
            errors.append("missing core clock phandle/id")
        if args.expect == "enabled":
            if clock_names != ["core", "bus"]:
                errors.append(f"enabled GPU needs core,bus clocks: {clock_names}")
            if len(clocks) != 4:
                errors.append("enabled GPU needs exactly two clocks")
            else:
                infrasys = int(fdtget(args.dtb, args.infrasys_path, "phandle", "x")[0], 16)
                if clocks[2:] != [infrasys, 83]:
                    errors.append(f"bus clock is {[hex(v) for v in clocks[2:]]}; expected infra_mfg_vcg (83)")

            mfgsys = int(fdtget(args.dtb, args.mfgsys_path, "phandle", "x")[0], 16)
            assigned = [int(v, 16) for v in fdtget(args.dtb, args.gpu_path, "assigned-clocks", "x")]
            if assigned != [mfgsys, 1]:
                errors.append(f"GPU assigned-clocks {[hex(v) for v in assigned]}; expected core clock")
            rates = [int(v, 16) for v in fdtget(args.dtb, args.gpu_path, "assigned-clock-rates", "x")]
            if rates != [520000000]:
                errors.append(f"GPU assigned-clock-rates {rates}; expected [520000000]")

            topckgen = int(fdtget(args.dtb, args.topckgen_path, "phandle", "x")[0], 16)
            scpsys_clocks = [int(v, 16) for v in fdtget(args.dtb, args.scpsys_path, "assigned-clocks", "x")]
            if scpsys_clocks != [topckgen, 34]:
                errors.append(f"SCPSYS assigned-clocks {[hex(v) for v in scpsys_clocks]}; expected mfg_52m_sel")
            parents = [int(v, 16) for v in fdtget(args.dtb, args.scpsys_path, "assigned-clock-parents", "x")]
            if parents != [topckgen, 64]:
                errors.append(f"SCPSYS assigned-clock-parents {[hex(v) for v in parents]}; expected univpll2_d8")

            for prop, want in (
                ("regulator-min-microvolt", 1000000),
                ("regulator-max-microvolt", 1000000),
                ("regulator-enable-ramp-delay", 350),
                ("regulator-settling-time-up-us", 350),
                ("regulator-ramp-delay", 4000),
            ):
                value = int(fdtget(args.dtb, args.regulator_path, prop, "x")[0], 16)
                if value != want:
                    errors.append(f"{prop}={value}; expected {want}")

            regulator = int(fdtget(args.dtb, args.regulator_path, "phandle", "x")[0], 16)
            supply = int(fdtget(args.dtb, args.gpu_path, "mali-supply", "x")[0], 16)
            if supply != regulator:
                errors.append("mali-supply does not reference the RT5735 node")

            watchdog = int(fdtget(args.dtb, args.watchdog_path, "phandle", "x")[0], 16)
            cells = int(fdtget(args.dtb, args.watchdog_path, "#reset-cells", "x")[0], 16)
            if cells != 1:
                errors.append(f"watchdog #reset-cells={cells}; expected 1")
            resets = [int(v, 16) for v in fdtget(args.dtb, args.gpu_path, "resets", "x")]
            if resets != [watchdog, 2]:
                errors.append(f"GPU resets {[hex(v) for v in resets]}; expected TOPRGU MFG reset 2")

        domains = [int(v, 16) for v in fdtget(args.dtb, args.gpu_path, "power-domains", "x")]
        if len(domains) != 8:
            errors.append(f"expected four core power-domain phandle/id pairs, got {len(domains)} cells")
        domain_names = fdtget(args.dtb, args.gpu_path, "power-domain-names", "s")
        if domain_names != ["core0", "core1", "core2", "core3"]:
            errors.append(f"unexpected power-domain-names: {domain_names}")

        status = " ".join(fdtget(args.dtb, args.gpu_path, "status", "s"))
        if args.expect == "disabled" and status != "disabled":
            errors.append(f"base GPU status is {status!r}, expected disabled")
        if args.expect == "enabled" and status != "okay":
            errors.append(f"composed GPU status is {status!r}, expected okay")

        try:
            fdtget(args.dtb, args.gpu_path, "iommus", "x")
            errors.append("GPU must not have an iommus property")
        except ValueError:
            pass
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: GPU config and {args.expect} DT contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
