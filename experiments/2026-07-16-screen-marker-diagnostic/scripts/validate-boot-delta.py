#!/usr/bin/env python3
"""Validate an Android-v0 screen diagnostic against an exact baseline."""

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
        "ramdisk": data[ramdisk_start:ramdisk_end],
        "stored_id": data[576:596],
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
    parser.add_argument("--expected-baseline-sha256", required=True)
    parser.add_argument(
        "--same-ramdisk",
        action="store_true",
        help="require an identical ramdisk and permit only the DTB payload delta",
    )
    args = parser.parse_args()
    try:
        baseline = parse(args.baseline)
        candidate = parse(args.candidate)
        image_gz = args.image_gz.read_bytes()
        baseline_dtb = args.baseline_dtb.read_bytes()
        candidate_dtb = args.candidate_dtb.read_bytes()
        baseline_ramdisk = args.baseline_ramdisk.read_bytes()
        candidate_ramdisk = args.candidate_ramdisk.read_bytes()

        if baseline["sha256"] != args.expected_baseline_sha256:
            raise ValueError("baseline SHA-256 does not match the pinned candidate")
        if baseline_dtb == candidate_dtb:
            raise ValueError("candidate DTB unexpectedly matches the baseline")
        if args.same_ramdisk:
            if baseline_ramdisk != candidate_ramdisk:
                raise ValueError("candidate initramfs differs in same-ramdisk mode")
        elif baseline_ramdisk == candidate_ramdisk:
            raise ValueError("candidate initramfs unexpectedly matches the baseline")
        if baseline["kernel"] != image_gz + baseline_dtb:
            raise ValueError("baseline kernel segment is not Image.gz plus baseline DTB")
        if candidate["kernel"] != image_gz + candidate_dtb:
            raise ValueError("candidate kernel segment is not Image.gz plus candidate DTB")
        if baseline["ramdisk"] != baseline_ramdisk:
            raise ValueError("baseline image ramdisk does not match its explicit file")
        if candidate["ramdisk"] != candidate_ramdisk:
            raise ValueError("candidate image ramdisk does not match its explicit file")

        differing_fields = [
            name
            for name in FIELDS
            if baseline["fields"][name] != candidate["fields"][name]
        ]
        expected_fields = {"kernel_size", "ramdisk_size"}
        if args.same_ramdisk:
            expected_fields = set()
            if len(baseline_dtb) != len(candidate_dtb):
                expected_fields.add("kernel_size")
        if set(differing_fields) != expected_fields:
            raise ValueError(f"unexpected Android field deltas: {differing_fields}")

        for label, image in (("baseline", baseline), ("candidate", candidate)):
            expected_id = canonical_v0_id(image["kernel"], image["ramdisk"])
            if image["stored_id"] != expected_id:
                raise ValueError(f"{label} image has a noncanonical Android-v0 ID")

        baseline_header = bytearray(baseline["header"])
        candidate_header = bytearray(candidate["header"])
        for header in (baseline_header, candidate_header):
            header[8:12] = b"\0" * 4
            header[16:20] = b"\0" * 4
            header[576:596] = b"\0" * 20
        if baseline_header != candidate_header:
            raise ValueError(
                "header differs outside kernel_size, ramdisk_size, and canonical ID"
            )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=android-v0-screen-marker-delta")
    print(f"same_ramdisk={'yes' if args.same_ramdisk else 'no'}")
    print(f"baseline_sha256={baseline['sha256']}")
    print(f"candidate_sha256={candidate['sha256']}")
    print(f"image_gz_sha256={digest(image_gz)}")
    print(f"baseline_dtb_sha256={digest(baseline_dtb)}")
    print(f"candidate_dtb_sha256={digest(candidate_dtb)}")
    print(f"baseline_ramdisk_sha256={digest(baseline_ramdisk)}")
    print(f"candidate_ramdisk_sha256={digest(candidate_ramdisk)}")
    print("unchanged_kernel_image_gz=yes")
    if args.same_ramdisk:
        print("appended_dtb_delta=allowlisted-simplefb-clock")
        print("initramfs_delta=none")
        print("header_delta=payload-size-if-changed,canonical_sha1_id")
    else:
        print("appended_dtb_delta=allowlisted-simplefb")
        print("initramfs_delta=validated-separately")
        print("header_delta=kernel_size,ramdisk_size,canonical_sha1_id")
    print("canonical_sha1_ids_verified=yes")
    print("storage_access=none")
    print("build_hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
