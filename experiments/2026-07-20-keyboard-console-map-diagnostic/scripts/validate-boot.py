#!/usr/bin/env python3
"""Validate Candidate AA as an exact-Z kernel/DT Android-v0 ramdisk delta."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import stat
import struct
import sys


Z_BOOT_SHA256 = "985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9"
Z_BOOT_SIZE = 6_866_944
Z_INITRAMFS_SHA256 = "a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2"
Z_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
Z_DTB_SIZE = 26_259
Z_IMAGE_GZ_SHA256 = "d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"
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
    parser.add_argument("--z-boot", type=pathlib.Path, required=True)
    parser.add_argument("--z-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--aa-boot", type=pathlib.Path, required=True)
    parser.add_argument("--aa-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        z_boot = read_regular(args.z_boot, "Candidate Z boot")
        z_ramdisk = read_regular(args.z_initramfs, "Candidate Z initramfs")
        aa_boot = read_regular(args.aa_boot, "Candidate AA boot")
        aa_ramdisk = read_regular(args.aa_initramfs, "Candidate AA initramfs")
        dtb = read_regular(args.dtb, "exact Candidate Z DTB")
        if len(z_boot) != Z_BOOT_SIZE or digest(z_boot) != Z_BOOT_SHA256:
            raise ValueError("Candidate Z boot identity mismatch")
        if digest(z_ramdisk) != Z_INITRAMFS_SHA256:
            raise ValueError("Candidate Z initramfs identity mismatch")
        if len(dtb) != Z_DTB_SIZE or digest(dtb) != Z_DTB_SHA256:
            raise ValueError("exact Candidate Z DTB identity mismatch")
        if len(aa_boot) > CAPACITY:
            raise ValueError("Candidate AA exceeds boot2 capacity")

        z_fields, z_ko, z_ke, z_ro, z_re = layout(z_boot)
        aa_fields, aa_ko, aa_ke, aa_ro, aa_re = layout(aa_boot)
        if z_fields[2] != len(z_ramdisk) or aa_fields[2] != len(aa_ramdisk):
            raise ValueError("ramdisk size/header mismatch")
        if z_boot[z_ro:z_re] != z_ramdisk or aa_boot[aa_ro:aa_re] != aa_ramdisk:
            raise ValueError("ramdisk field bytes mismatch")
        if z_boot[z_ko:z_ke] != aa_boot[aa_ko:aa_ke]:
            raise ValueError("Candidate AA kernel field differs from exact Z")
        kernel = aa_boot[aa_ko:aa_ke]
        if kernel[-Z_DTB_SIZE:] != dtb or digest(kernel[:-Z_DTB_SIZE]) != Z_IMAGE_GZ_SHA256:
            raise ValueError("Candidate AA kernel is not exact Z Image.gz plus DTB")

        expected_header = bytearray(z_boot[: z_fields[7]])
        struct.pack_into("<I", expected_header, 16, len(aa_ramdisk))
        image_id = hashlib.sha1()
        for payload in (kernel, aa_ramdisk, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        expected_header[576:608] = image_id.digest() + b"\0" * 12
        if aa_boot[: aa_fields[7]] != bytes(expected_header):
            raise ValueError("Candidate AA Android header has an unrelated delta")
        if any(aa_boot[aa_ke:aa_ro]) or any(aa_boot[aa_re:]):
            raise ValueError("Candidate AA payload padding is nonzero")
        if len(aa_boot) != align(aa_re, aa_fields[7]):
            raise ValueError("Candidate AA has trailing or missing bytes")

        print("validation=candidate-aa-android-v0")
        print(f"candidate_sha256={digest(aa_boot)}")
        print(f"candidate_size={len(aa_boot)}")
        print(f"initramfs_sha256={digest(aa_ramdisk)}")
        print(f"image_gz_sha256={Z_IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={Z_DTB_SHA256}")
        print("kernel_field=byte-exact-candidate-z")
        print("header_delta=ramdisk-size-and-canonical-id-only")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
