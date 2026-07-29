#!/usr/bin/env python3
"""Build Photon by replacing only exact Cassini's Android-v0 ramdisk field."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import struct
import sys

sys.dont_write_bytecode = True
import candidate_photon as cp


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def publish(path: pathlib.Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite output")
    parent = path.parent.resolve(strict=True)
    if path.parent.is_symlink() or not parent.is_dir():
        raise ValueError("output parent is unsafe")
    output = parent / path.name
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)


def build(
    cassini_boot_path: pathlib.Path,
    cassini_initramfs_path: pathlib.Path,
    photon_initramfs_path: pathlib.Path,
) -> bytes:
    boot = read_regular(cassini_boot_path, "exact Cassini boot")
    old_ramdisk = read_regular(cassini_initramfs_path, "exact Cassini initramfs")
    new_ramdisk = read_regular(photon_initramfs_path, "Photon initramfs")
    if len(boot) != cp.CASSINI_BOOT_SIZE or digest(boot) != cp.CASSINI_BOOT_SHA256:
        raise ValueError("Cassini boot identity mismatch")
    if digest(old_ramdisk) != cp.CASSINI_INITRAMFS_SHA256:
        raise ValueError("Cassini initramfs identity mismatch")
    if cp.HEX256.fullmatch(cp.INITRAMFS_SHA256) is not None:
        if digest(new_ramdisk) != cp.INITRAMFS_SHA256:
            raise ValueError("calibrated Photon initramfs changed")
    if boot[:8] != b"ANDROID!":
        raise ValueError("Cassini Android magic mismatch")

    fields = struct.unpack_from("<10I", boot, 8)
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
        _unused,
    ) = fields
    if (
        kernel_size != cp.CASSINI_KERNEL_FIELD_SIZE
        or kernel_addr != 0x40200000
        or ramdisk_size != len(old_ramdisk)
        or ramdisk_addr != 0x45000000
        or second_size
        or second_addr != 0x40F00000
        or tags_addr != 0x44000000
        or page_size != cp.BOOT_PAGE_SIZE
        or dt_size
    ):
        raise ValueError("Cassini Android-v0 layout changed")
    if boot[48:64] != cp.BOOT_NAME.encode() + b"\0" * 2:
        raise ValueError("Cassini Android header name changed")
    expected_cmdline = cp.BOOT_CMDLINE.encode()
    if boot[64:576] != expected_cmdline + b"\0" * (512 - len(expected_cmdline)):
        raise ValueError("Cassini Android command line changed")

    kernel_offset = page_size
    kernel_end = kernel_offset + kernel_size
    ramdisk_offset = align(kernel_end, page_size)
    if ramdisk_offset != cp.CASSINI_RAMDISK_OFFSET:
        raise ValueError("Cassini ramdisk offset changed")
    kernel = boot[kernel_offset:kernel_end]
    if digest(kernel) != cp.CASSINI_KERNEL_FIELD_SHA256:
        raise ValueError("Cassini combined kernel field changed")
    if any(boot[kernel_end:ramdisk_offset]):
        raise ValueError("Cassini pre-ramdisk padding is not zero")
    if boot[ramdisk_offset : ramdisk_offset + ramdisk_size] != old_ramdisk:
        raise ValueError("Cassini ramdisk field mismatch")
    if any(boot[ramdisk_offset + ramdisk_size :]):
        raise ValueError("Cassini final padding is not zero")

    header = bytearray(boot[:page_size])
    struct.pack_into("<I", header, 16, len(new_ramdisk))
    image_id = hashlib.sha1()
    for payload in (kernel, new_ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    header[576:608] = image_id.digest() + b"\0" * 12

    candidate = bytes(header)
    candidate += kernel
    candidate += b"\0" * (ramdisk_offset - len(candidate))
    candidate += new_ramdisk
    candidate += b"\0" * (align(len(candidate), page_size) - len(candidate))
    if len(candidate) > cp.BOOT2_SIZE:
        raise ValueError("Photon exceeds logical boot2 capacity")
    if candidate[kernel_offset:kernel_end] != kernel:
        raise ValueError("Photon changed the Cassini kernel field")
    if cp.HEX256.fullmatch(cp.RAW_SHA256) is not None:
        if digest(candidate) != cp.RAW_SHA256:
            raise ValueError("calibrated Photon raw image changed")
    if cp.RAW_SIZE != "UNRESOLVED":
        if not cp.RAW_SIZE.isdecimal() or len(candidate) != int(cp.RAW_SIZE):
            raise ValueError("calibrated Photon raw size changed")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cassini-boot", type=pathlib.Path, required=True)
    parser.add_argument("--cassini-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--photon-initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = build(
            args.cassini_boot,
            args.cassini_initramfs,
            args.photon_initramfs,
        )
        publish(args.output, candidate)
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=photon-direct-cassini-ramdisk-replacement")
    print(f"candidate_sha256={digest(candidate)}")
    print(f"candidate_size={len(candidate)}")
    print(f"initramfs_sha256={cp.digest_path(args.photon_initramfs)}")
    print(f"kernel_field_sha256={cp.CASSINI_KERNEL_FIELD_SHA256}")
    print("header_identity=gemini-cassini-preserved")
    print("changed_android_fields=ramdisk-size,image-id,ramdisk-bytes,final-padding")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
