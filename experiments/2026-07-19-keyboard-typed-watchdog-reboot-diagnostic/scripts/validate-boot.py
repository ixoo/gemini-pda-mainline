#!/usr/bin/env python3
"""Validate Candidate Y as an exact-X kernel/DT Android-v0 ramdisk delta."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import stat
import struct
import sys


X_BOOT_SHA256 = "bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296"
X_BOOT_SIZE = 6_864_896
X_INITRAMFS_SHA256 = "b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769"
X_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
X_DTB_SIZE = 26_259
X_IMAGE_GZ_SHA256 = "d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"
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
    parser.add_argument("--x-boot", type=pathlib.Path, required=True)
    parser.add_argument("--x-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--y-boot", type=pathlib.Path, required=True)
    parser.add_argument("--y-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        x_boot = read_regular(args.x_boot, "Candidate X boot")
        x_ramdisk = read_regular(args.x_initramfs, "Candidate X initramfs")
        y_boot = read_regular(args.y_boot, "Candidate Y boot")
        y_ramdisk = read_regular(args.y_initramfs, "Candidate Y initramfs")
        dtb = read_regular(args.dtb, "exact X DTB")
        if len(x_boot) != X_BOOT_SIZE or digest(x_boot) != X_BOOT_SHA256:
            raise ValueError("Candidate X boot identity mismatch")
        if digest(x_ramdisk) != X_INITRAMFS_SHA256:
            raise ValueError("Candidate X initramfs identity mismatch")
        if len(dtb) != X_DTB_SIZE or digest(dtb) != X_DTB_SHA256:
            raise ValueError("exact Candidate X DTB identity mismatch")
        if len(y_boot) > CAPACITY:
            raise ValueError("Candidate Y exceeds boot2 capacity")

        x_fields, x_ko, x_ke, x_ro, x_re = layout(x_boot)
        y_fields, y_ko, y_ke, y_ro, y_re = layout(y_boot)
        if x_fields[2] != len(x_ramdisk) or y_fields[2] != len(y_ramdisk):
            raise ValueError("ramdisk size/header mismatch")
        if x_boot[x_ro:x_re] != x_ramdisk or y_boot[y_ro:y_re] != y_ramdisk:
            raise ValueError("ramdisk field bytes mismatch")
        if x_boot[x_ko:x_ke] != y_boot[y_ko:y_ke]:
            raise ValueError("Candidate Y kernel field differs from exact X")
        kernel = y_boot[y_ko:y_ke]
        if kernel[-X_DTB_SIZE:] != dtb or digest(kernel[:-X_DTB_SIZE]) != X_IMAGE_GZ_SHA256:
            raise ValueError("Candidate Y kernel is not exact X Image.gz plus DTB")

        # Header must be byte-exact X except ramdisk size and canonical ID.
        expected_header = bytearray(x_boot[:x_fields[7]])
        struct.pack_into("<I", expected_header, 16, len(y_ramdisk))
        image_id = hashlib.sha1()
        for payload in (kernel, y_ramdisk, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        expected_header[576:608] = image_id.digest() + b"\0" * 12
        if y_boot[:y_fields[7]] != bytes(expected_header):
            raise ValueError("Candidate Y Android header has an unrelated delta")
        if any(y_boot[y_ke:y_ro]) or any(y_boot[y_re:]):
            raise ValueError("Candidate Y payload padding is nonzero")
        if len(y_boot) != align(y_re, y_fields[7]):
            raise ValueError("Candidate Y has trailing or missing bytes")

        print("validation=candidate-y-android-v0")
        print(f"candidate_sha256={digest(y_boot)}")
        print(f"candidate_size={len(y_boot)}")
        print(f"initramfs_sha256={digest(y_ramdisk)}")
        print(f"image_gz_sha256={X_IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={X_DTB_SHA256}")
        print("kernel_field=byte-exact-candidate-x")
        print("header_delta=ramdisk-size-and-canonical-id-only")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
