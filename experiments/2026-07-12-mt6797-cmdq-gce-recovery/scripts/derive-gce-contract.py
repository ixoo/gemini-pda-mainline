#!/usr/bin/env python3
"""Derive MT6797 GCE subsystem/event constants from the pinned vendor tree."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DECL_EVENT_RE = re.compile(
    r"DECLARE_CMDQ_EVENT\(\s*([A-Z0-9_]+)\s*,\s*[^,]+,\s*([a-zA-Z0-9_]+)\s*\)"
)
DECL_SUBSYS_RE = re.compile(
    r"DECLARE_CMDQ_SUBSYS\(\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([a-zA-Z0-9_]+)\s*\)"
)
PROPERTY_RE = re.compile(r"^\s*([a-zA-Z0-9_,_-]+)\s*=\s*<([^;]+)>;", re.MULTILINE)
DEFINE_RE = re.compile(r"^\s*#define\s+([A-Z0-9_]+)\s+([^\s/]+)", re.MULTILINE)


def extract_node(text: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\{{", text)
    if not match:
        raise ValueError(f"node {name!r} not found")
    start = match.start()
    depth = 0
    for index in range(match.end() - 1, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError(f"unterminated node {name!r}")


def parse_cells(value: str) -> tuple[int, ...] | None:
    cells: list[int] = []
    for token in value.split():
        try:
            cells.append(int(token, 0))
        except ValueError:
            return None
    return tuple(cells)


def parse_defines(path: Path) -> dict[str, int]:
    defines: dict[str, int] = {}
    for name, value in DEFINE_RE.findall(path.read_text()):
        try:
            defines[name] = int(value.strip("()"), 0)
        except ValueError:
            continue
    return defines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_dts", type=Path)
    parser.add_argument("vendor_event_header", type=Path)
    parser.add_argument("vendor_subsys_header", type=Path)
    parser.add_argument("proposed_header", type=Path, nargs="?")
    parser.add_argument("--live-capture", type=Path)
    args = parser.parse_args()

    node = extract_node(args.vendor_dts.read_text(), "gce@10212000")
    properties = {
        name: cells
        for name, raw in PROPERTY_RE.findall(node)
        if (cells := parse_cells(raw)) is not None
    }

    subsys_properties = DECL_SUBSYS_RE.findall(args.vendor_subsys_header.read_text())
    subsystems: dict[str, int] = {}
    for property_name in subsys_properties:
        cells = properties.get(property_name)
        if not cells or len(cells) != 3:
            continue
        base, subsystem_id, mask = cells
        if mask != 0xFFFF0000:
            raise ValueError(f"unexpected mask for {property_name}: {mask:#x}")
        macro = "SUBSYS_NO_SUPPORT" if subsystem_id == 99 else f"SUBSYS_{base >> 16:04X}XXXX"
        previous = subsystems.setdefault(macro, subsystem_id)
        if previous != subsystem_id:
            raise ValueError(f"conflicting subsystem ID for {macro}")

    events: dict[str, int] = {}
    for macro, property_name in DECL_EVENT_RE.findall(args.vendor_event_header.read_text()):
        cells = properties.get(property_name)
        if not cells or len(cells) != 1:
            continue
        previous = events.setdefault(macro, cells[0])
        if previous != cells[0]:
            raise ValueError(f"conflicting event value for {macro}")

    expected = {**subsystems, **events}

    live_count = 0
    if args.live_capture:
        live_values = {
            name: tuple(int(raw[index : index + 8], 16) for index in range(0, len(raw), 8))
            for name, raw in re.findall(
                r"^([a-zA-Z0-9_,_-]+)=([0-9a-fA-F]+)$",
                args.live_capture.read_text(),
                re.MULTILINE,
            )
            if len(raw) % 8 == 0
        }
        for name, cells in properties.items():
            if name not in live_values:
                continue
            if live_values[name] != cells:
                print(
                    f"live mismatch {name}: source={cells} live={live_values[name]}",
                    file=sys.stderr,
                )
                return 1
            live_count += 1
    if args.proposed_header is None:
        print("/* GCE HW thread priority */")
        for name, value in (
            ("CMDQ_THR_PRIO_LOWEST", 0),
            ("CMDQ_THR_PRIO_NORMAL", 1),
            ("CMDQ_THR_PRIO_NORMAL_2", 2),
            ("CMDQ_THR_PRIO_MEDIUM", 3),
            ("CMDQ_THR_PRIO_MEDIUM_2", 4),
            ("CMDQ_THR_PRIO_HIGH", 5),
            ("CMDQ_THR_PRIO_HIGHER", 6),
            ("CMDQ_THR_PRIO_HIGHEST", 7),
        ):
            print(f"#define {name:<44} {value}")
        print("\n/* GCE subsystem IDs */")
        for name, value in sorted(subsystems.items(), key=lambda item: item[1]):
            print(f"#define {name:<44} {value}")
        print("\n/* GCE hardware events */")
        for name, value in sorted(events.items(), key=lambda item: (item[1], item[0])):
            print(f"#define {name:<44} {value}")
        print(
            f"\n/* derived subsystems={len(subsystems)} events={len(events)}"
            f" live_properties={live_count} */"
        )
        return 0

    actual = parse_defines(args.proposed_header)
    errors = 0
    for name, value in expected.items():
        if name not in actual:
            print(f"missing {name}={value}", file=sys.stderr)
            errors += 1
        elif actual[name] != value:
            print(f"mismatch {name}: expected={value} actual={actual[name]}", file=sys.stderr)
            errors += 1
    extra = sorted(
        name
        for name in actual
        if (name.startswith("SUBSYS_") or name.startswith("CMDQ_EVENT_")) and name not in expected
    )
    for name in extra:
        print(f"unexpected {name}={actual[name]}", file=sys.stderr)
        errors += 1
    if errors:
        return 1
    print(
        f"PASS subsystems={len(subsystems)} events={len(events)}"
        f" live_properties={live_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
