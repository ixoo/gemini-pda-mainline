#!/usr/bin/env python3
"""Print a redacted Android boot-image v0 contract without extracting payloads."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import struct
import sys


PAGE_FIELDS = (
    "kernel_size",
    "kernel_addr",
    "ramdisk_size",
    "ramdisk_addr",
    "second_size",
    "second_addr",
    "tags_addr",
    "page_size",
    "dt_size",
    "unused",
)


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def redact(command_line: str) -> str:
    command_line = re.sub(
        r"(?i)(androidboot\.)?(serialno|imei|meid|cid|wifi_mac|bt_mac|macaddr)=[^ ]+",
        lambda match: f"{match.group(1) or ''}{match.group(2)}=<redacted>",
        command_line,
    )
    return re.sub(r"(?i)([0-9a-f]{2}:){5}[0-9a-f]{2}", "<redacted-mac>", command_line)


def valid_fdt(data: bytes, offset: int, limit: int) -> int | None:
    """Return a valid FDT size, rejecting random magic-like byte sequences."""

    if offset < 0 or offset + 40 > limit or data[offset : offset + 4] != b"\xd0\x0d\xfe\xed":
        return None
    totalsize = int.from_bytes(data[offset + 4 : offset + 8], "big")
    version = int.from_bytes(data[offset + 20 : offset + 24], "big")
    last_comp_version = int.from_bytes(data[offset + 24 : offset + 28], "big")
    off_struct = int.from_bytes(data[offset + 8 : offset + 12], "big")
    off_strings = int.from_bytes(data[offset + 12 : offset + 16], "big")
    size_strings = int.from_bytes(data[offset + 32 : offset + 36], "big")
    size_struct = int.from_bytes(data[offset + 36 : offset + 40], "big")
    if not 40 <= totalsize <= limit - offset:
        return None
    if not 16 <= version <= 17 or not 16 <= last_comp_version <= version:
        return None
    if off_struct + size_struct > totalsize or off_strings + size_strings > totalsize:
        return None
    return totalsize


def find_fdt(data: bytes, start: int, limit: int) -> tuple[int, int] | None:
    """Find the last structurally valid FDT in a bounded payload region."""

    found: tuple[int, int] | None = None
    offset = max(0, start)
    while True:
        offset = data.find(b"\xd0\x0d\xfe\xed", offset, limit)
        if offset < 0:
            return found
        size = valid_fdt(data, offset, limit)
        if size is not None:
            found = (offset, size)
        offset += 4


def parse(path: pathlib.Path) -> dict[str, object]:
    payload = path.read_bytes()
    header = payload[:2048]
    if header[:8] != b"ANDROID!":
        raise ValueError("not an Android boot image")
    values = struct.unpack_from("<10I", header, 8)
    result: dict[str, object] = dict(zip(PAGE_FIELDS, values, strict=True))
    name = header[48:64].split(b"\0", 1)[0].decode("ascii", "replace")
    command_line = header[64:576] + header[608:1632]
    result["name"] = name
    result["cmdline"] = redact(command_line.split(b"\0", 1)[0].decode("ascii", "replace"))
    result["header_id_present"] = any(header[576:608])
    page = int(result["page_size"])
    kernel_offset = page
    ramdisk_offset = align(kernel_offset + int(result["kernel_size"]), page)
    second_offset = align(ramdisk_offset + int(result["ramdisk_size"]), page)
    dt_offset = align(second_offset + int(result["second_size"]), page)
    end_offset = align(dt_offset + int(result["dt_size"]), page)
    result.update(
        kernel_offset=kernel_offset,
        ramdisk_offset=ramdisk_offset,
        second_offset=second_offset,
        dt_offset=dt_offset,
        end_offset=end_offset,
        file_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    result["header_dtb_offset"] = "absent"
    result["header_dtb_size"] = "absent"
    if int(result["dt_size"]):
        result["header_dtb_offset"] = dt_offset
        result["header_dtb_size"] = int(result["dt_size"])
        result["appended_dtb_offset"] = "absent"
        result["appended_dtb_size"] = "absent"
    else:
        appended = find_fdt(payload, kernel_offset, kernel_offset + int(result["kernel_size"]))
        if appended is None:
            result["appended_dtb_offset"] = "absent"
            result["appended_dtb_size"] = "absent"
        else:
            result["appended_dtb_offset"], result["appended_dtb_size"] = appended
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=pathlib.Path)
    args = parser.parse_args()
    if not args.image.is_file():
        print(f"error: image not found: {args.image}", file=sys.stderr)
        return 2
    try:
        result = parse(args.image)
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"path={args.image}")
    for key in (
        "file_size",
        "sha256",
        "name",
        "kernel_size",
        "kernel_addr",
        "kernel_offset",
        "ramdisk_size",
        "ramdisk_addr",
        "ramdisk_offset",
        "second_size",
        "second_addr",
        "second_offset",
        "dt_size",
        "dt_offset",
        "header_dtb_offset",
        "header_dtb_size",
        "appended_dtb_offset",
        "appended_dtb_size",
        "end_offset",
        "page_size",
        "header_id_present",
        "cmdline",
    ):
        print(f"{key}={result[key]}")
    if int(result["end_offset"]) > int(result["file_size"]):
        print("layout=truncated", file=sys.stderr)
        return 1
    print("layout=complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
