#!/usr/bin/env python3
"""Classify the two retained A72 transition-ledger lanes after recovery."""

from __future__ import annotations

import argparse
import binascii
from dataclasses import dataclass
from pathlib import Path
import struct


MAGIC = 0x4C543747
VERSION = 0x00010009
PSTORE_SIGNATURE = 0x43474244
COPY_WORDS = 9
COPY_BYTES = COPY_WORDS * 4
PAYLOAD_BYTES = COPY_BYTES * 2
HEADER_BYTES = 12
CPU8_STAGE_MEMBERSHIP = 10
CPU8_TERMINAL_ONLINE = 5
CPU9_STAGE_MEMBERSHIP = 5
CPU9_TERMINAL_ONLINE = 3


class ClassificationError(ValueError):
    """Retained evidence did not satisfy the exact decision contract."""


@dataclass(frozen=True)
class Record:
    attempt_id: int
    generation: int
    phase: int
    stage: int
    terminal: int
    copy: int


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClassificationError(message)


def decode_record(data: bytes, copy: int, max_stage: int) -> Record | None:
    require(len(data) == COPY_BYTES, "ledger-copy-size-mismatch")
    words = struct.unpack("<9I", data)
    expected_crc = binascii.crc32(data[:32]) & 0xFFFFFFFF
    if words[0] != MAGIC or words[1] != VERSION or words[8] != expected_crc:
        return None
    attempt_id = words[2] | words[3] << 32
    generation, phase, stage, terminal = words[4:8]
    if (
        not attempt_id
        or not generation
        or not 1 <= phase <= 3
        or not 1 <= stage <= max_stage
        or not 0 <= terminal <= 5
        or (phase == 3 and not terminal)
        or (phase != 3 and terminal)
    ):
        return None
    return Record(attempt_id, generation, phase, stage, terminal, copy)


def latest_record(payload: bytes, max_stage: int) -> tuple[Record, tuple[Record, ...]]:
    require(len(payload) == PAYLOAD_BYTES, "ledger-payload-size-mismatch")
    records = tuple(
        record
        for copy in range(2)
        if (
            record := decode_record(
                payload[copy * COPY_BYTES : (copy + 1) * COPY_BYTES],
                copy,
                max_stage,
            )
        )
        is not None
    )
    require(records, "ledger-has-no-crc-valid-copy")
    generations = tuple(record.generation for record in records)
    require(
        len(generations) == len(set(generations)),
        "ledger-has-duplicate-valid-generations",
    )
    return max(records, key=lambda record: record.generation), records


def logical_empty_header(data: bytes) -> bool:
    require(len(data) == HEADER_BYTES, "pstore-header-size-mismatch")
    signature, start, size = struct.unpack("<3I", data)
    return signature == PSTORE_SIGNATURE and start == 0 and size == 0


def classify(
    cpu8_payload: bytes,
    cpu9_payload: bytes | None,
    cpu9_header: bytes,
    spare_header: bytes,
) -> tuple[str, Record, tuple[Record, ...], Record | None]:
    cpu8_latest, cpu8_records = latest_record(cpu8_payload, CPU8_STAGE_MEMBERSHIP)
    require(cpu8_latest.phase == 3, "CPU8-latest-is-not-terminal")
    require(
        cpu8_latest.stage == CPU8_STAGE_MEMBERSHIP,
        "CPU8-latest-is-not-membership-stage",
    )
    require(
        cpu8_latest.terminal == CPU8_TERMINAL_ONLINE,
        "CPU8-latest-is-not-online-proof",
    )
    require(logical_empty_header(spare_header), "spare-record-is-not-logical-empty")

    if cpu9_payload is None:
        require(logical_empty_header(cpu9_header), "missing-CPU9-file-but-lane-not-empty")
        return (
            "cpu8-terminal-cpu9-not-durably-admitted",
            cpu8_latest,
            cpu8_records,
            None,
        )

    cpu9_latest, _ = latest_record(cpu9_payload, CPU9_STAGE_MEMBERSHIP)
    require(
        cpu9_latest.attempt_id != cpu8_latest.attempt_id,
        "CPU8-and-CPU9-attempt-identities-collide",
    )
    if (
        cpu9_latest.phase == 3
        and cpu9_latest.stage == CPU9_STAGE_MEMBERSHIP
        and cpu9_latest.terminal == CPU9_TERMINAL_ONLINE
    ):
        result = "cpu8-and-cpu9-terminal-ledgers-present"
    else:
        result = "cpu8-terminal-cpu9-ledger-non-success"
    return result, cpu8_latest, cpu8_records, cpu9_latest


def encode_record(
    *, attempt_id: int, generation: int, phase: int, stage: int, terminal: int
) -> bytes:
    prefix = struct.pack(
        "<8I",
        MAGIC,
        VERSION,
        attempt_id & 0xFFFFFFFF,
        attempt_id >> 32,
        generation,
        phase,
        stage,
        terminal,
    )
    return prefix + struct.pack("<I", binascii.crc32(prefix) & 0xFFFFFFFF)


def rejected(*args: bytes | None) -> None:
    try:
        classify(*args)  # type: ignore[arg-type]
    except ClassificationError:
        return
    raise AssertionError("invalid retained evidence was accepted")


def self_test() -> None:
    empty_header = struct.pack("<3I", PSTORE_SIGNATURE, 0, 0)
    cpu8_payload = encode_record(
        attempt_id=1, generation=21, phase=3, stage=10, terminal=5
    ) + encode_record(attempt_id=1, generation=20, phase=2, stage=10, terminal=0)
    result, latest, records, cpu9 = classify(
        cpu8_payload, None, empty_header, empty_header
    )
    assert result == "cpu8-terminal-cpu9-not-durably-admitted"
    assert latest.generation == 21 and len(records) == 2 and cpu9 is None

    cpu9_payload = encode_record(
        attempt_id=2, generation=11, phase=3, stage=5, terminal=3
    ) + encode_record(attempt_id=2, generation=10, phase=2, stage=5, terminal=0)
    result, _, _, cpu9 = classify(
        cpu8_payload, cpu9_payload, empty_header, empty_header
    )
    assert result == "cpu8-and-cpu9-terminal-ledgers-present"
    assert cpu9 is not None and cpu9.generation == 11

    corrupt = bytearray(cpu8_payload)
    corrupt[0] ^= 0x80
    corrupt[COPY_BYTES] ^= 0x80
    rejected(bytes(corrupt), None, empty_header, empty_header)
    rejected(cpu8_payload, None, bytes(HEADER_BYTES), empty_header)
    rejected(cpu8_payload, None, empty_header, bytes(HEADER_BYTES))
    rejected(cpu8_payload, cpu8_payload, empty_header, empty_header)
    print("cpu9_recovery_classifier_tests=6-of-6-pass")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu8-payload", type=Path)
    parser.add_argument("--cpu9-payload", type=Path)
    parser.add_argument("--cpu9-header-hex")
    parser.add_argument("--spare-header-hex")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(args.cpu8_payload is not None, "--cpu8-payload-is-required")
    require(args.cpu9_header_hex is not None, "--cpu9-header-hex-is-required")
    require(args.spare_header_hex is not None, "--spare-header-hex-is-required")
    try:
        result, cpu8_latest, cpu8_records, cpu9_latest = classify(
            args.cpu8_payload.read_bytes(),
            args.cpu9_payload.read_bytes() if args.cpu9_payload else None,
            bytes.fromhex(args.cpu9_header_hex),
            bytes.fromhex(args.spare_header_hex),
        )
    except (ClassificationError, OSError, ValueError) as error:
        print("runtime_classification=rejected-attribution")
        print(f"runtime_reason={str(error).replace(' ', '-')}")
        return 3
    print(f"runtime_classification={result}")
    print(f"cpu8_valid_copies={len(cpu8_records)}")
    for record in sorted(cpu8_records, key=lambda item: item.copy):
        print(
            f"cpu8_copy_{record.copy}=attempt:{record.attempt_id},"
            f"generation:{record.generation},phase:{record.phase},"
            f"stage:{record.stage},terminal:{record.terminal},crc:valid"
        )
    print(f"cpu8_latest_copy={cpu8_latest.copy}")
    print("cpu9_lane=logical-empty" if cpu9_latest is None else "cpu9_lane=committed")
    if cpu9_latest is not None:
        print(f"cpu9_latest_copy={cpu9_latest.copy}")
        print(f"cpu9_latest_attempt_id={cpu9_latest.attempt_id}")
        print(f"cpu9_latest_generation={cpu9_latest.generation}")
        print(f"cpu9_latest_phase={cpu9_latest.phase}")
        print(f"cpu9_latest_stage={cpu9_latest.stage}")
        print(f"cpu9_latest_terminal={cpu9_latest.terminal}")
    print("spare_lane=logical-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
