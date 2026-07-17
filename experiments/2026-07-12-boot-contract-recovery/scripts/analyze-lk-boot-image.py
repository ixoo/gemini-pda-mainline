#!/usr/bin/env python3
"""Analyze and optionally validate the Gemini Planet LK boot-image contract."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys
import zlib


MAGIC = b"ANDROID!"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
ARM64_MAGIC = b"ARM\x64"
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
LK_ANDROID_BOOT_IMAGE_LIMIT = 0x01000000
LK_GENERIC_DECOMPRESS_LIMIT = 0x01C00000
LK_MT6797_DECOMPRESS_LIMIT = 0x03200000
ARM64_PLACEMENT_ALIGNMENT = 0x00200000
LK_BOOTOPT_VALUE_OFFSET = 0x12 - len("bootopt=")
LK_KERNEL_ADDR = 0x40200000
LK_RAMDISK_ADDR = 0x45000000
LK_SECOND_ADDR = 0x40F00000
LK_TAGS_ADDR = 0x44000000
LK_ARM64_IMAGE_FLAGS = 0x0A


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


def has_lk_64_bootopt(cmdline: str) -> bool:
    for token in cmdline.split():
        if token.startswith("bootopt="):
            value = token[len("bootopt=") :]
            return value[LK_BOOTOPT_VALUE_OFFSET : LK_BOOTOPT_VALUE_OFFSET + 2] == "64"
    return False


def canonical_v0_id(payloads: tuple[bytes, bytes, bytes, bytes]) -> bytes:
    digest = hashlib.sha1()
    for payload in payloads[:3]:
        digest.update(payload)
        digest.update(struct.pack("<I", len(payload)))
    if payloads[3]:
        digest.update(payloads[3])
        digest.update(struct.pack("<I", len(payloads[3])))
    return digest.digest()


def yes(value: bool) -> str:
    return "yes" if value else "no"


def parse(
    path: pathlib.Path, expected_dtb: pathlib.Path | None = None
) -> tuple[dict[str, int | str], list[str]]:
    payload = path.read_bytes()
    if len(payload) < 2048 or payload[:8] != MAGIC:
        raise ValueError("not an Android v0 boot image")
    values = struct.unpack_from("<10I", payload, 8)
    result: dict[str, int | str] = dict(zip(PAGE_FIELDS, values, strict=True))
    failures: list[str] = []

    page = int(result["page_size"])
    if page < 2048 or page & (page - 1):
        raise ValueError(f"invalid Android page size: {page}")
    kernel_offset = page
    kernel_end = kernel_offset + int(result["kernel_size"])
    ramdisk_offset = align(kernel_end, page)
    ramdisk_end = ramdisk_offset + int(result["ramdisk_size"])
    second_offset = align(ramdisk_end, page)
    second_end = second_offset + int(result["second_size"])
    dt_offset = align(second_end, page)
    dt_end = dt_offset + int(result["dt_size"])
    expected_image_end = align(dt_end, page)
    if kernel_end > len(payload) or ramdisk_end > len(payload):
        raise ValueError("kernel or ramdisk payload exceeds image")
    if second_end > len(payload) or dt_end > len(payload):
        raise ValueError("second or DT payload exceeds image")

    kernel = payload[kernel_offset:kernel_end]
    ramdisk = payload[ramdisk_offset:ramdisk_end]
    second = payload[second_offset:second_end]
    dt_payload = payload[dt_offset:dt_end]
    cmdline = (payload[64:576] + payload[608:1632]).split(b"\0", 1)[0].decode(
        "ascii", "replace"
    )
    stored_id = payload[576:596]
    id_padding_zero = not any(payload[596:608])
    header_padding_zero = not any(payload[1632:page])
    computed_id = canonical_v0_id((kernel, ramdisk, second, dt_payload))
    padding_zero = all(
        not any(region)
        for region in (
            payload[kernel_end:ramdisk_offset],
            payload[ramdisk_end:second_offset],
            payload[second_end:dt_offset],
            payload[dt_end:expected_image_end],
        )
    )
    result.update(
        image_size=len(payload),
        image_sha256=hashlib.sha256(payload).hexdigest(),
        image_layout_size=expected_image_end,
        image_layout_exact=yes(len(payload) == expected_image_end),
        payload_padding_zero=yes(padding_zero),
        kernel_offset=kernel_offset,
        ramdisk_offset=ramdisk_offset,
        second_offset=second_offset,
        dt_offset=dt_offset,
        kernel_gzip_magic=yes(kernel.startswith(b"\x1f\x8b")),
        boot_image_within_16m=yes(len(payload) <= LK_ANDROID_BOOT_IMAGE_LIMIT),
        kernel_addr_aligned_512k=yes((int(result["kernel_addr"]) & 0x7FFFF) == 0),
        cmdline=cmdline,
        bootopt_64=yes(has_lk_64_bootopt(cmdline)),
        stored_sha1_id=stored_id.hex(),
        computed_sha1_id=computed_id.hex(),
        canonical_sha1_id_matches=yes(stored_id == computed_id),
        id_padding_zero=yes(id_padding_zero),
        header_padding_zero=yes(header_padding_zero),
        lk_generic_decompress_limit=LK_GENERIC_DECOMPRESS_LIMIT,
        lk_mt6797_decompress_limit=LK_MT6797_DECOMPRESS_LIMIT,
    )

    appended = b""
    if kernel.startswith(b"\x1f\x8b"):
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            decompressed = decompressor.decompress(kernel) + decompressor.flush()
            gzip_error = "none"
        except zlib.error as exc:
            decompressed = b""
            gzip_error = str(exc)
        appended = decompressor.unused_data
        gzip_stream_size = len(kernel) - len(appended)
        result.update(
            gzip_error=gzip_error,
            gzip_eof=yes(decompressor.eof),
            gzip_unconsumed_tail_size=len(decompressor.unconsumed_tail),
            gzip_stream_size=gzip_stream_size,
            decompressed_kernel_size=len(decompressed),
            decompressed_within_mt6797_limit=yes(
                len(decompressed) <= LK_MT6797_DECOMPRESS_LIMIT
            ),
        )
        if len(decompressed) >= 64 and decompressed[56:60] == ARM64_MAGIC:
            text_offset, arm64_image_size, flags = struct.unpack_from(
                "<3Q", decompressed, 8
            )
            kernel_addr = int(result["kernel_addr"])
            placement_valid = kernel_addr >= text_offset
            placement_base = kernel_addr - text_offset if placement_valid else -1
            result.update(
                arm64_image_magic="yes",
                arm64_text_offset=text_offset,
                arm64_image_size=arm64_image_size,
                arm64_flags=flags,
                arm64_relocatable=yes(bool(flags & (1 << 3))),
                arm64_flags_exact_handoff=yes(flags == LK_ARM64_IMAGE_FLAGS),
                arm64_image_size_valid=yes(
                    0 < arm64_image_size <= LK_MT6797_DECOMPRESS_LIMIT
                ),
                arm64_placement_base=(
                    f"0x{placement_base:x}" if placement_valid else "underflow"
                ),
                arm64_placement_aligned_2m=yes(
                    placement_valid
                    and placement_base % ARM64_PLACEMENT_ALIGNMENT == 0
                ),
            )
        else:
            result.update(
                arm64_image_magic="no",
                arm64_text_offset="absent",
                arm64_image_size="absent",
                arm64_flags="absent",
                arm64_relocatable="no",
                arm64_flags_exact_handoff="no",
                arm64_image_size_valid="no",
                arm64_placement_base="absent",
                arm64_placement_aligned_2m="no",
            )
    else:
        result.update(
            gzip_error="not_checked",
            gzip_eof="no",
            gzip_unconsumed_tail_size="not_checked",
            gzip_stream_size="not_checked",
            decompressed_kernel_size="not_checked",
            decompressed_within_mt6797_limit="not_checked",
            arm64_image_magic="not_checked",
            arm64_text_offset="not_checked",
            arm64_image_size="not_checked",
            arm64_flags="not_checked",
            arm64_relocatable="not_checked",
            arm64_flags_exact_handoff="not_checked",
            arm64_image_size_valid="not_checked",
            arm64_placement_base="not_checked",
            arm64_placement_aligned_2m="not_checked",
        )

    fdt_size = valid_fdt(appended, 0, len(appended)) if appended else None
    if fdt_size is None:
        result.update(
            appended_dtb_offset="absent",
            appended_dtb_size="absent",
            fdt_starts_at_gzip_stream_end="no",
            fdt_ends_at_kernel_field_end="no",
            appended_dtb_sha256="absent",
        )
        appended_dtb = b""
    else:
        appended_dtb = appended[:fdt_size]
        gzip_stream_size = result.get("gzip_stream_size")
        result.update(
            appended_dtb_offset=(
                kernel_offset + gzip_stream_size
                if isinstance(gzip_stream_size, int)
                else "absent"
            ),
            appended_dtb_size=fdt_size,
            fdt_starts_at_gzip_stream_end=yes(
                isinstance(gzip_stream_size, int)
                and kernel[gzip_stream_size : gzip_stream_size + 4] == FDT_MAGIC
            ),
            fdt_ends_at_kernel_field_end=yes(fdt_size == len(appended)),
            appended_dtb_sha256=hashlib.sha256(appended_dtb).hexdigest(),
        )

    if expected_dtb is not None:
        expected = expected_dtb.read_bytes()
        result.update(
            expected_dtb_sha256=hashlib.sha256(expected).hexdigest(),
            expected_dtb_matches=yes(appended_dtb == expected),
        )
    else:
        result.update(expected_dtb_sha256="not_supplied", expected_dtb_matches="not_checked")

    result["header_dt_size"] = int(result["dt_size"])
    gates = {
        "android_page_size_2048": page == 2048,
        "image_layout_exact": len(payload) == expected_image_end,
        "payload_padding_zero": padding_zero,
        "canonical_sha1_id": stored_id == computed_id,
        "id_padding_zero": id_padding_zero,
        "header_padding_zero": header_padding_zero,
        "boot_image_within_16m": len(payload) <= LK_ANDROID_BOOT_IMAGE_LIMIT,
        "bootopt_selects_64bit": has_lk_64_bootopt(cmdline),
        "kernel_addr_recovered_value": int(result["kernel_addr"]) == LK_KERNEL_ADDR,
        "ramdisk_addr_recovered_value": int(result["ramdisk_addr"]) == LK_RAMDISK_ADDR,
        "second_addr_recovered_value": int(result["second_addr"]) == LK_SECOND_ADDR,
        "tags_addr_recovered_value": int(result["tags_addr"]) == LK_TAGS_ADDR,
        "header_dt_field_empty": int(result["dt_size"]) == 0,
        "header_unused_field_zero": int(result["unused"]) == 0,
        "second_payload_empty": int(result["second_size"]) == 0,
        "ramdisk_payload_present": int(result["ramdisk_size"]) > 0,
        "gzip_stream_complete": result.get("gzip_eof") == "yes",
        "gzip_stream_has_no_unconsumed_tail": result.get("gzip_unconsumed_tail_size") == 0,
        "decompressed_image_within_50m": result.get("decompressed_within_mt6797_limit") == "yes",
        "arm64_image_header": result.get("arm64_image_magic") == "yes",
        "arm64_image_size_valid": result.get("arm64_image_size_valid") == "yes",
        "arm64_image_relocatable": result.get("arm64_relocatable") == "yes",
        "arm64_image_flags_exact_handoff": result.get("arm64_flags_exact_handoff") == "yes",
        "kernel_address_aligned_512k": result.get("kernel_addr_aligned_512k") == "yes",
        "arm64_placement_aligned_2m": result.get("arm64_placement_aligned_2m") == "yes",
        "fdt_starts_at_gzip_eof": result.get("fdt_starts_at_gzip_stream_end") == "yes",
        "fdt_ends_at_kernel_field_end": result.get("fdt_ends_at_kernel_field_end") == "yes",
    }
    if expected_dtb is not None:
        gates["expected_dtb_matches"] = result.get("expected_dtb_matches") == "yes"
    for gate, passed in gates.items():
        result[f"gate_{gate}"] = yes(passed)
        if not passed:
            failures.append(gate)
    result["lk_validation"] = "passed" if not failures else "failed"
    result["lk_validation_failures"] = ",".join(failures) if failures else "none"
    return result, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=pathlib.Path)
    parser.add_argument(
        "--expected-dtb",
        type=pathlib.Path,
        help="require the appended DTB to match this file byte-for-byte",
    )
    parser.add_argument(
        "--validate-lk",
        action="store_true",
        help="exit nonzero unless every retained-LK packaging gate passes",
    )
    args = parser.parse_args()
    try:
        result, failures = parse(args.image, args.expected_dtb)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for key, value in result.items():
        print(f"{key}={value}")
    print("hardware_write=none")
    if args.validate_lk and failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
