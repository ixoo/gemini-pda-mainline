#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Inspect a pinned private firmware file without emitting its contents.

The selected MT6797 gen3 MTKE structure and the gen2 MTKW comparison
structure come from public Planet source. This is never a firmware loader.
"""

import argparse
import hashlib
import json
import os
import stat
import struct
import sys
import zlib


MAX_FILE_BYTES = 1024 * 1024
MAX_SECTIONS = 256
MAX_PATH_COMPONENTS = 64
MAX_PATH_BYTES = 4096
KNOWN_SIZE = 411632
KNOWN_SHA256 = "a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd"
HEADER_SIZE = 16
ENTRY_SIZE = 16
ADDRESS_LIMIT = 1 << 32
MTKE_HEADER_SIZE = 24
EMI_WINDOW_BYTES = 512 * 1024
EMI_OFFSET_MASK = 0xFFFFF


class Refusal(Exception):
    """A fixed reason code which never embeds input data or a host path."""


def contract():
    return {
        "status": "contract_only",
        "file_opened": False,
        "format": "planet_gen3_mt6797_mtke",
        "comparison_format": "planet_gen2_mtkw",
        "known_size": KNOWN_SIZE,
        "known_sha256": KNOWN_SHA256,
        "max_file_bytes": MAX_FILE_BYTES,
        "max_sections": MAX_SECTIONS,
        "hardware_access": False,
        "load_authorized": False,
        "runtime_loader_applicability": "unproven",
        "redistribution_permission": "unresolved",
    }


def _file_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def read_regular_file(path):
    """Open only through nonsymlink path components and read at most cap+1.

    A stable, ordinary local file is required. No special file, directory,
    network connection, subprocess, firmware service or device API is used.
    """
    if not isinstance(path, str) or not path or "\x00" in path:
        raise Refusal("invalid_path")
    if len(os.fsencode(path)) > MAX_PATH_BYTES:
        raise Refusal("path_limit")
    components = path.split(os.sep)
    if os.path.isabs(path):
        components = components[1:]
    if any(part in ("", ".", "..") for part in components):
        raise Refusal("invalid_path")
    if len(components) > MAX_PATH_COMPONENTS:
        raise Refusal("path_limit")
    needed = ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")
    if any(not hasattr(os, name) for name in needed):
        raise Refusal("safe_open_unavailable")

    directory = None
    descriptor = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory = os.open(os.sep if os.path.isabs(path) else ".", flags)
        for component in components[:-1]:
            child = os.open(component, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        before = os.stat(components[-1], dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise Refusal("not_regular_file")
        if before.st_size > MAX_FILE_BYTES:
            raise Refusal("file_size_limit")
        descriptor = os.open(
            components[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise Refusal("not_regular_file")
        if _file_identity(before) != _file_identity(opened):
            raise Refusal("file_changed")

        chunks = []
        total = 0
        while total <= MAX_FILE_BYTES:
            block = os.read(descriptor, min(65536, MAX_FILE_BYTES + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
        after = os.fstat(descriptor)
        if total > MAX_FILE_BYTES:
            raise Refusal("file_size_limit")
        if total != opened.st_size or _file_identity(opened) != _file_identity(after):
            raise Refusal("file_changed")
        return b"".join(chunks)
    except OSError:
        raise Refusal("file_open_or_read_refused") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def _overlaps(ranges):
    ordered = sorted(ranges)
    return any(left[1] > right[0] for left, right in zip(ordered, ordered[1:]))


def _parse_divided(data, mtke):
    """Use source-established layout; impose explicit bounded read policy."""
    header_size = MTKE_HEADER_SIZE if mtke else HEADER_SIZE
    signature = b"MTKE" if mtke else b"MTKW"
    if len(data) > MAX_FILE_BYTES:
        raise Refusal("file_size_limit")
    if len(data) < header_size:
        raise Refusal("truncated_header")
    if data[:4] != signature:
        return {"status": "inconclusive", "reason": "unsupported_container_format"}
    stored_crc, count = struct.unpack_from("<II", data, 4)
    reserved = struct.unpack_from("<I", data, 20 if mtke else 12)[0]
    if not 1 <= count <= MAX_SECTIONS:
        raise Refusal("section_count_policy")
    table_end = header_size + ENTRY_SIZE * count
    if table_end > len(data):
        raise Refusal("truncated_section_table")
    if zlib.crc32(memoryview(data)[8:]) & 0xFFFFFFFF != stored_crc:
        raise Refusal("container_crc_mismatch")

    source_ranges = []
    destination_ranges = []
    emi_ranges = []
    lengths = []
    reserved_zero = reserved == 0
    encrypted_hif_count = 0
    masked_hif_key_index = False
    for index in range(count):
        if mtke:
            offset, key_index, encrypted, section_reserved, length, destination = struct.unpack_from(
                "<IBBHII", data, header_size + ENTRY_SIZE * index,
            )
            if index < 2 and encrypted:
                # Gen3 treats ucEnc as a boolean and masks ucKIdx to two bits.
                encrypted_hif_count += 1
                masked_hif_key_index = masked_hif_key_index or key_index > 3
        else:
            offset, section_reserved, length, destination = struct.unpack_from(
                "<IIII", data, header_size + ENTRY_SIZE * index,
            )
        reserved_zero = reserved_zero and section_reserved == 0
        if length == 0:
            raise Refusal("empty_section_policy")
        if offset < table_end:
            raise Refusal("section_intersects_metadata")
        if offset > len(data) or length > len(data) - offset:
            raise Refusal("section_out_of_file")
        if length > ADDRESS_LIMIT - destination:
            raise Refusal("destination_range_overflow")
        source_ranges.append((offset, offset + length))
        if mtke and index >= 2:
            emi_offset = destination & EMI_OFFSET_MASK
            if length > EMI_WINDOW_BYTES - emi_offset:
                raise Refusal("emi_section_out_of_window")
            emi_ranges.append((emi_offset, emi_offset + length))
        else:
            destination_ranges.append((destination, destination + length))
        lengths.append(length)
    if _overlaps(source_ranges):
        raise Refusal("overlapping_source_sections_policy")
    if _overlaps(destination_ranges):
        raise Refusal("overlapping_destination_sections_policy")
    if _overlaps(emi_ranges):
        raise Refusal("overlapping_emi_sections_policy")

    result = {
        "status": "structurally_valid" if reserved_zero else "inconclusive",
        "reason": ("bounded_mtke_structure" if mtke else "bounded_mtkw_structure") if reserved_zero else "reserved_semantics_unproven",
        "format": "planet_gen3_mt6797_mtke" if mtke else "planet_gen2_mtkw",
        "header_bytes": header_size,
        "section_table_bytes": count * ENTRY_SIZE,
        "section_count": count,
        "section_lengths": lengths,
        "section_payload_bytes": sum(lengths),
        "unreferenced_file_bytes": len(data) - table_end - sum(lengths),
        "container_crc_matches": True,
        "source_sections_disjoint": True,
        "destination_ranges_disjoint": True,
        "reserved_fields_zero": reserved_zero,
    }
    if mtke:
        result.update({
            "hif_section_count": min(count, 2),
            "emi_section_count": max(count - 2, 0),
            "hif_encrypted_section_count": encrypted_hif_count,
            "hif_key_index_masking_needed": masked_hif_key_index,
            "emi_window_bytes": EMI_WINDOW_BYTES,
            "emi_destination_ranges_in_window": True,
            "emi_destination_ranges_disjoint": True,
        })
    return result


def parse_mtkw(data):
    """Synthetic-testable gen2 comparator; does not establish file identity."""
    return _parse_divided(data, mtke=False)


def parse_mtke(data):
    """Synthetic-testable selected gen3 layout; never emits address/key data."""
    return _parse_divided(data, mtke=True)


def parse_container(data):
    """Recognize only the two individually source-established formats."""
    return parse_mtke(data) if data[:4] == b"MTKE" else parse_mtkw(data)


def inspect_bytes(data):
    """Gate any structural interpretation on the already recorded artifact."""
    if len(data) > MAX_FILE_BYTES:
        raise Refusal("file_size_limit")
    result = {
        "file_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "hardware_access": False,
        "load_authorized": False,
        "runtime_loader_applicability": "unproven",
        "redistribution_permission": "unresolved",
    }
    if len(data) != KNOWN_SIZE or result["sha256"] != KNOWN_SHA256:
        result.update(status="refused", reason="artifact_identity_mismatch")
        return result
    result["artifact_identity"] = "recorded_gemini_wifi_firmware"
    try:
        result.update(parse_container(data))
    except Refusal as exc:
        result.update(status="refused", reason=str(exc))
    return result


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal("invalid_arguments")


def main(argv=None):
    parser = SafeArgumentParser(
        prog="wifi_firmware.py",
        description="Default: describe the contract without opening a file.",
        allow_abbrev=False,
    )
    parser.add_argument("--inspect", metavar="FILE", help="inspect the exact recorded private firmware")
    try:
        args = parser.parse_args(argv)
        result = contract() if args.inspect is None else inspect_bytes(read_regular_file(args.inspect))
    except (Refusal, UnicodeError) as exc:
        result = {"status": "refused", "reason": str(exc) if isinstance(exc, Refusal) else "invalid_path"}
    print(json.dumps(result, sort_keys=True))
    return {"refused": 2, "inconclusive": 3}.get(result["status"], 0)


if __name__ == "__main__":
    sys.exit(main())
