#!/usr/bin/env python3
"""Classify the exact immutable CPU8 admission retained records."""

from __future__ import annotations

import argparse
import struct


SIGNATURE = 0x43474244
SLOT_SIZE = 4096
HEADER_SIZE = 12
ENTRY = (
    b"====0.000000-D\n"
    b"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
    b"kind=entry slot=2\n"
)
TERMINALS = {
    "zero-source-register": (
        b"====0.000000-D\n"
        b"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
        b"kind=zero-source-register slot=3\n"
    ),
    "zero-derive": (
        b"====0.000000-D\n"
        b"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
        b"kind=zero-derive slot=3\n"
    ),
    "zero-publish": (
        b"====0.000000-D\n"
        b"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
        b"kind=zero-publish slot=3\n"
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def classify_slot(data: bytes, records: dict[str, bytes]) -> str:
    require(len(data) == SLOT_SIZE, "slot must be exactly 4096 bytes")
    signature, start, size = struct.unpack_from("<3I", data)
    if signature == SIGNATURE and start == 0 and size == 0:
        return "logical-empty"
    require(signature == SIGNATURE, "foreign signature")
    require(start == size and 0 < size <= SLOT_SIZE - HEADER_SIZE,
            "torn or invalid committed header")
    payload = data[HEADER_SIZE:HEADER_SIZE + size]
    matches = [name for name, expected in records.items()
               if size == len(expected) and payload == expected]
    require(len(matches) == 1, "foreign or mutated payload")
    return matches[0]


def classify(entry: bytes, terminal: bytes) -> tuple[str, str]:
    entry_state = classify_slot(entry, {"entry": ENTRY})
    terminal_state = classify_slot(terminal, TERMINALS)
    require(not (entry_state == "logical-empty" and
                 terminal_state != "logical-empty"),
            "terminal exists without exact entry")
    if entry_state == "logical-empty":
        return "empty", "controller-not-established"
    if terminal_state == "logical-empty":
        return "entry-only", "controller-entered-no-zero-terminal"
    return "entry-and-terminal", terminal_state


def make_slot(payload: bytes | None) -> bytes:
    data = bytearray(SLOT_SIZE)
    struct.pack_into("<I", data, 0, SIGNATURE)
    if payload is not None:
        data[HEADER_SIZE:HEADER_SIZE + len(payload)] = payload
        struct.pack_into("<II", data, 4, len(payload), len(payload))
    return bytes(data)


def rejected(entry: bytes, terminal: bytes) -> None:
    try:
        classify(entry, terminal)
    except ValueError:
        return
    raise AssertionError("invalid trace combination was accepted")


def self_test() -> None:
    empty = make_slot(None)
    exact_entry = make_slot(ENTRY)
    assert classify(empty, empty) == ("empty", "controller-not-established")
    assert classify(exact_entry, empty) == (
        "entry-only", "controller-entered-no-zero-terminal")
    for name, payload in TERMINALS.items():
        assert classify(exact_entry, make_slot(payload)) == (
            "entry-and-terminal", name)
    rejected(empty, make_slot(TERMINALS["zero-derive"]))
    foreign = bytearray(empty)
    foreign[0] ^= 1
    rejected(bytes(foreign), empty)
    torn = bytearray(exact_entry)
    struct.pack_into("<I", torn, 8, len(ENTRY) - 1)
    rejected(bytes(torn), empty)
    mutated = bytearray(exact_entry)
    mutated[HEADER_SIZE + 5] ^= 1
    rejected(bytes(mutated), empty)
    oversize = bytearray(empty)
    struct.pack_into("<II", oversize, 4, SLOT_SIZE, SLOT_SIZE)
    rejected(bytes(oversize), empty)
    print("admission_trace_mutation_tests=10-of-10-pass")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-hex")
    parser.add_argument("--terminal-hex")
    parser.add_argument("--require-empty", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(args.entry_hex is not None and args.terminal_hex is not None,
            "--entry-hex and --terminal-hex are required")
    try:
        state, detail = classify(bytes.fromhex(args.entry_hex),
                                 bytes.fromhex(args.terminal_hex))
        if args.require_empty:
            require(state == "empty", "trace slots are not both logical-empty")
    except (ValueError, struct.error) as error:
        print("admission_trace_validation=rejected")
        print(f"admission_trace_reason={str(error).replace(' ', '-')}")
        return 3
    print("admission_trace_validation=passed")
    print(f"admission_trace_state={state}")
    print(f"admission_trace_detail={detail}")
    print("retained_ram_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
