#!/usr/bin/env python3
"""Validate Candidate W's exact Android-v0/LK component container."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import struct
import sys


PLACEHOLDER_PREFIX = "REPLACE_AFTER_CALIBRATION_"
IMAGE_GZ_SHA256 = "e5da5fe6c1e4ae21e8005e0638abc938e37526ea872ede2c2163ee07397c8f21"
INITRAMFS_SHA256 = "3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6"
BOOT_SHA256 = "34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4"
BOOT_SIZE_TEXT = "6866944"

V_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
V_DTB_SIZE = 26_259
BOOTOPT = b"bootopt=64S3,32N2,64N2"
HEADER_NAME = b"gemini-obs-L"
CAPACITY = 16 * 1024 * 1024
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def calibrated_constants() -> tuple[str, str, str, int]:
    values = {
        "IMAGE_GZ_SHA256": IMAGE_GZ_SHA256,
        "INITRAMFS_SHA256": INITRAMFS_SHA256,
        "BOOT_SHA256": BOOT_SHA256,
        "BOOT_SIZE_TEXT": BOOT_SIZE_TEXT,
    }
    remaining = [
        name
        for name, value in values.items()
        if value.startswith(PLACEHOLDER_PREFIX)
    ]
    if remaining:
        raise ValueError("calibration placeholder remains: " + ",".join(remaining))
    for name in ("IMAGE_GZ_SHA256", "INITRAMFS_SHA256", "BOOT_SHA256"):
        if HEX256.fullmatch(values[name]) is None:
            raise ValueError(f"invalid calibrated SHA-256 constant: {name}")
    try:
        boot_size = int(BOOT_SIZE_TEXT, 10)
    except ValueError as exc:
        raise ValueError("invalid calibrated boot-size constant") from exc
    if not 0 < boot_size <= CAPACITY:
        raise ValueError("calibrated boot size exceeds the boot2 contract")
    return IMAGE_GZ_SHA256, INITRAMFS_SHA256, BOOT_SHA256, boot_size


def read_regular(path: pathlib.Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        image_pin, initramfs_pin, boot_pin, boot_size_pin = calibrated_constants()
        boot = read_regular(args.candidate, "candidate")
        image_gz = read_regular(args.image_gz, "Image.gz")
        dtb = read_regular(args.dtb, "DTB")
        ramdisk = read_regular(args.initramfs, "initramfs")
        pins = (
            (digest(image_gz), image_pin, "Image.gz"),
            (digest(dtb), V_DTB_SHA256, "exact Candidate V DTB"),
            (digest(ramdisk), initramfs_pin, "Candidate W initramfs"),
        )
        for actual, expected, label in pins:
            if actual != expected:
                raise ValueError(f"{label} hash mismatch")
        if len(dtb) != V_DTB_SIZE:
            raise ValueError("exact Candidate V DTB size mismatch")
        if len(boot) != boot_size_pin or digest(boot) != boot_pin:
            raise ValueError("candidate is not the pinned Candidate W container")
        if len(boot) > CAPACITY:
            raise ValueError("candidate exceeds logical boot2 capacity")
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
        if boot[48:64] != HEADER_NAME.ljust(16, b"\0"):
            raise ValueError("Android name or name-field padding changed")
        if boot[64:576] != BOOTOPT.ljust(512, b"\0"):
            raise ValueError("Android command line or field padding changed")
        if any(boot[608:1632]):
            raise ValueError("Android extra command-line field is nonzero")
        if any(boot[1632:page_size]):
            raise ValueError("Android header padding is nonzero")

        kernel_offset = page_size
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end, page_size)
        ramdisk_end = ramdisk_offset + ramdisk_size
        container_end = align(ramdisk_end, page_size)
        if boot[kernel_offset:kernel_end] != expected_kernel:
            raise ValueError("kernel field is not exact W Image.gz plus V DTB")
        if any(boot[kernel_end:ramdisk_offset]):
            raise ValueError("kernel padding is nonzero")
        if boot[ramdisk_offset:ramdisk_end] != ramdisk:
            raise ValueError("ramdisk field is not exact Candidate W initramfs")
        if any(boot[ramdisk_end:container_end]) or len(boot) != container_end:
            raise ValueError("ramdisk padding or trailing bytes changed")

        sha1 = hashlib.sha1()
        for payload in (expected_kernel, ramdisk, b""):
            sha1.update(payload)
            sha1.update(struct.pack("<I", len(payload)))
        expected_id = sha1.digest() + b"\0" * 12
        if boot[576:608] != expected_id:
            raise ValueError("Android canonical SHA-1 ID mismatch")

        print("validation=candidate-w-android-v0")
        print(f"candidate_sha256={digest(boot)}")
        print(f"candidate_size={len(boot)}")
        print(f"image_gz_sha256={image_pin}")
        print(f"dtb_sha256={V_DTB_SHA256}")
        print(f"initramfs_sha256={initramfs_pin}")
        print("kernel_field=exact-w-image-gz-plus-byte-exact-v-dtb")
        print("ramdisk_field=exact-candidate-w-initramfs")
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
