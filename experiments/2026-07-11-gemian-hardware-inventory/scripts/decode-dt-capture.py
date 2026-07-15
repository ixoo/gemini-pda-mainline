#!/usr/bin/env python3

"""Decode phandle-based references in a sanitized Gemini DT capture."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


SECTION = "===== selected device tree property values ====="
CELL_COUNT_PROPERTY = {
    "clocks": "#clock-cells",
    "resets": "#reset-cells",
    "power-domains": "#power-domain-cells",
    "iommus": "#iommu-cells",
    "phys": "#phy-cells",
    "dmas": "#dma-cells",
    "interrupts-extended": "#interrupt-cells",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve phandles in collect.sh device-tree output."
    )
    parser.add_argument("capture", type=pathlib.Path)
    parser.add_argument(
        "--match",
        default=".",
        help="regular expression selecting node paths (default: all)",
    )
    return parser.parse_args()


def cells(value: str) -> list[int]:
    if value == "<present>" or not value or len(value) % 8:
        return []
    try:
        return [int(value[offset : offset + 8], 16) for offset in range(0, len(value), 8)]
    except ValueError:
        return []


def load(path: pathlib.Path) -> dict[str, dict[str, str]]:
    nodes: dict[str, dict[str, str]] = {}
    active = False
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw_line == SECTION:
            active = True
            continue
        if active and raw_line.startswith("====="):
            break
        if not active or "|" not in raw_line:
            continue
        node, assignment = raw_line.split("|", 1)
        if "=" not in assignment:
            continue
        name, value = assignment.split("=", 1)
        nodes.setdefault(node, {})[name] = value.strip()
    return nodes


def phandle_map(nodes: dict[str, dict[str, str]]) -> dict[int, str]:
    result: dict[int, str] = {}
    for node, properties in nodes.items():
        value = cells(properties.get("phandle", properties.get("linux,phandle", "")))
        if len(value) == 1:
            result[value[0]] = node
    return result


def argument_count(
    property_name: str,
    provider: str,
    nodes: dict[str, dict[str, str]],
) -> int | None:
    if (
        property_name == "interrupt-parent"
        or property_name.endswith("-supply")
        or property_name.startswith("pinctrl-")
        or property_name == "pinctl"
        or property_name.startswith("pinctl_")
        or property_name == "register_setting"
    ):
        return 0
    if (
        property_name.endswith("-gpios")
        or property_name.endswith("-gpio")
        or property_name.endswith("_gpio")
    ):
        count_name = "#gpio-cells"
    else:
        count_name = CELL_COUNT_PROPERTY.get(property_name)
    if count_name is None:
        return None
    count = cells(nodes.get(provider, {}).get(count_name, ""))
    return count[0] if len(count) == 1 else None


def decode_reference(
    property_name: str,
    value: str,
    nodes: dict[str, dict[str, str]],
    phandles: dict[int, str],
) -> str | None:
    raw_cells = cells(value)
    if not raw_cells:
        return None
    decoded: list[str] = []
    offset = 0
    while offset < len(raw_cells):
        provider = phandles.get(raw_cells[offset])
        if provider is None:
            return None
        count = argument_count(property_name, provider, nodes)
        if count is None or offset + count >= len(raw_cells):
            return None
        args = raw_cells[offset + 1 : offset + 1 + count]
        suffix = "" if not args else "(" + ",".join(f"0x{arg:x}" for arg in args) + ")"
        decoded.append(provider + suffix)
        offset += 1 + count
    return ", ".join(decoded)


def main() -> int:
    args = arguments()
    try:
        matcher = re.compile(args.match)
    except re.error as error:
        print(f"error: invalid --match expression: {error}", file=sys.stderr)
        return 2
    if not args.capture.is_file():
        print(f"error: capture not found: {args.capture}", file=sys.stderr)
        return 2

    nodes = load(args.capture)
    if not nodes:
        print(f"error: selected-property section not found: {args.capture}", file=sys.stderr)
        return 2
    phandles = phandle_map(nodes)

    print("node\tproperty\tvalue\tdecoded")
    for node in sorted(nodes):
        if not matcher.search(node):
            continue
        for name, value in sorted(nodes[node].items()):
            decoded = decode_reference(name, value, nodes, phandles)
            print(f"{node}\t{name}\t{value}\t{decoded or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
