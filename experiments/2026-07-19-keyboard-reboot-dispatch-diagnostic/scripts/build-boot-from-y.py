#!/usr/bin/env python3
"""Build Candidate Z by replacing only exact Candidate Y's ramdisk field."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import struct
import sys


Y_BOOT_SHA256 = "94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee"
Y_BOOT_SIZE = 6_866_944
Y_INITRAMFS_SHA256 = "11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--y-boot", type=pathlib.Path, required=True)
    parser.add_argument("--y-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--z-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite output")
        y_boot = read_regular(args.y_boot, "Candidate Y boot")
        y_ramdisk = read_regular(args.y_initramfs, "Candidate Y initramfs")
        z_ramdisk = read_regular(args.z_initramfs, "Candidate Z initramfs")
        if len(y_boot) != Y_BOOT_SIZE or digest(y_boot) != Y_BOOT_SHA256:
            raise ValueError("Candidate Y boot identity mismatch")
        if digest(y_ramdisk) != Y_INITRAMFS_SHA256:
            raise ValueError("Candidate Y initramfs identity mismatch")
        if y_boot[:8] != b"ANDROID!":
            raise ValueError("Candidate Y Android magic mismatch")
        fields = struct.unpack_from("<10I", y_boot, 8)
        kernel_size, _kernel_addr, ramdisk_size = fields[:3]
        second_size, page_size, dt_size = fields[4], fields[7], fields[8]
        if page_size != 2048 or second_size or dt_size or ramdisk_size != len(y_ramdisk):
            raise ValueError("Candidate Y Android layout changed")
        kernel_offset = page_size
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end, page_size)
        if y_boot[ramdisk_offset:ramdisk_offset + ramdisk_size] != y_ramdisk:
            raise ValueError("Candidate Y ramdisk field mismatch")
        kernel = y_boot[kernel_offset:kernel_end]

        header = bytearray(y_boot[:page_size])
        struct.pack_into("<I", header, 16, len(z_ramdisk))
        image_id = hashlib.sha1()
        for payload in (kernel, z_ramdisk, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        header[576:608] = image_id.digest() + b"\0" * 12
        candidate = bytes(header)
        candidate += kernel
        candidate += b"\0" * (ramdisk_offset - len(candidate))
        candidate += z_ramdisk
        candidate += b"\0" * (align(len(candidate), page_size) - len(candidate))
        if len(candidate) > CAPACITY:
            raise ValueError("Candidate Z exceeds logical boot2 capacity")

        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(candidate)
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"initramfs_sha256={digest(z_ramdisk)}")
        print("kernel_field=byte-exact-candidate-y")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
