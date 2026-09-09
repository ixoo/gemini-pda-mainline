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
        event = r.encode(2, 1, CYCLE, 7, b'event')
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
        event = r.encode(2, 1, CYCLE, 7, b'event')
        for length in range(1, r.RECORD_BYTES):
            with self.assertRaises(ValueError):
                r.decode(start + event[:length], CYCLE)

    def test_order_and_cycle(self):
        start = self.identity()
        event = r.encode(2, 1, CYCLE, 1, b'')
        terminal = r.encode(r.TERMINAL, 1, CYCLE, 0, (1).to_bytes(4, 'little'))
        for stream, cycle in [(event, CYCLE), (start + start, CYCLE),
                              (start, bytes(reversed(CYCLE))),
                              (start + terminal + r.encode(2, 2, CYCLE, 1, b''), CYCLE)]:
            with self.assertRaises(ValueError):
                r.decode(stream, cycle)

    def test_capacity_reserves_terminal(self):
        self.assertEqual((r.MAX_RECORDS, r.MAX_ORDINARY_RECORDS, r.PAYLOAD_BYTES), (511, 510, 84))
        stream = self.identity() + b''.join(r.encode(2, seq, CYCLE, seq, b'')
                                          for seq in range(1, 510))
        stream += r.encode(r.TERMINAL, 510, CYCLE, 0, (3).to_bytes(4, 'little'))
        self.assertEqual(len(stream), 65408)
        self.assertEqual(len(r.decode(stream, CYCLE)), 511)
        with self.assertRaises(ValueError):
            r.encode(2, 510, CYCLE, 1, b'')
        with self.assertRaises(ValueError):
            r.decode(stream + self.identity(), CYCLE)

    def test_dma_raw_values_roundtrip(self):
        address = 0x123456789abcdef0
        payloads = [(3, r.DMA_MAP.pack(1, 1, 2000, 2048, address, 0x34, 1)),
                    (4, r.DMA_PROGRAM.pack(1, 1, address, 0x12340000, *range(13))),
                    (5, r.DMA_POLL.pack(2, 2, 3, 0, 100001, 1, 1)),
                    (6, r.DMA_UNMAP.pack(1, 1, address, 2048, 1))]
        for kind, payload in payloads:
            stream = self.identity() + r.encode(kind, 1, CYCLE, 7, payload)
            self.assertEqual(r.decode(stream, CYCLE)[1]['payload'], payload)
        self.assertEqual(r.DMA_MAP.unpack(payloads[0][1])[4], address)
        # Raw observations remain intact even when lengths/addresses would fail a later lifecycle check.
        r.encode(3, 1, CYCLE, 1, r.DMA_MAP.pack(1, 0, 2048, 0, 0, 0, 2))

    def test_dma_phase_boundaries(self):
        r.encode(4, 1, CYCLE, 1, r.DMA_PROGRAM.pack(1, 2, 0, 0, 1, 2, 3, 4, *([0] * 9)))
        for phase in (1, 2):
            r.encode(5, 1, CYCLE, 1, r.DMA_POLL.pack(phase, 1, 0, 0, 0, 0, 0))
            r.encode(5, 1, CYCLE, 1, r.DMA_POLL.pack(phase, 2, 2, 0, 0, 0, 0))
        for payload in [r.DMA_POLL.pack(1, 1, 1, 0, 1, 1, 1),
                        r.DMA_POLL.pack(1, 2, 0, 0, 1, 1, 1),
                        r.DMA_POLL.pack(2, 2, 1, 0, 0, 1, 0),
                        r.DMA_POLL.pack(2, 2, 1, 0, 1, 0, 0)]:
            with self.assertRaises(ValueError):
                r.encode(5, 1, CYCLE, 1, payload)
        for kind, layout in [(3, r.DMA_MAP), (4, r.DMA_PROGRAM), (5, r.DMA_POLL), (6, r.DMA_UNMAP)]:
            with self.assertRaises(ValueError):
                r.encode(kind, 1, CYCLE, 1, bytes(layout.size - 1))
            with self.assertRaises(ValueError):
                r.encode(kind, 1, CYCLE, 0, bytes(layout.size))

    def dma_trace(self, direction=1):
        address, endpoint = 0x100004000, 0x18000000
        source, destination = (address, endpoint) if direction else (endpoint, address)
        return [(3, r.DMA_MAP.pack(1, direction, 2000, 2048, address, 0x34, 1)),
                (4, r.DMA_PROGRAM.pack(1, 1, source, destination,
                                      0, 0x80030000 | (1 - direction), source & 0xffffffff,
                                      destination & 0xffffffff, 2048, 0, 1, 0, 1, 0, 1, 0, 1)),
                (5, r.DMA_POLL.pack(1, 1, 0, 0, 0, 0, 0)),
                (5, r.DMA_POLL.pack(1, 2, 1, 0, 2, 1, 1)),
                (4, r.DMA_PROGRAM.pack(1, 2, 0, 0, 1, 0, 1, 0, *([0] * 9))),
                (5, r.DMA_POLL.pack(2, 1, 0, 0, 0, 0, 0)),
                (5, r.DMA_POLL.pack(2, 2, 1, 0, 2, 0, 1)),
                (6, r.DMA_UNMAP.pack(1, 1, address, 2048, direction)),
                (6, r.DMA_UNMAP.pack(2, 1, address, 2048, direction))]

    def stream(self, events):
        return self.identity() + b''.join(r.encode(kind, seq, CYCLE, 7, payload)
                                          for seq, (kind, payload) in enumerate(events, 1))

    def test_dma_lifetime_rx_tx(self):
        for direction in (0, 1):
            result = r.check_dma(self.stream(self.dma_trace(direction)), CYCLE)
            self.assertEqual(result['checked_transactions'], [7])
        with self.assertRaises(ValueError):
            r.check_dma(self.identity(), CYCLE)

    def test_dma_semantic_mutations_with_valid_crc(self):
        layouts = {3: r.DMA_MAP, 4: r.DMA_PROGRAM, 5: r.DMA_POLL, 6: r.DMA_UNMAP}
        # Event index, field index, changed value: frames are re-encoded with valid CRCs.
        mutations = [(0, 6, 2), (0, 3, 1000), (1, 2, 0x100008000),
                     (1, 5, 0), (1, 6, 0), (1, 8, 4096), (1, 10, 0),
                     (1, 12, 0), (1, 14, 0), (1, 16, 0),
                     (3, 5, 0), (4, 5, 1), (4, 7, 1),
                     (6, 2, 3), (6, 5, 1), (7, 2, 0x100008000), (8, 3, 4096)]
        for event_index, field_index, value in mutations:
            events = self.dma_trace()
            kind, payload = events[event_index]
            fields = list(layouts[kind].unpack(payload))
            fields[field_index] = value
            events[event_index] = (kind, layouts[kind].pack(*fields))
            with self.assertRaises(ValueError):
                r.check_dma(self.stream(events), CYCLE)
        events = self.dma_trace()
        for changed in (events[:-1], events + events, events[:5] + events[7:9] + events[5:7]):
            with self.assertRaises(ValueError):
                r.check_dma(self.stream(changed), CYCLE)

    def test_invalid_fields(self):
        for kind, seq, cycle, transaction, payload in [
                (99, 1, CYCLE, 0, b''), (3, 1, bytes(16), 0, b''),
                (3, 1, CYCLE, 0, bytes(85)), (1, 0, CYCLE, 0, bytes(79)),
                (255, 1, CYCLE, 0, bytes(4)), (3, 1, CYCLE, -1, b'')]:
            with self.assertRaises(ValueError):
                r.encode(kind, seq, cycle, transaction, payload)


if __name__ == '__main__':
    unittest.main()
