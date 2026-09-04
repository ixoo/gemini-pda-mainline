#!/usr/bin/env python3
"""Focused positive and rejecting cases for the exact DT transform."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from build_dtb import DtbError, TARGET_PATH, TARGET_PROPERTY, properties, transform


def reject(data: bytes, expected: str, *, check_hash: bool) -> None:
    try:
        transform(data, check_control_hash=check_hash)
    except DtbError as exc:
        if expected not in str(exc):
            raise AssertionError(f"unexpected rejection: {exc}") from exc
    else:
        raise AssertionError(f"mutation was accepted: {expected}")


def mutate_tuple(data: bytes, phandle: int, reset_id: int) -> bytes:
    props = properties(data)
    offset, _ = props[(TARGET_PATH, TARGET_PROPERTY)]
    changed = bytearray(data)
    changed[offset:offset + 8] = struct.pack(">II", phandle, reset_id)
    return bytes(changed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", required=True, type=Path)
    args = parser.parse_args()
    control = args.control.read_bytes()
    repaired = transform(control)
    assert properties(repaired)[(TARGET_PATH, TARGET_PROPERTY)][1] == struct.pack(">II", 3, 1)
    reject(repaired, "not exact control", check_hash=False)
    reject(mutate_tuple(control, 4, 64), "not exact control", check_hash=False)
    reject(mutate_tuple(control, 3, 65), "not exact control", check_hash=False)
    reject(b"not-a-dtb", "header is truncated", check_hash=False)
    reject(control[:-1] + bytes([control[-1] ^ 1]), "SHA-256 changed", check_hash=True)
    print("validation=exact-pwrap-reset-dtb-transform-tests")
    print("positive_cases=1")
    print("mutations_rejected=5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
