#!/usr/bin/env python3
"""Validate Candidate P as an exact-O container with a new compiled kernel."""

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
PINNED_CANDIDATE_O_SHA256 = {
    "boot": "4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146",
    "Image.gz": "0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3",
    "DTB": "c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379",
    "initramfs": "3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8",
}


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


def encoded_string(value: str, size: int, label: str) -> bytes:
    data = value.encode("ascii")
    if len(data) >= size:
        raise ValueError(f"{label} is too long")
    return data.ljust(size, b"\0")


def encoded_cmdline(value: str) -> tuple[bytes, bytes]:
    data = value.encode("ascii")
    if len(data) >= CMDLINE_SIZE + EXTRA_CMDLINE_SIZE:
        raise ValueError("header command line is too long")
    return (
        data[:CMDLINE_SIZE].ljust(CMDLINE_SIZE, b"\0"),
        data[CMDLINE_SIZE:].ljust(EXTRA_CMDLINE_SIZE, b"\0"),
    )


def require_header_identity(header: bytes, label: str) -> None:
    expected_name = encoded_string(HEADER_NAME, NAME_SIZE, "header name")
    if header[NAME_OFFSET : NAME_OFFSET + NAME_SIZE] != expected_name:
        raise ValueError(f"{label} header name is not exact Candidate O")
    primary, extra = encoded_cmdline(HEADER_CMDLINE)
    if header[CMDLINE_OFFSET : CMDLINE_OFFSET + CMDLINE_SIZE] != primary:
        raise ValueError(f"{label} primary header cmdline is not exact Candidate O")
    if (
        header[EXTRA_CMDLINE_OFFSET : EXTRA_CMDLINE_OFFSET + EXTRA_CMDLINE_SIZE]
        != extra
    ):
        raise ValueError(f"{label} extra header cmdline is not exact Candidate O")


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
    parser.add_argument("--baseline-image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--expected-baseline-sha256", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--expected-baseline-image-gz-sha256", required=True)
    parser.add_argument("--expected-candidate-image-gz-sha256", required=True)
    parser.add_argument("--expected-dtb-sha256", required=True)
    parser.add_argument("--expected-initramfs-sha256", required=True)
    args = parser.parse_args()

    try:
        expected = {
            "Candidate O boot": expected_digest(
                args.expected_baseline_sha256, "--expected-baseline-sha256"
            ),
            "Candidate P boot": expected_digest(
                args.expected_candidate_sha256, "--expected-candidate-sha256"
            ),
            "Candidate O Image.gz": expected_digest(
                args.expected_baseline_image_gz_sha256,
                "--expected-baseline-image-gz-sha256",
            ),
            "Candidate P Image.gz": expected_digest(
                args.expected_candidate_image_gz_sha256,
                "--expected-candidate-image-gz-sha256",
            ),
            "Candidate O DTB": expected_digest(
                args.expected_dtb_sha256, "--expected-dtb-sha256"
            ),
            "Candidate O initramfs": expected_digest(
                args.expected_initramfs_sha256, "--expected-initramfs-sha256"
            ),
        }
        pinned_baseline = {
            "Candidate O boot": PINNED_CANDIDATE_O_SHA256["boot"],
            "Candidate O Image.gz": PINNED_CANDIDATE_O_SHA256["Image.gz"],
            "Candidate O DTB": PINNED_CANDIDATE_O_SHA256["DTB"],
            "Candidate O initramfs": PINNED_CANDIDATE_O_SHA256["initramfs"],
        }
        for label, value in pinned_baseline.items():
            if expected[label] != value:
                raise ValueError(f"expected {label} SHA-256 is not exact Candidate O")

        baseline = parse(args.baseline, "Candidate O boot image")
        candidate = parse(args.candidate, "Candidate P boot image")
        baseline_image_gz = read(args.baseline_image_gz, "Candidate O Image.gz")
        candidate_image_gz = read(args.candidate_image_gz, "Candidate P Image.gz")
        dtb = read(args.dtb, "Candidate O DTB")
        initramfs = read(args.initramfs, "Candidate O initramfs")
        actual = {
            "Candidate O boot": baseline["sha256"],
            "Candidate P boot": candidate["sha256"],
            "Candidate O Image.gz": digest(baseline_image_gz),
            "Candidate P Image.gz": digest(candidate_image_gz),
            "Candidate O DTB": digest(dtb),
            "Candidate O initramfs": digest(initramfs),
        }
        for label, value in expected.items():
            if actual[label] != value:
                raise ValueError(f"{label} SHA-256 is not pinned")

        if baseline_image_gz == candidate_image_gz:
            raise ValueError("compiled kernel payload did not change")

        baseline_segment = baseline_image_gz + dtb
        candidate_segment = candidate_image_gz + dtb
        if baseline["kernel"] != baseline_segment:
            raise ValueError(
                "Candidate O kernel segment is not its pinned Image.gz plus DTB"
            )
        if candidate["kernel"] != candidate_segment:
            raise ValueError(
                "Candidate P kernel segment is not its new Image.gz plus exact-O DTB"
            )
        if baseline["ramdisk"] != initramfs or candidate["ramdisk"] != initramfs:
            raise ValueError("boot image ramdisk is not exact Candidate O initramfs")

        require_header_identity(baseline["header"], "Candidate O")
        require_header_identity(candidate["header"], "Candidate P")
        differing_fields = [
            name
            for name in FIELDS
            if baseline["fields"][name] != candidate["fields"][name]
        ]
        expected_fields = []
        if len(baseline_segment) != len(candidate_segment):
            expected_fields.append("kernel_size")
        if differing_fields != expected_fields:
            raise ValueError(f"unexpected Android-v0 field changes: {differing_fields}")

        for label, image in (("Candidate O", baseline), ("Candidate P", candidate)):
            canonical_id = canonical_v0_id(image["kernel"], image["ramdisk"])
            if image["stored_id"] != canonical_id:
                raise ValueError(f"{label} has a noncanonical Android-v0 ID")

        expected_header = bytearray(baseline["header"])
        struct.pack_into("<I", expected_header, KERNEL_SIZE_OFFSET, len(candidate_segment))
        expected_header[ID_OFFSET : ID_OFFSET + ID_SHA1_SIZE] = candidate["stored_id"]
        if candidate["header"] != bytes(expected_header):
            raise ValueError("header differs outside kernel_size and its canonical ID")

        unchanged_fields = {
            "kernel_addr": 0x40200000,
            "ramdisk_addr": 0x45000000,
            "second_size": 0,
            "second_addr": 0x40F00000,
            "tags_addr": 0x44000000,
            "page_size": 2048,
            "dt_size": 0,
            "unused": 0,
        }
        for name, value in unchanged_fields.items():
            if candidate["fields"][name] != value:
                raise ValueError(f"Candidate P has unexpected {name}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    observed_header_delta = list(differing_fields)
    if baseline["stored_id"] != candidate["stored_id"]:
        observed_header_delta.append("canonical_sha1_id")
    print("validation=android-v0-fbcon-rotation-delta")
    print("baseline_label=O")
    print("candidate_label=P")
    print(f"baseline_sha256={baseline['sha256']}")
    print(f"candidate_sha256={candidate['sha256']}")
    print(f"baseline_image_gz_sha256={digest(baseline_image_gz)}")
    print(f"candidate_image_gz_sha256={digest(candidate_image_gz)}")
    print(f"dtb_sha256={digest(dtb)}")
    print(f"initramfs_sha256={digest(initramfs)}")
    print(f"header_name={HEADER_NAME}")
    print(f"header_cmdline={HEADER_CMDLINE}")
    print(f"observed_header_delta={','.join(observed_header_delta) or 'none'}")
    print("unchanged_header_name_and_cmdline=yes")
    print("unchanged_addresses_and_layout_fields=yes")
    print("unchanged_appended_candidate_o_dtb=yes")
    print("unchanged_candidate_o_initramfs=yes")
    print("zero_payload_padding_verified=yes")
    print("canonical_sha1_ids_verified=yes")
    print("single_container_payload_delta=compiled-Image.gz-only")
    print("validator_raw_block_device_access=none")
    print("build_hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
