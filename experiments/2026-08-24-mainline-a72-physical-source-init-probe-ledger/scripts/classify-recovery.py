#!/usr/bin/env python3
"""Classify exact changed-ID Gemian recovery of the A72 init/probe records."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


CANDIDATE = "4185b85192f036df09d547cdf68991e885c6d4849927e684a5923cde15c0a03c"
DEPLOYMENT_BOOT_ID = "ea0b76e9-0459-4bf1-a787-661b0e8bacd1"
PREFIX = b"====0.000000-D\n"
MARKER_1 = (
    b"GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A "
    b"checkpoint=driver-init slot=1 crc32=85e5f336\n"
)
MARKER_2 = (
    b"GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A "
    b"checkpoint=probe-enter slot=2 crc32=85116721\n"
)
RECORD_1 = PREFIX + MARKER_1
RECORD_2 = PREFIX + MARKER_2
VALID_HEADER = "444247436b0000006b000000"
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


def record_state(record: bytes, marker: bytes, label: str) -> str:
    require(len(record) == 4096, f"{label}-size")
    header = record[:12].hex()
    if header == EMPTY_HEADER:
        return "empty"
    require(header == VALID_HEADER, f"{label}-header")
    expected = PREFIX + marker
    require(record[12:12 + len(expected)] == expected, f"{label}-payload")
    require(record.count(marker) == 1, f"{label}-marker-count")
    return "valid"


def classify_text(path: Path) -> tuple[str, str, str]:
    values = parse(path)
    required = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": CANDIDATE,
        "pstore_mounted": "yes",
        "record_1_size": "4096",
        "record_2_size": "4096",
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    for key, expected in required.items():
        require(values.get(key) == expected, f"{key}-mismatch")
    boot_id = values.get("recovery_boot_id", "")
    require(bool(re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot_id
    )), "recovery-boot-id")
    require(boot_id != DEPLOYMENT_BOOT_ID, "recovery-boot-id-unchanged")
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
    state_1 = record_state(record_1, MARKER_1, "record-1")
    state_2 = record_state(record_2, MARKER_2, "record-2")
    require(values.get("record_1_header") == record_1[:12].hex(),
            "record-1-reported-header")
    require(values.get("record_2_header") == record_2[:12].hex(),
            "record-2-reported-header")

    for marker, record, state, label in (
        (MARKER_1, RECORD_1, state_1, "record-1"),
        (MARKER_2, RECORD_2, state_2, "record-2"),
    ):
        marker_count = pstore.count(marker)
        record_count = pstore.count(record)
        require(marker_count <= 1 and record_count <= 1,
                f"{label}-duplicate-pstore")
        require(marker_count == record_count, f"{label}-partial-pstore")
        require(not record_count or state == "valid", f"{label}-pstore-direct-conflict")

    if state_1 == "empty" and state_2 == "empty":
        return (
            "before-driver-init-or-writer-refused",
            "both-init-probe-records-exact-empty",
            "move-to-earlier-independent-init-writer-boundary",
        )
    if state_1 == "valid" and state_2 == "empty":
        return (
            "driver-init-only",
            "driver-init-committed-probe-enter-empty",
            "isolate-platform-driver-registration-return-and-match-bind",
        )
    if state_1 == "valid" and state_2 == "valid":
        return (
            "driver-init-and-probe-enter",
            "both-init-probe-records-exact",
            "split-allocation-and-three-source-lookups",
        )
    require(False, "record-order-invalid")
    raise AssertionError("unreachable")


def classify(path: Path) -> tuple[str, str, str]:
    try:
        return classify_text(path)
    except (OSError, UnicodeError, ValueError) as error:
        return "rejected-attribution", str(error).replace(" ", "-"), "repair-attribution"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result, reason, selected_next = classify(args.capture)
    accepted = result != "rejected-attribution"
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"selected_next={selected_next}")
    print("retained_records_1_2=exact" if accepted else "retained_records_1_2=unproved")
    print("allocations=0-by-candidate-contract")
    print("source_lookups=0-by-candidate-contract")
    print("platform_snapshots=0-by-candidate-contract")
    print("provider_snapshots=0-by-candidate-contract")
    print("clock_calls=0-by-candidate-contract")
    print("bigidvfs_calls=0-by-candidate-contract")
    print("provider_transactions=0-by-candidate-contract")
    print("publisher_calls=0-by-candidate-contract")
    print("owner_mutations=0-by-candidate-contract")
    print("cpu_requests=0-by-candidate-contract")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=observer-init-and-probe-entry-localization-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
