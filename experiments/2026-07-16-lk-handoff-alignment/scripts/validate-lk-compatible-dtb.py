#!/usr/bin/env python3
"""Fail closed unless an LK-compatible DTB has exactly the allowed delta."""

from __future__ import annotations

import argparse
import copy
import pathlib
import struct
import sys


FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


def align4(value: int) -> int:
    return (value + 3) & ~3


def cstring(data: bytes, offset: int, limit: int) -> tuple[str, int]:
    end = data.find(b"\0", offset, limit)
    if end < 0:
        raise ValueError("unterminated FDT string")
    try:
        value = data[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("non-ASCII FDT name") from exc
    return value, end + 1


def parse_fdt(
    path: pathlib.Path,
) -> tuple[dict[str, dict[str, bytes]], tuple[tuple[int, int], ...], int]:
    data = path.read_bytes()
    if len(data) < 40:
        raise ValueError(f"{path}: truncated FDT header")
    fields = struct.unpack_from(">10I", data)
    magic, total, off_struct, off_strings, off_reserve, version, last, boot_cpu, size_strings, size_struct = fields
    if magic != FDT_MAGIC:
        raise ValueError(f"{path}: bad FDT magic")
    if total != len(data) or total < 40:
        raise ValueError(f"{path}: invalid FDT total size")
    if not 16 <= last <= version <= 17:
        raise ValueError(f"{path}: unsupported FDT version {version}/{last}")
    if off_struct + size_struct > total or off_strings + size_strings > total:
        raise ValueError(f"{path}: FDT block exceeds total size")
    if off_reserve < 40 or off_reserve % 8:
        raise ValueError(f"{path}: invalid FDT reservation-map offset")

    reservations: list[tuple[int, int]] = []
    reserve_pos = off_reserve
    reserve_limit = min(
        offset for offset in (off_struct, off_strings, total) if offset >= off_reserve
    )
    while reserve_pos + 16 <= reserve_limit:
        address, size = struct.unpack_from(">2Q", data, reserve_pos)
        reserve_pos += 16
        if address == 0 and size == 0:
            break
        reservations.append((address, size))
    else:
        raise ValueError(f"{path}: unterminated FDT reservation map")

    trees: dict[str, dict[str, bytes]] = {}
    stack: list[str] = []
    pos = off_struct
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    saw_end = False
    while pos + 4 <= struct_end:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            name, pos = cstring(data, pos, struct_end)
            pos = align4(pos)
            if not stack:
                if name:
                    raise ValueError(f"{path}: root node has a name")
                node_path = "/"
            else:
                node_path = stack[-1].rstrip("/") + "/" + name
            if node_path in trees:
                raise ValueError(f"{path}: duplicate node {node_path}")
            trees[node_path] = {}
            stack.append(node_path)
        elif token == FDT_END_NODE:
            if not stack:
                raise ValueError(f"{path}: unmatched FDT_END_NODE")
            stack.pop()
        elif token == FDT_PROP:
            if not stack or pos + 8 > struct_end:
                raise ValueError(f"{path}: malformed FDT property")
            length, name_offset = struct.unpack_from(">2I", data, pos)
            pos += 8
            if pos + length > struct_end or name_offset >= size_strings:
                raise ValueError(f"{path}: FDT property exceeds its block")
            name, _ = cstring(data, off_strings + name_offset, strings_end)
            if name in trees[stack[-1]]:
                raise ValueError(f"{path}: duplicate property {stack[-1]}:{name}")
            trees[stack[-1]][name] = data[pos : pos + length]
            pos = align4(pos + length)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if stack:
                raise ValueError(f"{path}: FDT ended inside {stack[-1]}")
            if pos != struct_end:
                raise ValueError(f"{path}: trailing bytes after FDT_END")
            saw_end = True
            break
        else:
            raise ValueError(f"{path}: unknown FDT token {token}")
    if not saw_end:
        raise ValueError(f"{path}: missing FDT_END")
    return trees, tuple(reservations), boot_cpu


def cells(*values: int) -> bytes:
    return struct.pack(">" + "I" * len(values), *values)


def string(value: str) -> bytes:
    return value.encode("ascii") + b"\0"


def require_prop(
    tree: dict[str, dict[str, bytes]], path: str, name: str, value: bytes
) -> None:
    if path not in tree:
        raise ValueError(f"base DTB is missing required node {path}")
    actual = tree[path].get(name)
    if actual != value:
        raise ValueError(f"base DTB has unexpected {path}:{name}")


def validate(
    base_path: pathlib.Path,
    candidate_path: pathlib.Path,
    with_simplefb: bool,
    with_usb_gadget: bool,
) -> tuple[int, int]:
    base, base_reservations, base_boot_cpu = parse_fdt(base_path)
    candidate, candidate_reservations, candidate_boot_cpu = parse_fdt(candidate_path)
    if candidate_reservations != base_reservations:
        raise ValueError("DTB reservation map changed")
    if candidate_boot_cpu != base_boot_cpu:
        raise ValueError("DTB boot_cpuid_phys changed")
    require_prop(base, "/", "model", string("Planet Computers Gemini PDA"))
    require_prop(
        base,
        "/",
        "compatible",
        string("planet,gemini-pda") + string("mediatek,mt6797"),
    )
    scp_share = "/reserved-memory/reserve-memory-scp_share"
    require_prop(base, scp_share, "compatible", string("mediatek,reserve-memory-scp_share"))
    require_prop(base, scp_share, "no-map", b"")
    require_prop(base, scp_share, "size", cells(0, 0x01000000))
    require_prop(base, scp_share, "alignment", cells(0, 0x01000000))
    require_prop(base, scp_share, "alloc-ranges", cells(0, 0x40000000, 0, 0x50000000))
    chosen = "/chosen"
    framebuffer = "/chosen/framebuffer@7dfb0000"
    if chosen not in base:
        raise ValueError("base DTB is missing /chosen")
    if framebuffer in base:
        raise ValueError(f"base DTB unexpectedly already has {framebuffer}")
    for prop in ("#address-cells", "#size-cells", "ranges"):
        if prop in base[chosen]:
            raise ValueError(f"base DTB unexpectedly already has /chosen:{prop}")

    expected = copy.deepcopy(base)
    cpu_frequencies = {
        **{f"/cpus/cpu@{cpu:x}": 0x52E8F9C0 for cpu in range(4)},
        **{f"/cpus/cpu@{cpu:x}": 0x743AA380 for cpu in range(0x100, 0x104)},
        **{f"/cpus/cpu@{cpu:x}": 0x88601C00 for cpu in range(0x200, 0x202)},
    }
    for node, frequency in cpu_frequencies.items():
        if node not in expected:
            raise ValueError(f"base DTB is missing required node {node}")
        if "clock-frequency" in expected[node]:
            raise ValueError(f"base DTB unexpectedly already has {node}:clock-frequency")
        expected[node]["clock-frequency"] = cells(frequency)

    reserved_compatibles = {
        "/reserved-memory/memory@44600000": "mediatek,mt6797-atf-reserved-memory",
        "/reserved-memory/memory@44610000": "mediatek,mt6797-atf-ramdump-memory",
        "/reserved-memory/memory@44640000": "mediatek,cache-dump-memory",
    }
    for node, compatible in reserved_compatibles.items():
        if node not in expected:
            raise ValueError(f"base DTB is missing required node {node}")
        if "compatible" in expected[node]:
            raise ValueError(f"base DTB unexpectedly already has {node}:compatible")
        expected[node]["compatible"] = string(compatible)

    scp = "/scp@10020000"
    if scp in expected:
        raise ValueError(f"base DTB unexpectedly already has {scp}")
    expected[scp] = {
        "compatible": string("mediatek,scp"),
        "reg": cells(
            0, 0x10020000, 0, 0x00080000,
            0, 0x100A0000, 0, 0x00001000,
            0, 0x100A4000, 0, 0x00001000,
        ),
        "interrupts": cells(0, 199, 4),
        "status": string("disabled"),
    }

    if with_usb_gadget:
        usb_nodes = (
            "/t-phy@11290000",
            "/t-phy@11290000/usb-phy@11290800",
            "/usb@11271000",
        )
        for node in usb_nodes:
            require_prop(base, node, "status", string("disabled"))
            expected[node]["status"] = string("okay")

        u2_phy = "/t-phy@11290000/usb-phy@11290800"
        require_prop(base, u2_phy, "clock-names", string("ref"))
        require_prop(base, u2_phy, "mediatek,force-b-session-valid", b"")
        if len(base[u2_phy].get("clocks", b"")) != 4:
            raise ValueError("base DTB does not use one clock for the USB2 PHY")

        ssusb = "/usb@11271000"
        require_prop(base, ssusb, "dr_mode", string("peripheral"))
        require_prop(base, ssusb, "maximum-speed", string("high-speed"))
        if len(base[ssusb].get("phys", b"")) != 8:
            raise ValueError("base DTB does not use exactly one two-cell USB PHY")
        if len(base[ssusb].get("assigned-clocks", b"")) != 8:
            raise ValueError("base DTB is missing the SSUSB assigned clock")
        if len(base[ssusb].get("assigned-clock-parents", b"")) != 8:
            raise ValueError("base DTB is missing the SSUSB assigned clock parent")
        require_prop(base, "/t-phy@11290000/usb-phy@11290900", "status", string("disabled"))
        require_prop(base, "/usb@11271000/usb@11270000", "status", string("disabled"))

    if with_simplefb:
        expected[chosen]["#address-cells"] = cells(2)
        expected[chosen]["#size-cells"] = cells(2)
        expected[chosen]["ranges"] = b""
        expected[framebuffer] = {
            "compatible": string("simple-framebuffer"),
            "reg": cells(0, 0x7DFB0000, 0, 0x01F90000),
            "width": cells(1080),
            "height": cells(2160),
            "stride": cells(4352),
            "format": string("a8r8g8b8"),
        }

    if candidate != expected:
        base_nodes = set(expected)
        candidate_nodes = set(candidate)
        details: list[str] = []
        for path in sorted(base_nodes - candidate_nodes):
            details.append(f"missing node {path}")
        for path in sorted(candidate_nodes - base_nodes):
            details.append(f"unexpected node {path}")
        for path in sorted(base_nodes & candidate_nodes):
            expected_props = expected[path]
            actual_props = candidate[path]
            for prop in sorted(set(expected_props) - set(actual_props)):
                details.append(f"missing property {path}:{prop}")
            for prop in sorted(set(actual_props) - set(expected_props)):
                details.append(f"unexpected property {path}:{prop}")
            for prop in sorted(set(expected_props) & set(actual_props)):
                if expected_props[prop] != actual_props[prop]:
                    details.append(f"changed property {path}:{prop}")
        raise ValueError("DTB delta is not allowlisted: " + "; ".join(details[:20]))
    added_properties = sum(
        len(expected[path]) - len(base.get(path, {})) for path in expected
    )
    return len(expected) - len(base), added_properties


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--with-simplefb", action="store_true")
    parser.add_argument("--with-usb-gadget", action="store_true")
    args = parser.parse_args()
    try:
        added_nodes, added_properties = validate(
            args.base,
            args.candidate,
            args.with_simplefb,
            args.with_usb_gadget,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=lk-compatible-dtb-allow-delta")
    print(f"simplefb={'yes' if args.with_simplefb else 'no'}")
    print(f"usb_gadget={'yes' if args.with_usb_gadget else 'no'}")
    print(f"added_nodes={added_nodes}")
    print(f"added_properties={added_properties}")
    print("unexpected_delta=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
