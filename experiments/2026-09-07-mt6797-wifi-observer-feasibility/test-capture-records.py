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

    def stop_payloads(self):
        return [(r.FW_STOP_ENTRY, [1, 17, 1, 0, 1, 0, 0]),
                (r.FW_STOP_COMMAND, [2, 0, 1, 0]),
                (r.FW_STOP_POLL, [3, 1, 1, 5, 5, 5, 0, 0, 0x1234, 0x1234]),
                (r.FW_STOP_RETURN, [4, 0])]

    def stop_stream(self, payloads):
        return self.identity() + b''.join(
            r.encode(7, i, CYCLE, 23, layout.pack(*values))
            for i, (layout, values) in enumerate(payloads, 1))

    def test_stop_ordinary_and_faults(self):
        stream = self.stop_stream(self.stop_payloads())
        self.assertEqual(r.check_stop(stream, CYCLE)['checked_stops'], [23])
        # All faults retain valid framing/CRC and remain available to decode.
        faults = [(0, 2, 2), (0, 3, 1), (0, 4, 0), (0, 5, 1), (0, 6, 1),
                  (1, 1, 1), (1, 2, 0), (1, 3, 1), (2, 1, 2), (2, 1, 3),
                  (2, 2, 2), (2, 2, 3), (2, 2, 4), (2, 4, 4), (2, 5, 4),
                  (2, 6, 1), (2, 7, 4), (2, 8, 0), (2, 9, 0), (3, 1, 1)]
        for row, field, value in faults:
            with self.subTest(row=row, field=field):
                payloads = self.stop_payloads()
                payloads[row][1][field] = value
                stream = self.stop_stream(payloads)
                self.assertEqual(len(r.decode(stream, CYCLE)), 5)
                with self.assertRaises(ValueError):
                    r.check_stop(stream, CYCLE)
        for actual, consumed in [(1 << 21, 1 << 21), (0, 0)]:
            payloads = self.stop_payloads()
            payloads[2][1][8:] = [actual, consumed]
            if actual == 0:
                payloads[2][1][3:6] = [0, 0, 0]
            with self.assertRaises(ValueError):
                r.check_stop(self.stop_stream(payloads), CYCLE)

    def test_stop_structure_and_order(self):
        payloads = self.stop_payloads()
        for bad in [payloads[:-1], payloads + payloads, list(reversed(payloads))]:
            with self.assertRaises(ValueError):
                r.check_stop(self.stop_stream(bad), CYCLE)
        for payload in [b'', bytes(4), r.FW_STOP_ENTRY.pack(1, 0, 1, 0, 1, 0, 0),
                        r.FW_STOP_POLL.pack(3, 1, 1, 1, 2, 1, 0, 0, 0, 0)]:
            with self.assertRaises(ValueError):
                r.encode(7, 1, CYCLE, 23, payload)
        with self.assertRaises(ValueError):
            r.encode(7, 1, CYCLE, 0, r.FW_STOP_RETURN.pack(4, 0))
        with self.assertRaises(ValueError):
            r.check_stop(self.identity(), CYCLE)

    def emi_payloads(self):
        base = 0x100000000  # Synthetic full-width address, not a device reservation.
        return [(r.EMI_SECTION, [1, 17, 31, base, 2, 0x100, 0x200, 0x80101000, 0x1000]),
                (r.EMI_PROTECTION, [2, 1, 1, 1, base, base + 0x7ffff, r.EMI_OPEN, 0]),
                (r.EMI_PROTECTION, [2, 1, 2, 1, base, base + 0x7ffff, r.EMI_OPEN, 0]),
                (r.EMI_MAPPING, [3, 47, base, 0x80000]),
                (r.EMI_COPY, [4, 1, 47, 0x1000, 0x100, 0x200]),
                (r.EMI_COPY, [4, 2, 47, 0x1000, 0x100, 0x200]),
                (r.EMI_PROTECTION, [2, 2, 1, 1, base, base + 0x7ffff, r.EMI_RESTRICT, 0]),
                (r.EMI_PROTECTION, [2, 2, 2, 1, base, base + 0x7ffff, r.EMI_RESTRICT, 0])]

    def emi_stream(self, payloads):
        return self.identity() + b''.join(
            r.encode(8, i, CYCLE, 53, layout.pack(*values))
            for i, (layout, values) in enumerate(payloads, 1))

    def test_emi_operations_and_faults(self):
        self.assertEqual(r.check_emi(self.emi_stream(self.emi_payloads()), CYCLE)['checked_sections'], [53])
        faults = [(0, 3, 0), (0, 3, 0xffffffffffffffff), (0, 4, 1), (0, 5, 0x1001),
                  (0, 6, 0), (0, 6, 0xffffffff), (0, 7, 0x80180000), (0, 8, 0x200),
                  (1, 4, 0), (2, 3, 2), (2, 7, -1), (2, 7, -4), (2, 7, 1),
                  (3, 1, 0), (3, 2, 0), (3, 3, 0x100000), (4, 2, 48), (4, 3, 0),
                  (5, 4, 0), (5, 5, 0x100), (6, 5, 0x10007fffe),
                  (7, 1, 1), (7, 6, r.EMI_OPEN), (7, 7, -2)]
        for row, field, value in faults:
            with self.subTest(row=row, field=field):
                payloads = self.emi_payloads()
                payloads[row][1][field] = value
                stream = self.emi_stream(payloads)
                self.assertEqual(len(r.decode(stream, CYCLE)), 9)
                with self.assertRaises(ValueError):
                    r.check_emi(stream, CYCLE)
        # Source's 32-bit sum could wrap; the checker must not accept that span.
        payloads = self.emi_payloads()
        payloads[0][1][5:9] = [0, 0xfffff001, 0x80101000, 0xffffffff]
        with self.assertRaises(ValueError):
            r.check_emi(self.emi_stream(payloads), CYCLE)

    def test_emi_structure_and_order(self):
        payloads = self.emi_payloads()
        for bad in [payloads[:-1], payloads + payloads, payloads[:3] + payloads[4:6] + payloads[3:4] + payloads[6:]]:
            with self.assertRaises(ValueError):
                r.check_emi(self.emi_stream(bad), CYCLE)
        for payload in [b'', bytes(4), r.EMI_MAPPING.pack(3, 1, 0, 0)[:-1],
                        r.EMI_PROTECTION.pack(2, 1, 1, 1, 0, 0, 0, -1)]:
            with self.assertRaises(ValueError):
                r.encode(8, 1, CYCLE, 53, payload)
        with self.assertRaises(ValueError):
            r.check_emi(self.identity(), CYCLE)

    def off_stream(self, rows):
        return self.identity() + b''.join(r.encode(9, i, CYCLE, 61, r.OFF_POLL.pack(*row))
                                          for i, row in enumerate(rows, 1))

    def test_off_condition_short_circuit(self):
        entry = [1, 73, 0, 0, 0, 0, 0, 0, 0]
        result = [2, 73, 1, 0x100000001, 7, 0x100, 0x200, 1, 1]
        self.assertEqual(r.check_off_poll(self.off_stream([entry, result]), CYCLE)['checked_polls'], [61])
        for field, value in [(1, 74), (2, 2), (2, 3), (6, 2), (8, 0)]:
            bad = result.copy()
            bad[field] = value
            if field == 8:
                bad[6] = 0  # No final secondary value; older reads do not count.
            stream = self.off_stream([entry, bad])
            self.assertEqual(len(r.decode(stream, CYCLE)), 3)
            with self.assertRaises(ValueError):
                r.check_off_poll(stream, CYCLE)
        for bad in [[2, 73, 1, 0, 0, 0, 0, 0, 0],
                    [2, 73, 1, 7, 3, 2, 0, 1, 0]]:
            with self.assertRaises(ValueError):
                r.check_off_poll(self.off_stream([entry, bad]), CYCLE)
        for bad in [[2, 73, 1, 7, 8, 0, 0, 1, 1],
                    [2, 73, 1, 7, 3, 2, 0, 1, 1],
                    [2, 73, 1, 7, 3, 0, 0x200, 1, 0],
                    [2, 73, 1, 0, 0, 0, 0, 1, 1]]:
            with self.assertRaises(ValueError):
                self.off_stream([entry, bad])
        for rows in [[entry], [result, entry], [entry, result, entry, result]]:
            with self.assertRaises(ValueError):
                r.check_off_poll(self.off_stream(rows), CYCLE)
        with self.assertRaises(ValueError):
            r.check_off_poll(self.identity(), CYCLE)

    def provider_payloads(self):
        controls = []
        for index, (mask, set_bit) in enumerate([(2, True), (16, True), (1, False), (4, False), (8, False)]):
            before = 0x100 + index * 31
            controls += [before, before | mask if set_bit else before & ~mask]
        return [(r.OFF_ENTRY, [3, 73, 1, 1, 0]),
                (r.OFF_STATE, [4, 73, 0x102, 0x202, 1, 1]),
                (r.OFF_DISPATCH, [5, 73, 0, 0x0b160001]),
                (r.OFF_PROTECT_ENTRY, [6, 73, 0x60000, 1]),
                (r.OFF_PROTECT_RESULT, [7, 73, 0x100, 0x60100, 0x60200, 1, 3, 0x60400, 1, 1, 0]),
                (r.OFF_CONTROL, [8, 73] + controls),
                (r.OFF_POLL, [1, 73, 0, 0, 0, 0, 0, 0, 0]),
                (r.OFF_POLL, [2, 73, 1, 5, 3, 0x100, 0x200, 1, 1]),
                (r.OFF_RETURN, [9, 73, 0, 0])]

    def provider_stream(self, payloads):
        return self.identity() + b''.join(r.encode(9, i, CYCLE, 61, layout.pack(*values))
                                          for i, (layout, values) in enumerate(payloads, 1))

    def test_provider_off_operations(self):
        stream = self.provider_stream(self.provider_payloads())
        self.assertEqual(r.check_provider_off(stream, CYCLE)['checked_provider_operations'], [61])
        self.assertEqual(r.check_off_poll(stream, CYCLE)['checked_polls'], [61])
        faults = [(0, 2, 0), (0, 3, 2), (0, 3, 3), (1, 2, 0x100), (1, 3, 0x200),
                  (1, 4, 0), (1, 5, 2), (2, 1, 74), (2, 2, 1), (2, 3, 1),
                  (3, 2, 0x20000), (3, 3, 0), (4, 3, 0x100), (4, 4, 0x40200),
                  (4, 5, 2), (4, 7, 0x20400), (4, 9, 0), (4, 10, -1),
                  (8, 2, -1), (8, 3, -1)]
        faults += [(5, index, 0) for index in (3, 5, 7, 9, 11)]
        for row, field, value in faults:
            with self.subTest(row=row, field=field):
                payloads = self.provider_payloads()
                payloads[row][1][field] = value
                stream = self.provider_stream(payloads)
                self.assertEqual(len(r.decode(stream, CYCLE)), 10)
                with self.assertRaises(ValueError):
                    r.check_provider_off(stream, CYCLE)
        payloads = self.provider_payloads()
        for bad in [payloads[:-1], payloads + payloads, payloads[6:8],
                    payloads[:3] + payloads[5:6] + payloads[3:5] + payloads[6:]]:
            with self.assertRaises(ValueError):
                r.check_provider_off(self.provider_stream(bad), CYCLE)

    def image_records(self):
        sections = [(0x40, 0x20, 0x1000, 0, 0), (0x80, 0x20, 0x2000, 1, 2),
                    (0x100, 0x200, 0x80101000, 0, 0), (0x400, 0x100, 0x80102000, 0, 0)]
        rows = [(7, 79, r.FW_IMAGE, [5, 17, 31, 0x1000, 4, bytes(range(32))])]
        for index, fields in enumerate(sections):
            rows.append((7, 79, r.FW_SECTION, [6, 17, 31, index, *fields]))
            if index >= 2:
                payloads = self.emi_payloads()
                source, length, destination = fields[:3]
                payloads[0][1][4:9] = [index, source, length, destination, 0x1000]
                for i in (4, 5):
                    payloads[i][1][3:6] = [destination & 0xfffff, source, length]
                rows.extend((8, 53 + index, layout, values) for layout, values in payloads)
        rows.append((7, 79, r.FW_IMAGE_RETURN, [7, 17, 31, 0]))
        return rows, sections

    def image_stream(self, rows):
        return self.identity() + b''.join(r.encode(kind, seq, CYCLE, transaction, layout.pack(*values))
                                          for seq, (kind, transaction, layout, values) in enumerate(rows, 1))

    def test_image_metadata_and_emi_coverage(self):
        rows, sections = self.image_records()
        def check(rows, digest=bytes(range(32)), size=0x1000, metadata=sections):
            return r.check_image_sections(self.image_stream(rows), CYCLE, digest, size, metadata)
        self.assertEqual(check(rows)['checked_emi_indices'], [2, 3])
        for kwargs in [{'digest': bytes(reversed(range(32)))}, {'size': 0x1001}, {'metadata': sections[:-1]}]:
            with self.assertRaises(ValueError):
                check(rows, **kwargs)
        for row, field, value in [(1, 3, 1), (2, 7, 0), (3, 4, 0x200), (4, 2, 32),
                                  (4, 4, 3), (4, 8, 0x1001), (21, 3, 1)]:
            bad, _ = self.image_records()
            bad[row][3][field] = value
            with self.assertRaises(ValueError):
                check(bad)
        for bad in [rows[:4] + rows[12:], rows[:-1], rows + rows,
                    rows[:4] + rows[12:13] + rows[4:12] + rows[13:]]:
            with self.assertRaises(ValueError):
                check(bad)
        # Another complete, internally consistent copy cannot replace index 3.
        bad, _ = self.image_records()
        bad[13:21] = [(kind, 99, layout, values) for kind, _, layout, values in bad[4:12]]
        with self.assertRaises(ValueError):
            check(bad)

    def test_roundtrip_and_prefix(self):
        start = self.identity()
        self.assertEqual(len(r.decode(start, CYCLE)), 1)
        event = r.encode(10, 1, CYCLE, 7, b'event')
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
        event = r.encode(10, 1, CYCLE, 7, b'event')
        for length in range(1, r.RECORD_BYTES):
            with self.assertRaises(ValueError):
                r.decode(start + event[:length], CYCLE)

    def test_order_and_cycle(self):
        start = self.identity()
        event = r.encode(10, 1, CYCLE, 1, b'')
        terminal = r.encode(r.TERMINAL, 1, CYCLE, 0, (1).to_bytes(4, 'little'))
        for stream, cycle in [(event, CYCLE), (start + start, CYCLE),
                              (start, bytes(reversed(CYCLE))),
                              (start + terminal + r.encode(10, 2, CYCLE, 1, b''), CYCLE)]:
            with self.assertRaises(ValueError):
                r.decode(stream, cycle)

    def test_capacity_reserves_terminal(self):
        self.assertEqual((r.MAX_RECORDS, r.MAX_ORDINARY_RECORDS, r.PAYLOAD_BYTES), (511, 510, 84))
        stream = self.identity() + b''.join(r.encode(10, seq, CYCLE, seq, b'')
                                          for seq in range(1, 510))
        stream += r.encode(r.TERMINAL, 510, CYCLE, 0, (3).to_bytes(4, 'little'))
        self.assertEqual(len(stream), 65408)
        self.assertEqual(len(r.decode(stream, CYCLE)), 511)
        with self.assertRaises(ValueError):
            r.encode(10, 510, CYCLE, 1, b'')
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

    def shutdown_parts(self):
        bind = [(2, 1, r.HIF_BIND.pack(1, 1, 1, 1))]
        unbind = [(2, 1, r.HIF_UNBIND.pack(2, 1, 0))]
        dma = [(kind, 7, payload) for kind, payload in self.dma_trace()]
        payloads = self.stop_payloads()
        payloads[0][1][1] = 1
        stop = [(7, 7, layout.pack(*values)) for layout, values in payloads]
        return bind, dma, stop, unbind

    def shutdown_stream(self, events):
        return self.identity() + b''.join(
            r.encode(kind, seq, CYCLE, transaction, payload)
            for seq, (kind, transaction, payload) in enumerate(events, 1))

    def test_shutdown_binding_join(self):
        bind, dma, stop, unbind = self.shutdown_parts()
        # The stop command can itself use DMA. IDs are scoped by record family.
        for events in (bind + dma + stop + unbind,
                       bind + stop[:1] + dma + stop[1:] + unbind):
            result = r.check_shutdown_bindings(self.shutdown_stream(events), CYCLE)
            self.assertEqual(result['checked_device'], 1)
            self.assertEqual(result['checked_stop'], 7)
            self.assertEqual(result['checked_transactions'], [7])

    def test_shutdown_rejects_individually_valid_unjoined_records(self):
        bind, dma, stop, unbind = self.shutdown_parts()
        wrong_adapter = [(7, 7, r.FW_STOP_ENTRY.pack(1, 2, 1, 0, 1, 0, 0))] + stop[1:]
        second_stop = [(kind, 8, payload) for kind, _, payload in stop]
        faults = {
            'other adapter': bind + dma + wrong_adapter + unbind,
            'before binding': stop + bind + dma + unbind,
            'after release': bind + dma + unbind + stop,
            'entry before binding': stop[:1] + bind + dma + stop[1:] + unbind,
            'return after release': bind + dma + stop[:-1] + unbind + stop[-1:],
            'DMA after stop': bind + stop + dma + unbind,
            'second stop': bind + dma + stop + second_stop + unbind,
        }
        for name, events in faults.items():
            with self.subTest(name=name):
                data = self.shutdown_stream(events)
                r.check_dma_bindings(data, CYCLE)
                r.check_dma(data, CYCLE)
                r.check_stop(data, CYCLE)
                with self.assertRaises(ValueError):
                    r.check_shutdown_bindings(data, CYCLE)

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
