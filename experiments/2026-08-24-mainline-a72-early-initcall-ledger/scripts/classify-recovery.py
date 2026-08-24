#!/usr/bin/env python3
"""Classify exact changed-ID Gemian recovery of early-initcall records."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


CANDIDATE = "d2951eade3c08c889ecaeb1376f85262c44ad729048ddc3164c1db39acced609"
DEPLOYMENT_BOOT_ID = "ca6e280a-1d4b-4db3-ae9e-9d3234d4082c"
PREFIX = b"====0.000000-D\n"
MARKER_1 = (
    b"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A "
    b"checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f\n"
)
MARKER_2_CORE = (
    b"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A "
    b"checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5\n"
)
MARKER_2_REFUSAL = (
    b"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A "
    b"checkpoint=pure-init outcome=primary-refused slot=2 crc32=5767e326\n"
)
RECORD_1 = PREFIX + MARKER_1
RECORD_2_CORE = PREFIX + MARKER_2_CORE
RECORD_2_REFUSAL = PREFIX + MARKER_2_REFUSAL
VALID_HEADER_1 = "444247437800000078000000"
VALID_HEADER_2_CORE = "444247437800000078000000"
VALID_HEADER_2_REFUSAL = "444247438100000081000000"
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
    require(bool(re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", encoded)),
            f"{key}-encoding")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError(f"{key}-encoding") from error
    require(len(payload) <= maximum, f"{key}-oversize")
    return payload


def exact_tail(record: bytes, used: int, label: str) -> None:
    require(all(byte == 0xff for byte in record[used:]), f"{label}-tail")


def record_1_state(record: bytes) -> str:
    require(len(record) == 4096, "record-1-size")
    header = record[:12].hex()
    if header == EMPTY_HEADER:
        exact_tail(record, 12, "record-1")
        return "empty"
    require(header == VALID_HEADER_1, "record-1-header")
    expected = PREFIX + MARKER_1
    require(record[12:12 + len(expected)] == expected, "record-1-payload")
    require(record.count(MARKER_1) == 1, "record-1-marker-count")
    exact_tail(record, 12 + len(expected), "record-1")
    return "pure"


def record_2_state(record: bytes) -> str:
    require(len(record) == 4096, "record-2-size")
    header = record[:12].hex()
    if header == EMPTY_HEADER:
        exact_tail(record, 12, "record-2")
        return "empty"
    if header == VALID_HEADER_2_CORE:
        marker = MARKER_2_CORE
        state = "core"
    else:
        require(header == VALID_HEADER_2_REFUSAL, "record-2-header")
        marker = MARKER_2_REFUSAL
        state = "refusal"
    expected = PREFIX + marker
    require(record[12:12 + len(expected)] == expected, "record-2-payload")
    require(record.count(marker) == 1, "record-2-marker-count")
    exact_tail(record, 12 + len(expected), "record-2")
    return state


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
    state_1 = record_1_state(record_1)
    state_2 = record_2_state(record_2)
    require(values.get("record_1_header") == record_1[:12].hex(),
            "record-1-reported-header")
    require(values.get("record_2_header") == record_2[:12].hex(),
            "record-2-reported-header")

    for marker, retained, expected_state, actual_state, label in (
        (MARKER_1, RECORD_1, "pure", state_1, "record-1"),
        (MARKER_2_CORE, RECORD_2_CORE, "core", state_2, "record-2-core"),
        (MARKER_2_REFUSAL, RECORD_2_REFUSAL, "refusal", state_2,
         "record-2-refusal"),
    ):
        marker_count = pstore.count(marker)
        record_count = pstore.count(retained)
        require(marker_count <= 1 and record_count <= 1,
                f"{label}-duplicate-pstore")
        require(marker_count == record_count, f"{label}-partial-pstore")
        require(not record_count or actual_state == expected_state,
                f"{label}-pstore-direct-conflict")

    if state_1 == "empty" and state_2 == "empty":
        return (
            "before-pure-init-or-both-writers-refused",
            "both-early-initcall-records-exact-empty",
            "audit-pre-initcall-and-reset-retention-attribution",
        )
    if state_1 == "empty" and state_2 == "refusal":
        return (
            "pure-primary-refused-only",
            "primary-pure-record-empty-refusal-record-exact",
            "localize-primary-writer-refusal-gate",
        )
    if state_1 == "pure" and state_2 == "empty":
        return (
            "pure-init-only",
            "pure-init-committed-core-slot-exact-empty",
            "split-pure-to-core-initcall-order",
        )
    if state_1 == "pure" and state_2 == "refusal":
        return (
            "pure-plus-primary-refused",
            "pure-record-exact-and-refusal-record-exact",
            "audit-local-readback-and-ordering",
        )
    if state_1 == "pure" and state_2 == "core":
        return (
            "pure-and-core-initcalls",
            "both-early-initcall-records-exact",
            "move-forward-between-core-and-subsys-init",
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
    print("retained_records_1_2=exact" if accepted else
          "retained_records_1_2=unproved")
    print("observer_registrations=0-by-candidate-contract")
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
    print("claim_scope=early-initcall-order-localization-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
