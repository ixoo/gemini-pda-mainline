#!/usr/bin/env python3
"""Validate the retained LK ``atag,devinfo`` byte-level contract.

The script deliberately never prints payload words.  It is suitable for a
synthetic fixture or a private, redacted capture and only reports structural
metadata plus whether the MT6797 thermal word ordering is valid.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


ATAG_DEVINFO_DATA = 0x41000804
HEADER_WORDS = 2
PAYLOAD_WORDS = 100
TRAILER_WORDS = 1
TAG_WORDS = HEADER_WORDS + PAYLOAD_WORDS + TRAILER_WORDS
THERMAL_WORD_ORDER = (32, 31, 33)


class ContractError(ValueError):
    """Raised when a property does not match the retained LK contract."""


def parse_property(blob: bytes) -> tuple[int, tuple[int, ...]]:
    """Return the payload length and thermal indexes without exposing values."""

    if len(blob) == 0 or len(blob) % 4:
        raise ContractError("property is empty or not 32-bit aligned")

    words = struct.unpack(f"<{len(blob) // 4}I", blob)
    if len(words) != TAG_WORDS:
        raise ContractError(f"expected exactly {TAG_WORDS} words")

    tag_size, tag = words[0], words[1]
    if tag != ATAG_DEVINFO_DATA:
        raise ContractError("unexpected tag")
    if tag_size != TAG_WORDS:
        raise ContractError("unexpected tag size")

    payload = words[HEADER_WORDS : HEADER_WORDS + PAYLOAD_WORDS]
    reported_size = words[-1]
    if reported_size != PAYLOAD_WORDS:
        raise ContractError("unexpected payload size trailer")
    if max(THERMAL_WORD_ORDER) >= len(payload):
        raise ContractError("thermal index exceeds payload")

    # The tuple is used only by the self-test to prove ordering.  Callers do
    # not receive the values and the CLI never prints them.
    return len(payload), tuple(payload[index] for index in THERMAL_WORD_ORDER)


def synthetic_property() -> bytes:
    """Build a deterministic fixture with distinguishable, non-device words."""

    payload = [0xA5000000 + index for index in range(PAYLOAD_WORDS)]
    words = [TAG_WORDS, ATAG_DEVINFO_DATA, *payload, PAYLOAD_WORDS]
    return struct.pack(f"<{len(words)}I", *words)


def run_self_test() -> None:
    payload_words, selected = parse_property(synthetic_property())
    expected = tuple(0xA5000000 + index for index in THERMAL_WORD_ORDER)
    if payload_words != PAYLOAD_WORDS or selected != expected:
        raise ContractError("thermal word ordering self-test failed")

    malformed = (
        synthetic_property()[:-1],
        struct.pack("<I", TAG_WORDS - 1) + synthetic_property()[4:],
        synthetic_property()[:0] + struct.pack("<II", TAG_WORDS, 0),
    )
    for fixture in malformed:
        try:
            parse_property(fixture)
        except ContractError:
            continue
        raise ContractError("malformed-input rejection self-test failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="private binary property capture; values are never printed",
    )
    args = parser.parse_args()

    try:
        if args.input is None:
            run_self_test()
            source = "synthetic"
        else:
            payload_words, _ = parse_property(args.input.read_bytes())
            if payload_words != PAYLOAD_WORDS:
                raise ContractError("unexpected payload word count")
            source = "private-input"
    except (ContractError, OSError, struct.error) as exc:
        print(f"validation=mt6797-atag-devinfo-contract")
        print(f"status=fail reason={exc}")
        return 1

    print("validation=mt6797-atag-devinfo-contract")
    print("status=pass")
    print(f"source={source}")
    print(f"tag=0x{ATAG_DEVINFO_DATA:08x}")
    print(f"property_words={TAG_WORDS}")
    print(f"payload_words={PAYLOAD_WORDS}")
    print("property_word_encoding=little-endian-opaque-bytes")
    print("thermal_word_indices=31,32,33")
    print("thermal_cell_word_order=32,31,33")
    print("raw_values_printed=no")
    return 0


if __name__ == "__main__":
    sys.exit(main())
