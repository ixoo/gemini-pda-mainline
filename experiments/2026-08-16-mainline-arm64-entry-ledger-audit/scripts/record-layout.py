#!/usr/bin/env python3
"""Freeze exact framed entry-ledger records and aligned assembly words."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("entry_oracle", SCRIPT_DIR / "oracle.py")
assert spec and spec.loader
oracle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = oracle
spec.loader.exec_module(oracle)

FRAME = b"====0.000000-D\n"
HEADER_SIZE = 12
PAYLOAD_CAPACITY = oracle.ZONE_SIZE - HEADER_SIZE
STAGE_CODES = {
    "primary-entry": "E0",
    "pre-primary-switch": "E1",
    "post-mmu": "E2",
    "post-reserved-scan": "E3",
}


def record(stage) -> bytes:
    marker = f"{oracle.TOKEN} {STAGE_CODES[stage.name]}\n".encode("ascii")
    return FRAME + marker


def padded_words(payload: bytes) -> tuple[int, ...]:
    padded = payload + b"\0" * (-len(payload) % 4)
    return tuple(
        int.from_bytes(padded[offset : offset + 4], "little")
        for offset in range(0, len(padded), 4)
    )


def validate() -> tuple[tuple[object, bytes, tuple[int, ...]], ...]:
    design = oracle.exact_design()
    oracle.validate(design)
    rows = []
    seen = set()
    for stage in design.stages:
        payload = record(stage)
        words = padded_words(payload)
        rebuilt = b"".join(word.to_bytes(4, "little") for word in words)[: len(payload)]
        oracle.require(payload.startswith(FRAME), f"{stage.name} framing changed")
        oracle.require(payload.endswith(b"\n"), f"{stage.name} lacks final newline")
        oracle.require(len(payload) <= PAYLOAD_CAPACITY, f"{stage.name} exceeds zone")
        oracle.require(rebuilt == payload, f"{stage.name} word roundtrip failed")
        oracle.require(
            all((HEADER_SIZE + index * 4) % 4 == 0 for index in range(len(words))),
            f"{stage.name} generated an unaligned word store",
        )
        oracle.require(payload not in seen, f"{stage.name} record is not unique")
        seen.add(payload)
        rows.append((stage, payload, words))
    return tuple(rows)


def main() -> None:
    rows = validate()
    print("validation=arm64-entry-ledger-record-layout")
    for stage, payload, words in rows:
        print(f"stage={stage.name}")
        print(f"slot={stage.slot}")
        print(f"record_length={len(payload)}")
        print(f"record_sha256={hashlib.sha256(payload).hexdigest()}")
        print(f"aligned_word_count={len(words)}")
        print("words=" + ",".join(f"0x{word:08x}" for word in words))
    print("payload_offset=12")
    print("store_width=32-bit-or-narrower")
    print("start_equals_size_equals_exact_record_length=yes")
    print("result=pass")


if __name__ == "__main__":
    main()
