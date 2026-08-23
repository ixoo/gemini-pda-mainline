#!/usr/bin/env python3
"""Classify changed-ID Gemian recovery of the exact one-record raw write."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


CANDIDATE = "c10f2c03490fe1aa8ded11895a2d1817dd649edaffa307d0635fe2d69ce1c631"
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


def token_counts(payload: bytes) -> tuple[int, int, int]:
    first = payload.count(FIRST)
    second = payload.count(SECOND)
    tagged = payload.count(PREFIX)
    require(tagged == first + second, "foreign-manual-record")
    require(first <= 1 and second <= 1, "duplicate-manual-record")
    return first, second, tagged


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
    direct_first, direct_second, direct_tagged = token_counts(slot_173 + slot_174)
    pstore_first, pstore_second, pstore_tagged = token_counts(pstore)
    require(direct_second == 0 and pstore_second == 0, "unexpected-second-record")
    require(values.get("slot_174_header") == EMPTY_HEADER, "slot-174-not-empty")

    direct_recovered = (
        direct_first == direct_tagged == 1
        and values.get("slot_173_header") == EMPTY_HEADER
    )
    pstore_recovered = pstore_first == pstore_tagged == 1
    require(direct_recovered or pstore_recovered, "manual-first-record-not-recovered")
    source = "pstore" if pstore_recovered else "normalized-direct-slot"
    return "raw-writer-and-recovery-pass", f"manual-first-recovered-via-{source}"


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
    print("claim_scope=one-record-raw-writer-cross-version-recovery-only")
    return 0 if result == "raw-writer-and-recovery-pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
