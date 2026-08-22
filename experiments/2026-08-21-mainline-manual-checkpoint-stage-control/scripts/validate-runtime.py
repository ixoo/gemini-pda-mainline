#!/usr/bin/env python3
"""Classify the exact manual-checkpoint live-stage runtime probe."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__MANUAL_CHECKPOINT_STAGE_RUNTIME_BEGIN__"
END = "__MANUAL_CHECKPOINT_STAGE_RUNTIME_END__"
CANDIDATE = "43e7f44eeef694ef876f7686ae03e2a779a118141e7f9efa060ccc1182c8eac3"
RELEASE = "7.1.3-gemini-checkpoint-stage"
STAGES = (
    "sequence-refused",
    "dt-refused",
    "map-refused",
    "prefix-refused",
    "write-precondition-refused",
    "metadata-readback-refused",
    "payload-readback-refused",
    "success",
)
LIVE_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1 first=([01]) second=([01]) "
    r"retained_writes=([0-2]) protected_calls=0 cpu_requests=0"
)
STAGE_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_STAGE_V1 first=([01]) second=([01]) "
    r"stage=([a-z-]+) writes=([0-2]) protected=0 cpu=0"
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
        "cpu_online",
        "cpu_offline",
        "same_value_write_attributes",
        "clock_backend_devices",
        "bigidvfs_backend_devices",
        "protected_readback_devices",
        "manual_live_prefix_count",
        "manual_stage_prefix_count",
        "block_mounts",
        "device_storage_writes",
        "same_value_action_request",
        "protected_read_request",
        "secure_call_request",
        "owner_registration_request",
        "cpu_admission_request",
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

    live = LIVE_RE.fullmatch(values.get("manual_live_record", ""))
    stage = STAGE_RE.fullmatch(values.get("manual_stage_record", ""))
    if live is None or stage is None:
        reject("rejected-attribution", "malformed-live-or-stage-record")
    live_first, live_second, live_writes = map(int, live.groups())
    stage_first = int(stage.group(1))
    stage_second = int(stage.group(2))
    stage_value = stage.group(3)
    stage_writes = int(stage.group(4))
    if stage_value not in STAGES:
        reject("rejected-attribution", "unknown-stage")
    if (live_first, live_second, live_writes) != (
        stage_first,
        stage_second,
        stage_writes,
    ):
        reject("rejected-attribution", "boolean-stage-record-mismatch")
    if stage_second > stage_first or stage_writes != stage_first + stage_second:
        reject("rejected-attribution", "impossible-call-or-write-count")
    if stage_value == "success":
        if (stage_first, stage_second, stage_writes) != (1, 1, 2):
            reject("rejected-attribution", "success-count-mismatch")
    elif stage_second != 0:
        reject("rejected-attribution", "refusal-stage-with-second-success")
    return "manual-checkpoint-stage-pass", f"decision-stage-{stage_value}"


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
    accepted = result == "manual-checkpoint-stage-pass"
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"manual_checkpoint_stage={'accepted' if accepted else 'not-accepted'}")
    print("protected_calls=0")
    print("DA921x_register_data_writes=0")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=manual-checkpoint-stage-and-serviceability-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
