#!/usr/bin/env python3
"""Validate the Gemini MediaTek logo container without extracting artwork."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys
import zlib
from dataclasses import dataclass


OUTER_MAGIC = 0x58881688
EXTENDED_MAGIC = 0x58891689
OUTER_HEADER_SIZE = 512


@dataclass(frozen=True)
class Slot:
    name: str
    width: int
    height: int

    @property
    def raw_size(self) -> int:
        return self.width * self.height * 4


SLOTS = (
    Slot("uboot", 2160, 1080),
    Slot("battery", 1920, 1080),
    Slot("low_battery", 2160, 1080),
    Slot("charger_ov", 2160, 1080),
    *(Slot(f"num_{digit}", 84, 121) for digit in range(10)),
    Slot("num_percent", 108, 121),
    *(Slot(f"bat_animation_{frame:02d}", 304, 52) for frame in range(1, 11)),
    *(Slot(f"bat_10_{frame:02d}", 2160, 1080) for frame in range(1, 11)),
    Slot("bat_bg", 2160, 1080),
    Slot("bat_img", 16, 19),
    Slot("bat_100", 2160, 1080),
    Slot("kernel", 2160, 1080),
    Slot("fast_charging_100", 2160, 1080),
    *(Slot(f"fast_charging_ani-{frame:02d}", 2160, 1080) for frame in range(1, 7)),
    *(Slot(f"fast_charging_{digit:02d}", 108, 192) for digit in range(10)),
    Slot("fast_charging_percent", 108, 192),
)


def unpack_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def decode_stream(stream: bytes, index: int) -> bytes:
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(stream) + decoder.flush()
    except zlib.error as exc:
        raise ValueError(f"slot {index}: invalid zlib stream: {exc}") from exc
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError(f"slot {index}: zlib boundaries are not exact")
    return raw


def inspect(path: pathlib.Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < OUTER_HEADER_SIZE + 8:
        raise ValueError("image is shorter than the MediaTek and slot-table headers")

    outer_magic = unpack_u32(data, 0)
    payload_size = unpack_u32(data, 4)
    name = data[8:40].split(b"\0", 1)[0].decode("ascii", "replace")
    extended_magic = unpack_u32(data, 0x30)
    header_size = unpack_u32(data, 0x34)
    header_version = unpack_u32(data, 0x38)
    alignment = unpack_u32(data, 0x44)

    if outer_magic != OUTER_MAGIC:
        raise ValueError(f"unexpected outer magic: 0x{outer_magic:08x}")
    if extended_magic != EXTENDED_MAGIC:
        raise ValueError(f"unexpected extended magic: 0x{extended_magic:08x}")
    if header_size != OUTER_HEADER_SIZE:
        raise ValueError(f"unexpected outer header size: {header_size}")
    if name != "logo":
        raise ValueError(f"unexpected image name: {name!r}")

    payload_end = header_size + payload_size
    if payload_end > len(data):
        raise ValueError("declared payload extends beyond the input image")

    count, table_total = struct.unpack_from("<II", data, header_size)
    if count != len(SLOTS):
        raise ValueError(f"expected {len(SLOTS)} slots, found {count}")
    if table_total != payload_size:
        raise ValueError(
            f"inner total {table_total} differs from outer payload size {payload_size}"
        )

    offsets = struct.unpack_from(f"<{count}I", data, header_size + 8)
    expected_first = 8 + count * 4
    if offsets[0] != expected_first:
        raise ValueError(
            f"first stream offset is {offsets[0]}, expected table end {expected_first}"
        )
    if tuple(sorted(offsets)) != offsets or len(set(offsets)) != len(offsets):
        raise ValueError("slot offsets are not strictly increasing")
    if offsets[-1] >= table_total:
        raise ValueError("last slot begins outside the declared payload")

    rows: list[dict[str, object]] = []
    ends = offsets[1:] + (table_total,)
    for index, (slot, start, end) in enumerate(zip(SLOTS, offsets, ends, strict=True)):
        if end <= start:
            raise ValueError(f"slot {index}: empty or reversed range")
        stream = data[header_size + start : header_size + end]
        raw = decode_stream(stream, index)
        if len(raw) != slot.raw_size:
            raise ValueError(
                f"slot {index}: decoded {len(raw)} bytes, expected {slot.raw_size} "
                f"for {slot.width}x{slot.height} BGRA8888"
            )
        rows.append(
            {
                "slot": index,
                "name": slot.name,
                "width": slot.width,
                "height": slot.height,
                "stride": slot.width * 4,
                "raw_bytes": len(raw),
                "compressed_bytes": len(stream),
                "adler32": f"{zlib.adler32(raw) & 0xFFFFFFFF:08x}",
            }
        )

    padding = data[payload_end:]
    return {
        "file_size": len(data),
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "outer_magic": outer_magic,
        "extended_magic": extended_magic,
        "image_name": name,
        "header_size": header_size,
        "header_version": header_version,
        "alignment": alignment,
        "payload_size": payload_size,
        "payload_end": payload_end,
        "active_image_sha256": hashlib.sha256(data[:payload_end]).hexdigest(),
        "slot_count": count,
        "first_stream_offset": offsets[0],
        "padding_size": len(padding),
        "padding_all_zero": not any(padding),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and inventory a Gemini logo partition image without extracting pixels."
    )
    parser.add_argument("image", type=pathlib.Path)
    args = parser.parse_args()
    if not args.image.is_file():
        print(f"error: image not found: {args.image}", file=sys.stderr)
        return 2
    try:
        result = inspect(args.image)
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for key in (
        "file_size",
        "file_sha256",
        "outer_magic",
        "extended_magic",
        "image_name",
        "header_size",
        "header_version",
        "alignment",
        "payload_size",
        "payload_end",
        "active_image_sha256",
        "slot_count",
        "first_stream_offset",
        "padding_size",
        "padding_all_zero",
    ):
        value = result[key]
        if key.endswith("magic"):
            value = f"0x{int(value):08x}"
        print(f"{key}={value}")
    print("pixel_format=BGRA8888")
    print("all_streams_valid=yes")
    print("all_geometry_lengths_match=yes")
    print()
    print("slot\tname\twidth\theight\tstride\traw_bytes\tcompressed_bytes\tadler32")
    for row in result["rows"]:
        print(
            "{slot:02d}\t{name}\t{width}\t{height}\t{stride}\t{raw_bytes}\t"
            "{compressed_bytes}\t{adler32}".format(**row)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
