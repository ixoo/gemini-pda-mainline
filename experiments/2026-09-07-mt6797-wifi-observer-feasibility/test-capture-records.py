#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check capture framing refusal and capacity; no device or persistence test."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('records', Path(__file__).with_name('capture-records.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
CYCLE = bytes(range(16))


class RecordsTests(unittest.TestCase):
    def identity(self):
        return r.encode(r.IDENTITY, 0, CYCLE, 0, bytes(range(80)))

    def test_roundtrip_and_prefix(self):
        start = self.identity()
        self.assertEqual(len(r.decode(start, CYCLE)), 1)
        event = r.encode(3, 1, CYCLE, 7, b'event')
        terminal = r.encode(r.TERMINAL, 2, CYCLE, 0, (2).to_bytes(4, 'little'))
        rows = r.decode(start + event + terminal, CYCLE)
        self.assertEqual(rows[1]['payload'], b'event')
        self.assertEqual(rows[1]['transaction'], 7)

    def test_every_single_bit_corruption(self):
        start = self.identity()
        for bit in range(len(start) * 8):
            broken = bytearray(start)
            broken[bit // 8] ^= 1 << (bit % 8)
            with self.assertRaises(ValueError):
                r.decode(bytes(broken), CYCLE)

    def test_partial_record(self):
        start = self.identity()
        event = r.encode(3, 1, CYCLE, 7, b'event')
        for length in range(1, r.RECORD_BYTES):
            with self.assertRaises(ValueError):
                r.decode(start + event[:length], CYCLE)

    def test_order_and_cycle(self):
        start = self.identity()
        event = r.encode(3, 1, CYCLE, 1, b'')
        terminal = r.encode(r.TERMINAL, 1, CYCLE, 0, (1).to_bytes(4, 'little'))
        for stream, cycle in [(event, CYCLE), (start + start, CYCLE),
                              (start, bytes(reversed(CYCLE))),
                              (start + terminal + r.encode(3, 2, CYCLE, 1, b''), CYCLE)]:
            with self.assertRaises(ValueError):
                r.decode(stream, cycle)

    def test_capacity_reserves_terminal(self):
        self.assertEqual((r.MAX_RECORDS, r.MAX_ORDINARY_RECORDS, r.PAYLOAD_BYTES), (511, 510, 84))
        stream = self.identity() + b''.join(r.encode(3, seq, CYCLE, seq, b'')
                                          for seq in range(1, 510))
        stream += r.encode(r.TERMINAL, 510, CYCLE, 0, (3).to_bytes(4, 'little'))
        self.assertEqual(len(stream), 65408)
        self.assertEqual(len(r.decode(stream, CYCLE)), 511)
        with self.assertRaises(ValueError):
            r.encode(3, 510, CYCLE, 1, b'')
        with self.assertRaises(ValueError):
            r.decode(stream + self.identity(), CYCLE)

    def test_invalid_fields(self):
        for kind, seq, cycle, transaction, payload in [
                (99, 1, CYCLE, 0, b''), (3, 1, bytes(16), 0, b''),
                (3, 1, CYCLE, 0, bytes(85)), (1, 0, CYCLE, 0, bytes(79)),
                (255, 1, CYCLE, 0, bytes(4)), (3, 1, CYCLE, -1, b'')]:
            with self.assertRaises(ValueError):
                r.encode(kind, seq, cycle, transaction, payload)


if __name__ == '__main__':
    unittest.main()
