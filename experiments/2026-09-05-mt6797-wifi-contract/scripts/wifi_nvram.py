#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pure, non-authorizing inspection of one selected gen3 NVRAM record.

Accepts an already isolated immutable record, never a path or partition.
Calibration values, identifiers, country bytes and record hashes stay private.
"""

import json
import struct
import sys


RECORD_BYTES = 512
PART2_OFFSET = 256


class Refusal(Exception):
    """Fixed reason code only; never includes private input."""


def _version(value):
    if type(value) is not int or not 0 <= value <= 65535:
        raise Refusal("version_context_requires_uint16")


def _compatible(own, peer, driver_own, driver_peer):
    return peer <= driver_own and own >= driver_peer


def inspect_record(record, *, driver_own_version, driver_peer_version,
                   firmware_own_version=None, firmware_peer_version=None):
    """Inspect fixed structure and source predicates, never RF applicability.

    Driver versions are required independent context. Optional firmware
    versions must be supplied together; no version is inferred from a blob.
    Semantic mismatches are reported, not confused with malformed framing.
    """
    _version(driver_own_version)
    _version(driver_peer_version)
    if (firmware_own_version is None) != (firmware_peer_version is None):
        raise Refusal("incomplete_firmware_version_context")
    if firmware_own_version is not None:
        _version(firmware_own_version)
        _version(firmware_peer_version)
    if type(record) is not bytes:
        raise Refusal("immutable_record_bytes_required")
    if len(record) != RECORD_BYTES:
        raise Refusal("exact_512_byte_record_required")

    own1, peer1 = struct.unpack_from("<HH", record, 0)
    own2, peer2 = struct.unpack_from("<HH", record, PART2_OFFSET)
    versions_match = (_compatible(own1, peer1, driver_own_version, driver_peer_version)
                      and _compatible(own2, peer2, driver_own_version, driver_peer_version))
    firmware_match = "not_supplied"
    if firmware_own_version is not None:
        firmware_match = "compatible" if _compatible(
            firmware_own_version, firmware_peer_version,
            driver_own_version, driver_peer_version) else "incompatible"

    # Source treats flags as zero/nonzero, not a canonical 0/1 encoding.
    if not versions_match:
        tx_path = "manufacture_function_returns_before_power_parameters"
    elif own1 == 1:
        tx_path = "legacy_forces_valid_flag_without_base_power_command"
    elif record[196]:
        tx_path = "base_power_command_attempted"
    else:
        tx_path = "base_power_command_skipped"

    return {
        "status": "record_inspected",
        "record_bytes": RECORD_BYTES,
        "source_record_versions_compatible": versions_match,
        "source_firmware_versions": firmware_match,
        "source_base_power_path": tx_path,
        "record_mac_usable_by_source": bool(any(record[4:10]) and not record[4] & 1),
        "record_requests_5ghz": bool(record[262]),
        "record_claims_5ghz_support": bool(record[197]),
        "hardware_5ghz_capability": "not_observed",
        "record_checksum": "not_defined_by_audited_host_layout",
        "record_provenance": "not_established_by_structure",
        "calibration_applicability": "unproven",
        "regulatory_approval": "unproven",
        "hardware_access": False,
        "load_authorized": False,
        "transmit_authorized": False,
    }


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        print(json.dumps({"status": "refused", "reason": "arguments_not_supported"}))
        return 2
    print(json.dumps({
        "status": "contract_only", "record_bytes": RECORD_BYTES,
        "input_boundary": "one_independently_isolated_record",
        "driver_version_context": "required",
        "file_access": False, "hardware_access": False,
        "load_authorized": False, "transmit_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
