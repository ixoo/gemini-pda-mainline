#!/usr/bin/env python3

"""Decode MediaTek LCM parameters and operation tables from collect.sh output."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys


SECTION = "===== selected device tree property values ====="
FUNCTIONS = {1: "gpio", 2: "i2c", 3: "utility", 4: "dsi"}
GPIO_TYPES = {1: "mode", 2: "direction", 3: "output"}
UTILITY_TYPES = {
    1: "reset",
    2: "delay-ms",
    3: "delay-us",
    4: "write-command-v1",
    5: "write-command-v2",
    6: "read-command-v1",
    7: "read-command-v2",
    8: "write-command-v21",
    9: "write-command-v22",
    10: "write-command-v23",
    11: "rar",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode the live vendor LCM contract captured by collect.sh."
    )
    parser.add_argument("capture", type=pathlib.Path)
    parser.add_argument(
        "--full",
        action="store_true",
        help="print complete DSI payloads instead of compact previews",
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


def cells(value: str) -> list[int]:
    if not value or value == "<present>" or len(value) % 8:
        return []
    try:
        result = [int(value[index : index + 8], 16) for index in range(0, len(value), 8)]
    except ValueError:
        return []
    return result


def operation_bytes(value: str) -> list[int]:
    result = cells(value)
    if any(item > 0xFF for item in result):
        raise ValueError("LCM operation cell exceeds one byte")
    return result


def format_bytes(data: list[int], full: bool) -> str:
    encoded = bytes(data)
    if full or len(data) <= 8:
        return " ".join(f"{item:02x}" for item in data) or "-"
    preview = " ".join(f"{item:02x}" for item in data[:8])
    digest = hashlib.sha256(encoded).hexdigest()[:16]
    return f"{preview} ... ({len(data)} bytes, sha256:{digest})"


def describe(function: int, operation: int, payload: list[int], full: bool) -> str:
    if function == 1:
        value = payload[0] if payload else None
        if operation == 2 and value is not None:
            return "direction=" + ("output" if value else "input")
        if operation == 3 and value is not None:
            return "value=" + ("high" if value else "low")
        return f"{GPIO_TYPES.get(operation, f'type-{operation}')}={value}"
    if function == 2:
        if operation == 1 and len(payload) >= 2:
            return f"write register=0x{payload[0]:02x} value=0x{payload[1]:02x}"
        return "payload=" + format_bytes(payload, full)
    if function == 3:
        value = payload[0] if payload else None
        if operation == 1 and value is not None:
            return "reset=" + ("high" if value else "low")
        if operation in (2, 3) and value is not None:
            unit = "ms" if operation == 2 else "us"
            return f"delay={value}{unit}"
        return "payload=" + format_bytes(payload, full)
    if function == 4:
        if operation in (5, 10) and len(payload) >= 2:
            command, count = payload[:2]
            parameters = payload[2:]
            mismatch = "" if count == len(parameters) else f" declared={count}"
            return (
                f"DCS command=0x{command:02x} count={len(parameters)}{mismatch} "
                f"data={format_bytes(parameters, full)}"
            )
        if operation == 7 and len(payload) >= 3:
            return (
                f"DCS read command=0x{payload[0]:02x} "
                f"expect byte[{payload[1]}]=0x{payload[2]:02x}"
            )
        return "payload=" + format_bytes(payload, full)
    return "payload=" + format_bytes(payload, full)


def decode_table(name: str, value: str, full: bool) -> tuple[list[str], list[str]]:
    raw = operation_bytes(value)
    output: list[str] = []
    warnings: list[str] = []
    offset = 0
    record = 0
    while offset < len(raw):
        if len(raw) - offset < 3:
            warnings.append(f"{name}: trailing cells at offset {offset}: {raw[offset:]}")
            break
        function, operation, size = raw[offset : offset + 3]
        offset += 3
        available = min(size, len(raw) - offset)
        payload = raw[offset : offset + available]
        if available < size:
            # The downstream compare-id record declares the padded C structure
            # size while the DT stores only its three meaningful bytes.
            if function == 4 and operation == 7 and available >= 3:
                warnings.append(
                    f"{name}[{record}]: declared {size} bytes; "
                    f"DT stores {available} meaningful bytes"
                )
                offset = len(raw)
            else:
                warnings.append(
                    f"{name}[{record}]: truncated payload: expected {size}, got {available}"
                )
                offset = len(raw)
        else:
            offset += size
        function_name = FUNCTIONS.get(function, f"function-{function}")
        operation_name = (
            GPIO_TYPES.get(operation, f"type-{operation}")
            if function == 1
            else UTILITY_TYPES.get(operation, f"type-{operation}")
            if function in (3, 4)
            else "write"
            if function == 2 and operation == 1
            else f"type-{operation}"
        )
        detail = describe(function, operation, payload, full)
        output.append(f"{name}[{record:02d}] {function_name}/{operation_name}: {detail}")
        record += 1
    return output, warnings


def parameter_summary(properties: dict[str, str]) -> list[str]:
    selected = {
        "lcm_params-resolution": "resolution",
        "lcm_params-physical_width_um": "physical-width-um",
        "lcm_params-physical_height_um": "physical-height-um",
        "lcm_params-dsi-mode": "dsi-mode",
        "lcm_params-dsi-dual_dsi_type": "dual-dsi-type",
        "lcm_params-dsi-lane_num": "lanes-per-link",
        "lcm_params-dsi-data_format": "data-format",
        "lcm_params-dsi-pll_clock": "pll-clock-mhz",
        "lcm_params-dsi-ufoe_enable": "ufoe-enable",
        "lcm_params-dsi-ufoe_params": "ufoe-parameters",
        "lcm_params-dsi-lane_swap_en": "lane-swap-enable",
        "lcm_params-dsi-lane_swap0": "lane-swap-port0",
        "lcm_params-dsi-lane_swap1": "lane-swap-port1",
        "lcm_params-dsi-lcm_esd_check_table0": "esd-check",
    }
    result: list[str] = []
    for property_name, label in selected.items():
        value = properties.get(property_name)
        if value is None:
            continue
        parsed = cells(value)
        result.append(f"{label}: " + (" ".join(str(item) for item in parsed) or value))
    return result


def main() -> int:
    args = arguments()
    if not args.capture.is_file():
        print(f"error: capture not found: {args.capture}", file=sys.stderr)
        return 2
    try:
        nodes = load(args.capture)
        params = nodes.get("/lcm_params", {})
        ops = nodes.get("/lcm_ops", {})
        if not params or not ops:
            print("error: capture has no complete /lcm_params and /lcm_ops data", file=sys.stderr)
            return 2

        print("LCM parameters")
        print(f"compatible: {params.get('compatible', '<missing>')}")
        for line in parameter_summary(params):
            print(line)

        warnings: list[str] = []
        for table_name in ("init", "compare_id", "suspend", "backlight", "backlight_cmdq"):
            value = ops.get(table_name)
            if value is None:
                continue
            print(f"\n{table_name} operations")
            lines, table_warnings = decode_table(table_name, value, args.full)
            print("\n".join(lines))
            warnings.extend(table_warnings)
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
