#!/usr/bin/env python3
"""Build a non-flashing Android boot-image v0 candidate for LK experiments.

This deliberately does not know about partitions, fastboot, preloader, or
device-specific flashing. It only serializes an Android v0 header and the
explicit payload files supplied by the caller.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys
import zlib


MAGIC = b"ANDROID!"
GZIP_MAGIC = b"\x1f\x8b"
ARM64_MAGIC = b"ARM\x64"
HEADER_PAGE = 2048
CMDLINE_SIZE = 512 + 1024
LK_ANDROID_BOOT_IMAGE_LIMIT = 0x01000000
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


def read(path: pathlib.Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def put_string(header: bytearray, offset: int, size: int, value: str) -> None:
    encoded = value.encode("ascii")
    if len(encoded) >= size:
        raise ValueError(f"value at offset {offset} must be shorter than {size} bytes")
    header[offset : offset + size] = encoded + b"\0" * (size - len(encoded))


def has_lk_64_bootopt(cmdline: str) -> bool:
    for token in cmdline.split():
        if token.startswith("bootopt="):
            value = token[len("bootopt=") :]
            return value[LK_BOOTOPT_VALUE_OFFSET : LK_BOOTOPT_VALUE_OFFSET + 2] == "64"
    return False


def canonical_v0_id(payloads: tuple[bytes, bytes, bytes, bytes]) -> bytes:
    """Return the Android v0 ID used by AOSP mkbootimg.

    Kernel, ramdisk, and second are always followed by their little-endian
    uint32 sizes. The legacy DT field is included only when present, matching
    AOSP's legacy mkbootimg.c.
    """

    digest = hashlib.sha1()
    for payload in payloads[:3]:
        digest.update(payload)
        digest.update(struct.pack("<I", len(payload)))
    if payloads[3]:
        digest.update(payloads[3])
        digest.update(struct.pack("<I", len(payloads[3])))
    return digest.digest()


def decompress_arm64_image(kernel: bytes) -> tuple[bytes, int, int, int]:
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        decompressed = decompressor.decompress(kernel) + decompressor.flush()
    except zlib.error as exc:
        raise ValueError(f"--lk-android8 gzip payload is invalid: {exc}") from exc
    if not decompressor.eof:
        raise ValueError("--lk-android8 gzip payload is truncated before end-of-stream")
    if decompressor.unused_data or decompressor.unconsumed_tail:
        raise ValueError("--lk-android8 Image.gz must contain exactly one gzip stream")
    if len(decompressed) > LK_MT6797_DECOMPRESS_LIMIT:
        raise ValueError(
            "--lk-android8 decompressed Image exceeds the MT6797 LK 50 MiB buffer: "
            f"{len(decompressed)} > {LK_MT6797_DECOMPRESS_LIMIT}"
        )
    if len(decompressed) < 64 or decompressed[56:60] != ARM64_MAGIC:
        raise ValueError("--lk-android8 gzip payload does not contain an ARM64 Image")
    text_offset, image_size, flags = struct.unpack_from("<3Q", decompressed, 8)
    if image_size == 0:
        raise ValueError("--lk-android8 ARM64 Image header has a zero image_size")
    if image_size > LK_MT6797_DECOMPRESS_LIMIT:
        raise ValueError(
            "--lk-android8 ARM64 Image header image_size exceeds the LK buffer: "
            f"{image_size} > {LK_MT6797_DECOMPRESS_LIMIT}"
        )
    return decompressed, text_offset, image_size, flags


def build(args: argparse.Namespace) -> tuple[bytes, dict[str, int | str]]:
    page = args.page_size
    if page < HEADER_PAGE or page & (page - 1):
        raise ValueError("page size must be a power of two and at least 2048")
    kernel = read(args.kernel)
    ramdisk = read(args.ramdisk)
    dtb = read(args.dtb)
    arm64_text_offset: int | str = "not_checked"
    arm64_image_size: int | str = "not_checked"
    arm64_flags: int | str = "not_checked"
    arm64_placement_base: int | str = "not_checked"
    decompressed_size: int | str = "not_checked"
    if args.lk_android8:
        if not kernel.startswith(GZIP_MAGIC):
            raise ValueError(
                "--lk-android8 requires a gzip-compressed kernel payload (Image.gz)"
            )
        if args.dtb_mode != "append":
            raise ValueError(
                "--lk-android8 requires --dtb-mode append; Planet LK scans the kernel payload"
            )
        if not has_lk_64_bootopt(args.cmdline):
            raise ValueError(
                "--lk-android8 requires bootopt=...64... to select LK's 64-bit path"
            )
        recovered_addresses = (
            ("kernel", args.kernel_addr, LK_KERNEL_ADDR),
            ("ramdisk", args.ramdisk_addr, LK_RAMDISK_ADDR),
            ("second", args.second_addr, LK_SECOND_ADDR),
            ("tags", args.tags_addr, LK_TAGS_ADDR),
        )
        for name, actual, expected in recovered_addresses:
            if actual != expected:
                raise ValueError(
                    f"--lk-android8 requires recovered {name}_addr=0x{expected:x}; "
                    f"got 0x{actual:x}"
                )
        decompressed, text_offset, image_size, flags = decompress_arm64_image(kernel)
        if flags != LK_ARM64_IMAGE_FLAGS:
            raise ValueError(
                "--lk-android8 requires exact ARM64 Image flags 0x0a "
                "(little-endian, 4 KiB pages, relocatable, reserved bits zero); "
                f"got 0x{flags:x}"
            )
        if args.kernel_addr & 0x7FFFF:
            raise ValueError(
                "--lk-android8 kernel address does not satisfy LK's 512 KiB mask"
            )
        if args.kernel_addr < text_offset:
            raise ValueError(
                "--lk-android8 kernel address is below the ARM64 Image text_offset"
            )
        placement_base = args.kernel_addr - text_offset
        if placement_base % ARM64_PLACEMENT_ALIGNMENT:
            raise ValueError(
                "--lk-android8 requires (kernel_addr - Image.text_offset) to be "
                f"2 MiB aligned; got 0x{placement_base:x}"
            )
        arm64_text_offset = text_offset
        arm64_image_size = image_size
        arm64_flags = flags
        arm64_placement_base = placement_base
        decompressed_size = len(decompressed)
    if not dtb.startswith(b"\xd0\x0d\xfe\xed"):
        raise ValueError(f"{args.dtb} is not a flattened device tree blob")
    if not args.cmdline:
        raise ValueError("--cmdline is required; do not inherit vendor bootargs implicitly")
    if args.dtb_mode == "append":
        kernel_payload = kernel + dtb
        dt_payload = b""
    else:
        kernel_payload = kernel
        dt_payload = dtb
    payloads = (kernel_payload, ramdisk, b"", dt_payload)
    digest = canonical_v0_id(payloads)
    header = bytearray(page)
    values = (
        len(kernel_payload),
        args.kernel_addr,
        len(ramdisk),
        args.ramdisk_addr,
        0,
        args.second_addr,
        args.tags_addr,
        page,
        len(dt_payload),
        0,
    )
    struct.pack_into("<8s10I", header, 0, MAGIC, *values)
    put_string(header, 48, 16, args.name)
    cmdline = args.cmdline.encode("ascii")
    if len(cmdline) >= CMDLINE_SIZE:
        raise ValueError(f"--cmdline must be shorter than {CMDLINE_SIZE} bytes")
    header[64:576] = cmdline[:512].ljust(512, b"\0")
    header[608:1632] = cmdline[512:].ljust(1024, b"\0")
    header[576:596] = digest

    image = bytearray(header)
    for payload in payloads:
        image.extend(payload)
        image.extend(b"\0" * (align(len(image), page) - len(image)))
    if args.lk_android8 and len(image) > LK_ANDROID_BOOT_IMAGE_LIMIT:
        raise ValueError(
            "--lk-android8 serialized boot image exceeds the 16 MiB limit: "
            f"{len(image)} > {LK_ANDROID_BOOT_IMAGE_LIMIT}"
        )
    metadata: dict[str, int | str] = {
        "kernel_size": len(kernel_payload),
        "ramdisk_size": len(ramdisk),
        "dt_size": len(dt_payload),
        "page_size": page,
        "kernel_addr": args.kernel_addr,
        "ramdisk_addr": args.ramdisk_addr,
        "second_addr": args.second_addr,
        "tags_addr": args.tags_addr,
        "dtb_mode": args.dtb_mode,
        "lk_android8_compatible": "yes" if args.lk_android8 else "not_checked",
        "arm64_text_offset": arm64_text_offset,
        "arm64_image_size": arm64_image_size,
        "arm64_flags": arm64_flags,
        "arm64_placement_base": arm64_placement_base,
        "decompressed_kernel_size": decompressed_size,
        "file_size": len(image),
        "sha1_id": digest.hex(),
    }
    return bytes(image), metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=pathlib.Path, required=True)
    parser.add_argument("--ramdisk", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--cmdline", required=True)
    parser.add_argument("--name", default="gemini-mainline")
    parser.add_argument("--dtb-mode", choices=("append", "field"), default="append")
    parser.add_argument(
        "--lk-android8",
        action="store_true",
        help="enforce the retained Planet Android 8 LK gzip+appended-DTB contract",
    )
    parser.add_argument("--page-size", type=int, default=2048)
    parser.add_argument("--kernel-addr", type=lambda value: int(value, 0), default=0x40200000)
    parser.add_argument("--ramdisk-addr", type=lambda value: int(value, 0), default=0x45000000)
    parser.add_argument("--second-addr", type=lambda value: int(value, 0), default=0x40F00000)
    parser.add_argument("--tags-addr", type=lambda value: int(value, 0), default=0x44000000)
    args = parser.parse_args()
    if args.output.exists():
        print(f"error: refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    try:
        image, metadata = build(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(image)
    except (OSError, UnicodeEncodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"output={args.output}")
    for key, value in metadata.items():
        print(f"{key}={value}")
    print(f"sha256={hashlib.sha256(image).hexdigest()}")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
