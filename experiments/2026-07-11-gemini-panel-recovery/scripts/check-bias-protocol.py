#!/usr/bin/env python3
"""Compare Gemini's LCD-bias shim with Linux's TPS65132 protocol."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


VENDOR_PATH = "drivers/misc/mediatek/gpio/lp3101.c"


def require(text: str, needle: str, source: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL: {source}: missing {needle!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor-git", type=Path, required=True)
    parser.add_argument("--linux", type=Path, required=True)
    args = parser.parse_args()

    result = subprocess.run(
        ["git", "-C", str(args.vendor_git), "show", f"HEAD:{VENDOR_PATH}"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    vendor = result.stdout
    for needle in (
        "#define LP_ADDR 0x3E",
        "cmd = 0x00;",
        "cmd = 0x01;",
        "data = 0x0f;",
    ):
        require(vendor, needle, VENDOR_PATH)

    driver_path = args.linux / "drivers/regulator/tps65132-regulator.c"
    driver = driver_path.read_text(errors="strict")
    for needle in (
        "#define TPS65132_REG_VPOS\t\t0x00",
        "#define TPS65132_REG_VNEG\t\t0x01",
        "#define TPS65132_VOUT_MASK\t\t0x1F",
        "#define TPS65132_VOUT_VMIN\t\t4000000",
        "#define TPS65132_VOUT_STEP\t\t100000",
        'devm_fwnode_gpiod_get(tps->dev, of_fwnode_handle(np),',
    ):
        require(driver, needle, str(driver_path))

    selector_uv = 4_000_000 + 0x0F * 100_000
    print(
        "PASS candidate=tps65132 protocol=addr-3e-regs-00-01 "
        f"selector-0f={selector_uv // 1000}mV enables=per-output "
        "identity=unproven"
    )


if __name__ == "__main__":
    main()
