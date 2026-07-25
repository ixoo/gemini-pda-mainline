#!/usr/bin/env python3
"""Require exact AF plus the hardware-passed AD simplefb observation path."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import pathlib
import stat
import struct
import sys


AF_DTB_SHA256 = "3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b"
AD_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
FDT_PARSER_SHA256 = "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"

CHOSEN = "/chosen"
FRAMEBUFFER = "/chosen/framebuffer@7dfb0000"
LK_FRAMEBUFFER = "/reserved-memory/mblock-3-framebuffer"
INFRA_PROVIDER = "/syscon@10001000"
TOP_PROVIDER = "/topckgen@10000000"
CLK_INFRA_DISP_PWM = 45
CLK_TOP_MUX_MM = 6
FRAMEBUFFER_START = 0x7DFB0000
FRAMEBUFFER_SIZE = 0x01F90000
FRAMEBUFFER_END = FRAMEBUFFER_START + FRAMEBUFFER_SIZE


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_regular_dtb(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size == 0:
        raise ValueError(f"{label} DTB is missing, empty, or unsafe")


def load_fdt_parser() -> object:
    experiments = pathlib.Path(__file__).resolve().parents[2]
    source = (
        experiments
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    if digest(source) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("gemini_ag_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load FDT parser from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provider_phandle(fdt: object, tree: dict, path: str, compatible: bytes) -> int:
    fdt.require_prop(tree, path, "compatible", compatible)
    fdt.require_prop(tree, path, "#clock-cells", fdt.cells(1))
    raw = tree[path].get("phandle")
    if raw is None or len(raw) != 4:
        raise ValueError(f"{path} lacks exactly one phandle cell")
    value = struct.unpack(">I", raw)[0]
    if value == 0:
        raise ValueError(f"{path} has phandle zero")
    return value


def phandle_map(tree: dict) -> dict[int, str]:
    handles: dict[int, str] = {}
    for path, props in tree.items():
        values: list[int] = []
        for name in ("phandle", "linux,phandle"):
            raw = props.get(name)
            if raw is None:
                continue
            if len(raw) != 4:
                raise ValueError(f"{path}:{name} is not one cell")
            values.append(struct.unpack(">I", raw)[0])
        if len(set(values)) > 1:
            raise ValueError(f"{path} has conflicting phandle aliases")
        if not values:
            continue
        value = values[0]
        if value == 0 or (value in handles and handles[value] != path):
            raise ValueError(f"invalid or duplicate phandle 0x{value:x} at {path}")
        handles[value] = path
    return handles


def reject_static_framebuffer_reservation(tree: dict) -> None:
    for path, props in tree.items():
        compatible = props.get("compatible", b"").split(b"\0")
        if b"mediatek,framebuffer" in compatible:
            raise ValueError(f"static MediaTek framebuffer reservation at {path}")
        if not path.startswith("/reserved-memory/"):
            continue
        raw = props.get("reg")
        if raw is None:
            continue
        if len(raw) % 16:
            raise ValueError(f"reserved-memory reg width is unexpected at {path}")
        for offset in range(0, len(raw), 16):
            address_hi, address_lo, size_hi, size_lo = struct.unpack_from(
                ">4I", raw, offset
            )
            address = address_hi << 32 | address_lo
            size = size_hi << 32 | size_lo
            end = address + size
            if end > 1 << 64:
                raise ValueError(f"reserved-memory range overflows at {path}")
            if address < FRAMEBUFFER_END and end > FRAMEBUFFER_START:
                raise ValueError(f"static reserved-memory overlaps framebuffer at {path}")


def describe_delta(expected: dict, actual: dict) -> str:
    details: list[str] = []
    for path in sorted(set(expected) | set(actual)):
        if path not in expected:
            details.append(f"unexpected node {path}")
            continue
        if path not in actual:
            details.append(f"missing node {path}")
            continue
        for prop in sorted(set(expected[path]) | set(actual[path])):
            if prop not in expected[path]:
                details.append(f"unexpected property {path}:{prop}")
            elif prop not in actual[path]:
                details.append(f"missing property {path}:{prop}")
            elif expected[path][prop] != actual[path][prop]:
                details.append(f"changed property {path}:{prop}")
    return "; ".join(details[:24])


def validate(
    af_path: pathlib.Path, ad_path: pathlib.Path, candidate_path: pathlib.Path
) -> tuple[int, int]:
    require_regular_dtb(af_path, "Candidate AF")
    require_regular_dtb(ad_path, "Candidate AD")
    require_regular_dtb(candidate_path, "Candidate AG")
    if digest(af_path) != AF_DTB_SHA256:
        raise ValueError("exact Candidate AF DTB changed")
    if digest(ad_path) != AD_DTB_SHA256:
        raise ValueError("exact hardware-passed Candidate AD DTB changed")

    fdt = load_fdt_parser()
    af, af_reservations, af_boot_cpu = fdt.parse_fdt(af_path)
    ad, ad_reservations, ad_boot_cpu = fdt.parse_fdt(ad_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )

    if candidate_reservations != af_reservations:
        raise ValueError("Candidate AG changed AF's FDT reservation map")
    if candidate_boot_cpu != af_boot_cpu:
        raise ValueError("Candidate AG changed AF's boot_cpuid_phys")
    if ad_reservations != af_reservations or ad_boot_cpu != af_boot_cpu:
        raise ValueError("AD simplefb oracle does not share AF's FDT header contract")
    if LK_FRAMEBUFFER in af or LK_FRAMEBUFFER in ad or LK_FRAMEBUFFER in candidate:
        raise ValueError("LK runtime framebuffer reservation was added statically")
    for label, tree in (("AF", af), ("AD", ad), ("AG", candidate)):
        try:
            reject_static_framebuffer_reservation(tree)
        except ValueError as exc:
            raise ValueError(f"{label}: {exc}") from exc
    af_handles = phandle_map(af)
    if phandle_map(candidate) != af_handles:
        raise ValueError("Candidate AG changed AF's global phandle map")
    phandle_map(ad)

    af_infra = provider_phandle(
        fdt,
        af,
        INFRA_PROVIDER,
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    af_top = provider_phandle(
        fdt, af, TOP_PROVIDER, fdt.string("mediatek,mt6797-topckgen")
    )
    ad_infra = provider_phandle(
        fdt,
        ad,
        INFRA_PROVIDER,
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    ad_top = provider_phandle(
        fdt, ad, TOP_PROVIDER, fdt.string("mediatek,mt6797-topckgen")
    )

    ad_framebuffer = {
        "compatible": fdt.string("simple-framebuffer"),
        "reg": fdt.cells(0, FRAMEBUFFER_START, 0, FRAMEBUFFER_SIZE),
        "width": fdt.cells(1080),
        "height": fdt.cells(2160),
        "stride": fdt.cells(4352),
        "format": fdt.string("a8r8g8b8"),
        "clocks": fdt.cells(
            ad_infra,
            CLK_INFRA_DISP_PWM,
            ad_top,
            CLK_TOP_MUX_MM,
        ),
    }
    if ad.get(FRAMEBUFFER) != ad_framebuffer:
        raise ValueError("AD simplefb node is not the exact hardware-passed oracle")
    ad_chosen_delta = {
        "#address-cells": fdt.cells(2),
        "#size-cells": fdt.cells(2),
        "ranges": b"",
    }
    for prop, value in ad_chosen_delta.items():
        if ad.get(CHOSEN, {}).get(prop) != value:
            raise ValueError(f"AD /chosen oracle differs: {prop}")

    if FRAMEBUFFER in af:
        raise ValueError("AF unexpectedly already contains the simplefb node")
    for prop in ad_chosen_delta:
        if prop in af.get(CHOSEN, {}):
            raise ValueError(f"AF unexpectedly already contains /chosen:{prop}")

    expected = copy.deepcopy(af)
    expected[CHOSEN].update(ad_chosen_delta)
    expected[FRAMEBUFFER] = {
        **ad_framebuffer,
        "clocks": fdt.cells(
            af_infra,
            CLK_INFRA_DISP_PWM,
            af_top,
            CLK_TOP_MUX_MM,
        ),
    }
    if candidate != expected:
        raise ValueError(
            "Candidate AG DT delta is not exact AF plus AD simplefb: "
            + describe_delta(expected, candidate)
        )

    visible_bytes = 4352 * 2160
    if (
        1080 * 4 > 4352
        or visible_bytes != 0x008F7000
        or visible_bytes > FRAMEBUFFER_SIZE
        or FRAMEBUFFER_END != 0x7FF40000
    ):
        raise ValueError("simplefb geometry exceeds its exact resource")
    return af_infra, af_top


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--af", required=True, type=pathlib.Path)
    parser.add_argument("--ad", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        infra_phandle, top_phandle = validate(args.af, args.ad, args.candidate)
    except (OSError, RuntimeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-ag-simplefb-dtb-delta")
    print(f"af_dtb_sha256={AF_DTB_SHA256}")
    print(f"ad_dtb_sha256={AD_DTB_SHA256}")
    print("changed_nodes=/chosen/framebuffer@7dfb0000")
    print("changed_chosen_properties=#address-cells,#size-cells,ranges")
    print("framebuffer_base=0x7dfb0000")
    print("framebuffer_size=0x01f90000")
    print("framebuffer_geometry=1080x2160")
    print("framebuffer_stride=4352")
    print("framebuffer_format=a8r8g8b8")
    print(f"infra_provider_path={INFRA_PROVIDER}")
    print(f"infra_provider_phandle={infra_phandle}")
    print(f"infra_clock_id={CLK_INFRA_DISP_PWM}")
    print(f"top_provider_path={TOP_PROVIDER}")
    print(f"top_provider_phandle={top_phandle}")
    print(f"top_clock_id={CLK_TOP_MUX_MM}")
    print("static_lk_framebuffer_reservation=absent")
    print("unexpected_semantic_delta=none")
    print("framebuffer_write=none")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
