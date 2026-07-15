#!/usr/bin/env python3

"""Decode the downstream MT6797 GPIO-to-EINT map from collect.sh output."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


SECTION = "===== selected device tree property values ====="


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode a MediaTek mt-eic node captured by collect.sh."
    )
    parser.add_argument("capture", type=pathlib.Path)
    parser.add_argument("--gpio", type=int, action="append", default=[])
    parser.add_argument("--eint", type=int, action="append", default=[])
    parser.add_argument(
        "--all", action="store_true", help="print the complete GPIO-to-EINT map"
    )
    parser.add_argument(
        "--kernel-header",
        type=pathlib.Path,
        help="validate mappings in a pinctrl-mtk-mt6797.h file",
    )
    return parser.parse_args()


def load(path: pathlib.Path) -> dict[str, dict[str, str]]:
    nodes: dict[str, dict[str, str]] = {}
    active = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line == SECTION:
            active = True
            continue
        if active and line.startswith("====="):
            break
        if not active or "|" not in line:
            continue
        node, assignment = line.split("|", 1)
        if "=" not in assignment:
            continue
        name, value = assignment.split("=", 1)
        nodes.setdefault(node, {})[name] = value.strip()
    return nodes


def cells(value: str | None) -> list[int]:
    if not value or value == "<present>" or len(value) % 8:
        return []
    try:
        return [int(value[index : index + 8], 16) for index in range(0, len(value), 8)]
    except ValueError:
        return []


def scalar(properties: dict[str, str], name: str) -> int | None:
    values = cells(properties.get(name))
    return values[0] if len(values) == 1 else None


def kernel_mappings(path: pathlib.Path) -> dict[int, int]:
    text = path.read_text(encoding="utf-8", errors="strict")
    pattern = re.compile(
        r'MTK_PIN\(\s*(\d+),\s*"[^"]+",\s*'
        r"MTK_EINT_FUNCTION\(\s*(?:\d+|NO_EINT_SUPPORT),\s*"
        r"(\d+|NO_EINT_SUPPORT)\s*\)",
        re.MULTILINE,
    )
    result: dict[int, int] = {}
    for pin, eint in pattern.findall(text):
        if eint != "NO_EINT_SUPPORT":
            result[int(pin)] = int(eint)
    return result


def main() -> int:
    args = arguments()
    if not args.capture.is_file():
        print(f"error: capture not found: {args.capture}", file=sys.stderr)
        return 2

    nodes = load(args.capture)
    matches = [
        (node, properties)
        for node, properties in nodes.items()
        if properties.get("compatible") == "mediatek,mt-eic"
    ]
    if len(matches) != 1:
        print(f"error: expected one mediatek,mt-eic node, found {len(matches)}", file=sys.stderr)
        return 2

    node, properties = matches[0]
    raw_map = cells(properties.get("mediatek,mapping_table"))
    if not raw_map:
        print("error: capture has no decoded mapping table", file=sys.stderr)
        return 2
    if len(raw_map) % 2:
        print("error: mapping table has an odd number of cells", file=sys.stderr)
        return 2
    mapping = dict(zip(raw_map[0::2], raw_map[1::2], strict=True))
    inverse: dict[int, list[int]] = {}
    for gpio, eint in mapping.items():
        inverse.setdefault(eint, []).append(gpio)

    declared = scalar(properties, "mediatek,mapping_table_entry")
    maximum = scalar(properties, "mediatek,max_eint_num")
    deint_count = scalar(properties, "mediatek,max_deint_cnt")
    deint_irqs = cells(properties.get("mediatek,deint_possible_irq"))
    builtin = cells(properties.get("mediatek,builtin_mapping"))
    debounce = cells(properties.get("mediatek,debtime_setting_array"))

    print(f"node: {node}")
    print(f"channels: {maximum if maximum is not None else '<missing>'}")
    print(f"mapping-entries: {len(mapping)} (declared {declared})")
    print(f"direct-eint-count: {deint_count}; parent-irqs: {' '.join(map(str, deint_irqs)) or '-'}")
    if builtin:
        triples = [builtin[index : index + 3] for index in range(0, len(builtin), 3)]
        print("builtin-map: " + " ".join(f"gpio={a}/mode={b}/eint={c}" for a, b, c in triples))
    if debounce:
        pairs = [debounce[index : index + 2] for index in range(0, len(debounce), 2)]
        print("debounce-us: " + " ".join(f"setting={a}:{b}" for a, b in pairs))

    if args.kernel_header:
        if not args.kernel_header.is_file():
            print(f"error: kernel header not found: {args.kernel_header}", file=sys.stderr)
            return 2
        described = kernel_mappings(args.kernel_header)
        mismatches = {
            gpio: (eint, described.get(gpio))
            for gpio, eint in mapping.items()
            if described.get(gpio) != eint
        }
        unexpected = {
            gpio: eint
            for gpio, eint in described.items()
            if gpio <= max(mapping) and gpio not in mapping
        }
        builtin_eints = set(builtin[2::3])
        described_eints = set(described.values())
        missing_builtin = builtin_eints - described_eints
        if mismatches or unexpected or missing_builtin:
            for gpio, (expected, actual) in sorted(mismatches.items()):
                print(
                    f"error: GPIO {gpio}: expected EINT {expected}, got {actual}",
                    file=sys.stderr,
                )
            for gpio, eint in sorted(unexpected.items()):
                print(f"error: unexpected GPIO {gpio} -> EINT {eint}", file=sys.stderr)
            for eint in sorted(missing_builtin):
                print(f"error: built-in EINT {eint} is not represented", file=sys.stderr)
            return 1
        print(
            f"kernel-header: {args.kernel_header}; "
            f"{len(mapping)} mappings and built-in EINTs match"
        )

    if declared is not None and declared != len(mapping):
        print("warning: declared mapping count differs from decoded count", file=sys.stderr)
    duplicates = {eint: gpios for eint, gpios in inverse.items() if len(gpios) > 1}
    if duplicates:
        for eint, gpios in duplicates.items():
            print(f"warning: EINT {eint} maps from GPIOs {gpios}", file=sys.stderr)

    queries: list[tuple[int, int]] = []
    for gpio in args.gpio:
        if gpio in mapping:
            queries.append((gpio, mapping[gpio]))
        else:
            print(f"gpio {gpio}: no mapping")
    for eint in args.eint:
        gpios = inverse.get(eint, [])
        print(f"eint {eint}: gpios {' '.join(map(str, gpios)) or '-'}")
    if args.all:
        queries.extend(sorted(mapping.items()))
    for gpio, eint in queries:
        print(f"gpio {gpio} -> eint {eint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
