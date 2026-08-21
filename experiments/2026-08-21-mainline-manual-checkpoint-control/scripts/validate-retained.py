#!/usr/bin/env python3
"""Classify bounded changed-ID Gemian recovery of the two manual records."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


CANDIDATE = "53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c"
PREFIX = b"GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A "
FIRST = PREFIX + b"checkpoint=manual-first slot=173 crc32=9576f05d\n"
SECOND = PREFIX + b"checkpoint=manual-second slot=174 crc32=c90b9e18\n"
EMPTY_HEADER = "444247430000000000000000"
MAX_PSTORE_BYTES = 4_194_304


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


def source_state(payload: bytes, first: bytes, second: bytes) -> str:
    first_count = payload.count(FIRST)
    second_count = payload.count(SECOND)
    tagged = payload.count(PREFIX)
    require(tagged == first_count + second_count, "foreign-manual-record")
    require(first_count <= 1 and second_count <= 1, "duplicate-manual-record")
    if first_count == second_count == 1:
        return "both"
    if first_count == second_count == 0:
        return "empty"
    raise ValueError("partial-manual-record")


def direct_state(slot_173: bytes, slot_174: bytes) -> str:
    first_in_173 = slot_173.count(FIRST)
    second_in_173 = slot_173.count(SECOND)
    first_in_174 = slot_174.count(FIRST)
    second_in_174 = slot_174.count(SECOND)
    tagged = slot_173.count(PREFIX) + slot_174.count(PREFIX)
    require(tagged == first_in_173 + second_in_173 + first_in_174 + second_in_174,
            "foreign-manual-record")
    if (first_in_173, second_in_173, first_in_174, second_in_174) == (1, 0, 0, 1):
        return "both"
    if tagged == 0:
        return "empty"
    raise ValueError("partial-crossed-or-duplicate-manual-record")


def classify_text(path: Path) -> tuple[str, str]:
    values = parse(path)
    required = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": CANDIDATE,
        "slot_173_size": "4096",
        "slot_174_size": "4096",
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    for key, expected in required.items():
        require(values.get(key) == expected, f"{key}-mismatch")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", values.get("recovery_boot_id_sha256", ""))),
            "recovery-boot-id-hash")
    require(bool(re.fullmatch(r"\d+", values.get("pstore_file_count", ""))),
            "pstore-file-count")

    slot_173 = decode(values, "slot_173_b64", 4096)
    slot_174 = decode(values, "slot_174_b64", 4096)
    pstore = decode(values, "pstore_payload_b64", MAX_PSTORE_BYTES)
    require(len(slot_173) == len(slot_174) == 4096, "retained-slot-size")
    direct = direct_state(slot_173, slot_174)
    pstore_state = source_state(pstore, FIRST, SECOND)

    if direct == "both" or pstore_state == "both":
        return "writer-and-recovery-pass", "both-exact-records-recovered"
    require(values.get("slot_173_header") == EMPTY_HEADER, "slot-173-not-empty")
    require(values.get("slot_174_header") == EMPTY_HEADER, "slot-174-not-empty")
    return "live-pass-recovered-empty", "cross-version-recovery-empty-not-local-writer-failure"


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
    print(f"retained_classification={result}")
    print(f"retained_reason={reason}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=manual-checkpoint-cross-version-recovery-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
