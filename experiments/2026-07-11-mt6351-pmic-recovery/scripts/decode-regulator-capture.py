#!/usr/bin/env python3
"""Decode the allowlisted MT6351 live regulator-register capture."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BUCKS = (
    ("vcore", 0x600, 0x7F),
    ("vgpu", 0x614, 0x7F),
    ("vmodem", 0x628, 0x7F),
    ("vmd1", 0x63C, 0x7F),
    ("vsram_md", 0x650, 0x7F),
    ("vs1", 0x664, 0x7F),
    ("vs2", 0x678, 0x7F),
    ("vpa", 0x68C, 0x3F),
    ("vsram_proc", 0x6A0, 0x7F),
)


def gray_to_binary(gray: int) -> int:
    value = gray
    while gray:
        gray >>= 1
        value ^= gray
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()

    registers = {
        int(match.group(1), 16): int(match.group(2), 16)
        for match in re.finditer(r"^0x([0-9a-fA-F]+)=0x([0-9a-fA-F]+)$", args.capture.read_text(), re.M)
    }

    print("# MT6351 live buck state decoded from explicitly allowlisted control-register reads.")
    print("# Voltage formula is 600000 uV + selector * 6250 uV; VPA's proven selector ceiling is 0x3f.")
    print("# CON7 is analog Gray-code readback. A mismatch below is a decoder/evidence failure.")
    print("name\tenable_request\teffective_enable\tvoltage_control\tdirect_selector\ton_selector\tsleep_selector\tactive_selector\tactive_microvolts\tgray_readback")

    for name, base, selector_mask in BUCKS:
        missing = [base + offset for offset in (0, 4, 8, 10, 12, 14) if base + offset not in registers]
        if missing:
            formatted = ", ".join(f"0x{address:04x}" for address in missing)
            raise SystemExit(f"{name}: capture is missing {formatted}")

        control = registers[base]
        enable = registers[base + 4]
        direct_selector = registers[base + 8] & selector_mask
        on_selector = registers[base + 10] & selector_mask
        sleep_selector = registers[base + 12] & selector_mask
        gray_readback = registers[base + 14] & 0x7F
        active_selector = gray_to_binary(gray_readback)
        hardware_controlled = bool(control & 0x2)
        expected_selector = on_selector if hardware_controlled else direct_selector
        if active_selector != expected_selector:
            raise SystemExit(
                f"{name}: decoded active selector {active_selector} does not match "
                f"{'ON' if hardware_controlled else 'direct'} selector {expected_selector}"
            )

        fields = (
            name,
            enable & 1,
            (enable >> 13) & 1,
            "hardware-on/sleep" if hardware_controlled else "software-direct",
            direct_selector,
            on_selector,
            sleep_selector,
            active_selector,
            600000 + active_selector * 6250,
            f"0x{gray_readback:02x}",
        )
        print("\t".join(str(field) for field in fields))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
