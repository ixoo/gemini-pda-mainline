#!/usr/bin/env python3
"""Validate the source-derived Gemini matrix map against the DT patch.

This compares the sanitized keymap table with the disabled mainline DT
candidate. KEY_UNKNOWN positions are intentionally treated as omitted
KEY_RESERVED slots; see audit-keyboard-keycode-semantics.sh for Linux input
core behavior. It does not read a device, compile a tree, or mutate hardware.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


PATCH_ENTRY = re.compile(
    r"MATRIX_KEY\(\s*(\d+)\s*,\s*(\d+)\s*,\s*([A-Z0-9_]+)\s*\)"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_table(path: Path) -> dict[tuple[int, int], str]:
    entries: dict[tuple[int, int], str] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line or line.startswith("#") or line == "row col key":
            continue
        fields = line.split()
        if len(fields) != 3 or not fields[0].isdigit() or not fields[1].isdigit():
            raise ValueError(f"{path}:{line_number}: malformed keymap row")
        coordinate = (int(fields[0]), int(fields[1]))
        if coordinate in entries:
            raise ValueError(f"{path}:{line_number}: duplicate coordinate {coordinate}")
        entries[coordinate] = fields[2]
    return entries


def read_patch(path: Path) -> dict[tuple[int, int], str]:
    entries: dict[tuple[int, int], str] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        match = PATCH_ENTRY.search(line)
        if not match:
            continue
        coordinate = (int(match.group(1)), int(match.group(2)))
        if coordinate in entries:
            raise ValueError(f"{path}:{line_number}: duplicate coordinate {coordinate}")
        entries[coordinate] = match.group(3)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--keymap", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    patch = args.patch or repo / "patches/v7.1.3/0054-arm64-dts-mediatek-add-disabled-Gemini-AW9523-keyboard-candidate.patch"
    keymap = args.keymap or repo / "experiments/2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt"

    table = read_table(keymap)
    candidate = read_patch(patch)
    expected_coordinates = {(row, col) for row in range(8) for col in range(7)}
    if set(table) != expected_coordinates:
        missing = sorted(expected_coordinates - set(table))
        extra = sorted(set(table) - expected_coordinates)
        raise ValueError(f"keymap coordinates differ: missing={missing} extra={extra}")

    assigned = {coordinate: key for coordinate, key in table.items() if key != "KEY_UNKNOWN"}
    unknown = {coordinate for coordinate, key in table.items() if key == "KEY_UNKNOWN"}
    if candidate != assigned:
        missing = sorted(set(assigned) - set(candidate))
        extra = sorted(set(candidate) - set(assigned))
        mismatched = sorted(
            coordinate
            for coordinate in set(assigned) & set(candidate)
            if assigned[coordinate] != candidate[coordinate]
        )
        raise ValueError(
            f"DT map differs: missing={missing} extra={extra} mismatched={mismatched}"
        )
    if unknown & set(candidate):
        raise ValueError(f"DT map assigns KEY_UNKNOWN positions: {sorted(unknown & set(candidate))}")

    print("validation=gemini-keyboard-keymap-consistency")
    print(f"keymap={keymap}")
    print(f"keymap_sha256={sha256(keymap)}")
    print(f"patch={patch}")
    print(f"patch_sha256={sha256(patch)}")
    print("matrix_rows=8")
    print("matrix_columns=7")
    print(f"matrix_positions={len(table)}")
    print(f"assigned_positions={len(assigned)}")
    print(f"unknown_positions={len(unknown)}")
    print("status=pass")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
