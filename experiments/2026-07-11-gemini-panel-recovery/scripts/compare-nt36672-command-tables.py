#!/usr/bin/env python3
"""Compare the Gemini NT36672 table with Linux's NT36672E variant."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess


VENDOR_PATH = (
    "drivers/misc/mediatek/lcm/"
    "aeon_nt36672_fhd_dsi_vdo_x600_xinli/"
    "aeon_nt36672_fhd_dsi_vdo_x600_xinli.c"
)
VENDOR_DSI_PATH = "drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c"
VENDOR_DTS_PATH = "arch/arm64/boot/dts/aeon_gpio.dtsi"


def git_source(repository: Path, path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "show", f"HEAD:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def vendor_source(repository: Path) -> str:
    return git_source(repository, VENDOR_PATH)


def vendor_commands(source: str) -> list[tuple[int, int, tuple[int, ...]]]:
    table = source.split("static struct LCM_setting_table init_setting[] = {", 1)[1]
    table = table.split("#if 1", 1)[1].split("#else", 1)[0]
    entry = re.compile(
        r"\{\s*0x([0-9a-f]+)\s*,\s*(\d+)\s*,\s*\{([^}]*)\}\s*\}",
        re.IGNORECASE,
    )
    page = -1
    commands: list[tuple[int, int, tuple[int, ...]]] = []
    for match in entry.finditer(table):
        command = int(match.group(1), 16)
        count = int(match.group(2))
        payload = tuple(
            int(value, 16)
            for value in re.findall(r"0x([0-9a-f]+)", match.group(3), re.IGNORECASE)
        )[:count]
        if command == 0xFF:
            page = payload[0]
        elif command != 0xFB:
            commands.append((page, command, payload))
    return commands


def upstream_commands(source: str) -> list[tuple[int, int, tuple[int, ...]]]:
    function = source.split(
        "static void nt36672e_1080x2408_60hz_init", 1
    )[1].split("static int nt36672e_power_on", 1)[0]
    token = re.compile(
        r"nt36672e_switch_page\(ctx,\s*0x([0-9a-f]+)\)"
        r"|mipi_dsi_dcs_write_seq_multi\(ctx,\s*0x([0-9a-f]+)(.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )
    page = -1
    commands: list[tuple[int, int, tuple[int, ...]]] = []
    for match in token.finditer(function):
        if match.group(1) is not None:
            page = int(match.group(1), 16)
            continue
        command = int(match.group(2), 16)
        payload = tuple(
            int(value, 16)
            for value in re.findall(r"0x([0-9a-f]+)", match.group(3), re.IGNORECASE)
        )
        if command != 0xFB:
            commands.append((page, command, payload))
    return commands


def overlap(left: Counter[object], right: Counter[object]) -> int:
    return sum((left & right).values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor-git", type=Path, required=True)
    parser.add_argument("--linux", type=Path, required=True)
    args = parser.parse_args()

    panel_source = vendor_source(args.vendor_git)
    dsi_source = git_source(args.vendor_git, VENDOR_DSI_PATH)
    dts_source = git_source(args.vendor_git, VENDOR_DTS_PATH)
    vendor = vendor_commands(panel_source)
    upstream_file = (
        args.linux
        / "drivers/gpu/drm/panel/panel-novatek-nt36672e.c"
    )
    upstream = upstream_commands(upstream_file.read_text(errors="strict"))

    vendor_addresses = Counter((page, command) for page, command, _ in vendor)
    upstream_addresses = Counter((page, command) for page, command, _ in upstream)
    vendor_exact = Counter(vendor)
    upstream_exact = Counter(upstream)

    vendor_pages = sorted({page for page, _, _ in vendor})
    upstream_pages = sorted({page for page, _, _ in upstream})
    address_overlap = overlap(vendor_addresses, upstream_addresses)
    exact_overlap = overlap(vendor_exact, upstream_exact)

    id_contract = (
        "#define LCM_ID_NT36672 (0x8070)",
        "read_reg_v2(0xDB, buffer, 1);",
        "read_reg_v2(0xF4, buffer, 1);",
        "#else\n\treturn 1;\n#endif",
    )
    for needle in id_contract:
        if needle not in panel_source:
            raise SystemExit(f"FAIL vendor ID contract: missing {needle!r}")

    reset_contract = (
        "static void lcm_set_reset_pin(UINT32 value)",
        "DSI_OUTREG32(NULL, DISPSYS_CONFIG_BASE + 0x150, value);",
    )
    for needle in reset_contract:
        if needle not in dsi_source:
            raise SystemExit(f"FAIL vendor reset contract: missing {needle!r}")

    for needle in (
        "pins = <PINMUX_GPIO60__FUNC_GPIO60>;",
        "pins = <PINMUX_GPIO251__FUNC_GPIO251>;",
    ):
        if needle not in dts_source:
            raise SystemExit(f"FAIL vendor bias-pin contract: missing {needle!r}")

    pinctrl = (
        args.linux / "drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h"
    ).read_text(errors="strict")
    if '180, "GPIO180"' not in pinctrl or 'MTK_FUNCTION(1, "LCM_RST")' not in pinctrl:
        raise SystemExit("FAIL mainline pin 180 LCM_RST function is absent")

    print(
        "PASS "
        f"vendor-commands={len(vendor)} upstream-commands={len(upstream)} "
        f"address-overlap={address_overlap} exact-overlap={exact_overlap} "
        "vendor-id=8070 linux-probe=unconditional "
        "reset=mmsys-0x150 bias-gpios=60,251 "
        f"vendor-pages={','.join(f'{page:02x}' for page in vendor_pages)} "
        f"upstream-pages={','.join(f'{page:02x}' for page in upstream_pages)}"
    )


if __name__ == "__main__":
    main()
