#!/usr/bin/env python3
"""Check the recovered MT6797 MMSYS routing and reset contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REGISTER_OFFSETS = {
    "OVL0_MOUT": 0x034,
    "OVL1_MOUT": 0x038,
    "DITHER_MOUT": 0x03C,
    "UFOE_MOUT": 0x040,
    "DSC_MOUT": 0x044,
    "COLOR0_SEL": 0x068,
    "WDMA0_SEL": 0x06C,
    "WDMA1_SEL": 0x070,
    "UFOE_SEL": 0x074,
    "DSC_SEL": 0x078,
    "DSI0_SEL": 0x07C,
    "DSI1_SEL": 0x080,
    "DPI0_SEL": 0x084,
    "PATH0_SEL": 0x088,
    "PATH0_SOUT": 0x08C,
    "RDMA0_SOUT": 0x090,
    "RDMA1_SOUT": 0x094,
    "OVL0_SOUT": 0x098,
    "OVL0_SEL": 0x09C,
    "OVL1_SOUT": 0x0A0,
    "SW0_RST_B": 0x140,
    "SW1_RST_B": 0x144,
}

ACTIVE_VALUES = {
    "OVL0_MOUT": 1,
    "OVL1_MOUT": 0,
    "DITHER_MOUT": 1,
    "UFOE_MOUT": 1,
    "DSC_MOUT": 0,
    "COLOR0_SEL": 1,
    "WDMA0_SEL": 0,
    "UFOE_SEL": 0,
    "DSC_SEL": 0,
    "DSI0_SEL": 0,
    "DSI1_SEL": 0,
    "DPI0_SEL": 0,
    "OVL0_SEL": 2,
    "PATH0_SOUT": 0,
    "RDMA0_SOUT": 0,
    "RDMA1_SOUT": 0,
    "OVL0_SOUT": 1,
    "OVL1_SOUT": 1,
}

ACTIVE_WRITES = {
    ("OVL_2L0", "OVL_2L1", 0x098, 0x1, 0x1),
    ("OVL_2L1", "COLOR0", 0x0A0, 0x1, 0x1),
    ("OVL_2L1", "COLOR0", 0x09C, 0x3, 0x2),
    ("OVL_2L1", "COLOR0", 0x034, 0x1, 0x1),
    ("OVL_2L1", "COLOR0", 0x068, 0x1, 0x1),
    ("DITHER0", "RDMA0", 0x03C, 0x1, 0x1),
    ("RDMA0", "UFOE", 0x090, 0x7, 0x0),
    ("RDMA0", "UFOE", 0x088, 0x1, 0x0),
    ("RDMA0", "UFOE", 0x08C, 0x1, 0x0),
    ("RDMA0", "UFOE", 0x074, 0x1, 0x0),
    ("UFOE", "DSI0", 0x040, 0x1, 0x1),
    ("UFOE", "DSI0", 0x07C, 0x3, 0x0),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def parse_defines(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    pending = dict(
        re.findall(r"^#define[ \t]+([A-Z0-9_]+)[ \t]+([^/\n]+)", text, re.MULTILINE)
    )
    for _ in range(len(pending) + 1):
        changed = False
        for name, expression in list(pending.items()):
            expression = expression.strip()
            expression = re.sub(r"\bBIT\((\d+)\)", lambda m: str(1 << int(m[1])), expression)
            expression = re.sub(
                r"\bGENMASK\((\d+),\s*(\d+)\)",
                lambda m: str(((1 << (int(m[1]) + 1)) - 1) ^ ((1 << int(m[2])) - 1)),
                expression,
            )
            for symbol, value in values.items():
                expression = re.sub(rf"\b{re.escape(symbol)}\b", str(value), expression)
            if re.fullmatch(r"[0-9a-fA-FxX()|&~<>+* \t-]+", expression):
                try:
                    values[name] = int(eval(expression, {"__builtins__": {}}, {}))
                except (SyntaxError, ValueError):
                    continue
                del pending[name]
                changed = True
        if not changed:
            break
    return values


def parse_routes(text: str, defines: dict[str, int]) -> set[tuple[str, str, int, int, int]]:
    routes = set()
    pattern = re.compile(
        r"MMSYS_ROUTE\(\s*([A-Z0-9_]+)\s*,\s*([A-Z0-9_]+)\s*,\s*"
        r"([A-Z0-9_]+)\s*,\s*([A-Z0-9_]+|0x[0-9a-fA-F]+|\d+)\s*,\s*"
        r"([A-Z0-9_]+|0x[0-9a-fA-F]+|\d+)\s*\)"
    )
    for source, target, register, mask, value in pattern.findall(text):
        resolve = lambda token: defines[token] if token in defines else int(token, 0)
        routes.add((source, target, resolve(register), resolve(mask), resolve(value)))
    return routes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_ddp_reg", type=Path)
    parser.add_argument("vendor_ddp_path", type=Path)
    parser.add_argument("linux_header", type=Path)
    parser.add_argument("linux_mmsys_c", type=Path)
    parser.add_argument("linux_dtsi", type=Path)
    args = parser.parse_args()

    vendor_reg = args.vendor_ddp_reg.read_text()
    vendor_path = args.vendor_ddp_path.read_text()
    header = args.linux_header.read_text()
    mmsys_c = args.linux_mmsys_c.read_text()
    dtsi = args.linux_dtsi.read_text()

    for short_name, offset in REGISTER_OFFSETS.items():
        vendor_name = "DISP_REG_CONFIG_" + {
            "OVL0_MOUT": "DISP_OVL0_MOUT_EN",
            "OVL1_MOUT": "DISP_OVL1_MOUT_EN",
            "DITHER_MOUT": "DISP_DITHER_MOUT_EN",
            "UFOE_MOUT": "DISP_UFOE_MOUT_EN",
            "DSC_MOUT": "DISP_DSC_MOUT_EN",
            "COLOR0_SEL": "DISP_COLOR0_SEL_IN",
            "WDMA0_SEL": "DISP_WDMA0_SEL_IN",
            "WDMA1_SEL": "DISP_WDMA1_SEL_IN",
            "UFOE_SEL": "DISP_UFOE_SEL_IN",
            "DSC_SEL": "DISP_DSC_SEL_IN",
            "DSI0_SEL": "DSI0_SEL_IN",
            "DSI1_SEL": "DSI1_SEL_IN",
            "DPI0_SEL": "DPI0_SEL_IN",
            "PATH0_SEL": "DISP_PATH0_SEL_IN",
            "PATH0_SOUT": "DISP_PATH0_SOUT_SEL_IN",
            "RDMA0_SOUT": "DISP_RDMA0_SOUT_SEL_IN",
            "RDMA1_SOUT": "DISP_RDMA1_SOUT_SEL_IN",
            "OVL0_SOUT": "DISP_OVL0_SOUT_SEL_IN",
            "OVL0_SEL": "DISP_OVL0_SEL_IN",
            "OVL1_SOUT": "DISP_OVL1_SOUT_SEL_IN",
            "SW0_RST_B": "MMSYS_SW0_RST_B",
            "SW1_RST_B": "MMSYS_SW1_RST_B",
        }[short_name]
        require(
            re.search(
                rf"#define\s+{vendor_name}\s+\(DISPSYS_CONFIG_BASE\s+\+\s+0x0*{offset:x}\)",
                vendor_reg,
                re.I,
            )
            is not None,
            f"vendor register {vendor_name} is not 0x{offset:03x}",
        )

    for token in (
        "{DISP_MODULE_OVL0_2L, {DISP_MODULE_OVL0_VIRTUAL, DISP_MODULE_OVL1_2L",
        "{DISP_MODULE_OVL1_2L, {DISP_MODULE_OVL1, DISP_MODULE_OVL0_VIRTUAL",
        "{DISP_MODULE_RDMA0, {DISP_PATH0, DISP_MODULE_COLOR0, DISP_MODULE_DSI0",
        "{DISP_MODULE_DSI0, {DISP_MODULE_UFOE, DISP_MODULE_SPLIT0, DISP_MODULE_RDMA0, DISP_MODULE_DSC",
    ):
        require(token in vendor_path, f"vendor route-table evidence missing: {token}")

    defines = parse_defines(header)
    routes = parse_routes(header, defines)
    require(ACTIVE_WRITES <= routes, f"active path lacks {sorted(ACTIVE_WRITES - routes)}")
    require(len({(source, target) for source, target, *_ in routes}) == 29, "expected 29 collapsed high-level routes")
    require(".routes = mt6797_mmsys_routing_table" in mmsys_c, "MT6797 routes not selected")
    require(".sw0_rst_offset = MT6797_MMSYS_SW0_RST_B" in mmsys_c, "MT6797 reset offset absent")
    require(".num_resets = 64" in mmsys_c, "MT6797 two-bank reset count absent")
    require(
        "DISP_REG_CONFIG_MMSYS_LCM_RST_B" in vendor_reg
        and "DISPSYS_CONFIG_BASE + 0x150" in vendor_reg,
        "separate MT6797 LCM reset output is not 0x150",
    )

    node = re.search(r"mmsys: syscon@14000000\s*\{(.*?)\n\t\};", dtsi, re.DOTALL)
    require(node is not None, "MT6797 MMSYS node missing")
    require("#reset-cells = <1>;" in node.group(1), "MMSYS reset provider property missing")
    require("mediatek,gce-client-reg = <&gce SUBSYS_1400XXXX 0 0x1000>;" in node.group(1), "MMSYS GCE tuple missing")

    print(
        "PASS registers=22 high-level-routes=29 active-writes=12 "
        "active-values=17 resets=64 panel-reset=separate-0x150 "
        "gce-subsys=SUBSYS_1400XXXX"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
