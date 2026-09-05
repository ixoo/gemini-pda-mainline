#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify one eMMC read frame; baseline/log/recovery acceptance stays separate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

BEGIN = "__GEMINI_EMMC_READONLY_BEGIN__"
END = "__GEMINI_EMMC_READONLY_END__"
SHA = re.compile(r"[0-9a-f]{64}")
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
FIELDS = {
    "boot_id", "kernel_release", "expected_sha256", "busybox_sha256",
    "target", "target_major_minor", "target_start_sector", "read_attempts",
    "requested_bytes", "read_timeout_seconds", "dd_status", "read_sha256",
    "elapsed_seconds", "controller_error_count", "kernel_log_before_sha256",
    "kernel_log_after_sha256", "guards_after", "device_storage_writes",
    "mount_requests", "sysfs_writes",
}


def classify(text: str, boot: str, release: str, padded_sha: str, busybox_sha: str) -> dict:
    """Never label the complete experiment passed from this frame alone."""
    result = {"classification": "inconclusive", "reason": "incomplete-frame"}
    if not UUID.fullmatch(boot) or not re.fullmatch(r"[A-Za-z0-9_.+-]+", release):
        return result | {"reason": "invalid-expected-identity"}
    if not SHA.fullmatch(padded_sha) or not SHA.fullmatch(busybox_sha):
        return result | {"reason": "invalid-expected-digest"}
    lines = text.splitlines()
    if not lines or lines[0] != BEGIN or lines[-1] != END:
        return result
    values = {}
    for line in lines[1:-1]:
        if "=" not in line:
            return result | {"reason": "malformed-frame"}
        key, value = line.split("=", 1)
        if key not in FIELDS or key in values or not value:
            return result | {"reason": "unknown-duplicate-or-empty-field"}
        values[key] = value
    if set(values) != FIELDS:
        return result | {"reason": "missing-fields"}
    for field, expected in {
        "boot_id": boot, "kernel_release": release, "expected_sha256": padded_sha,
        "busybox_sha256": busybox_sha, "read_attempts": "1", "requested_bytes": "16777216",
        "read_timeout_seconds": "20", "guards_after": "pass",
        "device_storage_writes": "none", "mount_requests": "none", "sysfs_writes": "none",
    }.items():
        if values[field] != expected:
            return result | {"reason": f"identity-or-contract-{field}"}
    if not re.fullmatch(r"/dev/mmcblk0p[1-9][0-9]*", values["target"]):
        return result | {"reason": "target"}
    if not re.fullmatch(r"179:(?:0|[1-9][0-9]*)", values["target_major_minor"]):
        return result | {"reason": "target-number"}
    for field in ("target_start_sector", "elapsed_seconds", "dd_status", "controller_error_count"):
        if not re.fullmatch(r"0|[1-9][0-9]*", values[field]):
            return result | {"reason": f"malformed-{field}"}
    if int(values["target_major_minor"].split(":")[1]) > 1048575:
        return result | {"reason": "target-number-range"}
    if not 1 <= int(values["target_start_sector"]) <= 122109952:
        return result | {"reason": "target-range"}
    for field in ("read_sha256", "kernel_log_before_sha256", "kernel_log_after_sha256"):
        if not SHA.fullmatch(values[field]):
            return result | {"reason": f"malformed-{field}"}
    if int(values["elapsed_seconds"]) > 20:
        return result | {"reason": "deadline-exceeded"}
    if values["dd_status"] == "137":
        return result | {"reason": "read-timeout-or-kill"}
    if values["dd_status"] != "0":
        return result | {"classification": "fail", "reason": "read-command-failed"}
    if int(values["controller_error_count"]):
        return result | {"classification": "fail", "reason": "controller-error"}
    if values["read_sha256"] != padded_sha:
        return result | {"classification": "fail", "reason": "readback-mismatch"}
    return {
        "classification": "read-integrity-pass",
        "reason": "requires-independent-log-serviceability-and-recovery-acceptance",
        "boot_id": boot,
        "candidate_padded_sha256": padded_sha,
        "observation_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "requested_bytes": 16777216,
        "attempts_consumed": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--boot-id", required=True)
    parser.add_argument("--kernel-release", required=True)
    parser.add_argument("--padded-sha256", required=True)
    parser.add_argument("--busybox-sha256", required=True)
    args = parser.parse_args()
    if args.capture.stat().st_size > 8192:
        result = {"classification": "inconclusive", "reason": "oversized-frame"}
    else:
        try:
            result = classify(args.capture.read_text(encoding="ascii"), args.boot_id,
                              args.kernel_release, args.padded_sha256, args.busybox_sha256)
        except UnicodeError:
            result = {"classification": "inconclusive", "reason": "non-ascii-frame"}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["classification"] == "read-integrity-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
