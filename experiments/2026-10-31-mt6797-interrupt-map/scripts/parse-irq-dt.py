#!/usr/bin/env python3
"""Extract enabled GIC SPI interrupts from a decompiled device tree.

Usage:
    dtc -I dtb -O dts -o board.dts board.dtb
    ./scripts/parse-irq-dt.py board.dts > results/spi-map.tsv

The parser is intentionally small: it understands the flat `node { prop = ...; }`
form produced by dtc for the MT6797 vendor DT. It emits unique (SPI, node)
pairs for nodes whose status is not "disabled".
"""

from __future__ import annotations

import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    stack: list[dict] = []
    nodes: list[dict] = []

    for line in open(sys.argv[1], encoding="utf-8"):
        s = line.strip()
        match = re.match(r"^([A-Za-z0-9_,.+\-@]+)\s*\{$", s)
        if match:
            stack.append(
                {
                    "name": match.group(1),
                    "props": {},
                    "parent": stack[-1] if stack else None,
                }
            )
            continue
        if s == "};":
            if stack:
                nodes.append(stack.pop())
            continue
        if not stack:
            continue
        if "=" in s and s.endswith(";"):
            key, value = s.split("=", 1)
            stack[-1]["props"][key.strip()] = value.strip().rstrip(";").strip()
        elif s.endswith(";") and not s.startswith("/*"):
            key = s.rstrip(";").strip()
            if key:
                stack[-1]["props"][key] = ""

    def path(node: dict) -> str:
        parts = []
        while node:
            parts.append(node["name"])
            node = node["parent"]
        return "/" + "/".join(reversed(parts))

    rows = {}
    for node in nodes:
        props = node["props"]
        if "interrupts" not in props:
            continue
        status = props.get("status", '"okay"').strip('"')
        if status == "disabled":
            continue
        values = [int(token, 0) for token in re.findall(r"0x[0-9a-fA-F]+|\d+", props["interrupts"])]
        for i in range(0, len(values) - 2, 3):
            kind, number, flags = values[i], values[i + 1], values[i + 2]
            if kind == 0:  # GIC_SPI
                rows[(number, path(node))] = (props.get("compatible", "").strip('"'), flags)

    print("spi\tlinux_irq\tnode\tcompatible\tflags")
    for (spi, node_path), (compatible, flags) in sorted(rows.items()):
        print(f"{spi}\t{spi + 32}\t{node_path.split('/')[-1]}\t{compatible.split(chr(34))[0]}\t{flags:#x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
