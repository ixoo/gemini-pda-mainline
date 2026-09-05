#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic record fixtures only; no file, firmware or device input."""

import contextlib
import io
import json
import struct
import unittest
from unittest import mock

import wifi_init_protocol as protocol


def command(sequence=19, address=0x10203040, length=5840, mode=0x8000000D):
    # Independent literal fixture for the public little-endian fields.
    return struct.pack("<HHBBBBIII", 20, 0x8000, 1, 0xA0, 0, sequence, address, length, mode)


def result(sequence=19, status=0, reserved=False, diagnostics=b"\0" * 16):
    header_reserved = b"\x55\xaa" if reserved else b"\0\0"
    result_reserved = b"\x01\x02\x03" if reserved else b"\0\0\0"
    return struct.pack("<HHBB", 28, 0xE000, 1, sequence) + header_reserved + bytes([status]) + result_reserved + diagnostics


def replace_byte(packet, offset, value):
    return packet[:offset] + bytes([value]) + packet[offset + 1:]


class CommandTests(unittest.TestCase):
    def decode(self, packet, sequence=19):
        return protocol.decode_download_config(packet, expected_sequence=sequence)

    def refusal(self, packet, reason):
        with self.assertRaisesRegex(protocol.Refusal, "^" + reason + "$"):
            self.decode(packet)

    def test_valid_selected_constructor(self):
        decoded = self.decode(command())
        self.assertEqual(decoded["section_bytes"], 5840)
        self.assertTrue(decoded["encryption_requested"])
        self.assertTrue(decoded["reset_requested"])
        self.assertTrue(decoded["ack_requested"])

    def test_all_short_command_lengths_and_extra_tail(self):
        for length in range(20):
            with self.subTest(length=length):
                self.refusal(command()[:length], "logical_record_length_policy")
        self.refusal(command() + b"tail", "logical_record_length_policy")

    def test_declared_command_size(self):
        for value in (0, 19, 21, 255):
            with self.subTest(value=value):
                self.refusal(replace_byte(command(), 0, value), "declared_byte_count_policy")

    def test_pda_queue_is_not_a_config_command(self):
        self.refusal(replace_byte(command(), 3, 0xC0), "pda_is_not_download_config")

    def test_other_queue(self):
        self.refusal(replace_byte(command(), 3, 0x40), "command_queue_mismatch")

    def test_wrong_command(self):
        for value in (0, 2, 3, 4, 5, 255):
            with self.subTest(value=value):
                self.refusal(replace_byte(command(), 4, value), "not_download_config")

    def test_stale_packet_type_comment_is_not_followed(self):
        self.refusal(replace_byte(command(), 5, 0x20), "command_packet_type_mismatch")

    def test_sequence_is_exact(self):
        self.refusal(command(sequence=20), "command_sequence_mismatch")

    def test_reserved_command_byte_was_explicitly_initialized(self):
        self.refusal(replace_byte(command(), 6, 1), "command_reserved_not_source_constructor")

    def test_zero_length_would_not_have_emitted_a_command(self):
        self.refusal(command(length=0), "zero_length_has_no_source_command")

    def test_destination_overflow_policy(self):
        self.refusal(command(address=0xFFFFFFFF, length=2), "destination_overflow_policy")
        self.assertEqual(self.decode(command(address=0xFFFFFFFF, length=1))["section_bytes"], 1)

    def test_every_unknown_mode_bit(self):
        for bit in range(4, 31):
            with self.subTest(bit=bit):
                self.refusal(command(mode=0x80000000 | (1 << bit)), "mode_not_source_constructor")

    def test_no_ack_command_does_not_admit_a_result_pair(self):
        self.refusal(command(mode=1), "ack_not_requested_by_command")

    def test_key_selector_requires_encryption(self):
        for selector in (2, 4, 6):
            with self.subTest(selector=selector):
                self.refusal(command(mode=0x80000000 | selector), "key_selector_without_encryption")

    def test_plain_config_and_all_encoded_key_selectors(self):
        self.assertFalse(self.decode(command(mode=0x80000000))["encryption_requested"])
        for selector in (0, 2, 4, 6):
            with self.subTest(selector=selector):
                self.assertTrue(self.decode(command(mode=0x80000001 | selector))["encryption_requested"])

    def test_no_address_selector_or_packet_dump_in_output(self):
        decoded = self.decode(command())
        self.assertEqual(set(decoded), {"status", "command", "packet_bytes", "section_bytes", "sequence_matches", "encryption_requested", "reset_requested", "ack_requested"})
        self.assertNotIn(str(0x10203040), json.dumps(decoded))


class ResultTests(unittest.TestCase):
    def decode(self, packet, sequence=19):
        return protocol.decode_command_result(packet, expected_sequence=sequence)

    def refusal(self, packet, reason):
        with self.assertRaisesRegex(protocol.Refusal, "^" + reason + "$"):
            self.decode(packet)

    def test_mt6797_result_has_twenty_byte_body(self):
        self.assertEqual(self.decode(result())["packet_bytes"], 28)

    def test_short_generic_result_and_all_other_short_lengths(self):
        for length in range(28):
            with self.subTest(length=length):
                self.refusal(result()[:length], "logical_record_length_policy")

    def test_extra_four_hif_read_bytes_are_outside_logical_record(self):
        self.refusal(result() + b"more", "logical_record_length_policy")

    def test_declared_result_size(self):
        for value in (0, 12, 27, 29, 255):
            with self.subTest(value=value):
                self.refusal(replace_byte(result(), 0, value), "declared_byte_count_policy")

    def test_packet_type(self):
        self.refusal(replace_byte(result(), 3, 0xA0), "event_packet_type_policy")

    def test_pending_error_is_not_a_config_ack(self):
        self.refusal(replace_byte(result(), 4, 3), "not_command_result")

    def test_sequence_is_exact(self):
        self.refusal(result(sequence=20), "result_sequence_mismatch")

    def test_all_nonzero_statuses_are_firmware_failures(self):
        for status in range(1, 256):
            with self.subTest(status=status):
                decoded = self.decode(result(status=status))
                self.assertEqual(decoded["firmware_status_code"], status)
                self.assertNotEqual(decoded["firmware_status"], "success")

    def test_only_source_defined_status_names(self):
        self.assertEqual([self.decode(result(status=i))["firmware_status"] for i in range(6)], ["success", "invalid_parameters", "crc_error", "decryption_failure", "unknown_command", "other_failure"])

    def test_nonzero_response_reserved_fields_are_not_invented_failure(self):
        decoded = self.decode(result(reserved=True))
        self.assertEqual(decoded["firmware_status"], "success")
        self.assertFalse(decoded["reserved_fields_zero"])

    def test_reserved1_is_also_advisory(self):
        decoded = self.decode(replace_byte(result(), 15, 42))
        self.assertEqual(decoded["firmware_status"], "success")
        self.assertFalse(decoded["reserved_fields_zero"])

    def test_diagnostic_echo_key_field_and_pse_are_not_dumped_or_gated(self):
        decoded = self.decode(result(diagnostics=b"PRIVATE-DETAILS!"))
        self.assertEqual(decoded["firmware_status"], "success")
        self.assertFalse(decoded["diagnostic_fields_interpreted"])
        self.assertNotIn("PRIVATE", json.dumps(decoded))


class ExchangeTests(unittest.TestCase):
    def test_pair_matches_but_grants_no_hardware_permission(self):
        decoded = protocol.validate_download_config_ack(command(), result(), expected_sequence=19)
        self.assertEqual(decoded["status"], "source_contract_match")
        self.assertEqual(decoded["runtime_protocol_match"], "unproven")
        self.assertFalse(decoded["hardware_access"])
        self.assertFalse(decoded["load_authorized"])

    def test_valid_error_result_is_not_classified_as_malformed(self):
        decoded = protocol.validate_download_config_ack(command(), result(status=3), expected_sequence=19)
        self.assertEqual(decoded["status"], "firmware_rejected")
        self.assertEqual(decoded["firmware_status"], "decryption_failure")

    def test_stale_response_refused(self):
        with self.assertRaisesRegex(protocol.Refusal, "result_sequence_mismatch"):
            protocol.validate_download_config_ack(command(sequence=20), result(sequence=19), expected_sequence=20)

    def test_stale_pair_refused_by_independent_expected_sequence(self):
        with self.assertRaisesRegex(protocol.Refusal, "command_sequence_mismatch"):
            protocol.validate_download_config_ack(command(), result(), expected_sequence=20)

    def test_sequence_boundaries_are_valid_without_assuming_nonzero(self):
        for sequence in (0, 255):
            with self.subTest(sequence=sequence):
                decoded = protocol.validate_download_config_ack(command(sequence=sequence), result(sequence=sequence), expected_sequence=sequence)
                self.assertEqual(decoded["status"], "source_contract_match")

    def test_invalid_expected_sequence_types_and_ranges(self):
        for sequence in (-1, 256, True, False, "19", None, 19.0):
            with self.subTest(sequence=sequence), self.assertRaisesRegex(protocol.Refusal, "invalid_expected_sequence"):
                protocol.validate_download_config_ack(command(), result(), expected_sequence=sequence)

    def test_input_requires_immutable_already_delimited_bytes(self):
        for packet in (bytearray(command()), memoryview(command()), "private", None):
            with self.subTest(packet_type=type(packet)), self.assertRaisesRegex(protocol.Refusal, "immutable_bytes_required"):
                protocol.decode_download_config(packet, expected_sequence=19)

    def test_no_cli_data_input_and_no_default_file_access(self):
        for args, expected in (([], 0), (["--inspect", "private-path"], 2)):
            out = io.StringIO()
            with mock.patch("builtins.open", side_effect=AssertionError("file access")), contextlib.redirect_stdout(out):
                code = protocol.main(args)
            self.assertEqual(code, expected)
            self.assertNotIn("private", out.getvalue())
            self.assertIsInstance(json.loads(out.getvalue()), dict)


if __name__ == "__main__":
    unittest.main()
