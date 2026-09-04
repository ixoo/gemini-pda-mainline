#!/usr/bin/env python3
"""Decode the exact record-5 MT6797 thermal ledger after recovery."""

from __future__ import annotations

import argparse
import binascii
from pathlib import Path
import struct
import sys
import uuid


PSTORE_SIGNATURE = 0x43474244
MAGIC = 0x4D485447
VERSION = 0x0001000C
ATTEMPT_ID = 0x54484D4C00000001
COPY_WORDS = 12
COPIES = 2
PAYLOAD_BYTES = COPY_WORDS * COPIES * 4
SLOT_BYTES = 0x1000
MAX_GENERATION = 96
INDEX_NONE = 0xFFFFFFFF

OPERATIONS = {
    1: "probe",
    2: "calibration",
    3: "resource",
    4: "auxadc-map",
    5: "apmixed-map",
    6: "reset-acquire",
    7: "auxadc-clock-acquire",
    8: "clock-acquire",
    9: "transaction",
    10: "auxadc-clock-enable",
    11: "clock-enable",
    12: "reset",
    13: "apmixed",
    14: "global-idle",
    15: "pause-banks",
    16: "clear-channel",
    17: "prepare-bank",
    18: "commit-channel",
    19: "enable-bank",
    20: "release-bank",
    21: "first-sample",
    22: "zone-register",
    23: "probe-complete",
}
INDEXED_OPERATIONS = {17, 19, 20, 21}
PHASES = {1: "before", 2: "after", 3: "terminal"}
TERMINALS = {0: "none", 1: "success", 2: "failure"}


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
        raise DecodeError("capture-size-not-96-or-4096")
    signature, start, size = struct.unpack_from("<III", data)
    if signature != PSTORE_SIGNATURE:
        raise DecodeError("raw-slot-signature-invalid")
    if start != PAYLOAD_BYTES or size != PAYLOAD_BYTES:
        raise DecodeError("raw-slot-length-invalid")
    return data[12:12 + PAYLOAD_BYTES]


def signed(value: int) -> int:
    return struct.unpack("<i", struct.pack("<I", value))[0]


def semantic_valid(words: tuple[int, ...]) -> bool:
    generation, operation, phase, index = words[2:6]
    result = signed(words[6])
    terminal = words[7]
    attempt_id = words[8] | words[9] << 32
    if not 1 <= generation <= MAX_GENERATION:
        return False
    if operation not in OPERATIONS or phase not in PHASES:
        return False
    if operation in INDEXED_OPERATIONS:
        if index > 5:
            return False
    elif index != INDEX_NONE:
        return False
    if attempt_id != ATTEMPT_ID or words[10] != 0:
        return False
    if phase == 1:
        return result == 0 and terminal == 0
    if phase == 2:
        return result <= 0 and terminal == 0
    if terminal == 1:
        return operation == 23 and result == 0
    return terminal == 2 and result < 0


def decode_copy(payload: bytes, copy: int) -> dict[str, int] | None:
    offset = copy * COPY_WORDS * 4
    words = struct.unpack_from(f"<{COPY_WORDS}I", payload, offset)
    expected_crc = binascii.crc32(payload[offset:offset + 44]) & 0xFFFFFFFF
    if words[0] != MAGIC or words[1] != VERSION or words[11] != expected_crc:
        return None
    if not semantic_valid(words):
        return None
    return {
        "copy": copy,
        "generation": words[2],
        "operation": words[3],
        "phase": words[4],
        "index": words[5],
        "result": signed(words[6]),
        "terminal": words[7],
        "attempt_id": words[8] | words[9] << 32,
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
        generations = [record["generation"] for record in records]
        if generations[0] == generations[1]:
            raise DecodeError("ambiguous-equal-generation")
        if abs(generations[0] - generations[1]) != 1:
            raise DecodeError("noncontiguous-generations")
    for record in records:
        if record["copy"] != (record["generation"] - 1) % COPIES:
            raise DecodeError("copy-generation-parity-invalid")
    return max(records, key=lambda record: record["generation"])


def decision(record: dict[str, int]) -> str:
    if record["phase"] == 1:
        return "operation-entered-no-return"
    if record["phase"] == 2 and record["result"] < 0:
        return "operation-returned-error"
    if record["phase"] == 2:
        return "operation-completed-next-boundary-absent"
    if record["terminal"] == 1:
        return "thermal-probe-complete"
    return "thermal-probe-returned-failure"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-boot-id", required=True)
    parser.add_argument("--recovery-boot-id", required=True)
    parser.add_argument("--record", required=True, type=Path)
    args = parser.parse_args()
    try:
        record = decode(args.record.read_bytes(), args.pre_boot_id,
                        args.recovery_boot_id)
    except (OSError, DecodeError) as exc:
        print(f"thermal_ledger_decode=fail reason={exc}", file=sys.stderr)
        return 1
    print("thermal_ledger_decode=pass")
    print("recovery_boot_id_changed=yes")
    print("record=5")
    print("remote_record_removal=no")
    print(f"copy={record['copy']}")
    print(f"version=0x{VERSION:08x}")
    print(f"generation={record['generation']}")
    print(f"operation={record['operation']}")
    print(f"operation_name={OPERATIONS[record['operation']]}")
    print(f"phase={record['phase']}")
    print(f"phase_name={PHASES[record['phase']]}")
    index = record["index"]
    print(f"bank_index={'none' if index == INDEX_NONE else index}")
    print(f"result={record['result']}")
    print(f"terminal={record['terminal']}")
    print(f"terminal_name={TERMINALS[record['terminal']]}")
    print(f"attempt_id=0x{record['attempt_id']:016x}")
    print(f"decision={decision(record)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
