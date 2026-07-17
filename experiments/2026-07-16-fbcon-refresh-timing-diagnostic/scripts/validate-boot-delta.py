#!/usr/bin/env python3
"""Validate Candidate I as an initramfs-only derivative of exact Candidate H."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import sys


MAGIC = b"ANDROID!"
MIN_PAGE_SIZE = 2048
HEADER_USED_SIZE = 1632
ID_OFFSET = 576
ID_SHA1_SIZE = 20
ID_FIELD_SIZE = 32
RAMDISK_SIZE_OFFSET = 16
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
        char not in "0123456789abcdef" for char in normalized
    ):
        raise ValueError(f"{option} must be an exact 64-digit SHA-256")
    return normalized


def read_explicit(path: pathlib.Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        detail = exc.strerror or "read failed"
        raise ValueError(f"cannot read {label}: {detail}") from exc


def canonical_v0_id(kernel: bytes, ramdisk: bytes) -> bytes:
    """Return the AOSP Android-v0 ID for empty second and legacy-DT payloads."""

    result = hashlib.sha1()
    for payload in (kernel, ramdisk, b""):
        result.update(payload)
        result.update(struct.pack("<I", len(payload)))
    return result.digest()


def parse(path: pathlib.Path, label: str) -> dict[str, object]:
    data = read_explicit(path, label)
    if len(data) < MIN_PAGE_SIZE or data[:8] != MAGIC:
        raise ValueError(f"{label} is not an Android-v0 image")

    values = dict(zip(FIELDS, struct.unpack_from("<10I", data, 8), strict=True))
    page = values["page_size"]
    if page < MIN_PAGE_SIZE or page & (page - 1):
        raise ValueError(f"{label} has an invalid page size")
    if len(data) < page:
        raise ValueError(f"{label} is truncated within its header page")
    if values["second_size"] or values["dt_size"]:
        raise ValueError(f"{label} unexpectedly uses second or header-DT payloads")
    if values["unused"]:
        raise ValueError(f"{label} has a nonzero Android-v0 unused field")

    header = data[:page]
    if any(header[HEADER_USED_SIZE:]):
        raise ValueError(f"{label} has nonzero header-page padding")
    if any(header[ID_OFFSET + ID_SHA1_SIZE : ID_OFFSET + ID_FIELD_SIZE]):
        raise ValueError(f"{label} has nonzero reserved Android ID words")

    kernel_start = page
    kernel_end = kernel_start + values["kernel_size"]
    ramdisk_start = align(kernel_end, page)
    ramdisk_end = ramdisk_start + values["ramdisk_size"]
    image_end = align(ramdisk_end, page)
    if image_end != len(data):
        raise ValueError(f"{label} has trailing or truncated payload data")
    if any(data[kernel_end:ramdisk_start]):
        raise ValueError(f"{label} has nonzero kernel-to-ramdisk padding")
    if any(data[ramdisk_end:image_end]):
        raise ValueError(f"{label} has nonzero ramdisk-tail padding")

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
    parser.add_argument("--expected-image-gz-sha256", required=True)
    parser.add_argument("--expected-dtb-sha256", required=True)
    parser.add_argument("--expected-baseline-ramdisk-sha256", required=True)
    args = parser.parse_args()

    try:
        expected_hashes = {
            "baseline boot": expected_digest(
                args.expected_baseline_sha256, "--expected-baseline-sha256"
            ),
            "Image.gz": expected_digest(
                args.expected_image_gz_sha256, "--expected-image-gz-sha256"
            ),
            "Candidate H DTB": expected_digest(
                args.expected_dtb_sha256, "--expected-dtb-sha256"
            ),
            "Candidate H initramfs": expected_digest(
                args.expected_baseline_ramdisk_sha256,
                "--expected-baseline-ramdisk-sha256",
            ),
        }
        baseline = parse(args.baseline, "baseline boot image")
        candidate = parse(args.candidate, "candidate boot image")
        image_gz = read_explicit(args.image_gz, "Image.gz")
        dtb = read_explicit(args.dtb, "Candidate H DTB")
        baseline_ramdisk = read_explicit(
            args.baseline_ramdisk, "Candidate H initramfs"
        )
        candidate_ramdisk = read_explicit(
            args.candidate_ramdisk, "Candidate I initramfs"
        )

        actual_hashes = {
            "baseline boot": baseline["sha256"],
            "Image.gz": digest(image_gz),
            "Candidate H DTB": digest(dtb),
            "Candidate H initramfs": digest(baseline_ramdisk),
        }
        for label, expected in expected_hashes.items():
            if actual_hashes[label] != expected:
                raise ValueError(f"{label} SHA-256 does not match its pinned input")

        exact_kernel_segment = image_gz + dtb
        if baseline["kernel"] != exact_kernel_segment:
            raise ValueError(
                "baseline kernel segment is not pinned Image.gz plus Candidate H DTB"
            )
        if candidate["kernel"] != exact_kernel_segment:
            raise ValueError(
                "candidate kernel segment differs from pinned Image.gz plus Candidate H DTB"
            )
        if candidate["kernel"] != baseline["kernel"]:
            raise ValueError("candidate kernel segment differs from exact Candidate H")
        if baseline["ramdisk"] != baseline_ramdisk:
            raise ValueError(
                "baseline image ramdisk does not match the explicit Candidate H initramfs"
            )
        if candidate["ramdisk"] != candidate_ramdisk:
            raise ValueError(
                "candidate image ramdisk does not match the explicit Candidate I initramfs"
            )
        if candidate_ramdisk == baseline_ramdisk:
            raise ValueError("Candidate I initramfs unexpectedly matches Candidate H")

        differing_fields = [
            name
            for name in FIELDS
            if baseline["fields"][name] != candidate["fields"][name]
        ]
        expected_fields = []
        if len(baseline_ramdisk) != len(candidate_ramdisk):
            expected_fields.append("ramdisk_size")
        if differing_fields != expected_fields:
            raise ValueError(
                f"unexpected Android-v0 header field deltas: {differing_fields}"
            )

        for label, image in (("baseline", baseline), ("candidate", candidate)):
            canonical_id = canonical_v0_id(image["kernel"], image["ramdisk"])
            if image["stored_id"] != canonical_id:
                raise ValueError(f"{label} image has a noncanonical Android-v0 ID")

        baseline_header = bytearray(baseline["header"])
        candidate_header = bytearray(candidate["header"])
        for header in (baseline_header, candidate_header):
            header[RAMDISK_SIZE_OFFSET : RAMDISK_SIZE_OFFSET + 4] = b"\0" * 4
            header[ID_OFFSET : ID_OFFSET + ID_SHA1_SIZE] = b"\0" * ID_SHA1_SIZE
        if baseline_header != candidate_header:
            raise ValueError(
                "header differs outside ramdisk_size and the canonical SHA-1 ID"
            )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    observed_header_delta = list(differing_fields)
    if baseline["stored_id"] != candidate["stored_id"]:
        observed_header_delta.append("canonical_sha1_id")

    print("validation=android-v0-fbcon-refresh-timing-delta")
    print("baseline_label=H")
    print("candidate_label=I")
    print(f"baseline_sha256={baseline['sha256']}")
    print(f"candidate_sha256={candidate['sha256']}")
    print(f"kernel_segment_sha256={digest(exact_kernel_segment)}")
    print(f"image_gz_sha256={digest(image_gz)}")
    print(f"dtb_sha256={digest(dtb)}")
    print(f"baseline_ramdisk_sha256={digest(baseline_ramdisk)}")
    print(f"candidate_ramdisk_sha256={digest(candidate_ramdisk)}")
    print("unchanged_kernel_segment=yes")
    print("unchanged_image_gz=yes")
    print("unchanged_appended_h_dtb=yes")
    print("explicit_ramdisks_match_images=yes")
    print("zero_padding_verified=yes")
    print("header_delta=ramdisk_size-if-changed,canonical_sha1_id")
    print(f"observed_header_delta={','.join(observed_header_delta) or 'none'}")
    print("canonical_sha1_ids_verified=yes")
    print("single_variable_container_delta=passed")
    print("storage_access=none")
    print("build_hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
