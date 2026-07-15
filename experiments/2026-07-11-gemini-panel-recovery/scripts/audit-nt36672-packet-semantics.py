#!/usr/bin/env python3
"""Audit the MT6797 vendor packet rule against the Gemini mainline patch.

The pinned vendor DSI helper emits DCS packets below 0xb0 and generic packets
at or above 0xb0.  This audit keeps that transport distinction reviewable and
checks that the generated Gemini init function follows the same rule.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess


PANEL_PATH = (
    "drivers/misc/mediatek/lcm/"
    "aeon_nt36672_fhd_dsi_vdo_x600_xinli/"
    "aeon_nt36672_fhd_dsi_vdo_x600_xinli.c"
)
DSI_PATH = "drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c"


def git_show(repository: Path, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), "show", f"HEAD:{path}"], text=True
    )


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_generator() -> object:
    path = Path(__file__).with_name("emit-gemini-panel-init.py")
    spec = importlib.util.spec_from_file_location("gemini_panel_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CALL = re.compile(
    r"nt36672e_gemini_write_cmd\(ctx,\s*\(const u8\[\]\)\s*\{"
    r"(?P<body>.*?)\}\s*,\s*(?P<length>\d+)\);",
    re.S,
)


def calls(source: str) -> list[tuple[int, tuple[int, ...]]]:
    result: list[tuple[int, tuple[int, ...]]] = []
    for match in CALL.finditer(source):
        values = [
            int(value, 16)
            for value in re.findall(r"0x([0-9a-f]+)", match.group("body"), re.I)
        ]
        length = int(match.group("length"))
        if len(values) != length:
            raise ValueError(f"array length mismatch: {len(values)} != {length}")
        result.append((values[0], tuple(values[1:])))
    return result


def patch_function(patch: str) -> str:
    start = patch.index(
        "+static void nt36672e_gemini_1080x2160_init"
    )
    end = patch.index("+static void nt36672e_delay_ms", start)
    return "\n".join(
        line[1:] for line in patch[start:end].splitlines() if line.startswith("+")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor-git", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    args = parser.parse_args()

    panel = git_show(args.vendor_git, PANEL_PATH)
    dsi = git_show(args.vendor_git, DSI_PATH)
    patch = args.patch.read_text()
    function = patch_function(patch)
    generator = load_generator()
    generated = generator.emit(panel)

    if dsi.count("if (cmd < 0xB0)") != 2:
        raise SystemExit("vendor DSI helper does not have both mode packet branches")
    if "DSI_DCS_LONG_PACKET_ID" not in dsi or "DSI_GERNERIC_LONG_PACKET_ID" not in dsi:
        raise SystemExit("vendor DSI helper packet IDs are incomplete")

    candidate = calls(function)
    expected = calls(generated)
    if candidate != expected:
        raise SystemExit("candidate command sequence differs from generator output")
    if "nt36672e_switch_page(ctx" in function or "nt36672e_enable_reload_cmds(ctx" in function:
        raise SystemExit("Gemini sequence bypasses the vendor packet selector")
    if "if (data[0] >= 0xb0)" not in patch:
        raise SystemExit("candidate packet selector is missing")
    if "mipi_dsi_generic_write_multi(ctx, data, len);" not in patch:
        raise SystemExit("candidate generic write path is missing")

    generic = [command for command, _ in candidate if command >= 0xB0]
    dcs = [command for command, _ in candidate if command < 0xB0]
    print("validation=gemini-nt36672-packet-semantics")
    print("schema=1")
    print(f"vendor_commit={subprocess.check_output(['git', '-C', str(args.vendor_git), 'rev-parse', 'HEAD'], text=True).strip()}")
    print(f"vendor_panel_blob_sha256={sha256(panel)}")
    print(f"vendor_dsi_blob_sha256={sha256(dsi)}")
    print(f"patch_sha256={sha256(patch)}")
    print(f"generator_sha256={sha256(Path(__file__).with_name('emit-gemini-panel-init.py').read_text())}")
    print("vendor_rule=cmd<0xb0:DCS;cmd>=0xb0:generic")
    print("candidate_selector=data[0]<0xb0:DCS;data[0]>=0xb0:generic")
    print(f"candidate_commands={len(candidate)}")
    print(f"candidate_generic_commands={len(generic)}")
    print(f"candidate_dcs_commands={len(dcs)}")
    print("candidate_sequence_matches_generator=true")
    print("decision=preserve_vendor_generic_packet_boundary_before_hardware_test")


if __name__ == "__main__":
    main()
