#!/usr/bin/env python3
"""Validate Candidate V's exact Android-v0/LK component container."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys


BOOTOPT = b"bootopt=64S3,32N2,64N2"
HEADER_NAME = b"gemini-obs-L"
CAPACITY = 16 * 1024 * 1024
IMAGE_GZ_SHA256 = "69095483a984eb05a94e5ae212aeeb87cc3ffbded2d753f09f89661972ed89a3"
DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
INITRAMFS_SHA256 = "9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6"
BOOT_SHA256 = "9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0"
BOOT_SIZE = 6_864_896


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        boot = args.candidate.read_bytes()
        image_gz = args.image_gz.read_bytes()
        dtb = args.dtb.read_bytes()
        ramdisk = args.initramfs.read_bytes()
        pins = (
            (digest(image_gz), IMAGE_GZ_SHA256, "Image.gz"),
            (digest(dtb), DTB_SHA256, "DTB"),
            (digest(ramdisk), INITRAMFS_SHA256, "initramfs"),
        )
        for actual, expected, label in pins:
            if actual != expected:
                raise ValueError(f"{label} hash mismatch")
        if len(boot) > CAPACITY:
            raise ValueError("candidate exceeds logical boot2 capacity")
        if len(boot) != BOOT_SIZE or digest(boot) != BOOT_SHA256:
            raise ValueError("candidate is not the pinned Candidate V container")
        if len(boot) < 2048 or boot[:8] != b"ANDROID!":
            raise ValueError("Android magic or minimum header size mismatch")

        values = struct.unpack_from("<10I", boot, 8)
        kernel_size, kernel_addr, ramdisk_size, ramdisk_addr = values[:4]
        second_size, second_addr, tags_addr, page_size, dt_size, unused = values[4:]
        expected_kernel = image_gz + dtb
        if (kernel_addr, ramdisk_addr, second_addr, tags_addr, page_size) != (
            0x40200000,
            0x45000000,
            0x40F00000,
            0x44000000,
            2048,
        ):
            raise ValueError("Android address or page contract changed")
        if second_size != 0 or dt_size != 0 or unused != 0:
            raise ValueError("second, DT, or unused header field is nonzero")
        if kernel_size != len(expected_kernel) or ramdisk_size != len(ramdisk):
            raise ValueError("header payload size mismatch")
        name = boot[48:64].split(b"\0", 1)[0]
        cmdline = boot[64:576].split(b"\0", 1)[0]
        extra = boot[608:1632].split(b"\0", 1)[0]
        if name != HEADER_NAME or cmdline != BOOTOPT or extra:
            raise ValueError("Android name or command line changed")
        if any(boot[1632:page_size]):
            raise ValueError("Android header padding is nonzero")

        kernel_offset = page_size
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end, page_size)
        ramdisk_end = ramdisk_offset + ramdisk_size
        end = align(ramdisk_end, page_size)
        if boot[kernel_offset:kernel_end] != expected_kernel:
            raise ValueError("kernel field is not exact Image.gz plus Candidate V DTB")
        if any(boot[kernel_end:ramdisk_offset]):
            raise ValueError("kernel padding is nonzero")
        if boot[ramdisk_offset:ramdisk_end] != ramdisk:
            raise ValueError("ramdisk field is not exact Candidate V initramfs")
        if any(boot[ramdisk_end:end]) or len(boot) != end:
            raise ValueError("ramdisk padding or trailing bytes changed")

        sha1 = hashlib.sha1()
        for payload in (expected_kernel, ramdisk, b""):
            sha1.update(payload)
            sha1.update(struct.pack("<I", len(payload)))
        expected_id = sha1.digest() + b"\0" * 12
        if boot[576:608] != expected_id:
            raise ValueError("Android canonical SHA-1 ID mismatch")

        print("validation=candidate-v-android-v0")
        print(f"candidate_sha256={digest(boot)}")
        print(f"candidate_size={len(boot)}")
        print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={DTB_SHA256}")
        print(f"initramfs_sha256={INITRAMFS_SHA256}")
        print("kernel_field=image-gz-plus-candidate-v-dtb")
        print("ramdisk_field=exact-candidate-v-initramfs")
        print("page_size=2048")
        print("name=gemini-obs-L")
        print("cmdline=bootopt=64S3,32N2,64N2")
        print("padding=zero")
        print("canonical_id=passed")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
