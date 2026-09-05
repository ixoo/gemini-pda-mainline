#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic envelope fixtures only; none are RF defaults or retained data."""

import contextlib
import io
import json
import struct
import unittest
from unittest import mock

import wifi_nvram as record_model
import wifi_nvram_storage as storage_model


def envelope(prefix=bytes(512), check=0):
    """Supply a hand-specified check; never calculate or repair a fixture."""
    return prefix + bytes((0xaa, check))


def word_prefix(offset, value):
    prefix = bytearray(512)
    struct.pack_into("<H", prefix, offset, value)
    return bytes(prefix)


def inspect(storage, **context):
    options = {"driver_own_version": 0x0200, "driver_peer_version": 0}
    options.update(context)
    return storage_model.inspect_storage(storage, **options)


class StorageTests(unittest.TestCase):
    def test_fixed_vectors_distinguish_parity_wrap_and_payload_end(self):
        # Expected checks are literal, independently worked small sequences.
        vectors = (
            (bytes(512), 0),
            (b"\x01\x02" + bytes(510), 3),
            (b"\xff\x00\x01\x00" + bytes(508), 0),
            (b"\x10\x03\x04\x05" + bytes(508), 0x12),
            (b"\xff\x80\x81\x01" + bytes(508), 1),
            (bytes(511) + b"\x5a", 0x5a),
            (bytes(510) + b"\x07\x03", 4),
            (b"\xff" * 512, 0),
        )
        for index, (prefix, check) in enumerate(vectors):
            with self.subTest(vector=index):
                self.assertEqual(inspect(envelope(prefix, check))["storage_integrity"], "matched")

    def test_marker_is_not_part_of_checksum_coverage(self):
        self.assertEqual(inspect(envelope())["storage_integrity"], "matched")
        with self.assertRaisesRegex(storage_model.Refusal, "^storage_checksum_mismatch$"):
            inspect(envelope(check=0xaa))

    def test_every_truncated_length_is_refused(self):
        for size in range(514):
            with self.subTest(size=size), self.assertRaisesRegex(
                storage_model.Refusal, "^exact_514_byte_storage_required$"
            ):
                inspect(envelope()[:size])

    def test_trailing_and_batched_storage_are_refused(self):
        for value in (envelope() + b"x", envelope() * 2, envelope() * 3):
            with self.assertRaisesRegex(storage_model.Refusal, "^exact_514_byte_storage_required$"):
                inspect(value)

    def test_wifi_custom_and_bare_record_are_not_this_envelope(self):
        for value in (bytes(4) + b"\xaa\x00", bytes(512)):
            with self.assertRaisesRegex(storage_model.Refusal, "^exact_514_byte_storage_required$"):
                inspect(value)

    def test_only_exact_immutable_bytes_are_accepted(self):
        class BytesSubclass(bytes):
            pass

        for value in (bytearray(envelope()), memoryview(envelope()), BytesSubclass(envelope()),
                      "private-path", None, 514):
            with self.assertRaisesRegex(storage_model.Refusal, "^immutable_storage_bytes_required$"):
                inspect(value)

    def test_every_incorrect_marker_is_refused(self):
        for marker in range(256):
            if marker == 0xaa:
                continue
            with self.subTest(marker=marker), self.assertRaisesRegex(
                storage_model.Refusal, "^storage_marker_mismatch$"
            ):
                inspect(bytes(512) + bytes((marker, 0)))

    def test_every_incorrect_checksum_byte_is_refused(self):
        for check in range(1, 256):
            with self.subTest(check=check), self.assertRaisesRegex(
                storage_model.Refusal, "^storage_checksum_mismatch$"
            ):
                inspect(envelope(check=check))

    def test_single_byte_mutation_at_every_payload_position_is_detected(self):
        for index in range(512):
            prefix = bytes(index) + b"\x01" + bytes(511 - index)
            with self.subTest(index=index), self.assertRaisesRegex(
                storage_model.Refusal, "^storage_checksum_mismatch$"
            ):
                inspect(envelope(prefix))

    def test_bad_storage_never_reaches_record_inspection(self):
        inputs = (bytes(512), bytes(514), envelope(check=1), bytearray(envelope()))
        with mock.patch.object(record_model, "inspect_record") as delegate:
            for value in inputs:
                with self.assertRaises(storage_model.Refusal):
                    inspect(value)
            delegate.assert_not_called()

    def test_trailer_failure_precedes_version_context_inspection(self):
        with mock.patch.object(record_model, "inspect_record") as delegate:
            with self.assertRaisesRegex(storage_model.Refusal, "^storage_checksum_mismatch$"):
                inspect(envelope(check=1), driver_own_version="private-value")
            delegate.assert_not_called()

    def test_valid_storage_delegates_exact_prefix_and_context(self):
        prefix = word_prefix(2, 0x0200)
        with mock.patch.object(record_model, "inspect_record", wraps=record_model.inspect_record) as delegate:
            result = inspect(envelope(prefix, 2), firmware_own_version=0, firmware_peer_version=0)
            delegate.assert_called_once_with(
                prefix, driver_own_version=0x0200, driver_peer_version=0,
                firmware_own_version=0, firmware_peer_version=0,
            )
        self.assertEqual(result["storage_integrity"], "matched")

    def test_independent_driver_context_is_required(self):
        with self.assertRaises(TypeError):
            storage_model.inspect_storage(envelope())

    def test_invalid_driver_context_is_refused_without_echo(self):
        for key in ("driver_own_version", "driver_peer_version"):
            for value in (-1, 65536, True, None, "private-value", 2.0):
                with self.subTest(key=key), self.assertRaisesRegex(
                    storage_model.Refusal, "^version_context_requires_uint16$"
                ):
                    inspect(envelope(), **{key: value})

    def test_exact_selected_driver_peer_boundary_for_both_halves(self):
        for offset in (2, 258):
            self.assertTrue(inspect(envelope(word_prefix(offset, 0x0200), 2))[
                "source_record_versions_compatible"])
            result = inspect(envelope(word_prefix(offset, 0x0201), 3))
            self.assertFalse(result["source_record_versions_compatible"])
            self.assertEqual(result["storage_integrity"], "matched")
            self.assertEqual(result["source_base_power_path"],
                             "manufacture_function_returns_before_power_parameters")

    def test_uint16_context_and_own_version_lower_bound_remain_unchanged(self):
        self.assertTrue(inspect(envelope(), driver_own_version=0)["source_record_versions_compatible"])
        result = inspect(envelope(), driver_own_version=65535, driver_peer_version=1)
        self.assertFalse(result["source_record_versions_compatible"])
        self.assertEqual(result["storage_integrity"], "matched")

    def test_legacy_power_branch_remains_unchanged(self):
        prefix = word_prefix(0, 1)
        prefix = prefix[:196] + b"\xff" + prefix[197:]
        result = inspect(envelope(prefix, 0))
        self.assertEqual(result["source_base_power_path"],
                         "legacy_forces_valid_flag_without_base_power_command")
        self.assertFalse(result["load_authorized"])

    def test_version_failure_still_precedes_legacy_override(self):
        prefix = bytearray(word_prefix(0, 1))
        struct.pack_into("<H", prefix, 258, 0x0201)
        self.assertEqual(inspect(envelope(bytes(prefix), 0))["source_base_power_path"],
                         "manufacture_function_returns_before_power_parameters")

    def test_power_flag_truthiness_remains_unchanged(self):
        for value in (0, 1, 2, 255):
            prefix = bytes(196) + bytes((value,)) + bytes(315)
            result = inspect(envelope(prefix, value))
            self.assertEqual(result["source_base_power_path"],
                             "base_power_command_attempted" if value else "base_power_command_skipped")

    def test_record_mac_and_5ghz_flags_do_not_become_hardware_claims(self):
        prefix = bytearray(512)
        prefix[4], prefix[9] = 2, 1
        result = inspect(envelope(bytes(prefix), 3))
        self.assertTrue(result["record_mac_usable_by_source"])
        prefix = bytearray(512)
        prefix[197], prefix[262] = 255, 2
        result = inspect(envelope(bytes(prefix), 1))
        self.assertTrue(result["record_claims_5ghz_support"])
        self.assertTrue(result["record_requests_5ghz"])
        self.assertEqual(result["hardware_5ghz_capability"], "not_observed")

    def test_firmware_compatibility_remains_separate_from_storage(self):
        for peer, expected in ((0x0200, "compatible"), (0x0201, "incompatible")):
            result = inspect(envelope(), firmware_own_version=0, firmware_peer_version=peer)
            self.assertEqual(result["source_firmware_versions"], expected)
            self.assertEqual(result["storage_integrity"], "matched")
            self.assertFalse(result["transmit_authorized"])

    def test_partial_and_invalid_firmware_context_remain_refusals(self):
        for key in ("firmware_own_version", "firmware_peer_version"):
            with self.assertRaisesRegex(storage_model.Refusal, "^incomplete_firmware_version_context$"):
                inspect(envelope(), **{key: 0})
            with self.assertRaisesRegex(storage_model.Refusal, "^version_context_requires_uint16$"):
                inspect(envelope(), **{
                    "firmware_own_version": 0, "firmware_peer_version": 0, key: "private-value",
                })

    def test_checksum_collision_does_not_establish_authenticity(self):
        first = bytes(512)
        second = bytes(300) + b"\x01\x01" + bytes(210)
        self.assertNotEqual(first, second)
        first_result = inspect(envelope(first, 0))
        second_result = inspect(envelope(second, 0))
        self.assertEqual(first_result, second_result)
        self.assertEqual(second_result["storage_integrity"], "matched")
        self.assertEqual(second_result["record_provenance"], "not_established_by_structure")
        self.assertEqual(second_result["calibration_applicability"], "unproven")
        self.assertFalse(second_result["transmit_authorized"])

    def test_composed_output_preserves_only_existing_record_schema(self):
        expected = record_model.inspect_record(bytes(512), driver_own_version=0x0200, driver_peer_version=0)
        result = inspect(envelope())
        self.assertEqual(set(result), set(expected) | {"storage_bytes", "storage_integrity"})
        self.assertEqual(result.pop("storage_bytes"), 514)
        self.assertEqual(result.pop("storage_integrity"), "matched")
        self.assertEqual(result, expected)

    def test_inspection_has_no_output_or_file_access(self):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch("builtins.open", side_effect=AssertionError("file access")), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = inspect(envelope())
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(result["regulatory_approval"], "unproven")
        self.assertFalse(result["hardware_access"])
        self.assertFalse(result["load_authorized"])

    def test_cli_is_contract_only_without_file_access_or_argument_echo(self):
        for arguments, code in (([], 0), (["--inspect", "private-path\nprivate-data"], 2)):
            output = io.StringIO()
            with mock.patch("builtins.open", side_effect=AssertionError("file access")), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(storage_model.main(arguments), code)
            self.assertNotIn("private", output.getvalue())
            result = json.loads(output.getvalue())
            if code == 0:
                self.assertEqual(result["status"], "contract_only")
                self.assertEqual(result["model_basis"], "analysis_derived_from_retained_libnvram")
                self.assertFalse(result["file_access"])
                self.assertFalse(result["transmit_authorized"])
            else:
                self.assertEqual(result, {"status": "refused", "reason": "arguments_not_supported"})


if __name__ == "__main__":
    unittest.main()
