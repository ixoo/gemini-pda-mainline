#!/usr/bin/env python3
"""Validate Candidate Z as an exact-Y kernel/DT Android-v0 ramdisk delta."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import stat
import struct
import sys


Y_BOOT_SHA256 = "94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee"
Y_BOOT_SIZE = 6_866_944
Y_INITRAMFS_SHA256 = "11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2"
Y_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
Y_DTB_SIZE = 26_259
Y_IMAGE_GZ_SHA256 = "d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"
CAPACITY = 16 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def layout(image: bytes) -> tuple[tuple[int, ...], int, int, int, int]:
    if len(image) < 2048 or image[:8] != b"ANDROID!":
        raise ValueError("Android magic or minimum size mismatch")
    fields = struct.unpack_from("<10I", image, 8)
    kernel_size, _kernel_addr, ramdisk_size = fields[:3]
    page_size = fields[7]
    kernel_offset = page_size
    kernel_end = kernel_offset + kernel_size
    ramdisk_offset = align(kernel_end, page_size)
    ramdisk_end = ramdisk_offset + ramdisk_size
    return fields, kernel_offset, kernel_end, ramdisk_offset, ramdisk_end


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--y-boot", type=pathlib.Path, required=True)
    parser.add_argument("--y-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--z-boot", type=pathlib.Path, required=True)
    parser.add_argument("--z-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        y_boot = read_regular(args.y_boot, "Candidate Y boot")
        y_ramdisk = read_regular(args.y_initramfs, "Candidate Y initramfs")
        z_boot = read_regular(args.z_boot, "Candidate Z boot")
        z_ramdisk = read_regular(args.z_initramfs, "Candidate Z initramfs")
        dtb = read_regular(args.dtb, "exact Y DTB")
        if len(y_boot) != Y_BOOT_SIZE or digest(y_boot) != Y_BOOT_SHA256:
            raise ValueError("Candidate Y boot identity mismatch")
        if digest(y_ramdisk) != Y_INITRAMFS_SHA256:
            raise ValueError("Candidate Y initramfs identity mismatch")
        if len(dtb) != Y_DTB_SIZE or digest(dtb) != Y_DTB_SHA256:
            raise ValueError("exact Candidate Y DTB identity mismatch")
        if len(z_boot) > CAPACITY:
            raise ValueError("Candidate Z exceeds boot2 capacity")

        y_fields, y_ko, y_ke, y_ro, y_re = layout(y_boot)
        z_fields, z_ko, z_ke, z_ro, z_re = layout(z_boot)
        if y_fields[2] != len(y_ramdisk) or z_fields[2] != len(z_ramdisk):
            raise ValueError("ramdisk size/header mismatch")
        if y_boot[y_ro:y_re] != y_ramdisk or z_boot[z_ro:z_re] != z_ramdisk:
            raise ValueError("ramdisk field bytes mismatch")
        if y_boot[y_ko:y_ke] != z_boot[z_ko:z_ke]:
            raise ValueError("Candidate Z kernel field differs from exact Y")
        kernel = z_boot[z_ko:z_ke]
        if kernel[-Y_DTB_SIZE:] != dtb or digest(kernel[:-Y_DTB_SIZE]) != Y_IMAGE_GZ_SHA256:
            raise ValueError("Candidate Z kernel is not exact Y Image.gz plus DTB")

        # Header must be byte-exact Y except ramdisk size and canonical ID.
        expected_header = bytearray(y_boot[:y_fields[7]])
        struct.pack_into("<I", expected_header, 16, len(z_ramdisk))
        image_id = hashlib.sha1()
        for payload in (kernel, z_ramdisk, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        expected_header[576:608] = image_id.digest() + b"\0" * 12
        if z_boot[:z_fields[7]] != bytes(expected_header):
            raise ValueError("Candidate Z Android header has an unrelated delta")
        if any(z_boot[z_ke:z_ro]) or any(z_boot[z_re:]):
            raise ValueError("Candidate Z payload padding is nonzero")
        if len(z_boot) != align(z_re, z_fields[7]):
            raise ValueError("Candidate Z has trailing or missing bytes")

        print("validation=candidate-z-android-v0")
        print(f"candidate_sha256={digest(z_boot)}")
        print(f"candidate_size={len(z_boot)}")
        print(f"initramfs_sha256={digest(z_ramdisk)}")
        print(f"image_gz_sha256={Y_IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={Y_DTB_SHA256}")
        print("kernel_field=byte-exact-candidate-y")
        print("header_delta=ramdisk-size-and-canonical-id-only")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
