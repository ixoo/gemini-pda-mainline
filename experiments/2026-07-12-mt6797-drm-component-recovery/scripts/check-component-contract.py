#!/usr/bin/env python3
"""Mechanically check the source-backed MT6797 primary DRM contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EXPECTED_CLOCKS = {
    "mm_disp_ovl0",
    "mm_disp_ovl0_2l",
    "mm_disp_ovl1_2l",
    "mm_disp_rdma0",
    "mm_disp_color",
    "mm_disp_ccorr",
    "mm_disp_aal",
    "mm_disp_gamma",
    "mm_disp_od",
    "mm_disp_dither",
    "mm_disp_ufoe",
    "mm_dsi0_mm clock",
    "mm_dsi0_interface_clock",
}

EXPECTED_IRQS = {
    245: "ovl0",
    247: "ovl0_2l",
    248: "ovl1_2l",
    249: "rdma0",
    255: "aal",
    261: "dsi0",
}

EXPECTED_COMPONENTS = (
    "OVL0",
    "OVL0_2L",
    "OVL1_2L",
    "COLOR0",
    "CCORR",
    "AAL",
    "GAMMA",
    "OD",
    "DITHER",
    "RDMA0",
    "UFOE",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    text = args.capture.read_text(errors="replace")

    for clock in EXPECTED_CLOCKS:
        match = re.search(
            rf"^{re.escape(clock)}\|clk_rate=(\d+)\|clk_enable_count=(\d+)"
            rf"\|clk_prepare_count=(\d+)$",
            text,
            re.MULTILINE,
        )
        require(match is not None, f"missing clock {clock}")
        rate, enabled, prepared = map(int, match.groups())
        if clock != "mm_dsi0_interface_clock":
            require(rate == 325_000_000, f"unexpected {clock} rate {rate}")
        require(enabled in (0, 1), f"invalid enable count for {clock}")
        require(prepared == 1, f"unprepared clock {clock}")

    for irq, name in EXPECTED_IRQS.items():
        match = re.search(rf"^\s*{irq}:.*\b{re.escape(name)}\b", text, re.MULTILINE)
        require(match is not None, f"missing IRQ {irq} ({name})")

    for component in EXPECTED_COMPONENTS:
        require(
            re.search(
                rf"== DISP {re.escape(component)} REGS ==", text, re.IGNORECASE
            )
            is not None,
            f"missing retained {component} register dump",
        )

    require("UFOE_START=0x4" in text, "UFOE is not in the observed bypass state")
    require("AAL_CFG=0x16" in text, "missing observed AAL configuration")
    require("DSI0 Lane Num:15" in text, "DSI0 is not using the four-lane mask")
    require("MODE:BURST_VDO_MODE" in text, "DSI0 is not in burst video mode")

    print(
        "PASS "
        f"clocks={len(EXPECTED_CLOCKS)} irqs={len(EXPECTED_IRQS)} "
        f"components={len(EXPECTED_COMPONENTS)} clocks=prepared "
        "ufoe=bypass dsi=4-lane-burst"
    )


if __name__ == "__main__":
    main()
