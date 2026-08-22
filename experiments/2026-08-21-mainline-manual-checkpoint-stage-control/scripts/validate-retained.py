#!/usr/bin/env python3
"""Source-pin retained recovery and bind it to the live-stage candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re


SOURCE_SHA256 = "52dc1ec02e24cbedfe03623b3e177899b8b5abd4cb80df484cd035dd6632460a"
CANDIDATE = "43e7f44eeef694ef876f7686ae03e2a779a118141e7f9efa060ccc1182c8eac3"
SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_PATH = (
    SCRIPT_DIR.parents[1]
    / "2026-08-21-mainline-manual-checkpoint-control/scripts/validate-retained.py"
)
if not SOURCE_PATH.is_file() or SOURCE_PATH.is_symlink():
    raise SystemExit("retained validator source is missing or unsafe")
if hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("retained validator source identity changed")
SPEC = importlib.util.spec_from_file_location("manual_checkpoint_retained_source", SOURCE_PATH)
assert SPEC and SPEC.loader
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)
SOURCE.CANDIDATE = CANDIDATE

PREFIX = SOURCE.PREFIX
FIRST = SOURCE.FIRST
SECOND = SOURCE.SECOND
EMPTY_HEADER = SOURCE.EMPTY_HEADER
MAX_PSTORE_BYTES = SOURCE.MAX_PSTORE_BYTES


def payload_state(payload: bytes) -> str:
    first = payload.count(FIRST)
    second = payload.count(SECOND)
    tagged = payload.count(PREFIX)
    if tagged != first + second or first > 1 or second > 1:
        raise ValueError("foreign-or-duplicate-manual-record")
    if (first, second) == (1, 1):
        return "both"
    if (first, second) == (1, 0):
        return "first"
    if (first, second) == (0, 0):
        return "empty"
    raise ValueError("second-only-manual-record")


def direct_state(slot_173: bytes, slot_174: bytes) -> str:
    first_173 = slot_173.count(FIRST)
    second_173 = slot_173.count(SECOND)
    first_174 = slot_174.count(FIRST)
    second_174 = slot_174.count(SECOND)
    tagged = slot_173.count(PREFIX) + slot_174.count(PREFIX)
    if tagged != first_173 + second_173 + first_174 + second_174:
        raise ValueError("foreign-manual-record")
    counts = (first_173, second_173, first_174, second_174)
    if counts == (1, 0, 0, 1):
        return "both"
    if counts == (1, 0, 0, 0):
        return "first"
    if tagged == 0:
        return "empty"
    raise ValueError("crossed-or-duplicate-manual-record")


def classify_text(path: Path) -> tuple[str, str]:
    values = SOURCE.parse(path)
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
        SOURCE.require(values.get(key) == expected, f"{key}-mismatch")
    SOURCE.require(
        bool(re.fullmatch(r"[0-9a-f]{64}", values.get("recovery_boot_id_sha256", ""))),
        "recovery-boot-id-hash",
    )
    SOURCE.require(bool(re.fullmatch(r"\d+", values.get("pstore_file_count", ""))),
                   "pstore-file-count")

    slot_173 = SOURCE.decode(values, "slot_173_b64", 4096)
    slot_174 = SOURCE.decode(values, "slot_174_b64", 4096)
    pstore = SOURCE.decode(values, "pstore_payload_b64", MAX_PSTORE_BYTES)
    SOURCE.require(len(slot_173) == len(slot_174) == 4096, "retained-slot-size")
    states = (direct_state(slot_173, slot_174), payload_state(pstore))
    nonempty = {state for state in states if state != "empty"}
    SOURCE.require(len(nonempty) <= 1, "recovery-source-conflict")
    state = next(iter(nonempty), "empty")
    if state == "both":
        return "writer-and-recovery-pass", "both-exact-records-recovered"
    if state == "first":
        return "writer-first-recovery-pass", "exact-first-record-only-recovered"
    SOURCE.require(values.get("slot_173_header") == EMPTY_HEADER, "slot-173-not-empty")
    SOURCE.require(values.get("slot_174_header") == EMPTY_HEADER, "slot-174-not-empty")
    return "live-pass-recovered-empty", "cross-version-recovery-empty-not-live-stage-failure"


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
    print("claim_scope=manual-checkpoint-stage-cross-version-recovery-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
