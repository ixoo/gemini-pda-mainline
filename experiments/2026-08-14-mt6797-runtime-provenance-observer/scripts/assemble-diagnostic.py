#!/usr/bin/env python3
"""Assemble the observer kernel with the exact vendor-RNDIS diagnostic ramdisk."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import stat
import struct
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
PARENT = SCRIPT_DIR.parents[1] / "2026-08-02-gemian-a72-bounded-observer-boot" / "scripts" / "assemble.py"
PARENT_SHA256 = "532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3"
ACTIVE_BOOT_SHA256 = "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513"
KERNEL_FIELD_SHA256 = "d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d"
RAMDISK_SHA256 = "86a112ef29fecdb8f47b003cbfb08b77b478c4f511cba46acd987af09c921358"
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-boot", type=Path, required=True)
    parser.add_argument("--kernel-field", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        print("error: refusing to overwrite output", file=sys.stderr)
        return 2
    try:
        parent_bytes = PARENT.read_bytes()
        if digest(parent_bytes) != PARENT_SHA256:
            raise ValueError("pinned Android-v0 validator changed")
        spec = importlib.util.spec_from_file_location("diagnostic_parent", PARENT)
        if spec is None or spec.loader is None:
            raise ValueError("cannot load pinned Android-v0 validator")
        parent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parent)
        parent.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256

        active = read_regular(args.active_boot, "project-start active boot")
        kernel = read_regular(args.kernel_field, "observer kernel field")
        ramdisk = read_regular(args.ramdisk, "diagnostic ramdisk")
        if len(active) != ACTIVE_SIZE or digest(active) != ACTIVE_BOOT_SHA256:
            raise ValueError("project-start active boot identity changed")
        if digest(kernel) != KERNEL_FIELD_SHA256 or digest(ramdisk) != RAMDISK_SHA256:
            raise ValueError("kernel or diagnostic ramdisk identity changed")
        fields = parent.boot_fields(active)
        if fields[1:] != (
            parent.KERNEL_ADDR,
            fields[2],
            parent.RAMDISK_ADDR,
            0,
            parent.SECOND_ADDR,
            parent.TAGS_ADDR,
            PAGE_SIZE,
            0,
            0,
        ):
            raise ValueError("active Android-v0 layout contract changed")
        if any(active[48:64]) or parent.c_string(active[64:576] + active[608:1632]) != parent.CMDLINE:
            raise ValueError("active Android-v0 string contract changed")
        decompressed_size, appended_dtb_size = parent.validate_kernel_field(kernel)

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
            raise ValueError("raw diagnostic image does not fit boot2")
        result_fields = parent.boot_fields(candidate)
        expected_fields = (len(kernel), fields[1], len(ramdisk)) + fields[3:]
        if result_fields != expected_fields:
            raise ValueError("serialized Android-v0 fields changed")
        ramdisk_offset = align(PAGE_SIZE + len(kernel))
        if candidate[PAGE_SIZE : PAGE_SIZE + len(kernel)] != kernel:
            raise ValueError("serialized kernel mismatch")
        if candidate[ramdisk_offset : ramdisk_offset + len(ramdisk)] != ramdisk:
            raise ValueError("serialized ramdisk mismatch")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(candidate)
        args.output.chmod(0o600)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"output={args.output}")
    print(f"active_boot_sha256={ACTIVE_BOOT_SHA256}")
    print(f"kernel_field_sha256={KERNEL_FIELD_SHA256}")
    print(f"ramdisk_sha256={RAMDISK_SHA256}")
    print(f"decompressed_image_size={decompressed_size}")
    print(f"appended_dtb_size={appended_dtb_size}")
    print(f"raw_size={len(candidate)}")
    print(f"raw_sha256={digest(candidate)}")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
