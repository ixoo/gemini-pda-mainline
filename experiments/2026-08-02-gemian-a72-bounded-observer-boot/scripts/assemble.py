#!/usr/bin/env python3
"""Assemble and validate the exact bounded Gemian observer Android-v0 image."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import stat
import struct
import sys
import zlib


ACTIVE_BOOT_SHA256 = "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513"
ACTIVE_RAMDISK_SHA256 = "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4"
KERNEL_FIELD_SHA256 = "5864c083a156fcb023e62a5e8dd3fd4c75d68fb119c82492ed4653065ca39a18"
ACTIVE_SIZE = 16 * 1024 * 1024
PAGE_SIZE = 2048
KERNEL_ADDR = 0x40080000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
CMDLINE = "bootopt=64S3,32N2,64N2 log_buf_len=4M"
ARM64_MAGIC = b"ARM\x64"
ARM64_TEXT_OFFSET = 0x80000
ARM64_FLAGS = 0x00
FDT_MAGIC = b"\xd0\x0d\xfe\xed"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int) -> int:
    return (value + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def boot_fields(image: bytes) -> tuple[int, ...]:
    if len(image) < PAGE_SIZE or image[:8] != b"ANDROID!":
        raise ValueError("active image is not Android boot image v0")
    return struct.unpack_from("<10I", image, 8)


def c_string(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("ascii")


def validate_kernel_field(kernel: bytes) -> tuple[int, int]:
    if digest(kernel) != KERNEL_FIELD_SHA256:
        raise ValueError("observer kernel field identity changed")
    if not kernel.startswith(b"\x1f\x8b"):
        raise ValueError("observer kernel field does not start with gzip")
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    image = decompressor.decompress(kernel) + decompressor.flush()
    if not decompressor.eof or decompressor.unconsumed_tail:
        raise ValueError("observer gzip stream is incomplete")
    dtb = decompressor.unused_data
    if len(image) < 64 or image[56:60] != ARM64_MAGIC:
        raise ValueError("observer gzip does not contain an ARM64 Image")
    text_offset, image_size, flags = struct.unpack_from("<3Q", image, 8)
    if text_offset != ARM64_TEXT_OFFSET or not image_size or flags != ARM64_FLAGS:
        raise ValueError("observer ARM64 Image header contract changed")
    if len(dtb) < 8 or dtb[:4] != FDT_MAGIC:
        raise ValueError("observer kernel field lacks one appended DTB")
    dtb_size = struct.unpack_from(">I", dtb, 4)[0]
    if dtb_size != len(dtb):
        raise ValueError("appended DTB size does not consume the kernel suffix")
    return len(image), dtb_size


def build(active: bytes, kernel: bytes) -> tuple[bytes, dict[str, int | str]]:
    if len(active) != ACTIVE_SIZE or digest(active) != ACTIVE_BOOT_SHA256:
        raise ValueError("project-start active boot identity changed")
    fields = boot_fields(active)
    (
        active_kernel_size,
        kernel_addr,
        ramdisk_size,
        ramdisk_addr,
        second_size,
        second_addr,
        tags_addr,
        page_size,
        dt_size,
        unused,
    ) = fields
    if (
        kernel_addr != KERNEL_ADDR
        or ramdisk_addr != RAMDISK_ADDR
        or second_addr != SECOND_ADDR
        or tags_addr != TAGS_ADDR
        or page_size != PAGE_SIZE
        or second_size
        or dt_size
        or unused
    ):
        raise ValueError("active Android-v0 address or layout contract changed")
    if any(active[48:64]):
        raise ValueError("active Android-v0 name is no longer empty")
    cmdline = c_string(active[64:576] + active[608:1632])
    if cmdline != CMDLINE:
        raise ValueError("active command line changed")
    active_kernel_end = PAGE_SIZE + active_kernel_size
    ramdisk_offset = align(active_kernel_end)
    ramdisk_end = ramdisk_offset + ramdisk_size
    ramdisk = active[ramdisk_offset:ramdisk_end]
    if len(ramdisk) != ramdisk_size or digest(ramdisk) != ACTIVE_RAMDISK_SHA256:
        raise ValueError("active ramdisk field identity changed")
    if any(active[active_kernel_end:ramdisk_offset]) or any(active[ramdisk_end:]):
        raise ValueError("active boot padding is not zero")

    decompressed_size, appended_dtb_size = validate_kernel_field(kernel)
    header = bytearray(active[:PAGE_SIZE])
    struct.pack_into("<I", header, 8, len(kernel))
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    header[576:596] = image_id.digest()

    candidate = bytearray(header)
    candidate.extend(kernel)
    candidate.extend(b"\0" * (align(len(candidate)) - len(candidate)))
    candidate.extend(ramdisk)
    candidate.extend(b"\0" * (align(len(candidate)) - len(candidate)))
    if len(candidate) >= ACTIVE_SIZE:
        raise ValueError("raw observer boot image does not fit logical boot2")

    # Parse the result again instead of relying only on construction state.
    result_fields = boot_fields(candidate)
    if result_fields != (len(kernel),) + fields[1:]:
        raise ValueError("serialized Android-v0 fields changed unexpectedly")
    result_ramdisk_offset = align(PAGE_SIZE + len(kernel))
    if candidate[PAGE_SIZE:PAGE_SIZE + len(kernel)] != kernel:
        raise ValueError("serialized kernel field mismatch")
    if candidate[result_ramdisk_offset:result_ramdisk_offset + ramdisk_size] != ramdisk:
        raise ValueError("serialized ramdisk field mismatch")
    if c_string(candidate[64:576] + candidate[608:1632]) != CMDLINE:
        raise ValueError("serialized command line mismatch")

    return bytes(candidate), {
        "active_boot_sha256": ACTIVE_BOOT_SHA256,
        "kernel_field_sha256": KERNEL_FIELD_SHA256,
        "kernel_field_size": len(kernel),
        "decompressed_image_size": decompressed_size,
        "appended_dtb_size": appended_dtb_size,
        "ramdisk_sha256": ACTIVE_RAMDISK_SHA256,
        "ramdisk_size": ramdisk_size,
        "raw_size": len(candidate),
        "raw_sha256": digest(candidate),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-boot", type=pathlib.Path, required=True)
    parser.add_argument("--kernel-field", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        print(f"error: refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    try:
        active = read_regular(args.active_boot, "project-start active boot")
        kernel = read_regular(args.kernel_field, "bounded observer kernel field")
        candidate, metadata = build(active, kernel)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(candidate)
        args.output.chmod(0o600)
    except (OSError, UnicodeDecodeError, ValueError, zlib.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"output={args.output}")
    for key, value in metadata.items():
        print(f"{key}={value}")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
