#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic format tests; fixtures are never calibration defaults."""

import contextlib
import io
import json
import struct
import unittest
from unittest import mock

import wifi_nvram as nvram


def fixture(own1=2, peer1=0, own2=2, peer2=0, power=1):
    record = bytearray(512)
    struct.pack_into("<HH", record, 0, own1, peer1)
    struct.pack_into("<HH", record, 256, own2, peer2)
    record[4:10] = b"\x02\0\0\0\0\x01"  # synthetic local unicast
    record[10:12] = b"XX"  # no regulatory meaning
    record[196] = power
    return bytes(record)


def inspect(record, **context):
    options = {"driver_own_version": 2, "driver_peer_version": 0}
    options.update(context)
    return nvram.inspect_record(record, **options)


def change(record, offset, value):
    return record[:offset] + bytes([value]) + record[offset + 1:]


class RecordTests(unittest.TestCase):
    def test_source_compatible_record_is_not_calibration_approval(self):
        result = inspect(fixture())
        self.assertTrue(result["source_record_versions_compatible"])
        self.assertEqual(result["source_base_power_path"], "base_power_command_attempted")
        for key in ("calibration_applicability", "regulatory_approval"):
            self.assertEqual(result[key], "unproven")
        for key in ("hardware_access", "load_authorized", "transmit_authorized"):
            self.assertFalse(result[key])

    def test_every_truncated_record_is_refused(self):
        for size in range(512):
            with self.subTest(size=size), self.assertRaisesRegex(nvram.Refusal, "^exact_512_byte_record_required$"):
                inspect(fixture()[:size])

    def test_trailing_bytes_and_multiple_records_are_refused(self):
        for record in (fixture() + b"x", fixture() * 2):
            with self.assertRaisesRegex(nvram.Refusal, "^exact_512_byte_record_required$"):
                inspect(record)

    def test_no_partition_search_or_mutable_buffer(self):
        for record in (bytearray(fixture()), memoryview(fixture()), "private-path", None):
            with self.assertRaisesRegex(nvram.Refusal, "^immutable_record_bytes_required$"):
                inspect(record)

    def test_driver_version_context_is_required(self):
        with self.assertRaises(TypeError):
            nvram.inspect_record(fixture())

    def test_invalid_version_context_types_and_ranges(self):
        for key in ("driver_own_version", "driver_peer_version"):
            for value in (-1, 65536, True, False, "2", None, 2.0):
                with self.subTest(key=key, value_type=type(value)), self.assertRaisesRegex(nvram.Refusal, "^version_context_requires_uint16$"):
                    inspect(fixture(), **{key: value})

    def test_each_part_peer_must_not_exceed_driver_own(self):
        for record in (fixture(peer1=3), fixture(peer2=3)):
            self.assertFalse(inspect(record)["source_record_versions_compatible"])
        self.assertTrue(inspect(fixture(peer1=2, peer2=2))["source_record_versions_compatible"])

    def test_each_part_own_must_meet_driver_peer(self):
        for record in (fixture(own1=1), fixture(own2=1)):
            self.assertFalse(inspect(record, driver_peer_version=2)["source_record_versions_compatible"])
        self.assertTrue(inspect(fixture(), driver_peer_version=2)["source_record_versions_compatible"])

    def test_little_endian_versions_and_part2_offset(self):
        self.assertFalse(inspect(fixture(peer2=0x0100), driver_own_version=0x00FF)["source_record_versions_compatible"])
        self.assertTrue(inspect(fixture(peer2=0x0100), driver_own_version=0x0100)["source_record_versions_compatible"])

    def test_uint16_context_boundaries(self):
        self.assertTrue(inspect(fixture(own1=0, own2=0), driver_own_version=0)["source_record_versions_compatible"])
        self.assertTrue(inspect(fixture(own1=65535, peer1=65535, own2=65535, peer2=65535), driver_own_version=65535, driver_peer_version=65535)["source_record_versions_compatible"])

    def test_zero_power_flag_is_reported_without_invented_fallback(self):
        self.assertEqual(inspect(fixture(power=0))["source_base_power_path"], "base_power_command_skipped")

    def test_all_nonzero_power_flags_follow_source_truthiness(self):
        for value in range(1, 256):
            self.assertEqual(inspect(fixture(power=value))["source_base_power_path"], "base_power_command_attempted")

    def test_legacy_own_version_one_does_not_send_base_power(self):
        for value in (0, 1, 255):
            self.assertEqual(inspect(fixture(own1=1, power=value))["source_base_power_path"], "legacy_forces_valid_flag_without_base_power_command")

    def test_version_failure_precedes_legacy_override(self):
        self.assertEqual(inspect(fixture(own1=1, peer2=3))["source_base_power_path"], "manufacture_function_returns_before_power_parameters")

    def test_record_mac_predicate_does_not_claim_factory_identity(self):
        self.assertTrue(inspect(fixture())["record_mac_usable_by_source"])
        for address in (b"\0" * 6, b"\xff" * 6, b"\x01\0\0\0\0\0"):
            record = fixture()[:4] + address + fixture()[10:]
            self.assertFalse(inspect(record)["record_mac_usable_by_source"])

    def test_5ghz_flags_do_not_stand_in_for_hardware_capability(self):
        result = inspect(change(change(fixture(), 197, 255), 262, 2))
        self.assertTrue(result["record_claims_5ghz_support"])
        self.assertTrue(result["record_requests_5ghz"])
        self.assertEqual(result["hardware_5ghz_capability"], "not_observed")
        self.assertFalse(result["transmit_authorized"])

    def test_firmware_context_unknown_and_pairing(self):
        self.assertEqual(inspect(fixture())["source_firmware_versions"], "not_supplied")
        for key in ("firmware_own_version", "firmware_peer_version"):
            with self.assertRaisesRegex(nvram.Refusal, "^incomplete_firmware_version_context$"):
                inspect(fixture(), **{key: 0})

    def test_firmware_version_mismatches_are_distinct(self):
        result = inspect(fixture(), firmware_own_version=0, firmware_peer_version=3)
        self.assertEqual(result["source_firmware_versions"], "incompatible")
        self.assertTrue(result["source_record_versions_compatible"])
        self.assertEqual(inspect(fixture(), firmware_own_version=2, firmware_peer_version=2)["source_firmware_versions"], "compatible")
        self.assertEqual(inspect(fixture(), firmware_own_version=0, firmware_peer_version=0, driver_peer_version=1)["source_firmware_versions"], "incompatible")

    def test_firmware_version_context_rejects_invalid_values(self):
        for key in ("firmware_own_version", "firmware_peer_version"):
            for value in (-1, 65536, True, "private", 1.0):
                options = {"firmware_own_version": 0, "firmware_peer_version": 0, key: value}
                with self.assertRaisesRegex(nvram.Refusal, "^version_context_requires_uint16$"):
                    inspect(fixture(), **options)

    def test_reserved_and_calibration_payload_are_not_invented_checksums(self):
        original = fixture()
        modified = original[:12] + bytes(range(184)) + original[196:]
        modified = modified[:271] + b"private-calibration".ljust(241, b"Z")
        self.assertEqual(inspect(original), inspect(modified))
        self.assertNotIn("private", json.dumps(inspect(modified)))
        self.assertEqual(inspect(modified)["record_checksum"], "not_defined_by_audited_host_layout")

    def test_zero_record_is_not_promoted_by_permissive_source_versions(self):
        result = inspect(bytes(512))
        self.assertTrue(result["source_record_versions_compatible"])
        self.assertEqual(result["source_base_power_path"], "base_power_command_skipped")
        self.assertEqual(result["calibration_applicability"], "unproven")

    def test_output_is_a_fixed_sanitized_schema(self):
        result = inspect(fixture())
        self.assertEqual(set(result), {"status", "record_bytes", "source_record_versions_compatible", "source_firmware_versions", "source_base_power_path", "record_mac_usable_by_source", "record_requests_5ghz", "record_claims_5ghz_support", "hardware_5ghz_capability", "record_checksum", "record_provenance", "calibration_applicability", "regulatory_approval", "hardware_access", "load_authorized", "transmit_authorized"})
        self.assertNotIn("XX", json.dumps(result))

    def test_cli_never_opens_files_or_echoes_arguments(self):
        for arguments, code in (([], 0), (["--inspect", "private-path"], 2)):
            output = io.StringIO()
            with mock.patch("builtins.open", side_effect=AssertionError("file access")), contextlib.redirect_stdout(output):
                self.assertEqual(nvram.main(arguments), code)
            self.assertNotIn("private", output.getvalue())
            self.assertIsInstance(json.loads(output.getvalue()), dict)


if __name__ == "__main__":
    unittest.main()
