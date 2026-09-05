#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic tests; no device access or real firmware is used."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock

import wifi_firmware as fw


def reference_crc(data):
    value = 0xFFFFFFFF
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xEDB88320 if value & 1 else 0)
    return value ^ 0xFFFFFFFF


def fixture(sections=None, reserved=0, count=None):
    if sections is None:
        sections = [(48, 0, 8, 0x1000), (56, 0, 8, 0x2000)]
    image = bytearray(b"MTKW" + b"\0" * 4)
    image += struct.pack("<II", len(sections) if count is None else count, reserved)
    for section in sections:
        image += struct.pack("<IIII", *section)
    image += b"PRIVATE!" * 2
    struct.pack_into("<I", image, 4, reference_crc(image[8:]))
    return bytes(image)


def mtke_fixture(sections=None, reserved=0, count=None):
    if sections is None:
        sections = [
            (72, 2, 1, 0, 8, 0x1000),
            (80, 0, 0, 0, 8, 0x2000),
            (88, 0, 0, 0, 8, 0xF0000020),
        ]
    image = bytearray(b"MTKE" + b"\0" * 4)
    image += struct.pack("<IHHII", len(sections) if count is None else count, 0xABCD, 0x1234, 0xDECAFBAD, reserved)
    for section in sections:
        image += struct.pack("<IBBHII", *section)
    image += b"PRIVATE!" * len(sections)
    struct.pack_into("<I", image, 4, reference_crc(image[8:]))
    return bytes(image)


class StructureTests(unittest.TestCase):
    def refusal(self, blob, reason):
        with self.assertRaisesRegex(fw.Refusal, "^" + reason + "$"):
            fw.parse_mtkw(blob)

    def test_independent_crc_oracle(self):
        self.assertEqual(reference_crc(b"123456789"), 0xCBF43926)

    def test_two_sections(self):
        result = fw.parse_mtkw(fixture())
        self.assertEqual(result["status"], "structurally_valid")
        self.assertEqual(result["section_lengths"], [8, 8])
        self.assertEqual(result["unreferenced_file_bytes"], 0)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("4096", json.dumps(result))
        self.assertNotIn("8192", json.dumps(result))

    def test_all_short_headers(self):
        for length in range(fw.HEADER_SIZE):
            with self.subTest(length=length):
                self.refusal(b"MTKW"[:length].ljust(length, b"\0"), "truncated_header")

    def test_mtkw_comparator_does_not_parse_mtke(self):
        result = fw.parse_mtkw(b"MTKE" + b"SECRET STRING" * 2)
        self.assertEqual(result, {"status": "inconclusive", "reason": "unsupported_container_format"})

    def test_unknown_signature_is_not_printed(self):
        self.assertEqual(fw.parse_mtkw(b"SECRET" * 4)["status"], "inconclusive")

    def test_size_cap(self):
        self.refusal(b"\0" * (fw.MAX_FILE_BYTES + 1), "file_size_limit")

    def test_section_count_policy(self):
        for count in (0, fw.MAX_SECTIONS + 1, 0xFFFFFFFF):
            with self.subTest(count=count):
                self.refusal(fixture(count=count), "section_count_policy")

    def test_truncated_table(self):
        self.refusal(fixture()[:47], "truncated_section_table")

    def test_crc_corruption(self):
        image = bytearray(fixture())
        image[-1] ^= 1
        self.refusal(image, "container_crc_mismatch")

    def test_crc_excludes_first_eight_bytes(self):
        image = fixture()
        self.assertEqual(struct.unpack_from("<I", image, 4)[0], reference_crc(image[8:]))
        self.assertNotEqual(struct.unpack_from("<I", image, 4)[0], reference_crc(image))

    def test_metadata_intersection(self):
        self.refusal(fixture([(31, 0, 1, 0)]), "section_intersects_metadata")

    def test_out_of_file_and_integer_wrap(self):
        for section in ((49, 0, 1, 0), (32, 0, 17, 0), (0xFFFFFFFF, 0, 2, 0)):
            with self.subTest(section=section):
                self.refusal(fixture([section]), "section_out_of_file")

    def test_empty_section(self):
        self.refusal(fixture([(32, 0, 0, 0)]), "empty_section_policy")

    def test_destination_overflow(self):
        self.refusal(fixture([(32, 0, 2, 0xFFFFFFFF)]), "destination_range_overflow")

    def test_last_address_does_not_overflow(self):
        result = fw.parse_mtkw(fixture([(32, 0, 1, 0xFFFFFFFF)]))
        self.assertEqual(result["status"], "structurally_valid")

    def test_source_overlap(self):
        self.refusal(fixture([(48, 0, 9, 0x1000), (56, 0, 8, 0x2000)]), "overlapping_source_sections_policy")

    def test_destination_overlap(self):
        self.refusal(fixture([(48, 0, 8, 0x1000), (56, 0, 8, 0x1007)]), "overlapping_destination_sections_policy")

    def test_adjacent_destinations(self):
        result = fw.parse_mtkw(fixture([(48, 0, 8, 0x1000), (56, 0, 8, 0x1008)]))
        self.assertEqual(result["status"], "structurally_valid")

    def test_unordered_nonoverlapping_sections(self):
        result = fw.parse_mtkw(fixture([(56, 0, 8, 0x2000), (48, 0, 8, 0x1000)]))
        self.assertEqual(result["status"], "structurally_valid")

    def test_reserved_semantics_remain_inconclusive(self):
        for image in (fixture(reserved=42), fixture([(32, 42, 16, 0x1000)])):
            self.assertEqual(fw.parse_mtkw(image)["reason"], "reserved_semantics_unproven")

    def test_trailing_bytes_are_counted_not_interpreted(self):
        result = fw.parse_mtkw(fixture([(32, 0, 8, 0x1000)]))
        self.assertEqual(result["unreferenced_file_bytes"], 8)

    def test_exact_section_limit(self):
        count = fw.MAX_SECTIONS
        start = fw.HEADER_SIZE + count * fw.ENTRY_SIZE
        image = bytearray(b"MTKW" + b"\0" * 4 + struct.pack("<II", count, 0))
        for i in range(count):
            image += struct.pack("<IIII", start + i, 0, 1, i)
        image += b"\0" * count
        struct.pack_into("<I", image, 4, reference_crc(image[8:]))
        self.assertEqual(fw.parse_mtkw(image)["section_count"], count)


class MtkeTests(unittest.TestCase):
    def refusal(self, blob, reason):
        with self.assertRaisesRegex(fw.Refusal, "^" + reason + "$"):
            fw.parse_mtke(blob)

    def test_source_selected_structure_and_transport_split(self):
        result = fw.parse_container(mtke_fixture())
        self.assertEqual(result["format"], "planet_gen3_mt6797_mtke")
        self.assertEqual(result["status"], "structurally_valid")
        self.assertEqual(result["header_bytes"], 24)
        self.assertEqual(result["hif_section_count"], 2)
        self.assertEqual(result["emi_section_count"], 1)
        self.assertEqual(result["hif_encrypted_section_count"], 1)
        self.assertEqual(result["section_lengths"], [8, 8, 8])

    def test_metadata_never_emits_addresses_key_selector_or_header_values(self):
        result = fw.parse_mtke(mtke_fixture())
        self.assertEqual(set(result), {
            "status", "reason", "format", "header_bytes", "section_table_bytes",
            "section_count", "section_lengths", "section_payload_bytes",
            "unreferenced_file_bytes", "container_crc_matches",
            "source_sections_disjoint", "destination_ranges_disjoint",
            "reserved_fields_zero", "hif_section_count", "emi_section_count",
            "hif_encrypted_section_count", "hif_key_index_masking_needed",
            "emi_window_bytes", "emi_destination_ranges_in_window",
            "emi_destination_ranges_disjoint",
        })
        serialized = json.dumps(result)
        for value in ("PRIVATE", "4096", "8192", str(0xDECAFBAD), str(0xABCD), str(0xF0000020)):
            self.assertNotIn(value, serialized)

    def test_all_short_mtke_headers(self):
        for size in range(24):
            with self.subTest(size=size):
                self.refusal(mtke_fixture()[:size], "truncated_header")

    def test_crc_covers_from_byte_eight_through_eof(self):
        image = mtke_fixture()
        self.assertEqual(struct.unpack_from("<I", image, 4)[0], reference_crc(image[8:]))
        for position in (12, 16, 20, 24, len(image) - 1):
            damaged = bytearray(image)
            damaged[position] ^= 1
            with self.subTest(position=position):
                self.refusal(damaged, "container_crc_mismatch")

    def test_truncated_mtke_table(self):
        self.refusal(mtke_fixture()[:71], "truncated_section_table")

    def test_mtke_count_limits(self):
        for count in (0, fw.MAX_SECTIONS + 1, 0xFFFFFFFF):
            with self.subTest(count=count):
                self.refusal(mtke_fixture(count=count), "section_count_policy")

    def test_table_intersection(self):
        self.refusal(mtke_fixture([(39, 0, 0, 0, 1, 0)]), "section_intersects_metadata")

    def test_mtke_source_bounds(self):
        self.refusal(mtke_fixture([(40, 0, 0, 0, 9, 0)]), "section_out_of_file")

    def test_hif_destination_overflow(self):
        self.refusal(mtke_fixture([(40, 0, 0, 0, 2, 0xFFFFFFFF)]), "destination_range_overflow")

    def test_last_emi_byte_is_in_window(self):
        entries = [(72, 0, 0, 0, 8, 0), (80, 0, 0, 0, 8, 8), (88, 0, 0, 0, 8, 0xF007FFF8)]
        self.assertEqual(fw.parse_mtke(mtke_fixture(entries))["status"], "structurally_valid")

    def test_emi_start_or_end_outside_window(self):
        for destination in (0xF007FFF9, 0xF0080000, 0xF00FFFF0):
            entries = [(72, 0, 0, 0, 8, 0), (80, 0, 0, 0, 8, 8), (88, 0, 0, 0, 8, destination)]
            with self.subTest(destination=destination):
                self.refusal(mtke_fixture(entries), "emi_section_out_of_window")

    def test_masked_emi_alias_overlap_policy(self):
        entries = [(88, 0, 0, 0, 8, 0), (96, 0, 0, 0, 8, 8), (104, 0, 0, 0, 8, 0xF0000020), (112, 0, 0, 0, 8, 0xE0000020)]
        self.refusal(mtke_fixture(entries), "overlapping_emi_sections_policy")

    def test_hif_and_emi_are_different_address_spaces(self):
        entries = [(72, 0, 0, 0, 8, 0x20), (80, 0, 0, 0, 8, 0x1000), (88, 0, 0, 0, 8, 0xF0000020)]
        self.assertEqual(fw.parse_mtke(mtke_fixture(entries))["status"], "structurally_valid")

    def test_hif_overlap_policy(self):
        entries = [(56, 0, 0, 0, 8, 0), (64, 0, 0, 0, 8, 7)]
        self.refusal(mtke_fixture(entries), "overlapping_destination_sections_policy")

    def test_nonzero_encryption_and_key_mask_follow_source_semantics(self):
        result = fw.parse_mtke(mtke_fixture([(40, 255, 255, 0, 8, 0)]))
        self.assertEqual(result["status"], "structurally_valid")
        self.assertEqual(result["hif_encrypted_section_count"], 1)
        self.assertTrue(result["hif_key_index_masking_needed"])
        self.assertNotIn("255", json.dumps(result))

    def test_emi_flags_do_not_describe_hif_encryption(self):
        entries = [(72, 0, 0, 0, 8, 0), (80, 0, 0, 0, 8, 8), (88, 255, 255, 0, 8, 0xF0000020)]
        result = fw.parse_mtke(mtke_fixture(entries))
        self.assertEqual(result["hif_encrypted_section_count"], 0)
        self.assertFalse(result["hif_key_index_masking_needed"])

    def test_reserved_values_are_inconclusive(self):
        for image in (mtke_fixture(reserved=1), mtke_fixture([(40, 0, 0, 1, 8, 0)])):
            self.assertEqual(fw.parse_mtke(image)["reason"], "reserved_semantics_unproven")

    def test_one_section_is_counted_without_claiming_complete_firmware(self):
        result = fw.parse_mtke(mtke_fixture([(40, 0, 0, 0, 8, 0)]))
        self.assertEqual((result["hif_section_count"], result["emi_section_count"]), (1, 0))

    def test_identity_gated_mtke_synthetic_integration(self):
        image = mtke_fixture()
        with mock.patch.object(fw, "KNOWN_SIZE", len(image)), mock.patch.object(fw, "KNOWN_SHA256", hashlib.sha256(image).hexdigest()):
            result = fw.inspect_bytes(image)
        self.assertEqual(result["reason"], "bounded_mtke_structure")
        self.assertFalse(result["load_authorized"])


class IdentityTests(unittest.TestCase):
    def test_unrecognized_artifact_never_reaches_parser(self):
        with mock.patch.object(fw, "parse_mtkw", side_effect=AssertionError("called")):
            result = fw.inspect_bytes(fixture())
        self.assertEqual(result["reason"], "artifact_identity_mismatch")

    def test_known_size_with_wrong_digest_is_refused(self):
        self.assertEqual(fw.inspect_bytes(b"\0" * fw.KNOWN_SIZE)["reason"], "artifact_identity_mismatch")

    def test_identity_gate_in_synthetic_fixture_only(self):
        image = fixture()
        with mock.patch.object(fw, "KNOWN_SIZE", len(image)), mock.patch.object(fw, "KNOWN_SHA256", hashlib.sha256(image).hexdigest()):
            result = fw.inspect_bytes(image)
        self.assertEqual(result["status"], "structurally_valid")
        self.assertFalse(result["load_authorized"])
        self.assertEqual(result["runtime_loader_applicability"], "unproven")


class FileAndCliTests(unittest.TestCase):
    def setUp(self):
        # TemporaryDirectory cleans its explicit system temporary root on failure.
        self.temporary = tempfile.TemporaryDirectory(prefix="gemini-wifi-firmware-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.image = self.root / "private-firmware"
        self.image.write_bytes(fixture())

    def test_regular_file(self):
        self.assertEqual(fw.read_regular_file(str(self.image)), fixture())

    def test_symlink_and_parent_symlink(self):
        link = self.root / "link"
        link.symlink_to(self.image)
        parent = self.root / "parent"
        parent.symlink_to(self.root, target_is_directory=True)
        for path in (link, parent / self.image.name):
            with self.subTest(path=path), self.assertRaises(fw.Refusal), mock.patch.object(fw.os, "read", side_effect=AssertionError("read")):
                fw.read_regular_file(str(path))

    def test_special_files_and_directory_never_read(self):
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        for path in (fifo, self.root):
            with self.subTest(path=path), self.assertRaises(fw.Refusal), mock.patch.object(fw.os, "read", side_effect=AssertionError("read")):
                fw.read_regular_file(str(path))

    def test_device_node_metadata_is_refused_before_read(self):
        observed = mock.Mock(st_mode=stat.S_IFCHR)
        with mock.patch.object(fw.os, "stat", return_value=observed), self.assertRaisesRegex(fw.Refusal, "not_regular_file"), mock.patch.object(fw.os, "read", side_effect=AssertionError("read")):
            fw.read_regular_file(str(self.image))

    def test_oversized_file_never_read(self):
        with self.image.open("wb") as stream:
            stream.truncate(fw.MAX_FILE_BYTES + 1)
        with self.assertRaisesRegex(fw.Refusal, "file_size_limit"), mock.patch.object(fw.os, "read", side_effect=AssertionError("read")):
            fw.read_regular_file(str(self.image))

    def test_lexical_path_refusals(self):
        for path in ("", "../private", "./private", "bad\0path", "a//b", "x" * (fw.MAX_PATH_BYTES + 1), "/".join(["a"] * 65)):
            with self.subTest(path=path), self.assertRaises(fw.Refusal), mock.patch.object(fw.os, "open", side_effect=AssertionError("open")):
                fw.read_regular_file(path)

    def test_changed_file_is_refused(self):
        original_read = os.read
        mutated = False

        def mutate(descriptor, count):
            nonlocal mutated
            block = original_read(descriptor, count)
            if not mutated:
                mutated = True
                with self.image.open("ab") as stream:
                    stream.write(b"changed")
            return block

        with mock.patch.object(fw.os, "read", side_effect=mutate), self.assertRaisesRegex(fw.Refusal, "file_changed"):
            fw.read_regular_file(str(self.image))

    def test_maximum_read_budget_even_if_file_grows(self):
        counts = []

        def growing_read(descriptor, count):
            counts.append(count)
            return b"x" * count

        with mock.patch.object(fw.os, "read", side_effect=growing_read), self.assertRaisesRegex(fw.Refusal, "file_size_limit"):
            fw.read_regular_file(str(self.image))
        self.assertEqual(sum(counts), fw.MAX_FILE_BYTES + 1)

    def run_cli(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = fw.main(args)
        return code, json.loads(output.getvalue())

    def test_default_opens_nothing(self):
        with mock.patch.object(fw.os, "open", side_effect=AssertionError("open")):
            code, result = self.run_cli([])
        self.assertEqual(code, 0)
        self.assertFalse(result["file_opened"])

    def test_cli_does_not_emit_path_or_payload(self):
        code, result = self.run_cli(["--inspect", str(self.image)])
        self.assertEqual(code, 2)
        serialized = json.dumps(result)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("PRIVATE", serialized)
        self.assertEqual(result["reason"], "artifact_identity_mismatch")

    def test_cli_errors_do_not_echo_private_arguments(self):
        for args in (["--bad-private-secret"], ["--inspect"], ["--inspect", str(self.root / "missing-private-file")]):
            with self.subTest(args=args):
                code, result = self.run_cli(args)
                self.assertEqual(code, 2)
                self.assertNotIn("private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
