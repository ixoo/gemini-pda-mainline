#!/usr/bin/env python3
"""Compare the downstream MT6797 M4U port table with a DT binding header."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VENDOR_PORT = re.compile(
    r'M4U0_PORT_INIT\("(?P<name>[A-Z0-9_]+)",\s*'
    r'(?P<slave>\d+),\s*(?P<larb>\d+),\s*(?P<port>\d+)\)'
)
HEADER_PORT = re.compile(
    r"^#define\s+M4U_PORT_(?P<name>[A-Z0-9_]+)\s+"
    r"MTK_M4U_ID\(M4U_LARB(?P<larb>\d+)_ID,\s*(?P<port>\d+)\)$",
    re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor", type=Path, help="downstream m4u_platform.h")
    parser.add_argument("header", type=Path, help="mainline mt6797-larb-port.h")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vendor_text = args.vendor.read_text(encoding="utf-8")
    header_text = args.header.read_text(encoding="utf-8")

    vendor = {
        match["name"]: (int(match["larb"]), int(match["port"]), int(match["slave"]))
        for match in VENDOR_PORT.finditer(vendor_text)
        if match["name"] != "UNKNOWN"
    }
    header = {
        match["name"]: (int(match["larb"]), int(match["port"]))
        for match in HEADER_PORT.finditer(header_text)
    }

    errors: list[str] = []
    if len(vendor) != 71:
        errors.append(f"vendor port count is {len(vendor)}, expected 71")
    if len(header) != 71:
        errors.append(f"header port count is {len(header)}, expected 71")

    for name in sorted(vendor.keys() - header.keys()):
        errors.append(f"missing header port: {name}")
    for name in sorted(header.keys() - vendor.keys()):
        errors.append(f"extra header port: {name}")
    for name in sorted(vendor.keys() & header.keys()):
        expected = vendor[name][:2]
        if header[name] != expected:
            errors.append(f"{name}: header={header[name]} vendor={expected}")

    ids = [(larb << 5) | port for larb, port in header.values()]
    if len(ids) != len(set(ids)):
        errors.append("header contains duplicate compact DT port IDs")
    for name, (larb, port) in header.items():
        if not 0 <= larb <= 6 or not 0 <= port <= 31:
            errors.append(f"{name}: out-of-range larb/port ({larb}, {port})")

    if errors:
        print("FAIL")
        print("\n".join(errors))
        return 1

    slave0 = sum(1 for _, _, slave in vendor.values() if slave == 0)
    slave1 = sum(1 for _, _, slave in vendor.values() if slave == 1)
    print(f"PASS ports={len(header)} slave0={slave0} slave1={slave1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
