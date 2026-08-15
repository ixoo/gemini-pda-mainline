#!/usr/bin/env python3
"""Classify one direct-USB runtime capture for the provenance observer."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


EXPECTED_KERNEL = "3.18.79-gemini-provenance-observer+"
EXPECTED_CANDIDATE = "ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02"
BEGIN = "__GEMINI_PROVENANCE_RUNTIME_BEGIN__"
END = "__GEMINI_PROVENANCE_RUNTIME_END__"
SNAPSHOT_KEYS = {
    "abi",
    "state",
    "observation_complete",
    "variant_id",
    "observer_generation",
    "table_epoch",
    "calibration_handle",
    "ppm_expected_cluster_count",
    "ppm_cluster_mask",
    "eem_required_bank_mask",
    "eem_calibration_bank_mask",
    "table_commit_count",
    "calibration_bank_publish_count",
    "calibration_publish_count",
    "calibration_invalidate_count",
    "owner_handle",
    "transition_handle",
    "coherent_transition_owner",
    "provider",
    "hardware_write",
    "cpu8_cpu9_admission",
}
OUTER_KEYS = {
    "installed_full_sha256",
    "kernel_release",
    "architecture",
    "boot_id",
    "cpu_possible",
    "cpu_present",
    "cpu_online",
    "state_path",
    "state_access",
    "state_mode",
    "device_partition_reads",
    "device_storage_writes",
    "hardware_write",
    "reboot_request",
}


class Classification(Exception):
    def __init__(self, result: str, reason: str, code: int) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason
        self.code = code


def normalize(raw: str) -> list[str]:
    lines: list[str] = []
    for raw_line in raw.replace("\r", "").splitlines():
        line = re.sub(r"^(?:GEMINI-AC-USB# )+", "", raw_line)
        lines.append(line)
    return lines


def unique_region(lines: list[str], begin: str, end: str) -> list[str]:
    starts = [index for index, line in enumerate(lines) if line == begin]
    stops = [index for index, line in enumerate(lines) if line == end]
    if len(starts) != 1 or len(stops) != 1 or starts[0] >= stops[0]:
        raise Classification("service-failure", f"missing-or-duplicate-region:{begin}", 4)
    return lines[starts[0] + 1 : stops[0]]


def parse_records(lines: list[str], allowed: set[str] | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([a-z0-9_]+)=([^\n]+)", line)
        if match is None:
            continue
        key, value = match.groups()
        if allowed is not None and key not in allowed:
            continue
        if key in result:
            raise Classification("rejected-attribution", f"duplicate-key:{key}", 5)
        result[key] = value
    return result


def unsigned(records: dict[str, str], key: str) -> int:
    value = records.get(key, "")
    if not re.fullmatch(r"[0-9]+", value):
        raise Classification("rejected-attribution", f"malformed-integer:{key}", 5)
    return int(value)


def classify(path: Path) -> tuple[str, str]:
    if not path.is_file() or path.is_symlink():
        raise Classification("service-failure", "capture-missing-or-unsafe", 4)
    lines = normalize(path.read_text(errors="strict"))
    body = unique_region(lines, BEGIN, END)
    outer_lines: list[str] = []
    in_snapshot = False
    for line in body:
        if re.fullmatch(r"__GEMINI_PROVENANCE_SNAPSHOT_[12]_BEGIN__", line):
            in_snapshot = True
        elif re.fullmatch(r"__GEMINI_PROVENANCE_SNAPSHOT_[12]_END__", line):
            in_snapshot = False
        elif not in_snapshot:
            outer_lines.append(line)
    outer = parse_records(outer_lines, OUTER_KEYS)

    identity = {
        "kernel_release": EXPECTED_KERNEL,
        "architecture": "aarch64",
        "state_path": "/sys/kernel/debug/gemini_dvfsp_provenance/state",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "reboot_request": "none",
    }
    for key, expected in identity.items():
        if outer.get(key) != expected:
            raise Classification("rejected-attribution", f"identity-mismatch:{key}", 5)
    if outer.get("installed_full_sha256") != EXPECTED_CANDIDATE:
        raise Classification("rejected-attribution", "candidate-identity-mismatch", 5)
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", outer.get("boot_id", "")):
        raise Classification("rejected-attribution", "malformed-boot-id", 5)
    if outer.get("state_access") != "readable":
        raise Classification("service-failure", "observer-state-unavailable", 4)
    if outer.get("state_mode") != "444":
        raise Classification("rejected-safety", "observer-state-not-mode-0444", 5)

    for key, expected in {
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "hardware_write": "none",
    }.items():
        if outer.get(key) != expected:
            raise Classification("rejected-safety", f"serviceability-or-write-mismatch:{key}", 5)

    first_lines = unique_region(
        body,
        "__GEMINI_PROVENANCE_SNAPSHOT_1_BEGIN__",
        "__GEMINI_PROVENANCE_SNAPSHOT_1_END__",
    )
    second_lines = unique_region(
        body,
        "__GEMINI_PROVENANCE_SNAPSHOT_2_BEGIN__",
        "__GEMINI_PROVENANCE_SNAPSHOT_2_END__",
    )
    first = parse_records(first_lines, SNAPSHOT_KEYS)
    second = parse_records(second_lines, SNAPSHOT_KEYS)
    if set(first) != SNAPSHOT_KEYS or set(second) != SNAPSHOT_KEYS:
        raise Classification("rejected-attribution", "snapshot-inventory-mismatch", 5)

    nonclaims = {
        "owner_handle": "0",
        "transition_handle": "0",
        "coherent_transition_owner": "0",
        "provider": "none",
        "hardware_write": "none",
        "cpu8_cpu9_admission": "closed",
    }
    for snapshot in (first, second):
        for key, expected in nonclaims.items():
            if snapshot.get(key) != expected:
                raise Classification("rejected-safety", f"nonclaim-violated:{key}", 5)
        if snapshot.get("abi") != "1":
            raise Classification("rejected-attribution", "observer-abi-mismatch", 5)
        if snapshot.get("state") == "fault":
            raise Classification("rejected-safety", "observer-reported-fault", 5)

    if first != second:
        raise Classification("inconclusive", "two-snapshots-not-stable", 3)

    incomplete_reasons: list[str] = []
    if first["state"] != "available" or first["observation_complete"] != "1":
        incomplete_reasons.append("observer-not-complete")
    for key in ("variant_id", "observer_generation", "table_epoch", "calibration_handle"):
        if unsigned(first, key) == 0:
            incomplete_reasons.append(f"zero-{key}")
    if unsigned(first, "ppm_expected_cluster_count") != 3:
        incomplete_reasons.append("unexpected-cluster-count")
    if first["ppm_cluster_mask"] != "0x00000007":
        incomplete_reasons.append("incomplete-ppm-mask")
    if first["eem_required_bank_mask"] != "0x0000003b" or first["eem_calibration_bank_mask"] != "0x0000003b":
        incomplete_reasons.append("incomplete-eem-mask")
    if unsigned(first, "table_commit_count") < 3:
        incomplete_reasons.append("insufficient-table-commits")
    if unsigned(first, "calibration_bank_publish_count") < 5:
        incomplete_reasons.append("insufficient-bank-publications")
    if unsigned(first, "calibration_publish_count") < 1:
        incomplete_reasons.append("missing-calibration-publication")
    unsigned(first, "calibration_invalidate_count")
    if incomplete_reasons:
        raise Classification("inconclusive", ",".join(incomplete_reasons), 3)
    return "success", "stable-complete-read-only-lifecycle-publication"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason = classify(args.capture)
        code = 0
    except Classification as outcome:
        result, reason, code = outcome.result, outcome.reason, outcome.code
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=vendor-ppm-eem-lifecycle-publication-only")
    return code


if __name__ == "__main__":
    sys.exit(main())
