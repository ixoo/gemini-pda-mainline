#!/usr/bin/env python3
"""Hardware-free tests for the changed-boot-ID record-4 decoder."""

from __future__ import annotations

import binascii
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("decode-hotplug-ledger.py")
SPEC = importlib.util.spec_from_file_location("hotplug_decoder", SCRIPT)
assert SPEC and SPEC.loader
DECODER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DECODER)

BEFORE = "11111111-2222-4333-8444-555555555555"
AFTER = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def wire(generation: int, stage: int, terminal: int = 0,
         error: int = 0, readback_mismatch: int = 0) -> bytes:
    words = [0] * 27
    words[0] = DECODER.MAGIC
    words[1] = DECODER.VERSION
    words[2] = generation
    words[3] = stage
    words[4] = terminal
    words[5] = error & 0xFFFFFFFF
    words[6:8] = [0x87654321, 0x12345678]
    words[8] = 7
    words[9:11] = [0x33334444, 0x11112222]
    if stage >= 2:
        words[13] = 8
        words[14:16] = [0x44445555, 0x22223333]
    if stage >= 3:
        words[11:13] = [0x55556666, 0x33334444]
    if stage >= 14:
        words[16] = 9
        words[17:19] = [0x66667777, 0x44445555]
    words[20] = 1 if stage >= 8 else 0
    words[21] = 1 if stage >= 9 else 0
    words[22] = 1 if stage >= 11 else 0
    words[23] = 1 if stage >= 16 else 0
    online = 0x1FF if 9 <= stage < 16 else 0x3FF
    members = 1 if 13 <= stage < 17 else 3
    words[24] = online | members << 16
    words[25] = readback_mismatch
    prefix = struct.pack("<26I", *words[:26])
    words[26] = binascii.crc32(prefix) & 0xFFFFFFFF
    return struct.pack("<27I", *words)


def payload(*copies: bytes) -> bytes:
    empty = bytes([0xFF]) * (27 * 4)
    values = list(copies) + [empty] * (2 - len(copies))
    return b"".join(values[:2])


class DecoderTests(unittest.TestCase):
    def test_payload_newest(self) -> None:
        result = DECODER.decode(payload(wire(1, 1), wire(2, 2)), BEFORE, AFTER)
        self.assertEqual((result["copy"], result["generation"], result["stage"]),
                         (1, 2, 2))

    def test_raw_slot(self) -> None:
        body = payload(wire(1, 1))
        raw = struct.pack("<III", DECODER.PSTORE_SIGNATURE,
                          len(body), len(body)) + body
        raw += bytes(DECODER.SLOT_BYTES - len(raw))
        self.assertEqual(DECODER.decode(raw, BEFORE, AFTER)["generation"], 1)

    def test_terminal(self) -> None:
        result = DECODER.decode(payload(wire(1, 1, 1, -1)), BEFORE, AFTER)
        self.assertEqual(result["terminal"], 1)
        self.assertEqual(result["error"], -1)

    def test_changed_boot_required(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "unchanged"):
            DECODER.decode(payload(wire(1, 1)), BEFORE, BEFORE)

    def test_crc_refused(self) -> None:
        damaged = bytearray(wire(1, 1))
        damaged[20] ^= 1
        with self.assertRaisesRegex(DECODER.DecodeError, "no-crc-valid"):
            DECODER.decode(payload(bytes(damaged)), BEFORE, AFTER)

    def test_equal_generation_refused(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "ambiguous"):
            DECODER.decode(payload(wire(1, 1), wire(1, 1)), BEFORE, AFTER)

    def test_gap_refused(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "noncontiguous"):
            DECODER.decode(payload(wire(1, 1), wire(4, 4)), BEFORE, AFTER)

    def test_wrong_copy_parity_refused(self) -> None:
        with self.assertRaisesRegex(DECODER.DecodeError, "parity"):
            DECODER.decode(payload(wire(2, 2)), BEFORE, AFTER)

    def test_bad_shape_refused(self) -> None:
        bad = bytearray(wire(1, 1))
        struct.pack_into("<I", bad, 20 * 4, 2)
        struct.pack_into("<I", bad, 26 * 4,
                         binascii.crc32(bad[:26 * 4]) & 0xFFFFFFFF)
        with self.assertRaisesRegex(DECODER.DecodeError, "no-crc-valid"):
            DECODER.decode(payload(bytes(bad)), BEFORE, AFTER)

    def test_legacy_readback_boolean(self) -> None:
        self.assertEqual(DECODER.readback_mismatch_details(1),
                         ("legacy-boolean", ["mismatch"]))

    def test_readback_bitmap_names(self) -> None:
        value = (DECODER.READBACK_BITMAP_V1 | 1 << 12 | 1 << 22)
        result = DECODER.decode(
            payload(wire(1, 12, 3, -5, value)), BEFORE, AFTER)
        self.assertEqual(result["readback_mismatch"], value)
        self.assertEqual(DECODER.readback_mismatch_details(value), (
            "bitmap-v1",
            ["post-status-cpu9-present", "clock-changed"],
        ))

    def test_unknown_readback_bitmap_bit_refused(self) -> None:
        value = DECODER.READBACK_BITMAP_V1 | 1 << 29
        with self.assertRaisesRegex(DECODER.DecodeError, "no-crc-valid"):
            DECODER.decode(
                payload(wire(1, 12, 3, -5, value)), BEFORE, AFTER)

    def test_file_is_never_modified(self) -> None:
        data = payload(wire(1, 1))
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "record"
            path.write_bytes(data)
            before = path.read_bytes()
            DECODER.decode(path.read_bytes(), BEFORE, AFTER)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
