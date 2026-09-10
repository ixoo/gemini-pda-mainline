#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check fixed-slot native pmsg extraction without accepting suffixes or hardware success."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('records', Path(__file__).with_name('capture-records.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
CYCLE = bytes(range(16))
IDENTITY = bytes(range(80))


def record(kind, sequence, payload):
    return r.encode(kind, sequence, CYCLE, 0, payload)


def zone(stream):
    return stream + bytes(r.ZONE_PAYLOAD_BYTES - len(stream))


class PmsgTests(unittest.TestCase):
    def setUp(self):
        self.identity = record(r.IDENTITY, 0, IDENTITY)
        self.event = record(10, 1, b'event')

    def decode(self, payload):
        return r.decode_pmsg(payload, CYCLE, IDENTITY)

    def test_terminals_are_only_producer_reports(self):
        for status in (1, 2, 3):
            result = self.decode(zone(self.identity + record(r.TERMINAL, 1, status.to_bytes(4, 'little'))))
            self.assertEqual(result['framing'], 'terminal-recorded')
            self.assertEqual(result['producer_status'], status)
            self.assertIsNone(result['interrupted_slot'])

    def test_every_interrupted_event_prefix(self):
        # Byte-copy interruption anywhere before all 128 bytes are committed.
        for count in range(1, 128):
            with self.subTest(count=count):
                result = self.decode(zone(self.identity + self.event[:count]))
                self.assertEqual(result['framing'], 'incomplete')
                self.assertEqual(result['interrupted_slot'], 1)
                self.assertEqual(len(result['records']), 1)
                self.assertIsNone(result['producer_status'])

    def test_empty_next_slot_is_incomplete(self):
        result = self.decode(zone(self.identity))
        self.assertEqual(result['framing'], 'incomplete')
        self.assertIsNone(result['interrupted_slot'])

    def test_identity_is_independent_and_required(self):
        for payload in (bytes(r.ZONE_PAYLOAD_BYTES), zone(self.identity[:127])):
            with self.assertRaises(ValueError):
                self.decode(payload)
        for expected_cycle, identity in ((bytes(reversed(CYCLE)), IDENTITY),
                                          (CYCLE, bytes(reversed(IDENTITY))), (CYCLE, b'')):
            with self.assertRaises(ValueError):
                r.decode_pmsg(zone(self.identity), expected_cycle, identity)

    def test_no_resynchronization_or_suffix(self):
        for stream in (bytes(128) + self.identity,
                       self.identity + bytes(128) + record(10, 2, b'later'),
                       self.identity + self.event[:120] + bytes(8) + record(10, 2, b'later')):
            with self.assertRaises(ValueError):
                self.decode(zone(stream))

    def test_committed_corruption_is_rejected(self):
        for offset in range(124):
            broken = bytearray(self.event)
            broken[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.decode(zone(self.identity + broken))

    def test_no_data_after_terminal(self):
        terminal = record(r.TERMINAL, 1, (1).to_bytes(4, 'little'))
        for tail in (record(10, 2, b'later'), b'partial'):
            with self.assertRaises(ValueError):
                self.decode(zone(self.identity + terminal + tail))

    def test_exact_payload_and_tail(self):
        payload = zone(self.identity)
        for broken in (payload[:-1], payload + b'\0', payload[:-1] + b'x'):
            with self.assertRaises(ValueError):
                self.decode(broken)

    def test_full_capacity_keeps_terminal_slot(self):
        stream = self.identity + b''.join(record(10, i, b'event') for i in range(1, 510))
        result = self.decode(zone(stream + record(r.TERMINAL, 510, (3).to_bytes(4, 'little'))))
        self.assertEqual(len(result['records']), 511)
        self.assertEqual(result['producer_status'], 3)

    def test_raw_zone_requires_exact_header_and_size(self):
        header = bytes.fromhex('4442474300000000f4ff0000')
        raw = header + zone(self.identity)
        self.assertEqual(r.decode_pmsg_zone(raw, CYCLE, IDENTITY), self.decode(raw[12:]))
        for bit in range(96):
            damaged = bytearray(raw)
            damaged[bit // 8] ^= 1 << (bit % 8)
            with self.subTest(bit=bit), self.assertRaises(ValueError):
                r.decode_pmsg_zone(damaged, CYCLE, IDENTITY)
        for damaged in (raw[:-1], raw + b'\0', raw[12:], bytes(65536)):
            with self.assertRaises(ValueError):
                r.decode_pmsg_zone(damaged, CYCLE, IDENTITY)


if __name__ == '__main__':
    unittest.main()
