#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pure inspection of one selected WIFI storage envelope, without authorization.

The two-byte trailer model is analysis-derived from the retained 64-bit
libnvram ComputeCheckNo, NVM_SetCheckNo and NVM_CheckFile instruction paths.
The owning experiment records that evidence; this is an independent model,
not imported vendor implementation or a claim about other library versions.

The check starts at zero, adds even-indexed payload bytes, XORs odd-indexed
ones, and retains eight bits. The trailer is marker 0xaa followed by the
check. Collisions exist: a match establishes neither authenticity nor record
provenance, calibration applicability, or permission to load or transmit.
No input bytes, checksum values, identifiers or calibration values are emitted.
"""

import json
import sys

import wifi_nvram as record_model


STORAGE_BYTES = 514
Refusal = record_model.Refusal


def inspect_storage(storage, *, driver_own_version, driver_peer_version,
                    firmware_own_version=None, firmware_peer_version=None):
    """Validate the exact envelope before invoking the existing record model.

    Input must already be independently isolated immutable bytes. Version
    context is never inferred from the record. No filesystem or device API
    is provided, and no corrected envelope is constructed or returned.
    """
    if type(storage) is not bytes:
        raise Refusal("immutable_storage_bytes_required")
    if len(storage) != STORAGE_BYTES:
        raise Refusal("exact_514_byte_storage_required")
    if storage[-2] != 0xaa:
        raise Refusal("storage_marker_mismatch")

    check = 0
    for index in range(record_model.RECORD_BYTES):
        # TST uses the previous parity; CSEL toggles it without changing NZCV.
        # ADD/EOR/AND (without S) retain those flags: first ADD, then XOR.
        if index % 2 == 0:
            check = (check + storage[index]) & 0xff
        else:
            check ^= storage[index]
    if storage[-1] != check:
        raise Refusal("storage_checksum_mismatch")

    result = record_model.inspect_record(
        storage[:record_model.RECORD_BYTES],
        driver_own_version=driver_own_version,
        driver_peer_version=driver_peer_version,
        firmware_own_version=firmware_own_version,
        firmware_peer_version=firmware_peer_version,
    )
    result["storage_bytes"] = STORAGE_BYTES
    result["storage_integrity"] = "matched"
    return result


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        print(json.dumps({"status": "refused", "reason": "arguments_not_supported"}))
        return 2
    print(json.dumps({
        "status": "contract_only", "storage_bytes": STORAGE_BYTES,
        "record_bytes": record_model.RECORD_BYTES,
        "input_boundary": "one_independently_isolated_WIFI_storage_file",
        "model_basis": "analysis_derived_from_retained_libnvram",
        "driver_version_context": "required",
        "file_access": False, "hardware_access": False,
        "load_authorized": False, "transmit_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
