#!/usr/bin/env python3
"""Analyze the gzip and appended-DTB contract used by Gemini Planet LK."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import struct
import zlib


MAGIC = b"ANDROID!"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
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
LK_GENERIC_DECOMPRESS_LIMIT = 0x1C00000
LK_MT6797_DECOMPRESS_LIMIT = 0x03200000


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def valid_fdt(data: bytes, offset: int, limit: int) -> int | None:
    if offset < 0 or offset + 40 > limit or data[offset : offset + 4] != FDT_MAGIC:
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


def last_fdt(data: bytes, start: int, limit: int) -> tuple[int, int] | None:
    found: tuple[int, int] | None = None
    offset = max(0, start)
    while True:
        offset = data.find(FDT_MAGIC, offset, limit)
        if offset < 0:
            return found
        size = valid_fdt(data, offset, limit)
        if size is not None:
            found = (offset, size)
        offset += 4


def parse(path: pathlib.Path) -> dict[str, int | str]:
    payload = path.read_bytes()
    if len(payload) < 2048 or payload[:8] != MAGIC:
        raise ValueError("not an Android v0 boot image")
    values = struct.unpack_from("<10I", payload, 8)
    result: dict[str, int | str] = dict(zip(PAGE_FIELDS, values, strict=True))
    page = int(result["page_size"])
    kernel_offset = page
    kernel_end = kernel_offset + int(result["kernel_size"])
    if kernel_end > len(payload):
        raise ValueError("kernel payload exceeds image")
    kernel = payload[kernel_offset:kernel_end]
    cmdline = (payload[64:576] + payload[608:1632]).split(b"\0", 1)[0].decode(
        "ascii", "replace"
    )
    result.update(
        image_size=len(payload),
        image_sha256=hashlib.sha256(payload).hexdigest(),
        kernel_offset=kernel_offset,
        kernel_gzip_magic="yes" if kernel[:2] == b"\x1f\x8b" else "no",
        kernel_addr_aligned_512k="yes"
        if (int(result["kernel_addr"]) & 0x7FFFF) == 0
        else "no",
        cmdline=cmdline,
        bootopt_64="yes"
        if re.search(r"(?:^|\s)bootopt=[^ ]*64", cmdline)
        else "no",
        lk_generic_decompress_limit=LK_GENERIC_DECOMPRESS_LIMIT,
        lk_mt6797_decompress_limit=LK_MT6797_DECOMPRESS_LIMIT,
    )
    if kernel[:2] == b"\x1f\x8b":
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            decompressed = decompressor.decompress(kernel)
        except zlib.error as exc:
            raise ValueError(f"gzip kernel stream is invalid: {exc}") from exc
        unused = decompressor.unused_data
        result.update(
            gzip_stream_size=len(kernel) - len(unused),
            decompressed_kernel_size=len(decompressed),
            decompressed_within_mt6797_limit="yes"
            if len(decompressed) <= LK_MT6797_DECOMPRESS_LIMIT
            else "no",
        )
    else:
        result.update(
            gzip_stream_size="not_checked",
            decompressed_kernel_size="not_checked",
            decompressed_within_mt6797_limit="not_checked",
        )
    fdt = last_fdt(kernel, 0, len(kernel))
    if fdt is None:
        result.update(appended_dtb_offset="absent", appended_dtb_size="absent")
    else:
        gzip_stream_size = result.get("gzip_stream_size")
        result.update(
            appended_dtb_offset=kernel_offset + fdt[0],
            appended_dtb_size=fdt[1],
            fdt_starts_at_gzip_stream_end="yes"
            if isinstance(gzip_stream_size, int) and gzip_stream_size == fdt[0]
            else "no",
        )
    result["header_dt_size"] = int(result["dt_size"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=pathlib.Path)
    args = parser.parse_args()
    for key, value in parse(args.image).items():
        print(f"{key}={value}")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
