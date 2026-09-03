#!/usr/bin/env python3
"""Decode an exact record-4 ledger only after changed-boot-ID recovery."""

from __future__ import annotations

import argparse
import binascii
from pathlib import Path
import struct
import sys
import uuid


PSTORE_SIGNATURE = 0x43474244
MAGIC = 0x4C483947
VERSION_V1 = 0x00010001
VERSION_V2 = 0x00010002
VERSION_V3 = 0x00010003
VERSION = VERSION_V1
COPY_WORDS_V1 = 27
COPY_WORDS_V2 = 37
COPY_WORDS = COPY_WORDS_V1
COPIES = 2
PAYLOAD_BYTES_V1 = COPY_WORDS_V1 * COPIES * 4
PAYLOAD_BYTES_V2 = COPY_WORDS_V2 * COPIES * 4
PAYLOAD_BYTES = PAYLOAD_BYTES_V1
SLOT_BYTES = 0x1000
MAX_GENERATION_V1_V2 = 16
MAX_GENERATION_V3 = 17
READBACK_BITMAP_V1 = 1 << 31
READBACK_MISMATCH_NAMES = {
    0: "baseline-null",
    1: "post-null",
    2: "baseline-invalid",
    3: "baseline-status-cpu8-missing",
    4: "baseline-status2-cpu8-missing",
    5: "baseline-status-cpu9-missing",
    6: "baseline-status2-cpu9-missing",
    7: "baseline-cci-before-pending",
    8: "baseline-cci-after-pending",
    9: "post-invalid",
    10: "post-status-cpu8-missing",
    11: "post-status2-cpu8-missing",
    12: "post-status-cpu9-present",
    13: "post-status2-cpu9-present",
    14: "post-cci-before-pending",
    15: "post-cci-after-pending",
    16: "mp2-cpusys-pwr-con-changed",
    17: "cpu8-pwr-con-changed",
    18: "ext-iso-changed",
    19: "dcm-changed",
    20: "cci-request-changed",
    21: "provider-changed",
    22: "clock-changed",
    23: "bigidvfs-changed",
}
READBACK_MISMATCH_MASK = sum(1 << bit for bit in READBACK_MISMATCH_NAMES)

STAGES_V1_V2 = {
    1: "binding-entry-parent-exact",
    2: "down-owner-prepared",
    3: "watchdog-validated",
    4: "baseline-valid",
    5: "down-owner-validated",
    6: "target-disable-valid",
    7: "cpu-off-committed-before-smc",
    8: "cpu-off-returned-fault",
    9: "affinity-level0-off",
    10: "post-state-valid",
    11: "cpu8-responsive",
    12: "off-proof-accepted",
    13: "generic-down-complete-members-0x1",
    14: "restore-prepared",
    15: "cpu-on-committed-before-call",
    16: "secondary-complete",
    17: "generic-restore-complete-members-0x3",
}
STAGES_V3 = {
    **{stage: name for stage, name in STAGES_V1_V2.items() if stage < 16},
    16: "p30e-rearmed",
    17: "secondary-complete",
    18: "generic-restore-complete-members-0x3",
}
TERMINALS = {
    0: "none",
    1: "rejected-precommit",
    2: "cpu-off-returned",
    3: "postcommit-down-fault",
    4: "restore-fault",
    5: "restored-success",
}


class DecodeError(ValueError):
    pass


def canonical_uuid(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise DecodeError("malformed-boot-id") from exc
    if str(parsed) != value.lower():
        raise DecodeError("noncanonical-boot-id")
    return str(parsed)


def payload_from_capture(data: bytes) -> tuple[bytes, int]:
    if len(data) in (PAYLOAD_BYTES_V1, PAYLOAD_BYTES_V2):
        return data, len(data)
    if len(data) != SLOT_BYTES:
        raise DecodeError("capture-size-not-216-296-or-4096")
    signature, start, size = struct.unpack_from("<III", data)
    if signature != PSTORE_SIGNATURE:
        raise DecodeError("raw-slot-signature-invalid")
    if start != size or size not in (PAYLOAD_BYTES_V1, PAYLOAD_BYTES_V2):
        raise DecodeError("raw-slot-length-invalid")
    return data[12:12 + size], size


def semantic_valid(words: tuple[int, ...], version: int) -> bool:
    generation, stage, terminal, error_u32 = words[2:6]
    error = struct.unpack("<i", struct.pack("<I", error_u32))[0]
    session = words[6] | words[7] << 32
    parent_generation = words[8]
    parent_cookie = words[9] | words[10] << 32
    watchdog = words[11] | words[12] << 32
    down_generation = words[13]
    down_cookie = words[14] | words[15] << 32
    restore_generation = words[16]
    restore_cookie = words[17] | words[18] << 32
    call_counts = words[20:24]
    online_mask = words[24] & 0xFFFF
    members = words[24] >> 16
    readback_mismatch = words[25]
    stages = STAGES_V3 if version == VERSION_V3 else STAGES_V1_V2
    max_generation = (MAX_GENERATION_V3 if version == VERSION_V3
                      else MAX_GENERATION_V1_V2)
    completion_stage = 18 if version == VERSION_V3 else 17
    if not 1 <= generation <= max_generation or stage not in stages:
        return False
    if terminal not in TERMINALS or not session or not parent_generation or not parent_cookie:
        return False
    if stage >= 2 and (not down_generation or not down_cookie):
        return False
    if stage >= 3 and not watchdog:
        return False
    if stage >= 14 and (not restore_generation or not restore_cookie):
        return False
    if any(count > 1 for count in call_counts):
        return False
    if online_mask & ~0x3FF or members & ~0x3:
        return False
    if (readback_mismatch & READBACK_BITMAP_V1 and
            readback_mismatch & ~(READBACK_BITMAP_V1 |
                                  READBACK_MISMATCH_MASK)):
        return False
    if version in (VERSION_V2, VERSION_V3):
        readiness_samples = words[26]
        readiness_sleeps = words[27]
        readiness_error = struct.unpack("<i", struct.pack("<I", words[28]))[0]
        readiness_flags = words[29]
        readiness_values = words[30:36]
        if readiness_samples > 51 or readiness_sleeps > 50:
            return False
        if readiness_flags & ~0x3:
            return False
        if stage < 15:
            if (readiness_samples or readiness_sleeps or readiness_error or
                    readiness_flags or any(readiness_values)):
                return False
        else:
            if not readiness_samples or readiness_sleeps + 1 != readiness_samples:
                return False
            if not readiness_flags & 0x1:
                return False
            ready = bool(readiness_flags & 0x2)
            if ready == bool(readiness_error):
                return False
            if not ready and not (terminal == 4 and stage == 15 and
                                  call_counts[3] == 0):
                return False
    if terminal == 0:
        return error == 0 and stage not in (8, completion_stage)
    if terminal == 5:
        return stage == completion_stage and error == 0
    if error == 0:
        return False
    if terminal == 1:
        return stage <= 6
    if terminal == 2:
        return stage == 8
    if terminal == 3:
        return 9 <= stage <= 13
    return terminal == 4 and stage >= 14


def decode_copy(payload: bytes, copy: int, payload_bytes: int) -> dict[str, int] | None:
    if payload_bytes == PAYLOAD_BYTES_V1:
        copy_words = COPY_WORDS_V1
        allowed_versions = (VERSION_V1,)
    elif payload_bytes == PAYLOAD_BYTES_V2:
        copy_words = COPY_WORDS_V2
        allowed_versions = (VERSION_V2, VERSION_V3)
    else:
        return None
    offset = copy * copy_words * 4
    words = struct.unpack_from(f"<{copy_words}I", payload, offset)
    version = words[1]
    expected_crc = binascii.crc32(
        payload[offset:offset + (copy_words - 1) * 4]) & 0xFFFFFFFF
    if (words[0] != MAGIC or version not in allowed_versions or
            words[copy_words - 1] != expected_crc):
        return None
    if not semantic_valid(words, version):
        return None
    error = struct.unpack("<i", struct.pack("<I", words[5]))[0]
    record = {
        "copy": copy,
        "version": version,
        "generation": words[2],
        "stage": words[3],
        "terminal": words[4],
        "error": error,
        "session_id": words[6] | words[7] << 32,
        "parent_generation": words[8],
        "parent_cookie": words[9] | words[10] << 32,
        "watchdog_identity": words[11] | words[12] << 32,
        "down_generation": words[13],
        "down_cookie": words[14] | words[15] << 32,
        "restore_generation": words[16],
        "restore_cookie": words[17] | words[18] << 32,
        "result_flags": words[19],
        "cpu_off_calls": words[20],
        "affinity_calls": words[21],
        "cpu8_ipi_calls": words[22],
        "cpu_on_calls": words[23],
        "online_mask": words[24] & 0xFFFF,
        "members": words[24] >> 16,
        "readback_mismatch": words[25],
    }
    if version in (VERSION_V2, VERSION_V3):
        record.update({
            "restore_readiness_samples": words[26],
            "restore_readiness_sleeps": words[27],
            "restore_readiness_error": struct.unpack(
                "<i", struct.pack("<I", words[28]))[0],
            "restore_readiness_flags": words[29],
            "restore_first_status": words[30],
            "restore_first_status2": words[31],
            "restore_first_cpu9_pwr_con": words[32],
            "restore_last_status": words[33],
            "restore_last_status2": words[34],
            "restore_last_cpu9_pwr_con": words[35],
        })
    return record


def decode(data: bytes, pre_boot_id: str, recovery_boot_id: str) -> dict[str, int]:
    before = canonical_uuid(pre_boot_id)
    after = canonical_uuid(recovery_boot_id)
    if before == after:
        raise DecodeError("recovery-boot-id-unchanged")
    payload, payload_bytes = payload_from_capture(data)
    records = [record for copy in range(COPIES)
               if (record := decode_copy(payload, copy, payload_bytes)) is not None]
    if not records:
        raise DecodeError("no-crc-valid-semantic-copy")
    if len(records) == 2:
        if records[0]["generation"] == records[1]["generation"]:
            raise DecodeError("ambiguous-equal-generation")
        if abs(records[0]["generation"] - records[1]["generation"]) != 1:
            raise DecodeError("noncontiguous-generations")
    for record in records:
        if record["copy"] != (record["generation"] - 1) % COPIES:
            raise DecodeError("copy-generation-parity-invalid")
    return max(records, key=lambda record: record["generation"])


def readback_mismatch_details(value: int) -> tuple[str, list[str]]:
    if not value & READBACK_BITMAP_V1:
        return "legacy-boolean", ["mismatch"] if value else []
    names = [name for bit, name in READBACK_MISMATCH_NAMES.items()
             if value & 1 << bit]
    return "bitmap-v1", names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-boot-id", required=True)
    parser.add_argument("--recovery-boot-id", required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = args.record.read_bytes()
        record = decode(data, args.pre_boot_id, args.recovery_boot_id)
    except (OSError, DecodeError) as exc:
        print(f"hotplug_ledger_decode=fail reason={exc}", file=sys.stderr)
        return 1
    print("hotplug_ledger_decode=pass")
    print("recovery_boot_id_changed=yes")
    print("remote_record_removal=no")
    print(f"copy={record['copy']}")
    print(f"version=0x{record['version']:08x}")
    print(f"generation={record['generation']}")
    print(f"stage={record['stage']}")
    stages = STAGES_V3 if record["version"] == VERSION_V3 else STAGES_V1_V2
    print(f"stage_name={stages[record['stage']]}")
    print(f"terminal={record['terminal']}")
    print(f"terminal_name={TERMINALS[record['terminal']]}")
    print(f"error={record['error']}")
    for name in (
        "session_id", "parent_generation", "parent_cookie",
        "watchdog_identity", "down_generation", "down_cookie",
        "restore_generation", "restore_cookie", "result_flags",
        "cpu_off_calls", "affinity_calls", "cpu8_ipi_calls",
        "cpu_on_calls", "online_mask", "members", "readback_mismatch",
    ):
        value = record[name]
        if name.endswith("_id") or name.endswith("_cookie") or name in {
            "watchdog_identity", "result_flags", "online_mask", "members",
            "readback_mismatch",
        }:
            print(f"{name}=0x{value:x}")
        else:
            print(f"{name}={value}")
    if "restore_readiness_samples" in record:
        for name in (
            "restore_readiness_samples", "restore_readiness_sleeps",
            "restore_readiness_error", "restore_readiness_flags",
            "restore_first_status", "restore_first_status2",
            "restore_first_cpu9_pwr_con", "restore_last_status",
            "restore_last_status2", "restore_last_cpu9_pwr_con",
        ):
            value = record[name]
            if name.endswith("flags") or "status" in name or "pwr_con" in name:
                print(f"{name}=0x{value:x}")
            else:
                print(f"{name}={value}")
    mismatch_format, mismatch_names = readback_mismatch_details(
        record["readback_mismatch"])
    print(f"readback_mismatch_format={mismatch_format}")
    print("readback_mismatch_names=" +
          (",".join(mismatch_names) if mismatch_names else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
