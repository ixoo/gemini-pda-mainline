#!/usr/bin/env python3
"""Decode a sanitized /sys/class/input capability capture.

This is intentionally a passive parser.  It does not open an input device or
generate events; it only compares the key bitmap of a named input device with
the key names in a source-derived matrix map.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFINE = re.compile(r"^#define\s+(KEY|BTN)_(\w+)\s+(0x[0-9a-fA-F]+|\d+)")
CAPABILITY = re.compile(
    r"input_set_capability\([^,]+,\s*EV_KEY,\s*(KEY|BTN)_(\w+)"
    r"(?:\s*/\*.*?\*/)?\s*\)"
)


def load_names(header: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    for line in header.read_text(encoding="utf-8").splitlines():
        match = DEFINE.match(line)
        if match:
            names[int(match.group(3), 0)] = f"{match.group(1)}_{match.group(2)}"
    return names


def parse_bitmap(capture: str, device: str) -> list[int]:
    prefix = f"{device}/key="
    for line in capture.splitlines():
        if line.startswith(prefix):
            words = line.removeprefix(prefix).split()
            result: list[int] = []
            # sysfs prints bitmap words most-significant first.  The final
            # word therefore contains codes 0..63, not the first word.
            for word_index, word in enumerate(reversed(words)):
                bits = int(word, 16)
                result.extend(
                    word_index * 64 + bit
                    for bit in range(64)
                    if bits & (1 << bit)
                )
            return result
    raise ValueError(f"missing {prefix} capability line")


def parse_keymap(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit():
            if fields[2] != "KEY_UNKNOWN":
                keys.add(fields[2])
    return keys


def parse_vendor_capabilities(path: Path) -> set[str]:
    capabilities: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = CAPABILITY.search(line)
        if match:
            capabilities.add(f"{match.group(1)}_{match.group(2)}")
    return capabilities


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--device", default="input2")
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--keymap", type=Path, required=True)
    parser.add_argument("--vendor-source", type=Path)
    args = parser.parse_args()

    capture = args.capture.read_text(encoding="utf-8")
    names = load_names(args.header)
    observed_codes = parse_bitmap(capture, args.device)
    observed = {names.get(code, f"CODE_{code}") for code in observed_codes}
    expected = parse_keymap(args.keymap)

    print(f"device={args.device}")
    print(f"observed_code_count={len(observed_codes)}")
    print("observed=" + ",".join(f"{code}:{names.get(code, f'CODE_{code}')}" for code in observed_codes))
    print(f"matrix_key_count={len(expected)}")
    print("matrix_keys=" + ",".join(sorted(expected)))
    print("observed_not_in_matrix=" + ",".join(sorted(observed - expected)))
    print("matrix_not_observed=" + ",".join(sorted(expected - observed)))
    print("decision=" + ("capability_bitmap_contains_non_matrix_key" if observed - expected else "capability_bitmap_matches_matrix"))
    if args.vendor_source:
        vendor = parse_vendor_capabilities(args.vendor_source)
        print(f"vendor_source_capability_count={len(vendor)}")
        print("vendor_source_capabilities=" + ",".join(sorted(vendor)))
        print("observed_not_in_vendor_source=" + ",".join(sorted(observed - vendor)))
        print("vendor_source_not_observed=" + ",".join(sorted(vendor - observed)))
        print("vendor_source_decision=" + ("runtime_capability_differs_from_source" if observed != vendor else "runtime_capability_matches_source"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
