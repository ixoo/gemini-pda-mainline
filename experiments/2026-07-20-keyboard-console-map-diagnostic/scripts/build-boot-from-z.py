#!/usr/bin/env python3
"""Build Candidate AA by replacing only exact Candidate Z's ramdisk field."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import struct
import sys


Z_BOOT_SHA256 = "985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9"
Z_BOOT_SIZE = 6_866_944
Z_INITRAMFS_SHA256 = "a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2"
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
    parser.add_argument("--z-boot", type=pathlib.Path, required=True)
    parser.add_argument("--z-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--aa-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite output")
        z_boot = read_regular(args.z_boot, "Candidate Z boot")
        z_ramdisk = read_regular(args.z_initramfs, "Candidate Z initramfs")
        aa_ramdisk = read_regular(args.aa_initramfs, "Candidate AA initramfs")
        if len(z_boot) != Z_BOOT_SIZE or digest(z_boot) != Z_BOOT_SHA256:
            raise ValueError("Candidate Z boot identity mismatch")
        if digest(z_ramdisk) != Z_INITRAMFS_SHA256:
            raise ValueError("Candidate Z initramfs identity mismatch")
        if z_boot[:8] != b"ANDROID!":
            raise ValueError("Candidate Z Android magic mismatch")
        fields = struct.unpack_from("<10I", z_boot, 8)
        kernel_size, _kernel_addr, ramdisk_size = fields[:3]
        second_size, page_size, dt_size = fields[4], fields[7], fields[8]
        if page_size != 2048 or second_size or dt_size or ramdisk_size != len(z_ramdisk):
            raise ValueError("Candidate Z Android layout changed")
        kernel_offset = page_size
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end, page_size)
        if z_boot[ramdisk_offset : ramdisk_offset + ramdisk_size] != z_ramdisk:
            raise ValueError("Candidate Z ramdisk field mismatch")
        kernel = z_boot[kernel_offset:kernel_end]

        header = bytearray(z_boot[:page_size])
        struct.pack_into("<I", header, 16, len(aa_ramdisk))
        image_id = hashlib.sha1()
        for payload in (kernel, aa_ramdisk, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        header[576:608] = image_id.digest() + b"\0" * 12
        candidate = bytes(header)
        candidate += kernel
        candidate += b"\0" * (ramdisk_offset - len(candidate))
        candidate += aa_ramdisk
        candidate += b"\0" * (align(len(candidate), page_size) - len(candidate))
        if len(candidate) > CAPACITY:
            raise ValueError("Candidate AA exceeds logical boot2 capacity")

        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(candidate)
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"initramfs_sha256={digest(aa_ramdisk)}")
        print("kernel_field=byte-exact-candidate-z")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
