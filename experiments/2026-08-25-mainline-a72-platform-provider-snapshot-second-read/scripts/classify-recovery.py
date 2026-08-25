#!/usr/bin/env python3
"""Classify exact changed-ID Gemian recovery of the provider-boundary records."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


CANDIDATE = "ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f"
PREFIX = b"====0.000000-D\n"
MARKER_1 = (
    b"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 token=GAPP-20260825-A "
    b"checkpoint=before-provider slot=1 crc32=0150f9c7\n"
)
MARKER_2 = (
    b"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 token=GAPP-20260825-A "
    b"checkpoint=after-provider slot=2 crc32=4fffb31e\n"
)
RECORD_1 = PREFIX + MARKER_1
RECORD_2 = PREFIX + MARKER_2
VALID_HEADER_1 = "444247437f0000007f000000"
VALID_HEADER_2 = "444247437e0000007e000000"
EMPTY_HEADER = "444247430000000000000000"


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


def decode(values: dict[str, str], key: str) -> bytes:
    encoded = values.get(key, "")
    require(bool(re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", encoded)), f"{key}-encoding")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError(f"{key}-encoding") from error
    require(len(payload) == 4096, f"{key}-size")
    return payload


def record_state(record: bytes, marker: bytes, valid_header: str, label: str) -> str:
    header = record[:12].hex()
    if header == EMPTY_HEADER:
        return "empty"
    require(header == valid_header, f"{label}-header")
    expected = PREFIX + marker
    require(record[12:12 + len(expected)] == expected, f"{label}-payload")
    require(record.count(marker) == 1, f"{label}-marker-count")
    return "valid"


def classify_text(path: Path) -> tuple[str, str, str]:
    values = parse(path)
    required = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "boot2_full_sha256": CANDIDATE,
        "record_1_size": "4096",
        "record_2_size": "4096",
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    for key, expected in required.items():
        require(values.get(key) == expected, f"{key}-mismatch")
    boot_id = values.get("recovery_boot_id", "")
    deployment_boot_id = values.get("deployment_boot_id", "")
    uuid = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
    require(bool(re.fullmatch(uuid, boot_id)), "recovery-boot-id")
    require(bool(re.fullmatch(uuid, deployment_boot_id)), "deployment-boot-id")
    require(boot_id != deployment_boot_id, "recovery-boot-id-unchanged")
    target = values.get("boot2_device", "")
    root = values.get("active_root", "")
    require(bool(re.fullmatch(r"/dev/mmcblk0p[0-9]+", target)), "boot2-device")
    require(bool(re.fullmatch(r"/dev/mmcblk0p[0-9]+", root)), "active-root")
    require(root != target, "boot2-active-root")

    record_1 = decode(values, "record_1_b64")
    record_2 = decode(values, "record_2_b64")
    state_1 = record_state(record_1, MARKER_1, VALID_HEADER_1, "record-1")
    state_2 = record_state(record_2, MARKER_2, VALID_HEADER_2, "record-2")
    require(values.get("record_1_header") == record_1[:12].hex(),
            "record-1-reported-header")
    require(values.get("record_2_header") == record_2[:12].hex(),
            "record-2-reported-header")

    if state_1 == "empty" and state_2 == "empty":
        return (
            "before-provider-boundary-or-writer-refused",
            "both-provider-boundary-records-exact-empty",
            "localize-platform-return-or-first-checkpoint-refusal",
        )
    if state_1 == "valid" and state_2 == "empty":
        return (
            "before-provider-only",
            "before-provider-committed-after-provider-empty",
            "split-the-ten-fixed-provider-reads-without-unchanged-retry",
        )
    if state_1 == "valid" and state_2 == "valid":
        return (
            "provider-returned",
            "both-provider-boundary-records-exact",
            "repair-only-post-checkpoint-serviceability-or-observation",
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
    print("platform_snapshot_calls=at-most-one-by-candidate-contract")
    print("provider_snapshots=at-most-one-by-candidate-contract")
    print("provider_i2c_reads=at-most-ten-by-candidate-contract")
    print("provider_i2c_writes=0-by-candidate-contract")
    print("provider_acquires=0-by-candidate-contract")
    print("provider_releases=0-by-candidate-contract")
    print("protected_clock_reads=0-by-candidate-contract")
    print("bigidvfs_reads=0-by-candidate-contract")
    print("publisher_calls=0-by-candidate-contract")
    print("owner_mutations=0-by-candidate-contract")
    print("cpu_requests=0-by-candidate-contract")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=platform-provider-boundary-localization-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
