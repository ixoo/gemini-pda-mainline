#!/usr/bin/env python3
"""Classify one exact DA921x provider-only matched-control capture."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__DA921X_PROVIDER_CONTROL_RUNTIME_BEGIN__"
END = "__DA921X_PROVIDER_CONTROL_RUNTIME_END__"
DMESG_BEGIN = "__DA921X_PROVIDER_CONTROL_DMESG_BEGIN__"
DMESG_END = "__DA921X_PROVIDER_CONTROL_DMESG_END__"
CANDIDATE = "3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2"
RELEASE = "7.1.3-gemini-da921x-resource"
IDENTITY = "DA9214 legacy direct-address identity matched; provider is read-only"


class Classification(Exception):
    def __init__(self, result: str, reason: str) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason


def reject(result: str, reason: str) -> None:
    raise Classification(result, reason)


def section(text: str, begin: str, end: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        reject("rejected-attribution", f"non-unique-{begin.strip('_').lower()}")
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    return text[start:finish].replace("\r", "")


def key_values(runtime: str) -> dict[str, str]:
    start = runtime.find(DMESG_BEGIN)
    end = runtime.find(DMESG_END)
    if start < 0 or end < start:
        reject("rejected-attribution", "missing-dmesg-section")
    metadata = runtime[:start] + runtime[end + len(DMESG_END) :]
    values: dict[str, str] = {}
    for raw in metadata.splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in values:
            reject("rejected-attribution", "malformed-or-duplicate-key")
        values[key] = value
    return values


def classify_text(text: str) -> tuple[str, str]:
    runtime = section(text, BEGIN, END)
    dmesg = section(runtime, DMESG_BEGIN, DMESG_END)
    values = key_values(runtime)
    expected = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "hardware_write_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    for key, required in expected.items():
        if values.get(key) != required:
            reject("rejected-attribution", f"{key}-mismatch")
    if not re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", values.get("boot_id", "")
    ):
        reject("rejected-attribution", "malformed-boot-id")
    if values.get("cpu_online") != "0-7" or values.get("cpu_offline") != "8-9":
        reject("rejected-safety", "cpu8-or-cpu9-admission-not-closed")
    for key in ("provider_identity_count", "provider_failure_count", "observer_marker_count"):
        if not re.fullmatch(r"\d+", values.get(key, "")):
            reject("rejected-attribution", f"malformed-{key}")
    identity_lines = [line for line in dmesg.splitlines() if IDENTITY in line]
    failure_lines = [
        line for line in dmesg.splitlines()
        if "read-only identity transcript failed" in line
        or "failed to register read-only provider" in line
    ]
    observer_lines = [line for line in dmesg.splitlines() if "da921x-observer-v1" in line]
    if int(values["provider_identity_count"]) != len(identity_lines):
        reject("rejected-attribution", "identity-count-disagrees")
    if int(values["provider_failure_count"]) != len(failure_lines):
        reject("rejected-attribution", "failure-count-disagrees")
    if int(values["observer_marker_count"]) != len(observer_lines):
        reject("rejected-attribution", "observer-count-disagrees")
    if observer_lines:
        reject("rejected-control", "observer-marker-present")
    if failure_lines:
        reject("provider-control-failure", "provider-probe-failure")
    if len(identity_lines) != 1:
        reject("provider-control-failure", "non-unique-provider-identity")
    if values.get("bound_i2c_paths") != "1-0068":
        reject("provider-control-failure", "provider-driver-binding-missing")
    if set(values.get("regulator_names", "").split()) != {
        "DA9213-legacy-BUCK0", "DA9213-legacy-BUCK1"
    }:
        reject("provider-control-failure", "read-only-regulator-pair-missing")
    return "success-provider-only-control", "exact-provider-control-serviceable"


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
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"matched_control={'accepted' if result == 'success-provider-only-control' else 'not-accepted'}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=provider-only-serviceability-control")
    return 0 if result == "success-provider-only-control" else 3


if __name__ == "__main__":
    raise SystemExit(main())
