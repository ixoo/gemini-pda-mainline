#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic complete-cycle records test cross-family joins, not native execution."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('controller_records', Path(__file__).with_name('test-capture-records.py'))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
r = fixture.r
CYCLE, IDENTITY = fixture.CYCLE, bytes(range(80))
IMAGE_BYTES, IMAGE_HASH = 411632, bytes([71]) * 32
SECTIONS = [(88, 5840, 0x80101000, 1, 0), (5928, 8992, 0x80111000, 1, 0),
            (14920, 331296, 0x80101000, 0, 0), (346216, 65392, 0x80162000, 0, 0)]
HASHES = [bytes([n]) * 32 for n in range(1, 9)]


def cycle_rows():
    f = fixture.RecordsTests()
    rows = [(1, 0, IDENTITY), (11, 0, r.RECOVERY.pack(1, 12, 0, 0, 0, 0, 0)),
            (11, 0, r.RECOVERY.pack(2, 12, 1, 0x48, 5, 24576, 0))]
    rows += [(12, 0, r.INITIALIZER.pack(site, stage, 0)) for site, stage in r.INITIALIZER_ORDER]
    rows += [(13, 0, r.TRANSPORT.pack(stage, 0x23, 0)) for stage in (1, 2)]

    def req(subtype, request, *values):
        rows.append((10, request, r.REQUEST_LAYOUTS[subtype].pack(subtype, request, *values)))

    def begin(request):
        req(16, request, 0x80000003 if request == 1 else 3)
        req(17, request, 3 if request == 1 else 4, 3, 4000)
        req(18, request)
        req(19, request, 3 if request == 1 else 4, 3)

    def end(request):
        req(20, request, 0);req(21, request, 10, 1, 0, 1);req(24, request, 0)

    begin(1)
    rows.append((2, 1, r.HIF_BIND.pack(1, 1, 1, 1)))
    req(25, 1, 1, 1)
    rows += [(7, 1, layout.pack(*values)) for layout, values in (
        (r.FW_READ_ENTRY, (8, 1)), (r.FW_READ_ALLOCATION, (9, 1, IMAGE_BYTES, IMAGE_BYTES, 1)),
        (r.FW_READ_RESULT, (10, 1, IMAGE_BYTES, 1, IMAGE_BYTES)),
        (r.FW_READ_RETURN, (11, 1, 1, IMAGE_BYTES, 1)))]
    req(26, 1, 1, 1)
    rows.append((7, 1, r.FW_IMAGE.pack(5, 1, 1, IMAGE_BYTES, 4, IMAGE_HASH)))
    chunk = 0
    for section, (offset, length, destination, enc, key) in enumerate(SECTIONS):
        rows.append((7, 1, r.FW_SECTION.pack(6, 1, 1, section, offset, length, destination, enc, key)))
        if section < 2:
            for relative in range(0, length, 2048):
                chunk += 1
                size = min(2048, length - relative)
                logical, rounded = size + 8, ((size + 8 + 511) // 512) * 512
                rows.append((7, chunk, r.FW_TX_PAYLOAD.pack(12, 1, 1, chunk, section,
                                                         offset + relative, size, logical, HASHES[chunk - 1])))
                transfer = f.dma_trace()
                values = list(r.DMA_MAP.unpack(transfer[0][1]));values[2:4] = [logical, rounded]
                transfer[0] = (3, r.DMA_MAP.pack(*values))
                values = list(r.DMA_PROGRAM.unpack(transfer[1][1]));values[8] = rounded
                transfer[1] = (4, r.DMA_PROGRAM.pack(*values))
                for i in (7, 8):
                    values = list(r.DMA_UNMAP.unpack(transfer[i][1]));values[3] = rounded
                    transfer[i] = (6, r.DMA_UNMAP.pack(*values))
                rows.append((3, chunk, transfer[0][1]))
                rows.append((7, chunk, r.FW_TX_DMA.pack(13, 1, 1, chunk, chunk)))
                rows += [(kind, chunk, payload) for kind, payload in transfer[1:]]
                rows.append((7, chunk, r.FW_TX_RETURN.pack(14, 1, 1, chunk, chunk, 1)))
        else:
            emi = f.emi_payloads()
            emi[0][1][1:3] = [1, 1]
            emi[0][1][4:] = [section, offset, length, destination, IMAGE_BYTES]
            for i in (4, 5): emi[i][1][3:] = [destination & 0xfffff, offset, length]
            rows += [(8, section, layout.pack(*values)) for layout, values in emi]
    rows.append((7, 1, r.FW_IMAGE_RETURN.pack(7, 1, 1, 0)))
    req(27, 1, 1, 1, 0)
    end(1);begin(2)
    rows.append((7, 1, r.FW_STOP_WORKERS.pack(15, 1, 1, 0, 1, 1, 1)))
    _, _, stop, unbind = f.shutdown_parts()
    rows += stop + unbind
    req(22, 2, 1)
    common = {1: (1, 1, 3, 0), 2: (2, 1, 1), 3: (3, 1, 1, 1),
              4: (4, 1), 5: (5, 1), 6: (6, 1, 0, 0)}
    for subtype in (1, 2, 3): rows.append((10, 1, r.COMMON_OFF_LAYOUTS[subtype].pack(*common[subtype])))
    for layout, values in f.provider_payloads():
        values[1] = 1;rows.append((9, 1, layout.pack(*values)))
    for subtype in (4, 5, 6): rows.append((10, 1, r.COMMON_OFF_LAYOUTS[subtype].pack(*common[subtype])))
    req(23, 2, 1);end(2)
    rows.append((255, 0, (1).to_bytes(4, 'little')))
    return rows


def zone(rows):
    data = b''.join(r.encode(kind, seq, CYCLE, tx, payload) for seq, (kind, tx, payload) in enumerate(rows))
    return struct.pack('<III', 0x43474244, 0, r.ZONE_PAYLOAD_BYTES) + data.ljust(r.ZONE_PAYLOAD_BYTES, b'\0')


def check(rows):
    return r.check_controller_cycle(zone(rows), CYCLE, IDENTITY, IMAGE_HASH, IMAGE_BYTES, SECTIONS, HASHES)


class ControllerClassifierTests(unittest.TestCase):
    def test_complete_sequence(self):
        result = check(cycle_rows())
        self.assertEqual(result['checked_requests'], [1, 2])
        self.assertEqual(result['checked_payload_chunks'], list(range(1, 9)))
        self.assertEqual(result['checked_transport'], 0x23)

    def test_every_missing_or_repeated_record_is_refused(self):
        rows = cycle_rows()
        for index in range(len(rows)):
            with self.subTest(index=index):
                with self.assertRaises(ValueError): check(rows[:index] + rows[index + 1:])
                with self.assertRaises(ValueError): check(rows[:index] + [rows[index]] + rows[index:])

    def test_transport_failure_and_wrong_order(self):
        rows = cycle_rows();start = 3 + len(r.INITIALIZER_ORDER)
        for replacement in ((13, 0, r.TRANSPORT.pack(2, 0x23, -5)),
                            (13, 1, r.TRANSPORT.pack(2, 0x23, 0)),
                            (13, 0, r.TRANSPORT.pack(2, 0x24, 0))):
            with self.assertRaises(ValueError): check(rows[:start + 1] + [replacement] + rows[start + 2:])
        moved = rows.copy();entry = moved.pop(start + 1);moved.insert(start + 2, entry)
        with self.assertRaises(ValueError): check(moved)

    def test_waits_must_be_inside_off(self):
        rows = cycle_rows()
        index = next(i for i, (kind, _, payload) in enumerate(rows) if kind == 7 and int.from_bytes(payload[:4], 'little') == 15)
        wait = rows.pop(index)
        rows.insert(40, wait)  # Inside ON, still before the ordinary stop.
        with self.assertRaises(ValueError): check(rows)

    def test_terminal_and_rejected_access_tail(self):
        rows = cycle_rows()
        for status in (2, 3):
            with self.assertRaises(ValueError): check(rows[:-1] + [(255, 0, status.to_bytes(4, 'little'))])
        raw = bytearray(zone(rows));raw[-1] = 1
        with self.assertRaises(ValueError):
            r.check_controller_cycle(raw, CYCLE, IDENTITY, IMAGE_HASH, IMAGE_BYTES, SECTIONS, HASHES)


if __name__ == '__main__':
    unittest.main()
