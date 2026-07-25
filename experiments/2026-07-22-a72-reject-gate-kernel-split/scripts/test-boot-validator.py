#!/usr/bin/env python3
"""Exercise Candidate AI's Android-v0 validator without final artifacts."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import pathlib
import struct
import sys

sys.dont_write_bytecode = True


def load_validator() -> object:
    source = pathlib.Path(__file__).resolve().with_name("validate-boot.py")
    spec = importlib.util.spec_from_file_location("gemini_ai_boot_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AI boot validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def serialize(
    validator: object,
    image_gz: bytes,
    dtb: bytes,
    initramfs: bytes,
    *,
    kernel_addr: int | None = None,
    ramdisk_addr: int | None = None,
    second_addr: int | None = None,
    tags_addr: int | None = None,
    page_size: int | None = None,
    second_size: int = 0,
    dt_size: int = 0,
    name: str | None = None,
    cmdline: str | None = None,
) -> bytes:
    page = validator.PAGE_SIZE if page_size is None else page_size
    kernel = image_gz + dtb
    fields = (
        len(kernel),
        validator.KERNEL_ADDR if kernel_addr is None else kernel_addr,
        len(initramfs),
        validator.RAMDISK_ADDR if ramdisk_addr is None else ramdisk_addr,
        second_size,
        validator.SECOND_ADDR if second_addr is None else second_addr,
        validator.TAGS_ADDR if tags_addr is None else tags_addr,
        page,
        dt_size,
        0,
    )
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, initramfs, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    header = bytearray(validator.PAGE_SIZE)
    struct.pack_into("<8s10I", header, 0, b"ANDROID!", *fields)
    name_bytes = (validator.NAME if name is None else name).encode("ascii")
    command_bytes = (validator.CMDLINE if cmdline is None else cmdline).encode("ascii")
    header[48:64] = name_bytes.ljust(16, b"\0")
    header[64:576] = command_bytes[:512].ljust(512, b"\0")
    header[576:596] = image_id.digest()
    header[608:1632] = command_bytes[512:].ljust(1024, b"\0")
    output = bytes(header) + kernel
    output += b"\0" * (validator.align(len(output)) - len(output))
    output += initramfs
    output += b"\0" * (validator.align(len(output)) - len(output))
    return output


def expect_rejected(function: object, *args: object) -> None:
    try:
        function(*args)  # type: ignore[operator]
    except (ValueError, gzip.BadGzipFile):
        return
    raise ValueError("boot mutation unexpectedly passed")


def flip(data: bytes, offset: int) -> bytes:
    output = bytearray(data)
    output[offset] ^= 1
    return bytes(output)


def synthetic_arm64_image(validator: object) -> bytes:
    image = bytearray(4096)
    struct.pack_into("<3Q", image, 8, 0x00200000, len(image), 0x0A)
    image[56:60] = b"ARM\x64"
    image[64:] = b"synthetic gate-only kernel".ljust(len(image) - 64, b"\0")
    return bytes(image)


def main() -> int:
    validator = load_validator()
    image_gz = gzip.compress(synthetic_arm64_image(validator), mtime=0)
    dtb = b"synthetic exact AH DT"
    initramfs = b"synthetic exact AD initramfs"
    candidate = serialize(validator, image_gz, dtb, initramfs)
    validator.validate_container(candidate, image_gz, dtb, initramfs)
    rejected = 0

    coherent_mutations = [
        serialize(validator, image_gz, dtb, initramfs, kernel_addr=validator.KERNEL_ADDR + 1),
        serialize(validator, image_gz, dtb, initramfs, ramdisk_addr=validator.RAMDISK_ADDR + 1),
        serialize(validator, image_gz, dtb, initramfs, second_addr=validator.SECOND_ADDR + 1),
        serialize(validator, image_gz, dtb, initramfs, tags_addr=validator.TAGS_ADDR + 1),
        serialize(validator, image_gz, dtb, initramfs, page_size=4096),
        serialize(validator, image_gz, dtb, initramfs, second_size=1),
        serialize(validator, image_gz, dtb, initramfs, dt_size=len(dtb)),
        serialize(validator, image_gz, dtb, initramfs, name="gemini-obs-X"),
        serialize(validator, image_gz, dtb, initramfs, cmdline=validator.CMDLINE + " changed=1"),
    ]
    for mutation in coherent_mutations:
        expect_rejected(validator.validate_container, mutation, image_gz, dtb, initramfs)
        rejected += 1

    for mutation in (
        flip(candidate, 0),
        flip(candidate, 576),
        candidate + b"\0" * validator.PAGE_SIZE,
    ):
        expect_rejected(validator.validate_container, mutation, image_gz, dtb, initramfs)
        rejected += 1

    expect_rejected(
        validator.validate_container,
        candidate,
        gzip.compress(b"different kernel", mtime=0),
        dtb,
        initramfs,
    )
    rejected += 1

    for bad_gzip in (
        image_gz + gzip.compress(b"second gzip member", mtime=0),
        image_gz + b"trailing bytes after gzip",
    ):
        coherent = serialize(validator, bad_gzip, dtb, initramfs)
        expect_rejected(
            validator.validate_container,
            coherent,
            bad_gzip,
            dtb,
            initramfs,
        )
        rejected += 1
    expect_rejected(
        validator.validate_container,
        candidate,
        image_gz,
        dtb + b"changed",
        initramfs,
    )
    rejected += 1
    expect_rejected(
        validator.validate_container,
        candidate,
        image_gz,
        dtb,
        initramfs + b"changed",
    )
    rejected += 1

    nonzero_padding = bytearray(candidate)
    kernel_end = validator.PAGE_SIZE + len(image_gz) + len(dtb)
    nonzero_padding[kernel_end] = 1
    expect_rejected(
        validator.validate_container,
        bytes(nonzero_padding),
        image_gz,
        dtb,
        initramfs,
    )
    rejected += 1

    if rejected != 18:
        raise ValueError(f"expected 18 rejections, observed {rejected}")
    print("validation=candidate-ai-boot-validator-mutations")
    print("positive_synthetic_container=passed")
    print(f"mutations_rejected={rejected}")
    print("final_ai_artifact_required=no")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
