#!/usr/bin/env python3
"""Validate Candidate AD's canonical Android-v0 container and AC lineage."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import stat
import struct
import sys
import zlib


PAGE_SIZE = 2048
BOOT2_CAPACITY = 16 * 1024 * 1024
KERNEL_ADDR = 0x40200000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
NAME = "gemini-obs-L"
CMDLINE = "bootopt=64S3,32N2,64N2"
AC_IMAGE_GZ_SHA256 = "37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f"
AC_INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AC_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def align(value: int) -> int:
    return (value + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def put_string(header: bytearray, offset: int, size: int, value: str) -> None:
    encoded = value.encode("ascii")
    if len(encoded) >= size:
        raise ValueError("canonical string is oversized")
    header[offset : offset + size] = encoded + b"\0" * (size - len(encoded))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = read_regular(args.candidate, "Candidate AD boot")
        image_gz = read_regular(args.image_gz, "Candidate AD Image.gz")
        dtb = read_regular(args.dtb, "exact AC final DTB")
        initramfs = read_regular(args.initramfs, "exact AC initramfs")
        if digest(image_gz) == AC_IMAGE_GZ_SHA256:
            raise ValueError("Candidate AD retained the CPU0-only AC kernel")
        if digest(dtb) != AC_DTB_SHA256 or digest(initramfs) != AC_INITRAMFS_SHA256:
            raise ValueError("exact AC runtime payload changed")
        if not gzip.decompress(image_gz):
            raise ValueError("Candidate AD Image.gz expands empty")
        if not 0 < len(candidate) <= BOOT2_CAPACITY:
            raise ValueError("Candidate AD size is invalid or exceeds boot2")
        if len(candidate) < PAGE_SIZE or candidate[:8] != b"ANDROID!":
            raise ValueError("Candidate AD is not Android boot image v0")

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
            raise ValueError("Android-v0 layout changed")

        kernel = image_gz + dtb
        if kernel_size != len(kernel) or ramdisk_size != len(initramfs):
            raise ValueError("Android-v0 payload sizes changed")
        kernel_offset = PAGE_SIZE
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end)
        ramdisk_end = ramdisk_offset + ramdisk_size
        if candidate[kernel_offset:kernel_end] != kernel:
            raise ValueError("kernel field is not AD Image.gz plus exact AC DTB")
        if candidate[ramdisk_offset:ramdisk_end] != initramfs:
            raise ValueError("ramdisk field is not exact AC initramfs")
        if any(candidate[kernel_end:ramdisk_offset]) or any(candidate[ramdisk_end:]):
            raise ValueError("Android-v0 padding is not zero")
        if len(candidate) != align(ramdisk_end):
            raise ValueError("Android-v0 trailing length changed")

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
            raise ValueError("Android-v0 header is not canonical")

        print("validation=candidate-ad-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={digest(image_gz)}")
        print(f"initramfs_sha256={AC_INITRAMFS_SHA256}")
        print(f"dtb_sha256={AC_DTB_SHA256}")
        print("kernel_delta=image-gz-only")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, gzip.BadGzipFile, struct.error, zlib.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
