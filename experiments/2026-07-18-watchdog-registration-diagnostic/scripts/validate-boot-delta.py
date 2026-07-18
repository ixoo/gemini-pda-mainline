#!/usr/bin/env python3
"""Validate Candidate M as an exact two-component derivative of Candidate L."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys


MAGIC = b"ANDROID!"
MIN_PAGE_SIZE = 2048
HEADER_USED_SIZE = 1632
KERNEL_SIZE_OFFSET = 8
RAMDISK_SIZE_OFFSET = 16
NAME_OFFSET = 48
NAME_SIZE = 16
CMDLINE_OFFSET = 64
CMDLINE_SIZE = 512
ID_OFFSET = 576
ID_SHA1_SIZE = 20
ID_FIELD_SIZE = 32
EXTRA_CMDLINE_OFFSET = 608
EXTRA_CMDLINE_SIZE = 1024
HEADER_NAME = "gemini-obs-L"
HEADER_CMDLINE = "bootopt=64S3,32N2,64N2"
FIELDS = (
    "kernel_size",
    "kernel_addr",
    "ramdisk_size",
    "ramdisk_addr",
    "second_size",
    "second_addr",
    "tags_addr",
    "page_size",
    "dt_size",
    "unused",
)
EXPECTED_SHA256 = {
    "Candidate L boot": "5291832296106d36bc919671960b6150e530467057540a195bcf59e582ebb4c9",
    "Candidate M boot": "a0a6c520fcc170ee0a422e66384559c50100ee65645811c331149beec8c347da",
    "Candidate L Image.gz": "0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3",
    "Candidate L DTB": "73a0c1913beaf41473accfcc6765407ffe11acc56c6ec0ff3a787abc29f00cae",
    "Candidate M DTB": "c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379",
    "Candidate L initramfs": "52dd9145b3d85d8f73990f5798b494293aab17d86a066f79f33274207986de32",
    "Candidate M initramfs": "e0edeceb127e08cd0b01749e289474479ccebe8f33995d39014d7dcf8c5b25fc",
}


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: pathlib.Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        detail = exc.strerror or "read failed"
        raise ValueError(f"cannot read {label}: {detail}") from exc


def canonical_v0_id(kernel: bytes, ramdisk: bytes) -> bytes:
    result = hashlib.sha1()
    for payload in (kernel, ramdisk, b""):
        result.update(payload)
        result.update(struct.pack("<I", len(payload)))
    return result.digest()


def encoded_string(value: str, size: int, label: str) -> bytes:
    data = value.encode("ascii")
    if len(data) >= size:
        raise ValueError(f"{label} is too long")
    return data.ljust(size, b"\0")


def require_header_identity(header: bytes, label: str) -> None:
    expected_name = encoded_string(HEADER_NAME, NAME_SIZE, "header name")
    if header[NAME_OFFSET : NAME_OFFSET + NAME_SIZE] != expected_name:
        raise ValueError(f"{label} header name is not exact Candidate L")

    cmdline = HEADER_CMDLINE.encode("ascii")
    if len(cmdline) >= CMDLINE_SIZE + EXTRA_CMDLINE_SIZE:
        raise ValueError("header command line is too long")
    primary = cmdline[:CMDLINE_SIZE].ljust(CMDLINE_SIZE, b"\0")
    extra = cmdline[CMDLINE_SIZE:].ljust(EXTRA_CMDLINE_SIZE, b"\0")
    if header[CMDLINE_OFFSET : CMDLINE_OFFSET + CMDLINE_SIZE] != primary:
        raise ValueError(f"{label} primary header command line changed")
    if (
        header[EXTRA_CMDLINE_OFFSET : EXTRA_CMDLINE_OFFSET + EXTRA_CMDLINE_SIZE]
        != extra
    ):
        raise ValueError(f"{label} extra header command line changed")


def parse(path: pathlib.Path, label: str) -> dict[str, object]:
    data = read(path, label)
    if len(data) < MIN_PAGE_SIZE or data[:8] != MAGIC:
        raise ValueError(f"{label} is not an Android-v0 image")
    values = dict(zip(FIELDS, struct.unpack_from("<10I", data, 8), strict=True))
    page = values["page_size"]
    if page < MIN_PAGE_SIZE or page & (page - 1):
        raise ValueError(f"{label} has an invalid page size")
    if len(data) < page:
        raise ValueError(f"{label} is truncated in its header")
    if values["second_size"] or values["dt_size"] or values["unused"]:
        raise ValueError(f"{label} has unexpected Android-v0 fields")

    header = data[:page]
    if any(header[HEADER_USED_SIZE:]):
        raise ValueError(f"{label} has nonzero header-page padding")
    if any(header[ID_OFFSET + ID_SHA1_SIZE : ID_OFFSET + ID_FIELD_SIZE]):
        raise ValueError(f"{label} has nonzero reserved ID words")

    kernel_start = page
    kernel_end = kernel_start + values["kernel_size"]
    ramdisk_start = align(kernel_end, page)
    ramdisk_end = ramdisk_start + values["ramdisk_size"]
    image_end = align(ramdisk_end, page)
    if image_end != len(data):
        raise ValueError(f"{label} has trailing or truncated payload data")
    if any(data[kernel_end:ramdisk_start]):
        raise ValueError(f"{label} has nonzero kernel padding")
    if any(data[ramdisk_end:image_end]):
        raise ValueError(f"{label} has nonzero ramdisk padding")

    return {
        "fields": values,
        "header": header,
        "kernel": data[kernel_start:kernel_end],
        "ramdisk": data[ramdisk_start:ramdisk_end],
        "stored_id": data[ID_OFFSET : ID_OFFSET + ID_SHA1_SIZE],
        "sha256": digest(data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--baseline-dtb", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-dtb", type=pathlib.Path, required=True)
    parser.add_argument("--baseline-ramdisk", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-ramdisk", type=pathlib.Path, required=True)
    args = parser.parse_args()

    try:
        baseline = parse(args.baseline, "Candidate L boot image")
        candidate = parse(args.candidate, "Candidate M boot image")
        image_gz = read(args.image_gz, "Candidate L Image.gz")
        baseline_dtb = read(args.baseline_dtb, "Candidate L DTB")
        candidate_dtb = read(args.candidate_dtb, "Candidate M DTB")
        baseline_ramdisk = read(args.baseline_ramdisk, "Candidate L initramfs")
        candidate_ramdisk = read(args.candidate_ramdisk, "Candidate M initramfs")

        actual = {
            "Candidate L boot": baseline["sha256"],
            "Candidate M boot": candidate["sha256"],
            "Candidate L Image.gz": digest(image_gz),
            "Candidate L DTB": digest(baseline_dtb),
            "Candidate M DTB": digest(candidate_dtb),
            "Candidate L initramfs": digest(baseline_ramdisk),
            "Candidate M initramfs": digest(candidate_ramdisk),
        }
        for label, expected in EXPECTED_SHA256.items():
            if actual[label] != expected:
                raise ValueError(f"{label} SHA-256 is not pinned")

        if baseline_dtb == candidate_dtb:
            raise ValueError("Candidate M DTB unexpectedly matches Candidate L")
        if baseline_ramdisk == candidate_ramdisk:
            raise ValueError("Candidate M initramfs unexpectedly matches Candidate L")
        if baseline["kernel"] != image_gz + baseline_dtb:
            raise ValueError("Candidate L kernel segment is not pinned Image.gz plus DTB")
        if candidate["kernel"] != image_gz + candidate_dtb:
            raise ValueError("Candidate M kernel segment is not pinned Image.gz plus DTB")
        if baseline["ramdisk"] != baseline_ramdisk:
            raise ValueError("Candidate L ramdisk does not match its explicit component")
        if candidate["ramdisk"] != candidate_ramdisk:
            raise ValueError("Candidate M ramdisk does not match its explicit component")

        for label, image in (("Candidate L", baseline), ("Candidate M", candidate)):
            require_header_identity(image["header"], label)
            if image["stored_id"] != canonical_v0_id(image["kernel"], image["ramdisk"]):
                raise ValueError(f"{label} has a noncanonical Android-v0 ID")

        differing_fields = [
            name
            for name in FIELDS
            if baseline["fields"][name] != candidate["fields"][name]
        ]
        if differing_fields != ["kernel_size", "ramdisk_size"]:
            raise ValueError(f"unexpected Android-v0 field changes: {differing_fields}")

        baseline_header = bytearray(baseline["header"])
        candidate_header = bytearray(candidate["header"])
        for header in (baseline_header, candidate_header):
            header[KERNEL_SIZE_OFFSET : KERNEL_SIZE_OFFSET + 4] = b"\0" * 4
            header[RAMDISK_SIZE_OFFSET : RAMDISK_SIZE_OFFSET + 4] = b"\0" * 4
            header[ID_OFFSET : ID_OFFSET + ID_SHA1_SIZE] = b"\0" * ID_SHA1_SIZE
        if baseline_header != candidate_header:
            raise ValueError(
                "header differs outside kernel_size, ramdisk_size, and canonical ID"
            )

        exact_layout = {
            "kernel_addr": 0x40200000,
            "ramdisk_addr": 0x45000000,
            "second_addr": 0x40F00000,
            "tags_addr": 0x44000000,
            "page_size": 2048,
        }
        for field, value in exact_layout.items():
            if candidate["fields"][field] != value:
                raise ValueError(f"Candidate M has unexpected {field}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=android-v0-watchdog-registration-delta")
    print("baseline_label=L")
    print("candidate_label=M")
    print(f"baseline_sha256={baseline['sha256']}")
    print(f"candidate_sha256={candidate['sha256']}")
    print(f"image_gz_sha256={digest(image_gz)}")
    print(f"baseline_dtb_sha256={digest(baseline_dtb)}")
    print(f"candidate_dtb_sha256={digest(candidate_dtb)}")
    print(f"baseline_ramdisk_sha256={digest(baseline_ramdisk)}")
    print(f"candidate_ramdisk_sha256={digest(candidate_ramdisk)}")
    print(f"header_name={HEADER_NAME}")
    print(f"header_cmdline={HEADER_CMDLINE}")
    print("observed_header_delta=kernel_size,ramdisk_size,canonical_sha1_id")
    print("unchanged_candidate_l_image_gz=yes")
    print("unchanged_addresses_layout_name_cmdline=yes")
    print("explicit_components_match_images=yes")
    print("zero_payload_padding_verified=yes")
    print("canonical_sha1_ids_verified=yes")
    print("container_payload_delta=appended-dtb-and-initramfs")
    print("validator_raw_block_device_access=none")
    print("build_hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
