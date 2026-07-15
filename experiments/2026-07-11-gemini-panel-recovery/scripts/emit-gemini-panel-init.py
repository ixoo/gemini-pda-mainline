#!/usr/bin/env python3
"""Emit the mainline DSI function for the Gemini NT36672 panel table.

The source is intentionally read from the pinned vendor Git object rather
than from a working tree.  Vendor page/reload commands become the shared
NT36672E helper calls; the vendor's DCS sleep/display commands are omitted
because the mainline framework owns them and supplies their delays from the
panel descriptor.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess


VENDOR_PATH = (
    "drivers/misc/mediatek/lcm/"
    "aeon_nt36672_fhd_dsi_vdo_x600_xinli/"
    "aeon_nt36672_fhd_dsi_vdo_x600_xinli.c"
)


def read_vendor(repository: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "show", f"HEAD:{VENDOR_PATH}"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def commands(source: str) -> list[tuple[int, int, tuple[int, ...]]]:
    table = source.split("static struct LCM_setting_table init_setting[] = {", 1)[1]
    table = table.split("#else", 1)[0]
    entry = re.compile(
        r"\{\s*0x([0-9a-f]+)\s*,\s*(\d+)\s*,\s*\{([^}]*)\}\s*\}",
        re.IGNORECASE,
    )
    page = -1
    result: list[tuple[int, int, tuple[int, ...]]] = []
    for match in entry.finditer(table):
        command = int(match.group(1), 16)
        count = int(match.group(2))
        payload = tuple(
            int(value, 16)
            for value in re.findall(r"0x([0-9a-f]+)", match.group(3), re.IGNORECASE)
        )[:count]
        if command == 0xFF:
            if len(payload) != 1:
                raise ValueError("page selection must contain one byte")
            page = payload[0]
        elif command == 0xFB:
            if payload != (0x01,):
                raise ValueError("unexpected NT36672 reload value")
        elif page == 0x10 and command in (0x11, 0x29) and payload == (0x00,):
            # The shared driver sends these through the DCS helpers so its
            # descriptor-selected delays remain visible and reviewable.
            continue
        elif command >= 0xFF00:
            continue
        else:
            result.append((page, command, payload))
    if page < 0 or len(result) != 165:
        raise ValueError(f"unexpected table shape: page={page} writes={len(result)}")
    return result


def emit(source: str) -> str:
    lines = [
        "/*",
        " * Generated from the pinned Planet vendor object by",
        " * experiments/2026-07-11-gemini-panel-recovery/scripts/",
        " * emit-gemini-panel-init.py. Keep the source commit in the experiment",
        " * record; do not hand-edit this command sequence.",
        " */",
        "static void nt36672e_gemini_1080x2160_init(struct mipi_dsi_multi_context *ctx)",
        "{",
    ]
    page = None
    for command_page, command, payload in commands(source):
        if command_page != page:
            page = command_page
            lines.extend(
                [
                    f"\tnt36672e_gemini_write_cmd(ctx, (const u8[]){{ 0xff, 0x{page:02x} }}, 2);",
                    "\tnt36672e_gemini_write_cmd(ctx, (const u8[]){ 0xfb, 0x01 }, 2);",
                ]
            )
        values = [f"0x{value:02x}" for value in (command, *payload)]
        if len(values) <= 8:
            data = ", ".join(values)
            lines.append(
                f"\tnt36672e_gemini_write_cmd(ctx, (const u8[]){{ {data} }}, "
                f"{len(payload) + 1});"
            )
            continue

        lines.append("\tnt36672e_gemini_write_cmd(ctx, (const u8[]) {")
        for offset in range(0, len(values), 8):
            chunk = ", ".join(values[offset : offset + 8])
            suffix = "," if offset + 8 < len(values) else ""
            lines.append(f"\t\t{chunk}{suffix}")
        lines.append(f"\t}}, {len(payload) + 1});")
    lines.extend(["}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor-git", type=Path, required=True)
    args = parser.parse_args()
    print(emit(read_vendor(args.vendor_git)), end="")


if __name__ == "__main__":
    main()
