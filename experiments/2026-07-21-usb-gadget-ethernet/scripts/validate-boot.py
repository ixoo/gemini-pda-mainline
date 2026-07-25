#!/usr/bin/env python3
"""Validate Candidate AC's canonical LK-compatible Android-v0 container."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import struct
import sys
import zlib

from ac_contract import (
    AB_DTB_SHA256,
    AB_DTB_SIZE,
    AB_IMAGE_GZ_SHA256,
    AB_IMAGE_GZ_SIZE,
    BOOT2_CAPACITY,
    digest_bytes,
    read_regular,
)


PAGE_SIZE = 2048
KERNEL_ADDR = 0x40200000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
NAME = "gemini-obs-L"
CMDLINE = "bootopt=64S3,32N2,64N2"


def align(value: int, boundary: int = PAGE_SIZE) -> int:
    return (value + boundary - 1) // boundary * boundary


def put_string(header: bytearray, offset: int, size: int, value: str) -> None:
    encoded = value.encode("ascii")
    if len(encoded) >= size:
        raise ValueError("canonical Android-v0 string is oversized")
    header[offset : offset + size] = encoded + b"\0" * (size - len(encoded))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = read_regular(args.candidate, "AC boot container")
        image_gz = read_regular(
            args.image_gz, "exact AB Image.gz", size=AB_IMAGE_GZ_SIZE
        )
        dtb = read_regular(args.dtb, "exact AB DTB", size=AB_DTB_SIZE)
        initramfs = read_regular(args.initramfs, "validated AC initramfs")
        if digest_bytes(image_gz) != AB_IMAGE_GZ_SHA256:
            raise ValueError("exact hardware-passed AB Image.gz changed")
        if digest_bytes(dtb) != AB_DTB_SHA256:
            raise ValueError("exact hardware-passed AB DTB changed")
        if not gzip.decompress(image_gz):
            raise ValueError("exact AB Image.gz expands to an empty Image")
        if not initramfs:
            raise ValueError("Candidate AC initramfs is empty")
        if len(candidate) > BOOT2_CAPACITY:
            raise ValueError("Candidate AC exceeds logical boot2 capacity")
        if len(candidate) < PAGE_SIZE or candidate[:8] != b"ANDROID!":
            raise ValueError("Candidate AC is not Android boot image v0")

        fields = struct.unpack_from("<10I", candidate, 8)
        (
            kernel_size,
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
            raise ValueError("Candidate AC Android-v0 address/layout contract changed")

        kernel = image_gz + dtb
        if kernel_size != len(kernel) or ramdisk_size != len(initramfs):
            raise ValueError("Candidate AC header payload sizes changed")
        kernel_offset = PAGE_SIZE
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end)
        ramdisk_end = ramdisk_offset + ramdisk_size
        if candidate[kernel_offset:kernel_end] != kernel:
            raise ValueError("AC kernel field is not exact AB Image.gz plus AB DTB")
        if candidate[ramdisk_offset:ramdisk_end] != initramfs:
            raise ValueError("AC ramdisk field differs from validated initramfs")
        if any(candidate[kernel_end:ramdisk_offset]) or any(candidate[ramdisk_end:]):
            raise ValueError("Candidate AC Android-v0 padding is not zero")
        if len(candidate) != align(ramdisk_end):
            raise ValueError("Candidate AC has trailing or missing bytes")

        image_id = hashlib.sha1(usedforsecurity=False)
        for payload in (kernel, initramfs, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        expected_header = bytearray(PAGE_SIZE)
        struct.pack_into("<8s10I", expected_header, 0, b"ANDROID!", *fields)
        put_string(expected_header, 48, 16, NAME)
        command_line = CMDLINE.encode("ascii")
        expected_header[64:576] = command_line[:512].ljust(512, b"\0")
        expected_header[608:1632] = command_line[512:].ljust(1024, b"\0")
        expected_header[576:596] = image_id.digest()
        if candidate[:PAGE_SIZE] != expected_header:
            raise ValueError("Candidate AC Android-v0 header is not canonical")

        print("validation=candidate-ac-android-v0")
        print(f"candidate_sha256={digest_bytes(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"initramfs_sha256={digest_bytes(initramfs)}")
        print(f"image_gz_sha256={AB_IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={AB_DTB_SHA256}")
        print("kernel_field=exact-hardware-passed-ab-image-gz-plus-ab-dtb")
        print("android_header=canonical-v0")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        gzip.BadGzipFile,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
