#!/usr/bin/env python3
"""Classify changed-ID Gemian recovery of exact protected-clock records 1 and 2."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


CANDIDATE = "3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6"
PREFIX = b"====0.000000-D\n"
MARKER_1 = (
    b"GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A "
    b"checkpoint=before-clock slot=1 crc32=183854b2\n"
)
MARKER_2 = (
    b"GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A "
    b"checkpoint=after-clock slot=2 crc32=d14b85aa\n"
)
RECORD_1 = PREFIX + MARKER_1
RECORD_2 = PREFIX + MARKER_2
VALID_HEADER_1 = "444247437900000079000000"
VALID_HEADER_2 = "444247437800000078000000"
MAX_PSTORE_BYTES = 4_194_304
MAX_DIAGNOSTIC_BYTES = 262_144


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="ascii", errors="strict").splitlines():
        if not raw or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        require(bool(re.fullmatch(r"[a-z0-9_]+", key)), "malformed-key")
        require(key not in values, "duplicate-key")
        values[key] = value
    return values


def decode(values: dict[str, str], key: str, maximum: int) -> bytes:
    encoded = values.get(key, "")
    require(bool(re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", encoded)), f"{key}-encoding")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError(f"{key}-encoding") from error
    require(len(payload) <= maximum, f"{key}-oversize")
    return payload


def validate_record(record: bytes, marker: bytes, header: str, label: str) -> None:
    complete = PREFIX + marker
    require(len(record) == 4096, f"{label}-size")
    require(record[:12].hex() == header, f"{label}-header-bytes")
    require(record[12:12 + len(complete)] == complete, f"{label}-payload")
    require(record.count(marker) == 1, f"{label}-marker-count")


def classify_text(path: Path) -> tuple[str, str]:
    values = parse(path)
    required = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": CANDIDATE,
        "pstore_mounted": "yes",
        "record_1_size": "4096",
        "record_1_header": VALID_HEADER_1,
        "record_2_size": "4096",
        "record_2_header": VALID_HEADER_2,
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    for key, expected in required.items():
        require(values.get(key) == expected, f"{key}-mismatch")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", values.get("recovery_boot_id_sha256", ""))),
            "recovery-boot-id-hash")
    require(bool(re.fullmatch(r"\d+", values.get("pstore_file_count", ""))),
            "pstore-file-count")
    require(bool(re.fullmatch(r"\d+", values.get("ramoops_registration_lines", ""))),
            "ramoops-registration-lines")

    record_1 = decode(values, "record_1_b64", 4096)
    record_2 = decode(values, "record_2_b64", 4096)
    pstore = decode(values, "pstore_payload_b64", MAX_PSTORE_BYTES)
    decode(values, "pstore_file_metadata_b64", MAX_DIAGNOSTIC_BYTES)
    decode(values, "ramoops_dmesg_b64", MAX_DIAGNOSTIC_BYTES)
    decode(values, "ramoops_parameters_b64", MAX_DIAGNOSTIC_BYTES)
    validate_record(record_1, MARKER_1, VALID_HEADER_1, "record-1")
    validate_record(record_2, MARKER_2, VALID_HEADER_2, "record-2")

    counts = (
        pstore.count(RECORD_1), pstore.count(MARKER_1),
        pstore.count(RECORD_2), pstore.count(MARKER_2),
    )
    require(all(count <= 1 for count in counts), "duplicate-pstore-record")
    require(counts[0] == counts[1] and counts[2] == counts[3],
            "partial-pstore-record")
    if counts[0] == 1 and counts[2] == 1:
        return (
            "protected-clock-cross-version-enumeration-pass",
            "exact-before-after-records-recovered-via-pstore-and-direct-ram",
        )
    require(counts[0] == 0 and counts[2] == 0, "incomplete-pstore-pair")
    return (
        "protected-clock-direct-retention-only",
        "exact-before-after-records-retained-but-not-exposed-by-pstore",
    )


def classify(path: Path) -> tuple[str, str]:
    try:
        return classify_text(path)
    except (OSError, UnicodeError, ValueError) as error:
        return "rejected-attribution", str(error).replace(" ", "-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result, reason = classify(args.capture)
    accepted = result in {
        "protected-clock-cross-version-enumeration-pass",
        "protected-clock-direct-retention-only",
    }
    print(f"retained_classification={result}")
    print(f"retained_reason={reason}")
    print("direct_records_1_2=exact" if accepted else "direct_records_1_2=unproved")
    print("before_clock_record=exact" if accepted else "before_clock_record=unproved")
    print("after_clock_record=exact" if accepted else "after_clock_record=unproved")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=one-clock-call-bracketing-warm-retention-and-recovery-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
