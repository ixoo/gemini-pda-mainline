#!/usr/bin/env python3
"""Classify changed-ID Gemian recovery of exact first dmesg record 1."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


CANDIDATE = "b96ec109b3f020fdaf0cdc6ca1733d012051e6607b5520a11d32a6441f569e96"
PREFIX = b"====0.000000-D\n"
MARKER = (
    b"GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260822-B "
    b"checkpoint=manual-first slot=1 crc32=7785e4ce\n"
)
RECORD = PREFIX + MARKER
VALID_HEADER = "444247437700000077000000"
EMPTY_HEADER = "444247430000000000000000"
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
        "record_1_header": VALID_HEADER,
        "record_2_header": EMPTY_HEADER,
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
    pstore = decode(values, "pstore_payload_b64", MAX_PSTORE_BYTES)
    decode(values, "pstore_file_metadata_b64", MAX_DIAGNOSTIC_BYTES)
    decode(values, "ramoops_dmesg_b64", MAX_DIAGNOSTIC_BYTES)
    decode(values, "ramoops_parameters_b64", MAX_DIAGNOSTIC_BYTES)
    require(len(record_1) == 4096, "record-1-size")
    require(record_1[:12].hex() == VALID_HEADER, "record-1-header-bytes")
    require(record_1[12:12 + len(RECORD)] == RECORD, "record-1-payload")
    require(record_1.count(MARKER) == 1, "record-1-marker-count")

    pstore_record_count = pstore.count(RECORD)
    pstore_marker_count = pstore.count(MARKER)
    require(pstore_record_count <= 1 and pstore_marker_count <= 1,
            "duplicate-pstore-record")
    require(pstore_record_count == pstore_marker_count,
            "partial-pstore-record")
    if pstore_record_count == 1:
        return (
            "first-dmesg-cross-version-enumeration-pass",
            "exact-record-1-recovered-via-pstore-and-direct-ram",
        )
    return (
        "first-dmesg-direct-retention-only",
        "exact-record-1-retained-but-not-exposed-by-pstore",
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
        "first-dmesg-cross-version-enumeration-pass",
        "first-dmesg-direct-retention-only",
    }
    print(f"retained_classification={result}")
    print(f"retained_reason={reason}")
    print("direct_record_1=exact" if accepted else "direct_record_1=unproved")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=first-dmesg-writer-warm-retention-and-recovery-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
