#!/usr/bin/env python3
"""Classify the exact manual-checkpoint live prefix-reason probe."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__MANUAL_CHECKPOINT_PREFIX_RUNTIME_BEGIN__"
END = "__MANUAL_CHECKPOINT_PREFIX_RUNTIME_END__"
CANDIDATE = "ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901"
RELEASE = "7.1.3-gemini-checkpoint-prefix"
SIGNATURE = "43474244"
REASONS = ("bad-signature", "nonzero-start", "nonzero-size", "unstable-or-other")
LIVE_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1 first=([01]) second=([01]) "
    r"retained_writes=([0-2]) protected_calls=0 cpu_requests=0"
)
STAGE_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_STAGE_V1 first=([01]) second=([01]) "
    r"stage=([a-z-]+) writes=([0-2]) protected=0 cpu=0"
)
REASON_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_PREFIX_V1 cp=(\d+) slot=(\d+) "
    r"why=([a-z-]+) hdr=([0-9a-f]{8})/(\d+)/(\d+) reads=(\d+)"
)


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
        "clock_backend_devices": "0",
        "bigidvfs_backend_devices": "0",
        "protected_readback_devices": "0",
        "manual_live_prefix_count": "1",
        "manual_stage_prefix_count": "1",
        "manual_reason_prefix_count": "1",
        "block_mounts": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "same_value_action_request": "none",
        "protected_read_request": "none",
        "secure_call_request": "none",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    safety_keys = {
        "cpu_online", "cpu_offline", "same_value_write_attributes",
        "clock_backend_devices", "bigidvfs_backend_devices",
        "protected_readback_devices", "manual_live_prefix_count",
        "manual_stage_prefix_count", "manual_reason_prefix_count",
        "block_mounts", "device_storage_writes", "same_value_action_request",
        "protected_read_request", "secure_call_request",
        "owner_registration_request", "cpu_admission_request", "reboot_request",
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

    live = LIVE_RE.fullmatch(values.get("manual_live_record", ""))
    stage = STAGE_RE.fullmatch(values.get("manual_stage_record", ""))
    reason = REASON_RE.fullmatch(values.get("manual_reason_record", ""))
    if live is None or stage is None or reason is None:
        reject("rejected-attribution", "malformed-live-stage-or-reason-record")
    if tuple(map(int, live.groups())) != (0, 0, 0):
        reject("rejected-attribution", "historical-prefix-refusal-count-mismatch")
    if (int(stage.group(1)), int(stage.group(2)), stage.group(3), int(stage.group(4))) != (
        0, 0, "prefix-refused", 0
    ):
        reject("rejected-attribution", "fixed-stage-mismatch")

    checkpoint, slot = int(reason.group(1)), int(reason.group(2))
    why, signature = reason.group(3), reason.group(4)
    header_start, header_size, reads = map(int, reason.groups()[4:])
    if checkpoint != 0 or slot not in range(4) or why not in REASONS or reads != 3:
        reject("rejected-attribution", "prefix-reason-contract-mismatch")
    consistent = {
        "bad-signature": signature != SIGNATURE,
        "nonzero-start": signature == SIGNATURE and header_start != 0,
        "nonzero-size": signature == SIGNATURE and header_start == 0 and header_size != 0,
        "unstable-or-other": signature == SIGNATURE and header_start == 0 and header_size == 0,
    }[why]
    if not consistent:
        reject("rejected-attribution", "prefix-reason-header-mismatch")
    return "manual-checkpoint-prefix-pass", f"decision-prefix-{why}"


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
    accepted = result == "manual-checkpoint-prefix-pass"
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"manual_checkpoint_prefix={'accepted' if accepted else 'not-accepted'}")
    print("retained_header_reads=3")
    print("protected_calls=0")
    print("DA921x_register_data_writes=0")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=manual-checkpoint-prefix-reason-and-serviceability-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
