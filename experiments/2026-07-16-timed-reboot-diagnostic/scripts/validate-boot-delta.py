#!/usr/bin/env python3
"""Validate that two Android v0 images differ only through their ramdisks."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys


MAGIC = b"ANDROID!"
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


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_v0_id(kernel: bytes, ramdisk: bytes) -> bytes:
    """Return the AOSP Android-v0 ID for empty second and DT payloads."""

    result = hashlib.sha1()
    for payload in (kernel, ramdisk, b""):
        result.update(payload)
        result.update(struct.pack("<I", len(payload)))
    return result.digest()


def parse(path: pathlib.Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 2048 or data[:8] != MAGIC:
        raise ValueError(f"{path} is not an Android v0 image")
    values = dict(zip(FIELDS, struct.unpack_from("<10I", data, 8), strict=True))
    page = values["page_size"]
    if page < 2048 or page & (page - 1):
        raise ValueError(f"{path} has an invalid page size")
    kernel_start = page
    kernel_end = kernel_start + values["kernel_size"]
    ramdisk_start = align(kernel_end, page)
    ramdisk_end = ramdisk_start + values["ramdisk_size"]
    image_end = align(ramdisk_end, page)
    if values["second_size"] or values["dt_size"]:
        raise ValueError(f"{path} unexpectedly uses second or header-DT payloads")
    if image_end != len(data):
        raise ValueError(f"{path} has trailing or truncated data")
    if any(data[kernel_end:ramdisk_start]) or any(data[ramdisk_end:image_end]):
        raise ValueError(f"{path} has nonzero payload padding")
    return {
        "data": data,
        "fields": values,
        "header": data[:page],
        "kernel": data[kernel_start:kernel_end],
        "kernel_padding": data[kernel_end:ramdisk_start],
        "ramdisk": data[ramdisk_start:ramdisk_end],
        "stored_id": data[576:596],
        "sha256": digest(data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--baseline-ramdisk", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-ramdisk", type=pathlib.Path, required=True)
    parser.add_argument("--expected-baseline-sha256", required=True)
    args = parser.parse_args()
    try:
        baseline = parse(args.baseline)
        candidate = parse(args.candidate)
        baseline_ramdisk = args.baseline_ramdisk.read_bytes()
        candidate_ramdisk = args.candidate_ramdisk.read_bytes()
        if baseline["sha256"] != args.expected_baseline_sha256:
            raise ValueError("baseline candidate SHA-256 is not the tested USB image")
        differing_fields = [
            name
            for name in FIELDS
            if baseline["fields"][name] != candidate["fields"][name]
        ]
        unexpected_fields = [
            name for name in differing_fields if name != "ramdisk_size"
        ]
        if unexpected_fields:
            raise ValueError(f"unexpected Android field deltas: {differing_fields}")
        if baseline["kernel"] != candidate["kernel"]:
            raise ValueError("kernel plus appended DTB payload differs")
        if baseline["kernel_padding"] != candidate["kernel_padding"]:
            raise ValueError("kernel-to-ramdisk padding differs")
        if baseline["ramdisk"] != baseline_ramdisk:
            raise ValueError("baseline image ramdisk does not match its explicit file")
        if candidate["ramdisk"] != candidate_ramdisk:
            raise ValueError("candidate image ramdisk does not match its explicit file")
        if baseline_ramdisk == candidate_ramdisk:
            raise ValueError("ramdisk payloads unexpectedly match")
        for label, image in (("baseline", baseline), ("candidate", candidate)):
            expected_id = canonical_v0_id(image["kernel"], image["ramdisk"])
            if image["stored_id"] != expected_id:
                raise ValueError(f"{label} image has a noncanonical Android-v0 ID")
        baseline_header = bytearray(baseline["header"])
        candidate_header = bytearray(candidate["header"])
        # Ramdisk size and the verified Android SHA-1 ID are the only header
        # regions allowed to differ when the explicit ramdisk changes.
        baseline_header[16:20] = b"\0" * 4
        candidate_header[16:20] = b"\0" * 4
        baseline_header[576:596] = b"\0" * 20
        candidate_header[576:596] = b"\0" * 20
        if baseline_header != candidate_header:
            raise ValueError("header differs outside ramdisk_size and canonical ID")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=android-v0-ramdisk-only-delta")
    print(f"baseline_sha256={baseline['sha256']}")
    print(f"candidate_sha256={candidate['sha256']}")
    print(f"kernel_payload_sha256={digest(baseline['kernel'])}")
    print("kernel_and_appended_dtb_identical=yes")
    header_deltas = list(differing_fields)
    if baseline["stored_id"] != candidate["stored_id"]:
        header_deltas.append("canonical_sha1_id")
    print(f"header_delta={','.join(header_deltas) or 'none'}")
    print("canonical_sha1_ids_verified=yes")
    print("explicit_ramdisks_match_images=yes")
    print("single_variable_container_delta=passed")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
