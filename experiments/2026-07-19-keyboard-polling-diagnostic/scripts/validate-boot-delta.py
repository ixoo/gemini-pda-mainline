#!/usr/bin/env python3
"""Validate Candidate U's exact Android boot-image v0 container contract."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys


P_BOOT_SHA256 = "d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341"
U_BOOT_SHA256 = "aa163793df1f6a82eb18ee71c73c7e8a07696b4fd2f866e34ec9e2703a1905fe"
U_IMAGE_GZ_SHA256 = "af5190f67db72f2e8748a746d2366a359e98331b233733e888323a591c338b86"
U_DTB_SHA256 = "e541c9dffac15de859a876e80409eec4591d36319646845cb25c6eecb8ddf5b1"
U_INITRAMFS_SHA256 = "d05b29071cc8d2be8795c246b527ed315591a2e8e692cf6d050d4c7915783f4f"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def read(path: pathlib.Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline = read(args.baseline, "baseline")
        boot = read(args.candidate, "candidate")
        image_gz = read(args.image_gz, "Image.gz")
        dtb = read(args.dtb, "DTB")
        ramdisk = read(args.initramfs, "initramfs")
        pins = (
            (digest(baseline), P_BOOT_SHA256, "baseline boot"),
            (digest(boot), U_BOOT_SHA256, "candidate boot"),
            (digest(image_gz), U_IMAGE_GZ_SHA256, "Image.gz"),
            (digest(dtb), U_DTB_SHA256, "DTB"),
            (digest(ramdisk), U_INITRAMFS_SHA256, "initramfs"),
        )
        for actual, expected, label in pins:
            if actual != expected:
                raise ValueError(f"{label} hash mismatch: {actual}")
        if boot[:8] != b"ANDROID!":
            raise ValueError("Android magic mismatch")
        values = struct.unpack_from("<10I", boot, 8)
        kernel_size, kernel_addr, ramdisk_size, ramdisk_addr = values[:4]
        second_size, second_addr, tags_addr, page_size, dt_size, unused = values[4:]
        expected_kernel = image_gz + dtb
        if (kernel_addr, ramdisk_addr, second_addr, tags_addr, page_size) != (
            0x40200000, 0x45000000, 0x40F00000, 0x44000000, 2048
        ):
            raise ValueError("Android address/page contract changed")
        if second_size != 0 or dt_size != 0 or unused != 0:
            raise ValueError("second/dt/unused header fields are not zero")
        if kernel_size != len(expected_kernel) or ramdisk_size != len(ramdisk):
            raise ValueError("header payload size mismatch")
        name = boot[48:64].split(b"\0", 1)[0]
        cmdline = boot[64:576].split(b"\0", 1)[0]
        extra = boot[608:1632].split(b"\0", 1)[0]
        if name != b"gemini-obs-L" or cmdline != b"bootopt=64S3,32N2,64N2" or extra:
            raise ValueError("Android name or command line changed")
        if any(boot[1632:page_size]):
            raise ValueError("nonzero Android header padding")
        kernel_offset = page_size
        ramdisk_offset = kernel_offset + align(kernel_size, page_size)
        end = ramdisk_offset + align(ramdisk_size, page_size)
        if boot[kernel_offset:kernel_offset + kernel_size] != expected_kernel:
            raise ValueError("kernel field is not exact Image.gz plus U DTB")
        if any(boot[kernel_offset + kernel_size:ramdisk_offset]):
            raise ValueError("nonzero kernel padding")
        if boot[ramdisk_offset:ramdisk_offset + ramdisk_size] != ramdisk:
            raise ValueError("ramdisk field is not exact U initramfs")
        if any(boot[ramdisk_offset + ramdisk_size:end]) or len(boot) != end:
            raise ValueError("nonzero ramdisk padding or trailing bytes")
        sha1 = hashlib.sha1()
        for payload in (expected_kernel, ramdisk, b""):
            sha1.update(payload)
            sha1.update(struct.pack("<I", len(payload)))
        expected_id = sha1.digest() + b"\0" * 12
        if boot[576:608] != expected_id:
            raise ValueError("Android canonical SHA-1 ID mismatch")
        print("validation=candidate-u-android-v0-delta")
        print(f"baseline_boot_sha256={P_BOOT_SHA256}")
        print(f"candidate_boot_sha256={U_BOOT_SHA256}")
        print(f"kernel_size={kernel_size}")
        print(f"ramdisk_size={ramdisk_size}")
        print("kernel_field=image-gz-plus-u-dtb")
        print("ramdisk_field=exact-u-initramfs")
        print("page_size=2048")
        print("name=gemini-obs-L")
        print("cmdline=bootopt=64S3,32N2,64N2")
        print("second_payload=empty")
        print("padding=zero")
        print("canonical_id=passed")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
