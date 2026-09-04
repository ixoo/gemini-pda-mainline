#!/usr/bin/env python3
"""Hardware-free tests for the changed-boot-ID record-5 decoder."""

from __future__ import annotations

import binascii
import importlib.util
from pathlib import Path
import struct
import unittest


SCRIPT = Path(__file__).with_name("decode_thermal_ledger.py")
SPEC = importlib.util.spec_from_file_location("thermal_ledger_decoder", SCRIPT)
assert SPEC and SPEC.loader
DECODER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DECODER)
BEFORE = "11111111-2222-4333-8444-555555555555"
AFTER = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def wire(generation: int, operation: int, phase: int,
         index: int = DECODER.INDEX_NONE, result: int = 0,
         terminal: int = 0) -> bytes:
    words = [0] * DECODER.COPY_WORDS
    words[:11] = [
        DECODER.MAGIC, DECODER.VERSION, generation, operation, phase, index,
        result & 0xFFFFFFFF, terminal, DECODER.ATTEMPT_ID & 0xFFFFFFFF,
        DECODER.ATTEMPT_ID >> 32, 0,
    ]
    words[11] = binascii.crc32(struct.pack("<11I", *words[:11])) & 0xFFFFFFFF
    return struct.pack("<12I", *words)


def payload(*copies: bytes) -> bytes:
    empty = bytes([0xFF]) * (DECODER.COPY_WORDS * 4)
    return b"".join((list(copies) + [empty, empty])[:2])


class DecoderTests(unittest.TestCase):
    def test_newest_alternating_copy(self) -> None:
        result = DECODER.decode(
            payload(wire(1, 1, 1), wire(2, 2, 2)), BEFORE, AFTER)
        self.assertEqual((result["copy"], result["generation"],
                          result["operation"]), (1, 2, 2))

    def test_raw_slot(self) -> None:
        body = payload(wire(1, 1, 1))
        raw = struct.pack("<III", DECODER.PSTORE_SIGNATURE,
                          len(body), len(body)) + body
        raw += bytes(DECODER.SLOT_BYTES - len(raw))
        self.assertEqual(DECODER.decode(raw, BEFORE, AFTER)["generation"], 1)

    def test_indexed_operation(self) -> None:
        result = DECODER.decode(payload(wire(1, 17, 2, index=5)), BEFORE, AFTER)
        self.assertEqual(result["index"], 5)

    def test_failure_terminal(self) -> None:
        result = DECODER.decode(
            payload(wire(1, 12, 3, result=-5, terminal=2)), BEFORE, AFTER)
        self.assertEqual(DECODER.decision(result),
                         "thermal-probe-returned-failure")

    def test_success_terminal(self) -> None:
        result = DECODER.decode(
            payload(wire(1, 23, 3, terminal=1)), BEFORE, AFTER)
        self.assertEqual(DECODER.decision(result), "thermal-probe-complete")

    def test_changed_boot_required(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "unchanged"):
            DECODER.decode(payload(wire(1, 1, 1)), BEFORE, BEFORE)

    def test_crc_refused(self) -> None:
        damaged = bytearray(wire(1, 1, 1))
        damaged[20] ^= 1
        with self.assertRaisesRegex(DECODER.DecodeError, "no-crc-valid"):
            DECODER.decode(payload(bytes(damaged)), BEFORE, AFTER)

    def test_equal_generation_refused(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "ambiguous"):
            DECODER.decode(payload(wire(1, 1, 1), wire(1, 2, 2)), BEFORE, AFTER)

    def test_generation_gap_refused(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "noncontiguous"):
            DECODER.decode(payload(wire(1, 1, 1), wire(4, 4, 2)), BEFORE, AFTER)

    def test_copy_parity_refused(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "parity"):
            DECODER.decode(payload(wire(2, 2, 2)), BEFORE, AFTER)

    def test_bad_bank_refused(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "no-crc-valid"):
            DECODER.decode(payload(wire(1, 17, 1, index=6)), BEFORE, AFTER)

    def test_wrong_attempt_refused(self) -> None:
        damaged = bytearray(wire(1, 1, 1))
        struct.pack_into("<I", damaged, 8 * 4, 2)
        struct.pack_into("<I", damaged, 11 * 4,
                         binascii.crc32(damaged[:44]) & 0xFFFFFFFF)
        with self.assertRaisesRegex(DECODER.DecodeError, "no-crc-valid"):
            DECODER.decode(payload(bytes(damaged)), BEFORE, AFTER)


if __name__ == "__main__":
    unittest.main()
