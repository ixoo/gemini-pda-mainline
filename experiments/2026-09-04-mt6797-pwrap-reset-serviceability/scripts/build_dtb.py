#!/usr/bin/env python3
"""Apply the sole source-pinned PWRAP reset-cell change to Candidate AW."""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


CONTROL_SHA256 = "e51891c839ab5e40e591346cb78ac66f1c5e0179a1cc30c4a33acf0b9c0667f7"
FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9
TARGET_PATH = "/pwrap@1000d000"
TARGET_PROPERTY = "resets"


class DtbError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def u32(data: bytes | bytearray, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise DtbError("truncated FDT word")
    return struct.unpack_from(">I", data, offset)[0]


def align4(value: int) -> int:
    return (value + 3) & ~3


def cstring(data: bytes | bytearray, offset: int, limit: int) -> tuple[str, int]:
    if offset < 0 or offset >= limit:
        raise DtbError("FDT string offset is outside its block")
    end = data.find(b"\0", offset, limit)
    if end < 0:
        raise DtbError("unterminated FDT string")
    try:
        return bytes(data[offset:end]).decode("ascii"), end + 1
    except UnicodeDecodeError as exc:
        raise DtbError("non-ASCII FDT name") from exc


def properties(data: bytes | bytearray) -> dict[tuple[str, str], tuple[int, bytes]]:
    if len(data) < 40:
        raise DtbError("FDT header is truncated")
    header = struct.unpack_from(">10I", data, 0)
    magic, total, off_struct, off_strings, _, _, _, _, size_strings, size_struct = header
    if magic != FDT_MAGIC or total != len(data):
        raise DtbError("FDT magic or exact total size changed")
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    if not (40 <= off_struct < struct_end <= len(data)):
        raise DtbError("invalid FDT structure bounds")
    if not (40 <= off_strings < strings_end <= len(data)):
        raise DtbError("invalid FDT strings bounds")

    result: dict[tuple[str, str], tuple[int, bytes]] = {}
    stack: list[str] = []
    pos = off_struct
    ended = False
    while pos < struct_end:
        token = u32(data, pos)
        pos += 4
        if token == FDT_BEGIN_NODE:
            name, after = cstring(data, pos, struct_end)
            pos = align4(after)
            stack.append(name)
        elif token == FDT_END_NODE:
            if not stack:
                raise DtbError("unbalanced FDT end-node token")
            stack.pop()
        elif token == FDT_PROP:
            length = u32(data, pos)
            name_offset = u32(data, pos + 4)
            pos += 8
            value_offset = pos
            value_end = pos + length
            if value_end > struct_end:
                raise DtbError("FDT property exceeds structure block")
            name, _ = cstring(data, off_strings + name_offset, strings_end)
            path = "/" + "/".join(part for part in stack if part)
            key = (path, name)
            if key in result:
                raise DtbError(f"duplicate FDT property: {path}:{name}")
            result[key] = (value_offset, bytes(data[value_offset:value_end]))
            pos = align4(value_end)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if stack:
                raise DtbError("FDT ended with open nodes")
            ended = True
            break
        else:
            raise DtbError(f"unknown FDT token: {token}")
    if not ended:
        raise DtbError("FDT end token is absent")
    return result


def transform(data: bytes, check_control_hash: bool = True) -> bytes:
    if check_control_hash and digest(data) != CONTROL_SHA256:
        raise DtbError("control DT SHA-256 changed")
    props = properties(data)
    key = (TARGET_PATH, TARGET_PROPERTY)
    if key not in props:
        raise DtbError("PWRAP resets property is absent")
    offset, value = props[key]
    if value != struct.pack(">II", 3, 64):
        raise DtbError("PWRAP reset tuple is not exact control <3 64>")
    if props.get((TARGET_PATH, "reset-names"), (0, b""))[1] != b"pwrap\0":
        raise DtbError("PWRAP reset-names changed")
    if props.get((TARGET_PATH, "compatible"), (0, b""))[1] != b"mediatek,mt6797-pwrap\0":
        raise DtbError("PWRAP compatible changed")
    if props.get((TARGET_PATH + "/pmic", "compatible"), (0, b""))[1] != b"mediatek,mt6351\0":
        raise DtbError("MT6351 child changed")
    if props.get(("/mmc@11230000", "status"), (0, b""))[1] != b"okay\0":
        raise DtbError("eMMC status is not okay")

    output = bytearray(data)
    output[offset + 4:offset + 8] = struct.pack(">I", 1)
    changed = [index for index, pair in enumerate(zip(data, output)) if pair[0] != pair[1]]
    if changed != [offset + 7]:
        raise DtbError(f"unexpected byte delta: {changed}")
    out_props = properties(output)
    if out_props[key][1] != struct.pack(">II", 3, 1):
        raise DtbError("PWRAP reset tuple was not repaired")
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise SystemExit("error: refusing to overwrite output")
    control = args.control.read_bytes()
    repaired = transform(control)
    args.output.write_bytes(repaired)
    print("validation=exact-pwrap-reset-dtb-transform")
    print(f"control_sha256={digest(control)}")
    print(f"output_sha256={digest(repaired)}")
    print("pwrap_reset_control=3,64")
    print("pwrap_reset_candidate=3,1")
    print("changed_property_count=1")
    print("changed_cell_count=1")
    print("thermal_change=none")
    print("device_action=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
