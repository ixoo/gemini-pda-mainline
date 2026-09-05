#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Independent synthetic WIFI_START records; no retained or runtime input."""

import struct
import unittest

import wifi_init_protocol as protocol


def packet(sequence=19, override=0, address=0):
    return struct.pack("<HHBBBBII", 16, 0x8000, 2, 0xA0, 0, sequence, override, address)


class StartTests(unittest.TestCase):
    def decode(self, data, sequence=19):
        return protocol.decode_wifi_start(data, expected_sequence=sequence)

    def refuse(self, data, code, sequence=19):
        with self.assertRaisesRegex(protocol.Refusal, "^" + code + "$"):
            self.decode(data, sequence)

    def test_both_constructor_branches_and_address_non_disclosure(self):
        for override in (0, 1):
            baseline = self.decode(packet(override=override))
            self.assertEqual(baseline["start_address_override"], bool(override))
            for address in (1, 0x10203040, 0xFFFFFFFF):
                self.assertEqual(self.decode(packet(override=override, address=address)), baseline)
            for field in ("start_address_validated", "firmware_ready_proven", "hardware_access", "load_authorized"):
                self.assertIs(baseline[field], False)
            self.assertEqual(baseline["runtime_protocol_match"], "unproven")

    def test_every_truncation_and_transport_tail(self):
        for length in range(16):
            self.refuse(packet()[:length], "logical_record_length_policy")
        for tail in (b"\0", b"\0" * 16, packet()):
            self.refuse(packet() + tail, "logical_record_length_policy")

    def test_declared_lengths_and_endian_confusion(self):
        for count in (0, 8, 15, 17, 20, 28, 4096, 65535):
            self.refuse(struct.pack("<H", count) + packet()[2:], "declared_byte_count_policy")

    def test_queue_id_type_and_reserved(self):
        for offset, value, reason in ((3, 0xC0, "command_queue_mismatch"),
                                      (2, 1, "command_queue_mismatch"),
                                      (4, 1, "not_wifi_start"),
                                      (4, 4, "not_wifi_start"),
                                      (5, 0x20, "command_packet_type_mismatch"),
                                      (5, 0, "command_packet_type_mismatch"),
                                      (6, 1, "command_reserved_not_source_constructor")):
            data = packet()
            self.refuse(data[:offset] + bytes([value]) + data[offset + 1:], reason)

    def test_all_sequences_and_mismatched_expectation(self):
        for sequence in range(256):
            self.assertTrue(self.decode(packet(sequence=sequence), sequence)["sequence_matches"])
            self.refuse(packet(sequence=sequence), "command_sequence_mismatch", (sequence + 1) % 256)

    def test_invalid_caller_sequence(self):
        for sequence in (-1, 256, True, False, 19.0, "19", None):
            self.refuse(packet(), "invalid_expected_sequence", sequence)

    def test_every_non_constructor_flag(self):
        # Includes the named delay-calibration bit: the audited constructor
        # does not emit it. Rejecting it is a scope gate, not an ABI claim.
        for bit in range(1, 32):
            for override in (1 << bit, (1 << bit) | 1):
                self.refuse(packet(override=override), "start_override_not_source_constructor")
        self.refuse(packet(override=0xFFFFFFFF), "start_override_not_source_constructor")

    def test_mutable_and_non_byte_records(self):
        for data in (bytearray(packet()), memoryview(packet()), None, "secret", 16):
            self.refuse(data, "immutable_bytes_required")

    def test_existing_config_decoder_does_not_accept_start(self):
        with self.assertRaises(protocol.Refusal):
            protocol.decode_download_config(packet(), expected_sequence=19)
        with self.assertRaises(protocol.Refusal):
            protocol.decode_command_result(packet(), expected_sequence=19)


if __name__ == "__main__":
    unittest.main()
