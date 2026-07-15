#!/usr/bin/env python3
"""Extract the MT6351 regulator model from the Planet MT6797 vendor tree.

This does not copy driver code.  It turns the vendor descriptor declarations
and generated register header into a reviewable, raw-selector-oriented table
that can be compared with an independently written mainline driver.
"""

from __future__ import annotations

import argparse
import ast
import csv
import re
import sys
from pathlib import Path


REVERSED_LDO_SELECTORS = {
    "va18",
    "vtcxo24",
    "vtcxo28",
    "vcn28",
    "vxo22",
    "vbif28",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pmic-c", required=True, type=Path)
    parser.add_argument("--upmu-hw", required=True, type=Path)
    parser.add_argument("--driver", type=Path)
    parser.add_argument("--registers", type=Path)
    return parser.parse_args()


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//.*", "", text)


def parse_defines(text: str) -> dict[str, str]:
    definitions: dict[str, str] = {}
    text = text.replace("\\\n", " ")
    for line in text.splitlines():
        match = re.match(r"\s*#define\s+(\w+)\s+(.+?)\s*$", line)
        if match:
            definitions[match.group(1)] = match.group(2)
    return definitions


def evaluate_define(name: str, definitions: dict[str, str], stack: set[str] | None = None) -> int:
    if stack is None:
        stack = set()
    if name in stack:
        raise ValueError(f"recursive macro definition involving {name}")
    if name not in definitions:
        raise ValueError(f"missing macro definition: {name}")

    stack = stack | {name}
    expression = definitions[name]
    expression = re.sub(r"\(\s*unsigned\s+(?:int|short|long)\s*\)", "", expression)

    def replace_identifier(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in {"x", "X"}:
            return token
        if token not in definitions:
            raise ValueError(f"unresolved token {token} while evaluating {name}")
        return str(evaluate_define(token, definitions, stack))

    expression = re.sub(r"\b[A-Za-z_]\w*\b", replace_identifier, expression)
    tree = ast.parse(expression, mode="eval")
    allowed = (
        ast.Expression,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.BitOr,
        ast.BitAnd,
        ast.LShift,
        ast.RShift,
        ast.UnaryOp,
        ast.USub,
        ast.BinOp,
    )
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError(f"unsupported expression for {name}: {expression}")
    return int(eval(compile(tree, "<macro>", "eval"), {"__builtins__": {}}, {}))


def parse_voltage_arrays(text: str) -> dict[str, list[int]]:
    arrays: dict[str, list[int]] = {}
    pattern = re.compile(r"static\s+const\s+(?:unsigned\s+)?int\s+(\w+)\[\]\s*=\s*\{(.*?)\};", re.S)
    for match in pattern.finditer(text):
        values = [int(value, 0) for value in re.findall(r"\b(?:0x[0-9a-fA-F]+|\d+)\b", match.group(2))]
        arrays[match.group(1)] = values
    return arrays


def split_arguments(arguments: str) -> list[str]:
    result: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(arguments):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == "," and depth == 0:
            result.append(arguments[start:index].strip())
            start = index + 1
    result.append(arguments[start:].strip())
    return result


def macro_calls(text: str, macro: str) -> list[list[str]]:
    calls: list[list[str]] = []
    start = 0
    needle = f"{macro}("
    while (offset := text.find(needle, start)) >= 0:
        index = offset + len(needle)
        depth = 1
        while index < len(text) and depth:
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
            index += 1
        if depth:
            raise ValueError(f"unterminated {macro} invocation")
        calls.append(split_arguments(text[offset + len(needle) : index - 1]))
        start = index
    return calls


def field(token: str, suffix: str, definitions: dict[str, str]) -> int:
    return evaluate_define(f"MT6351_{token}_{suffix}", definitions)


def driver_mask(expression: str) -> int:
    bit = re.fullmatch(r"BIT\((\d+)\)", expression)
    if bit:
        return 1 << int(bit.group(1))
    genmask = re.fullmatch(r"GENMASK\((\d+),\s*(\d+)\)", expression)
    if genmask:
        high, low = (int(value) for value in genmask.groups())
        return ((1 << (high - low + 1)) - 1) << low
    return int(expression, 0)


def validate_driver(
    driver_path: Path,
    registers_path: Path,
    expected_rows: list[dict[str, str | int]],
) -> None:
    driver_text = strip_comments(driver_path.read_text())
    definitions = parse_defines(strip_comments(registers_path.read_text()))
    arrays = parse_voltage_arrays(driver_text)
    actual: dict[tuple[str, str], dict[str, str]] = {}

    def register(name: str) -> int:
        return evaluate_define(name, definitions)

    for arguments in macro_calls(driver_text, "MT6351_LDO"):
        if len(arguments) != 6 or arguments[0] == "_match":
            continue
        _match, name, table, enable, selector, mask = arguments
        actual[("ldo", name.lower())] = {
            "enable_reg": f"0x{register(enable):04x}",
            "enable_mask": "0x0002",
            "vsel_reg": f"0x{register(selector):04x}",
            "vsel_mask": f"0x{driver_mask(mask):04x}",
            "voltages_uv_by_raw_selector": ",".join(str(value) for value in arrays[table]),
        }

    for arguments in macro_calls(driver_text, "MT6351_FIXED"):
        if len(arguments) != 4 or arguments[0] == "_match":
            continue
        _match, name, enable, voltage = arguments
        actual[("ldo", name.lower())] = {
            "enable_reg": f"0x{register(enable):04x}",
            "enable_mask": "0x0002",
            "vsel_reg": "-",
            "vsel_mask": "-",
            "voltages_uv_by_raw_selector": voltage,
        }

    for arguments in macro_calls(driver_text, "MT6351_BUCK"):
        if len(arguments) != 9 or arguments[0] == "_match":
            continue
        _match, name, _ranges, max_selector, _control, enable, selector, _on, mask = arguments
        maximum = int(max_selector, 0)
        actual[("buck", name.lower())] = {
            "enable_reg": f"0x{register(enable):04x}",
            "enable_mask": "0x0001",
            "vsel_reg": f"0x{register(selector):04x}",
            "vsel_mask": f"0x{driver_mask(mask):04x}",
            "voltages_uv_by_raw_selector": f"600000..{600000 + maximum * 6250}/6250",
        }

    expected: dict[tuple[str, str], dict[str, str | int]] = {}
    for row in expected_rows:
        key = (str(row["type"]), str(row["name"]))
        if key in {("ldo", "vsram_proc"), ("ldo", "vldo28_0")}:
            continue
        if key == ("buck", "vpa"):
            row = dict(row)
            row["voltages_uv_by_raw_selector"] = "600000..993750/6250"
        expected[key] = row

    if actual.keys() != expected.keys():
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        raise ValueError(f"driver regulator set mismatch: missing={missing}, extra={extra}")

    fields = ("enable_reg", "enable_mask", "vsel_reg", "vsel_mask", "voltages_uv_by_raw_selector")
    failures: list[str] = []
    for key in sorted(expected):
        for name in fields:
            if str(actual[key][name]) != str(expected[key][name]):
                failures.append(f"{key[0]} {key[1]} {name}: driver={actual[key][name]} evidence={expected[key][name]}")
    if failures:
        raise ValueError("driver descriptor mismatches:\n" + "\n".join(failures))

    print(f"validated {len(actual)} unique MT6351 regulator descriptors", file=sys.stderr)


def main() -> int:
    args = parse_args()
    pmic_text = strip_comments(args.pmic_c.read_text())
    hw_text = strip_comments(args.upmu_hw.read_text())
    definitions = parse_defines(hw_text)
    arrays = parse_voltage_arrays(pmic_text)

    rows: list[dict[str, str | int]] = []
    for arguments in macro_calls(pmic_text, "PMIC_LDO_GEN1"):
        if len(arguments) != 6 or arguments[0] == "_name":
            continue
        name, enable, selector, array_name, _usable, _mode = arguments
        voltages = arrays[array_name]
        if name in REVERSED_LDO_SELECTORS:
            voltages = list(reversed(voltages))
        rows.append(
            {
                "type": "ldo",
                "name": name,
                "enable_reg": f"0x{field(enable, 'ADDR', definitions):04x}",
                "enable_mask": f"0x{field(enable, 'MASK', definitions) << field(enable, 'SHIFT', definitions):04x}",
                "vsel_reg": "-" if selector == "NULL" else f"0x{field(selector, 'ADDR', definitions):04x}",
                "vsel_mask": "-" if selector == "NULL" else f"0x{field(selector, 'MASK', definitions) << field(selector, 'SHIFT', definitions):04x}",
                "voltages_uv_by_raw_selector": ",".join(str(value) for value in voltages),
                "note": "invalid vendor duplicate of buck" if name == "vsram_proc" else "",
            }
        )

    for arguments in macro_calls(pmic_text, "PMIC_BUCK_GEN"):
        if len(arguments) != 6 or arguments[0] == "_name":
            continue
        name, enable, selector, minimum, maximum, step = arguments
        rows.append(
            {
                "type": "buck",
                "name": name.lower(),
                "enable_reg": f"0x{field(enable, 'ADDR', definitions):04x}",
                "enable_mask": f"0x{field(enable, 'MASK', definitions) << field(enable, 'SHIFT', definitions):04x}",
                "vsel_reg": f"0x{field(selector, 'ADDR', definitions):04x}",
                "vsel_mask": f"0x{field(selector, 'MASK', definitions) << field(selector, 'SHIFT', definitions):04x}",
                "voltages_uv_by_raw_selector": f"{minimum}..{maximum}/{step}",
                "note": "",
            }
        )

    if bool(args.driver) != bool(args.registers):
        raise SystemExit("--driver and --registers must be supplied together")
    if args.driver:
        validate_driver(args.driver, args.registers, rows)

    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]), dialect="unix")
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
