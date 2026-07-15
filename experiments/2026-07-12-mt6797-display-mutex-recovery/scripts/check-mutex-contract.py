#!/usr/bin/env python3
"""Cross-check Gemian MT6797 mutex facts against the proposed Linux support."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


COMPONENTS = {
    "DISP_MODULE_OVL0": ("DDP_COMPONENT_OVL0", "OVL0"),
    "DISP_MODULE_OVL1": ("DDP_COMPONENT_OVL1", "OVL1"),
    "DISP_MODULE_OVL0_2L": ("DDP_COMPONENT_OVL_2L0", "OVL0_2L"),
    "DISP_MODULE_OVL1_2L": ("DDP_COMPONENT_OVL_2L1", "OVL1_2L"),
    "DISP_MODULE_RDMA0": ("DDP_COMPONENT_RDMA0", "RDMA0"),
    "DISP_MODULE_RDMA1": ("DDP_COMPONENT_RDMA1", "RDMA1"),
    "DISP_MODULE_WDMA0": ("DDP_COMPONENT_WDMA0", "WDMA0"),
    "DISP_MODULE_WDMA1": ("DDP_COMPONENT_WDMA1", "WDMA1"),
    "DISP_MODULE_COLOR0": ("DDP_COMPONENT_COLOR0", "COLOR0"),
    "DISP_MODULE_CCORR": ("DDP_COMPONENT_CCORR", "CCORR"),
    "DISP_MODULE_AAL": ("DDP_COMPONENT_AAL0", "AAL"),
    "DISP_MODULE_GAMMA": ("DDP_COMPONENT_GAMMA", "GAMMA"),
    "DISP_MODULE_OD": ("DDP_COMPONENT_OD0", "OD"),
    "DISP_MODULE_DITHER": ("DDP_COMPONENT_DITHER0", "DITHER"),
    "DISP_MODULE_UFOE": ("DDP_COMPONENT_UFOE", "UFOE"),
    "DISP_MODULE_DSC": ("DDP_COMPONENT_DSC0", "DSC"),
    "DISP_MODULE_PWM0": ("DDP_COMPONENT_PWM0", "PWM0"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_path", type=Path)
    parser.add_argument("vendor_registers", type=Path)
    parser.add_argument("linux_driver", type=Path)
    parser.add_argument("linux_dtsi", type=Path)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> int:
    args = parse_args()
    vendor = args.vendor_path.read_text()
    registers = args.vendor_registers.read_text()
    linux = args.linux_driver.read_text()
    dtsi = args.linux_dtsi.read_text()

    table_match = re.search(
        r"static module_map_t module_mutex_map.*?=\s*\{(.*?)\n\};",
        vendor,
        re.DOTALL,
    )
    require(table_match is not None, "vendor module_mutex_map not found")
    vendor_bits: dict[str, int] = {}
    for name, bit in re.findall(r"\{(DISP_[A-Z0-9_]+),\s*(-?\d+)\}", table_match.group(1)):
        vendor_bits.setdefault(name, int(bit))

    positive = {name: bit for name, bit in vendor_bits.items() if bit >= 0}
    require(set(positive) == set(COMPONENTS), "unexpected positive vendor module set")

    defines = {
        name: int(value)
        for name, value in re.findall(
            r"^#define MT6797_MUTEX_MOD_DISP_([A-Z0-9_]+)\s+(\d+)$",
            linux,
            re.MULTILINE,
        )
    }
    array_match = re.search(
        r"static const u8 mt6797_mutex_mod.*?=\s*\{(.*?)\n\};",
        linux,
        re.DOTALL,
    )
    require(array_match is not None, "Linux mt6797_mutex_mod not found")
    array_entries = dict(
        re.findall(
            r"\[(DDP_COMPONENT_[A-Z0-9_]+)\]\s*=\s*"
            r"MT6797_MUTEX_MOD_DISP_([A-Z0-9_]+)",
            array_match.group(1),
        )
    )

    for vendor_name, bit in sorted(positive.items(), key=lambda item: item[1]):
        component, suffix = COMPONENTS[vendor_name]
        require(defines.get(suffix) == bit, f"{suffix} bit differs from vendor")
        require(array_entries.get(component) == suffix, f"{component} array entry differs")

    vendor_sources = {
        name: int(value)
        for name, value in re.findall(
            r"^#define SOF_VAL_MUTEX0_SOF_(SINGLE_MODE|FROM_DSI0|FROM_DSI1|FROM_DPI)"
            r"\s+\((\d+)\)$",
            registers,
            re.MULTILINE,
        )
    }
    require(
        vendor_sources
        == {"SINGLE_MODE": 0, "FROM_DSI0": 1, "FROM_DSI1": 2, "FROM_DPI": 3},
        "vendor SOF source encoding changed",
    )
    for suffix, value in (("DSI0", 1), ("DSI1", 2), ("DPI0", 3)):
        require(
            re.search(rf"^#define MT6797_MUTEX_SOF_{suffix}\s+{value}$", linux, re.MULTILINE)
            is not None,
            f"Linux {suffix} SOF encoding differs",
        )
        require(
            re.search(
                rf"\[MUTEX_SOF_{suffix}\].*?MT6797_MUTEX_EOF\(MT6797_MUTEX_SOF_{suffix}\)",
                linux,
                re.DOTALL,
            )
            is not None,
            f"Linux {suffix} EOF encoding missing",
        )

    for token in (
        ".mutex_mod_reg = MT2701_MUTEX0_MOD0",
        ".mutex_mod1_reg = MT2701_MUTEX0_MOD1",
        ".mutex_sof_reg = MT2701_MUTEX0_SOF0",
        ".no_clk = true",
    ):
        require(token in linux, f"Linux driver data lacks {token}")

    node_match = re.search(r"mutex: mutex@1401f000\s*\{(.*?)\n\t\};", dtsi, re.DOTALL)
    require(node_match is not None, "MT6797 mutex DT node not found")
    node = node_match.group(1)
    for token in (
        'compatible = "mediatek,mt6797-disp-mutex"',
        "reg = <0 0x1401f000 0 0x1000>",
        "interrupts = <GIC_SPI 202 IRQ_TYPE_LEVEL_LOW>",
        "power-domains = <&scpsys MT6797_POWER_DOMAIN_MM>",
        "<CMDQ_EVENT_MUTEX0_STREAM_EOF>",
        "<CMDQ_EVENT_MUTEX1_STREAM_EOF>",
        "<&gce SUBSYS_1401XXXX 0xf000 0x1000>",
    ):
        require(token in node, f"MT6797 mutex DT node lacks {token}")

    print(
        "PASS "
        f"components={len(positive)} module-bits={min(positive.values())}-{max(positive.values())} "
        "sof-sources=4 register-layout=0x2c/0x30 no-clk=true "
        "irq-spi=202 power-domain=MM gce-subsys=2"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
