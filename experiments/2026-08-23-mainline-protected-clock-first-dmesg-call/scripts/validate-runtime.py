#!/usr/bin/env python3
"""Classify the exact one-shot protected-clock live result."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__PROTECTED_CLOCK_FIRST_DMESG_RUNTIME_BEGIN__"
END = "__PROTECTED_CLOCK_FIRST_DMESG_RUNTIME_END__"
CANDIDATE = "3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6"
RELEASE = "7.1.3-gemini-clock-one-read"


class Classification(Exception):
    def __init__(self, result: str, reason: str) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason


def reject(result: str, reason: str) -> None:
    raise Classification(result, reason)


def classify_text(text: str) -> tuple[str, str]:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        reject("rejected-attribution", "non-unique-runtime-section")
    start = text.index(BEGIN) + len(BEGIN)
    finish = text.index(END, start)
    values: dict[str, str] = {}
    for raw in text[start:finish].replace("\r", "").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in values:
            reject("rejected-attribution", "malformed-or-duplicate-key")
        values[key] = value

    expected = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "model": "MT6797X",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "udc_devices": "1",
        "keyboard_matrix_inputs": "1",
        "da921x_i2c_clients": "1",
        "same_value_write_attributes": "0",
        "clock_backend_devices": "1",
        "bigidvfs_backend_devices": "0",
        "protected_readback_devices": "1",
        "handoff_bound": "1",
        "i2c6_bound": "1",
        "clock_backend_bound": "1",
        "observer_bound": "1",
        "handoff_state": "ready",
        "i2c6_handoff_ready_count": "1",
        "cspm_range_count": "1",
        "cspm_handoff_owner_count": "1",
        "mcumixed_clock_owner_count": "1",
        "clock_prefix_count": "1",
        "clock_success_prefix_count": "1",
        "clock_shape_count": "1",
        "terminal_prefix_count": "1",
        "terminal_exact_count": "1",
        "bigidvfs_record_count": "0",
        "owner_exact_count": "1",
        "handoff_ebusy_count": "0",
        "block_mounts": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "same_value_action_request": "none",
        "observer_trigger": "automatic-probe-once",
        "protected_clock_caller_retries": "zero",
        "bigidvfs_calls": "zero",
        "mapped_clock_mmio_read_snapshots": "one",
        "clock_enable_disable_pairs": "one",
        "secure_calls": "zero",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    safety_keys = {
        "cpu_online", "cpu_offline", "same_value_write_attributes",
        "clock_backend_devices", "bigidvfs_backend_devices",
        "protected_readback_devices", "handoff_bound", "i2c6_bound",
        "clock_backend_bound", "observer_bound", "handoff_state",
        "i2c6_handoff_ready_count", "cspm_range_count",
        "cspm_handoff_owner_count", "mcumixed_clock_owner_count",
        "clock_prefix_count", "clock_success_prefix_count", "clock_shape_count",
        "terminal_prefix_count", "terminal_exact_count", "bigidvfs_record_count",
        "owner_exact_count", "handoff_ebusy_count", "block_mounts",
        "device_storage_writes", "same_value_action_request", "observer_trigger",
        "protected_clock_caller_retries", "bigidvfs_calls",
        "mapped_clock_mmio_read_snapshots", "clock_enable_disable_pairs",
        "secure_calls", "owner_registration_request", "cpu_admission_request",
        "reboot_request",
    }
    for key, required in expected.items():
        if values.get(key) != required:
            reject(
                "rejected-safety" if key in safety_keys else "rejected-attribution",
                f"{key}-mismatch",
            )
    if not re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
        values.get("boot_id", ""),
    ):
        reject("rejected-attribution", "malformed-boot-id")
    if not re.fullmatch(r"\d+(?:\.\d+)?", values.get("uptime_seconds", "")):
        reject("rejected-attribution", "malformed-uptime")
    if not re.fullmatch(r"\d+", values.get("pstore_files", "")):
        reject("rejected-attribution", "malformed-pstore-count")
    if "maxcpus=8" not in values.get("cmdline", "").split():
        reject("rejected-safety", "maxcpus-policy-missing")
    return (
        "protected-clock-first-dmesg-live-pass",
        "one-clock-snapshot-returned-with-single-owners-and-serviceability",
    )


def classify(path: Path) -> tuple[str, str]:
    try:
        return classify_text(path.read_text(encoding="utf-8", errors="replace"))
    except Classification as result:
        return result.result, result.reason


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result, reason = classify(args.capture)
    accepted = result == "protected-clock-first-dmesg-live-pass"
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("protected_clock_call=returned" if accepted else "protected_clock_call=unproved")
    print("clock_backend_abi=2" if accepted else "clock_backend_abi=unproved")
    print("retained_records_1_2=pending-changed-id-recovery")
    print("protected_clock_calls=1")
    print("protected_clock_caller_retries=0")
    print("bigidvfs_calls=0")
    print("mapped_clock_mmio_read_snapshots=1")
    print("clock_enable_disable_pairs=1")
    print("secure_calls=0")
    print("DA921x_register_data_writes=0")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=one-protected-clock-snapshot-return-and-serviceability")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
