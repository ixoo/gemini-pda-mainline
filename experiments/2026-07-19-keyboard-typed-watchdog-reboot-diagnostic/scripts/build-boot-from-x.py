#!/usr/bin/env python3
"""Build Candidate Y by replacing only exact Candidate X's ramdisk field."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import struct
import sys


X_BOOT_SHA256 = "bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296"
X_BOOT_SIZE = 6_864_896
X_INITRAMFS_SHA256 = "b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769"
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
    parser.add_argument("--x-boot", type=pathlib.Path, required=True)
    parser.add_argument("--x-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--y-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite output")
        x_boot = read_regular(args.x_boot, "Candidate X boot")
        x_ramdisk = read_regular(args.x_initramfs, "Candidate X initramfs")
        y_ramdisk = read_regular(args.y_initramfs, "Candidate Y initramfs")
        if len(x_boot) != X_BOOT_SIZE or digest(x_boot) != X_BOOT_SHA256:
            raise ValueError("Candidate X boot identity mismatch")
        if digest(x_ramdisk) != X_INITRAMFS_SHA256:
            raise ValueError("Candidate X initramfs identity mismatch")
        if x_boot[:8] != b"ANDROID!":
            raise ValueError("Candidate X Android magic mismatch")
        fields = struct.unpack_from("<10I", x_boot, 8)
        kernel_size, _kernel_addr, ramdisk_size = fields[:3]
        second_size, page_size, dt_size = fields[4], fields[7], fields[8]
        if page_size != 2048 or second_size or dt_size or ramdisk_size != len(x_ramdisk):
            raise ValueError("Candidate X Android layout changed")
        kernel_offset = page_size
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end, page_size)
        if x_boot[ramdisk_offset:ramdisk_offset + ramdisk_size] != x_ramdisk:
            raise ValueError("Candidate X ramdisk field mismatch")
        kernel = x_boot[kernel_offset:kernel_end]

        header = bytearray(x_boot[:page_size])
        struct.pack_into("<I", header, 16, len(y_ramdisk))
        image_id = hashlib.sha1()
        for payload in (kernel, y_ramdisk, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        header[576:608] = image_id.digest() + b"\0" * 12
        candidate = bytes(header)
        candidate += kernel
        candidate += b"\0" * (ramdisk_offset - len(candidate))
        candidate += y_ramdisk
        candidate += b"\0" * (align(len(candidate), page_size) - len(candidate))
        if len(candidate) > CAPACITY:
            raise ValueError("Candidate Y exceeds logical boot2 capacity")

        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(candidate)
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"initramfs_sha256={digest(y_ramdisk)}")
        print("kernel_field=byte-exact-candidate-x")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
