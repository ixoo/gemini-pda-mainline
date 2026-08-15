#!/usr/bin/env python3
"""Assemble the validated pre-init kernel with the corrected observation ramdisk."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import stat
import struct
import sys
import zlib


SCRIPT_DIR = Path(__file__).resolve().parent
PARENT = (
    SCRIPT_DIR.parents[1]
    / "2026-08-02-gemian-a72-bounded-observer-boot"
    / "scripts"
    / "assemble.py"
)
PARENT_SHA256 = "532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3"
ACTIVE_BOOT_SHA256 = "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513"
REFERENCE_RAW_SHA256 = "1d303dda10b47248f51a1fb2c8f3b1a7b8098522536f4f54ff763c17e75ff310"
REFERENCE_KERNEL_SHA256 = "d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d"
KERNEL_FIELD_SHA256 = "5a8db7fba3b4eb83932042e1105039157d4c8bb70c5794c00b03f9ac46526725"
RAMDISK_SHA256 = "86a112ef29fecdb8f47b003cbfb08b77b478c4f511cba46acd987af09c921358"
APPENDED_DTB_SHA256 = "d70cb5f679ca1135280b80cfc0308e9c4c74bf6a5b8b1a0a8c281a50d4a3d787"
ACTIVE_SIZE = 16 * 1024 * 1024
PAGE_SIZE = 2048


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def align(value: int) -> int:
    return (value + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def appended_dtb(kernel: bytes) -> bytes:
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decompressor.decompress(kernel)
    decompressor.flush()
    if not decompressor.eof or decompressor.unconsumed_tail:
        raise ValueError("kernel gzip stream is incomplete")
    dtb = decompressor.unused_data
    if len(dtb) < 8 or dtb[:4] != b"\xd0\x0d\xfe\xed":
        raise ValueError("kernel field lacks an appended DTB")
    if struct.unpack_from(">I", dtb, 4)[0] != len(dtb):
        raise ValueError("appended DTB does not consume the kernel suffix")
    return dtb


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-boot", type=Path, required=True)
    parser.add_argument("--kernel-field", type=Path, required=True)
    parser.add_argument("--corrected-raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        print("error: refusing to overwrite output", file=sys.stderr)
        return 2
    try:
        parent_bytes = PARENT.read_bytes()
        if digest(parent_bytes) != PARENT_SHA256:
            raise ValueError("pinned Android-v0 assembler changed")
        spec = importlib.util.spec_from_file_location("preinit_parent", PARENT)
        if spec is None or spec.loader is None:
            raise ValueError("cannot load pinned Android-v0 assembler")
        parent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parent)

        active = read_regular(args.active_boot, "project-start active boot")
        kernel = read_regular(args.kernel_field, "pre-init kernel field")
        reference = read_regular(args.corrected_raw, "corrected observation image")
        if len(active) != ACTIVE_SIZE or digest(active) != ACTIVE_BOOT_SHA256:
            raise ValueError("project-start active boot identity changed")
        if digest(reference) != REFERENCE_RAW_SHA256:
            raise ValueError("corrected observation image identity changed")
        if digest(kernel) != KERNEL_FIELD_SHA256:
            raise ValueError("pre-init kernel field identity changed")

        active_fields = parent.boot_fields(active)
        reference_fields = parent.boot_fields(reference)
        layout_indexes = (1, 3, 4, 5, 6, 7, 8, 9)
        if tuple(reference_fields[index] for index in layout_indexes) != tuple(
            active_fields[index] for index in layout_indexes
        ):
            raise ValueError("corrected observation layout differs from active boot")
        reference_kernel = reference[PAGE_SIZE : PAGE_SIZE + reference_fields[0]]
        ramdisk_offset = align(PAGE_SIZE + reference_fields[0])
        ramdisk = reference[ramdisk_offset : ramdisk_offset + reference_fields[2]]
        if digest(reference_kernel) != REFERENCE_KERNEL_SHA256:
            raise ValueError("corrected observation kernel identity changed")
        if digest(ramdisk) != RAMDISK_SHA256:
            raise ValueError("corrected observation ramdisk identity changed")
        if reference[48:576] != active[48:576]:
            raise ValueError("corrected observation header strings changed")
        if any(reference[PAGE_SIZE + len(reference_kernel) : ramdisk_offset]):
            raise ValueError("corrected observation kernel padding changed")
        if any(reference[ramdisk_offset + len(ramdisk) :]):
            raise ValueError("corrected observation ramdisk padding changed")

        parent.KERNEL_FIELD_SHA256 = REFERENCE_KERNEL_SHA256
        parent.validate_kernel_field(reference_kernel)
        parent.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
        decompressed_size, appended_dtb_size = parent.validate_kernel_field(kernel)
        reference_dtb = appended_dtb(reference_kernel)
        new_dtb = appended_dtb(kernel)
        if reference_dtb != new_dtb or digest(new_dtb) != APPENDED_DTB_SHA256:
            raise ValueError("appended DTB differs from corrected observation image")

        header = bytearray(active[:PAGE_SIZE])
        struct.pack_into("<I", header, 8, len(kernel))
        struct.pack_into("<I", header, 16, len(ramdisk))
        image_id = hashlib.sha1(usedforsecurity=False)
        for payload in (kernel, ramdisk, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        header[576:596] = image_id.digest()

        candidate = bytearray(header)
        candidate.extend(kernel)
        candidate.extend(b"\0" * (align(len(candidate)) - len(candidate)))
        candidate.extend(ramdisk)
        candidate.extend(b"\0" * (align(len(candidate)) - len(candidate)))
        if len(candidate) >= ACTIVE_SIZE:
            raise ValueError("raw pre-init image does not fit boot2")
        expected_fields = (len(kernel), active_fields[1], len(ramdisk)) + active_fields[3:]
        if parent.boot_fields(candidate) != expected_fields:
            raise ValueError("serialized Android-v0 fields changed")
        new_ramdisk_offset = align(PAGE_SIZE + len(kernel))
        if candidate[PAGE_SIZE : PAGE_SIZE + len(kernel)] != kernel:
            raise ValueError("serialized pre-init kernel mismatch")
        if candidate[new_ramdisk_offset : new_ramdisk_offset + len(ramdisk)] != ramdisk:
            raise ValueError("serialized corrected ramdisk mismatch")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(candidate)
        args.output.chmod(0o600)
    except (OSError, ValueError, zlib.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"output={args.output}")
    print(f"active_boot_sha256={ACTIVE_BOOT_SHA256}")
    print(f"corrected_raw_sha256={REFERENCE_RAW_SHA256}")
    print(f"reference_kernel_sha256={REFERENCE_KERNEL_SHA256}")
    print(f"kernel_field_sha256={KERNEL_FIELD_SHA256}")
    print(f"ramdisk_sha256={RAMDISK_SHA256}")
    print(f"appended_dtb_sha256={APPENDED_DTB_SHA256}")
    print(f"decompressed_image_size={decompressed_size}")
    print(f"appended_dtb_size={appended_dtb_size}")
    print(f"raw_size={len(candidate)}")
    print(f"raw_sha256={digest(candidate)}")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
