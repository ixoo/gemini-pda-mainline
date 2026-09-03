#!/usr/bin/env python3
"""Decode an exact record-4 ledger only after changed-boot-ID recovery."""

from __future__ import annotations

import argparse
import binascii
from pathlib import Path
import struct
import sys
import uuid


PSTORE_SIGNATURE = 0x43474244
MAGIC = 0x4C483947
VERSION = 0x00010001
COPY_WORDS = 27
COPIES = 2
PAYLOAD_BYTES = COPY_WORDS * COPIES * 4
SLOT_BYTES = 0x1000
MAX_GENERATION = 16

STAGES = {
    1: "binding-entry-parent-exact",
    2: "down-owner-prepared",
    3: "watchdog-validated",
    4: "baseline-valid",
    5: "down-owner-validated",
    6: "target-disable-valid",
    7: "cpu-off-committed-before-smc",
    8: "cpu-off-returned-fault",
    9: "affinity-level0-off",
    10: "post-state-valid",
    11: "cpu8-responsive",
    12: "off-proof-accepted",
    13: "generic-down-complete-members-0x1",
    14: "restore-prepared",
    15: "cpu-on-committed-before-call",
    16: "secondary-complete",
    17: "generic-restore-complete-members-0x3",
}
TERMINALS = {
    0: "none",
    1: "rejected-precommit",
    2: "cpu-off-returned",
    3: "postcommit-down-fault",
    4: "restore-fault",
    5: "restored-success",
}


class DecodeError(ValueError):
    pass


def canonical_uuid(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise DecodeError("malformed-boot-id") from exc
    if str(parsed) != value.lower():
        raise DecodeError("noncanonical-boot-id")
    return str(parsed)


def payload_from_capture(data: bytes) -> bytes:
    if len(data) == PAYLOAD_BYTES:
        return data
    if len(data) != SLOT_BYTES:
        raise DecodeError("capture-size-not-216-or-4096")
    signature, start, size = struct.unpack_from("<III", data)
    if signature != PSTORE_SIGNATURE:
        raise DecodeError("raw-slot-signature-invalid")
    if start != PAYLOAD_BYTES or size != PAYLOAD_BYTES:
        raise DecodeError("raw-slot-length-invalid")
    return data[12:12 + PAYLOAD_BYTES]


def semantic_valid(words: tuple[int, ...]) -> bool:
    generation, stage, terminal, error_u32 = words[2:6]
    error = struct.unpack("<i", struct.pack("<I", error_u32))[0]
    session = words[6] | words[7] << 32
    parent_generation = words[8]
    parent_cookie = words[9] | words[10] << 32
    watchdog = words[11] | words[12] << 32
    down_generation = words[13]
    down_cookie = words[14] | words[15] << 32
    restore_generation = words[16]
    restore_cookie = words[17] | words[18] << 32
    call_counts = words[20:24]
    online_mask = words[24] & 0xFFFF
    members = words[24] >> 16
    if not 1 <= generation <= MAX_GENERATION or stage not in STAGES:
        return False
    if terminal not in TERMINALS or not session or not parent_generation or not parent_cookie:
        return False
    if stage >= 2 and (not down_generation or not down_cookie):
        return False
    if stage >= 3 and not watchdog:
        return False
    if stage >= 14 and (not restore_generation or not restore_cookie):
        return False
    if any(count > 1 for count in call_counts):
        return False
    if online_mask & ~0x3FF or members & ~0x3:
        return False
    if terminal == 0:
        return error == 0 and stage not in (8, 17)
    if terminal == 5:
        return stage == 17 and error == 0
    if error == 0:
        return False
    if terminal == 1:
        return stage <= 6
    if terminal == 2:
        return stage == 8
    if terminal == 3:
        return 9 <= stage <= 13
    return terminal == 4 and stage >= 14


def decode_copy(payload: bytes, copy: int) -> dict[str, int] | None:
    offset = copy * COPY_WORDS * 4
    words = struct.unpack_from("<27I", payload, offset)
    expected_crc = binascii.crc32(payload[offset:offset + 26 * 4]) & 0xFFFFFFFF
    if words[0] != MAGIC or words[1] != VERSION or words[26] != expected_crc:
        return None
    if not semantic_valid(words):
        return None
    error = struct.unpack("<i", struct.pack("<I", words[5]))[0]
    return {
        "copy": copy,
        "generation": words[2],
        "stage": words[3],
        "terminal": words[4],
        "error": error,
        "session_id": words[6] | words[7] << 32,
        "parent_generation": words[8],
        "parent_cookie": words[9] | words[10] << 32,
        "watchdog_identity": words[11] | words[12] << 32,
        "down_generation": words[13],
        "down_cookie": words[14] | words[15] << 32,
        "restore_generation": words[16],
        "restore_cookie": words[17] | words[18] << 32,
        "result_flags": words[19],
        "cpu_off_calls": words[20],
        "affinity_calls": words[21],
        "cpu8_ipi_calls": words[22],
        "cpu_on_calls": words[23],
        "online_mask": words[24] & 0xFFFF,
        "members": words[24] >> 16,
        "readback_mismatch": words[25],
    }


def decode(data: bytes, pre_boot_id: str, recovery_boot_id: str) -> dict[str, int]:
    before = canonical_uuid(pre_boot_id)
    after = canonical_uuid(recovery_boot_id)
    if before == after:
        raise DecodeError("recovery-boot-id-unchanged")
    payload = payload_from_capture(data)
    records = [record for copy in range(COPIES)
               if (record := decode_copy(payload, copy)) is not None]
    if not records:
        raise DecodeError("no-crc-valid-semantic-copy")
    if len(records) == 2:
        if records[0]["generation"] == records[1]["generation"]:
            raise DecodeError("ambiguous-equal-generation")
        if abs(records[0]["generation"] - records[1]["generation"]) != 1:
            raise DecodeError("noncontiguous-generations")
    for record in records:
        if record["copy"] != (record["generation"] - 1) % COPIES:
            raise DecodeError("copy-generation-parity-invalid")
    return max(records, key=lambda record: record["generation"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-boot-id", required=True)
    parser.add_argument("--recovery-boot-id", required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = args.record.read_bytes()
        record = decode(data, args.pre_boot_id, args.recovery_boot_id)
    except (OSError, DecodeError) as exc:
        print(f"hotplug_ledger_decode=fail reason={exc}", file=sys.stderr)
        return 1
    print("hotplug_ledger_decode=pass")
    print("recovery_boot_id_changed=yes")
    print("remote_record_removal=no")
    print(f"copy={record['copy']}")
    print(f"generation={record['generation']}")
    print(f"stage={record['stage']}")
    print(f"stage_name={STAGES[record['stage']]}")
    print(f"terminal={record['terminal']}")
    print(f"terminal_name={TERMINALS[record['terminal']]}")
    print(f"error={record['error']}")
    for name in (
        "session_id", "parent_generation", "parent_cookie",
        "watchdog_identity", "down_generation", "down_cookie",
        "restore_generation", "restore_cookie", "result_flags",
        "cpu_off_calls", "affinity_calls", "cpu8_ipi_calls",
        "cpu_on_calls", "online_mask", "members", "readback_mismatch",
    ):
        value = record[name]
        if name.endswith("_id") or name.endswith("_cookie") or name in {
            "watchdog_identity", "result_flags", "online_mask", "members",
            "readback_mismatch",
        }:
            print(f"{name}=0x{value:x}")
        else:
            print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
