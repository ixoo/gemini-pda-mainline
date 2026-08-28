#!/usr/bin/env python3
"""Validate the exact retained transition-ledger preflight bytes."""

from __future__ import annotations

import argparse
import binascii
import struct


SLOT_PREFIX_SIZE = 84
SIGNATURE = 0x43474244
MAGIC = 0x4C543747
VERSION = 0x00010009
PAYLOAD_SIZE = 72
COPY_WORDS = 9
COPY_BYTES = COPY_WORDS * 4


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def record(words: tuple[int, ...]) -> dict[str, int] | None:
    require(len(words) == COPY_WORDS, "record word count")
    expected_crc = binascii.crc32(struct.pack("<8I", *words[:8])) & 0xFFFFFFFF
    if words[0] != MAGIC or words[1] != VERSION or words[8] != expected_crc:
        return None
    attempt = words[2] | words[3] << 32
    generation, phase, stage, terminal = words[4:8]
    if (not attempt or not generation or not 1 <= phase <= 3 or
            not 1 <= stage <= 9 or not 0 <= terminal <= 5 or
            (phase == 3 and not terminal) or (phase != 3 and terminal)):
        return None
    return {
        "attempt_id": attempt,
        "generation": generation,
        "phase": phase,
        "stage": stage,
        "terminal": terminal,
    }


def classify(data: bytes) -> tuple[str, dict[str, int] | None, int | None]:
    require(len(data) == SLOT_PREFIX_SIZE, "slot prefix must be exactly 84 bytes")
    words = struct.unpack("<21I", data)
    signature, start, size = words[:3]
    if signature == 0xFFFFFFFF and start == 0xFFFFFFFF and size == 0xFFFFFFFF:
        return "raw-header", None, None
    if signature == SIGNATURE and start == 0 and size == 0:
        return "logical-empty", None, None
    require(signature == SIGNATURE and start == PAYLOAD_SIZE and size == PAYLOAD_SIZE,
            "header is not raw, logical-empty, or committed transition ledger")
    valid: list[tuple[int, dict[str, int]]] = []
    for copy in range(2):
        offset = 3 + copy * COPY_WORDS
        decoded = record(words[offset:offset + COPY_WORDS])
        if decoded is not None:
            valid.append((copy, decoded))
    require(bool(valid), "committed ledger has no valid copy")
    generations = [item[1]["generation"] for item in valid]
    require(len(generations) == len(set(generations)),
            "committed ledger has duplicate valid generations")
    latest = max(valid, key=lambda item: item[1]["generation"])
    return "committed-valid", latest[1], latest[0]


def encode_record(*, attempt: int, generation: int, phase: int,
                  stage: int, terminal: int) -> bytes:
    first = struct.pack(
        "<8I", MAGIC, VERSION, attempt & 0xFFFFFFFF, attempt >> 32,
        generation, phase, stage, terminal,
    )
    return first + struct.pack("<I", binascii.crc32(first) & 0xFFFFFFFF)


def self_test() -> None:
    raw = b"\xff" * SLOT_PREFIX_SIZE
    assert classify(raw)[0] == "raw-header"
    empty = struct.pack("<3I", SIGNATURE, 0, 0) + b"\xa5" * PAYLOAD_SIZE
    assert classify(empty)[0] == "logical-empty"
    older = encode_record(attempt=0x1122334455667788, generation=7,
                          phase=2, stage=4, terminal=0)
    newer = encode_record(attempt=0x1122334455667788, generation=8,
                          phase=3, stage=4, terminal=2)
    committed = struct.pack("<3I", SIGNATURE, PAYLOAD_SIZE, PAYLOAD_SIZE) + older + newer
    state, latest, copy = classify(committed)
    assert state == "committed-valid" and latest is not None
    assert latest["generation"] == 8 and latest["terminal"] == 2 and copy == 1
    corrupt = bytearray(committed)
    corrupt[44] ^= 0x80
    corrupt[80] ^= 0x80
    try:
        classify(bytes(corrupt))
    except ValueError:
        pass
    else:
        raise AssertionError("corrupt committed ledger was accepted")
    print("transition_ledger_self_test=pass")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hex")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(args.hex is not None, "--hex is required")
    try:
        data = bytes.fromhex(args.hex)
        state, latest, copy = classify(data)
    except (ValueError, struct.error) as error:
        print("transition_ledger_preflight=rejected")
        print(f"transition_ledger_reason={str(error).replace(' ', '-')}")
        return 3
    print("transition_ledger_preflight=passed")
    print(f"transition_ledger_state={state}")
    print("retained_ram_write=none")
    if latest is not None:
        print(f"transition_ledger_latest_copy={copy}")
        for key in ("attempt_id", "generation", "phase", "stage", "terminal"):
            print(f"transition_ledger_latest_{key}={latest[key]}")
    else:
        print("transition_ledger_latest_copy=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
