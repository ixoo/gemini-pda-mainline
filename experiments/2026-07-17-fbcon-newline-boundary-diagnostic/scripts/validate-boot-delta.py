#!/usr/bin/env python3
"""Validate Candidate K as an initramfs-only derivative of exact Candidate J."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys


MAGIC = b"ANDROID!"
MIN_PAGE_SIZE = 2048
HEADER_USED_SIZE = 1632
CMDLINE_OFFSET = 64
CMDLINE_SIZE = 512
EXTRA_CMDLINE_OFFSET = 608
EXTRA_CMDLINE_SIZE = 1024
ID_OFFSET = 576
ID_SHA1_SIZE = 20
ID_FIELD_SIZE = 32
RAMDISK_SIZE_OFFSET = 16
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


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_digest(value: str, option: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{option} must be an exact 64-digit SHA-256")
    return normalized


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


def encoded_cmdline(value: str) -> tuple[bytes, bytes]:
    data = value.encode("ascii")
    if len(data) >= CMDLINE_SIZE + EXTRA_CMDLINE_SIZE:
        raise ValueError("header command line is too long")
    return (
        data[:CMDLINE_SIZE].ljust(CMDLINE_SIZE, b"\0"),
        data[CMDLINE_SIZE:].ljust(EXTRA_CMDLINE_SIZE, b"\0"),
    )


def require_cmdline(header: bytes, label: str) -> None:
    primary, extra = encoded_cmdline(HEADER_CMDLINE)
    if header[CMDLINE_OFFSET : CMDLINE_OFFSET + CMDLINE_SIZE] != primary:
        raise ValueError(f"{label} primary header cmdline is not exact Candidate J")
    if (
        header[EXTRA_CMDLINE_OFFSET : EXTRA_CMDLINE_OFFSET + EXTRA_CMDLINE_SIZE]
        != extra
    ):
        raise ValueError(f"{label} extra header cmdline is not exact Candidate J")


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
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--baseline-ramdisk", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-ramdisk", type=pathlib.Path, required=True)
    parser.add_argument("--expected-baseline-sha256", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--expected-image-gz-sha256", required=True)
    parser.add_argument("--expected-dtb-sha256", required=True)
    parser.add_argument("--expected-baseline-ramdisk-sha256", required=True)
    parser.add_argument("--expected-candidate-ramdisk-sha256", required=True)
    args = parser.parse_args()

    try:
        expected = {
            "Candidate J boot": expected_digest(
                args.expected_baseline_sha256, "--expected-baseline-sha256"
            ),
            "Candidate K boot": expected_digest(
                args.expected_candidate_sha256, "--expected-candidate-sha256"
            ),
            "Candidate J Image.gz": expected_digest(
                args.expected_image_gz_sha256, "--expected-image-gz-sha256"
            ),
            "Candidate J DTB": expected_digest(
                args.expected_dtb_sha256, "--expected-dtb-sha256"
            ),
            "Candidate J initramfs": expected_digest(
                args.expected_baseline_ramdisk_sha256,
                "--expected-baseline-ramdisk-sha256",
            ),
            "Candidate K initramfs": expected_digest(
                args.expected_candidate_ramdisk_sha256,
                "--expected-candidate-ramdisk-sha256",
            ),
        }
        baseline = parse(args.baseline, "Candidate J boot image")
        candidate = parse(args.candidate, "Candidate K boot image")
        image_gz = read(args.image_gz, "Candidate J Image.gz")
        dtb = read(args.dtb, "Candidate J appended DTB")
        baseline_ramdisk = read(args.baseline_ramdisk, "Candidate J initramfs")
        candidate_ramdisk = read(args.candidate_ramdisk, "Candidate K initramfs")
        actual = {
            "Candidate J boot": baseline["sha256"],
            "Candidate K boot": candidate["sha256"],
            "Candidate J Image.gz": digest(image_gz),
            "Candidate J DTB": digest(dtb),
            "Candidate J initramfs": digest(baseline_ramdisk),
            "Candidate K initramfs": digest(candidate_ramdisk),
        }
        for label, value in expected.items():
            if actual[label] != value:
                raise ValueError(f"{label} SHA-256 is not pinned")

        exact_kernel_segment = image_gz + dtb
        if baseline["kernel"] != exact_kernel_segment:
            raise ValueError("Candidate J kernel segment is not pinned Image.gz plus DTB")
        if candidate["kernel"] != exact_kernel_segment:
            raise ValueError("Candidate K kernel segment differs from exact Candidate J")
        if candidate["kernel"] != baseline["kernel"]:
            raise ValueError("Candidate K changed Candidate J kernel or appended DTB bytes")
        if baseline["ramdisk"] != baseline_ramdisk:
            raise ValueError("Candidate J image ramdisk does not match explicit baseline")
        if candidate["ramdisk"] != candidate_ramdisk:
            raise ValueError("Candidate K image ramdisk does not match explicit candidate")
        if candidate_ramdisk == baseline_ramdisk:
            raise ValueError("Candidate K initramfs unexpectedly matches Candidate J")

        for label, image in (("Candidate J", baseline), ("Candidate K", candidate)):
            require_cmdline(image["header"], label)
            if image["stored_id"] != canonical_v0_id(image["kernel"], image["ramdisk"]):
                raise ValueError(f"{label} has a noncanonical Android-v0 ID")

        differing_fields = [
            name
            for name in FIELDS
            if baseline["fields"][name] != candidate["fields"][name]
        ]
        expected_fields = []
        if len(baseline_ramdisk) != len(candidate_ramdisk):
            expected_fields.append("ramdisk_size")
        if differing_fields != expected_fields:
            raise ValueError(f"unexpected Android-v0 field changes: {differing_fields}")

        baseline_header = bytearray(baseline["header"])
        candidate_header = bytearray(candidate["header"])
        for header in (baseline_header, candidate_header):
            header[RAMDISK_SIZE_OFFSET : RAMDISK_SIZE_OFFSET + 4] = b"\0" * 4
            header[ID_OFFSET : ID_OFFSET + ID_SHA1_SIZE] = b"\0" * ID_SHA1_SIZE
        if baseline_header != candidate_header:
            raise ValueError("header differs outside ramdisk_size and canonical ID")

        exact_layout = {
            "kernel_addr": 0x40200000,
            "ramdisk_addr": 0x45000000,
            "second_addr": 0x40F00000,
            "tags_addr": 0x44000000,
            "page_size": 2048,
        }
        for field, value in exact_layout.items():
            if candidate["fields"][field] != value:
                raise ValueError(f"Candidate K has unexpected {field}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    observed = list(differing_fields)
    if baseline["stored_id"] != candidate["stored_id"]:
        observed.append("canonical_sha1_id")
    print("validation=android-v0-fbcon-newline-boundary-delta")
    print("baseline_label=J")
    print("candidate_label=K")
    print(f"baseline_sha256={baseline['sha256']}")
    print(f"candidate_sha256={candidate['sha256']}")
    print(f"kernel_segment_sha256={digest(exact_kernel_segment)}")
    print(f"image_gz_sha256={digest(image_gz)}")
    print(f"dtb_sha256={digest(dtb)}")
    print(f"baseline_ramdisk_sha256={digest(baseline_ramdisk)}")
    print(f"candidate_ramdisk_sha256={digest(candidate_ramdisk)}")
    print(f"header_cmdline={HEADER_CMDLINE}")
    print(f"observed_header_delta={','.join(observed) or 'none'}")
    print("unchanged_candidate_j_image_gz=yes")
    print("unchanged_appended_candidate_j_dtb=yes")
    print("unchanged_addresses_layout_name_cmdline=yes")
    print("explicit_ramdisks_match_images=yes")
    print("zero_payload_padding_verified=yes")
    print("canonical_sha1_ids_verified=yes")
    print("single_container_payload_delta=initramfs-only")
    print("validator_raw_block_device_access=none")
    print("build_hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
