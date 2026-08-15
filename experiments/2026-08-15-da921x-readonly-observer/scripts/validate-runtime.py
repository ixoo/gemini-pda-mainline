#!/usr/bin/env python3
"""Classify one exact read-only DA921x observer netcat capture."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__DA921X_OBSERVER_RUNTIME_BEGIN__"
END = "__DA921X_OBSERVER_RUNTIME_END__"
DMESG_BEGIN = "__DA921X_OBSERVER_DMESG_BEGIN__"
DMESG_END = "__DA921X_OBSERVER_DMESG_END__"
CANDIDATE = "7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564"
RELEASE = "7.1.3-gemini-da921x-observer"
BOUND = re.compile(
    r"da921x-observer-v1 event=bound valid=(\d+) identity_reads=(\d+) "
    r"providers=(\d+) provider_read_attempts=(\d+) provider_read_completed=(\d+) "
    r"register_data_writes=(\d+) buck0_selector=(\d+) buck0_uv=(\d+) "
    r"buck0_enabled=(\d+) buck1_selector=(\d+) buck1_uv=(\d+) buck1_enabled=(\d+)"
)


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
    if finish < start:
        reject("rejected-attribution", "reversed-section")
    return text[start:finish].replace("\r", "")


def key_values(text: str) -> dict[str, str]:
    dmesg_start = text.find(DMESG_BEGIN)
    dmesg_end = text.find(DMESG_END)
    if dmesg_start < 0 or dmesg_end < dmesg_start:
        reject("rejected-attribution", "missing-dmesg-section")
    metadata = text[:dmesg_start] + text[dmesg_end + len(DMESG_END) :]
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
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", values.get("boot_id", "")):
        reject("rejected-attribution", "malformed-boot-id")
    if values.get("cpu_online") != "0-7" or values.get("cpu_offline") != "8-9":
        reject("rejected-safety", "cpu8-or-cpu9-admission-not-closed")
    for key in ("bound_marker_count", "cleanup_marker_count", "failure_marker_count"):
        if not re.fullmatch(r"\d+", values.get(key, "")):
            reject("rejected-attribution", f"malformed-{key}")

    bound_lines = [line for line in dmesg.splitlines() if "da921x-observer-v1 event=bound" in line]
    cleanup_lines = [
        line for line in dmesg.splitlines()
        if "da921x-observer-v1 event=unbind" in line
        or "da921x-observer-v1 event=failed-probe" in line
    ]
    failure_lines = [line for line in dmesg.splitlines() if "read-only observation failed" in line]
    if int(values["bound_marker_count"]) != len(bound_lines):
        reject("rejected-attribution", "bound-count-disagrees")
    if int(values["cleanup_marker_count"]) != len(cleanup_lines):
        reject("rejected-attribution", "cleanup-count-disagrees")
    if int(values["failure_marker_count"]) != len(failure_lines):
        reject("rejected-attribution", "failure-count-disagrees")

    for line in bound_lines + cleanup_lines:
        write = re.search(r"register_data_writes=(\d+)", line)
        if write and int(write.group(1)) != 0:
            reject("rejected-safety", "nonzero-register-data-writes")
    if cleanup_lines or failure_lines:
        reject("provider-failure", "failed-probe-cleanup-or-sampling-error")
    if not bound_lines:
        reject("service-failure", "no-observer-record")
    if len(bound_lines) != 1:
        reject("rejected-attribution", "non-unique-bound-record")

    match = BOUND.search(bound_lines[0])
    if not match:
        reject("rejected-attribution", "malformed-bound-record")
    numbers = [int(value) for value in match.groups()]
    fixed = numbers[:6]
    if fixed != [1, 14, 2, 4, 4, 0]:
        if fixed[5] != 0:
            reject("rejected-safety", "nonzero-register-data-writes")
        reject("rejected-attribution", "bound-counters-mismatch")
    for selector, microvolts, enabled in (numbers[6:9], numbers[9:12]):
        if not 0 <= selector <= 127 or microvolts != 300000 + selector * 10000:
            reject("rejected-attribution", "invalid-selector-voltage-pair")
        if microvolts > 1570000 or enabled not in (0, 1):
            reject("rejected-attribution", "invalid-buck-state")
    return "success-read-only-provider", "exact-bound-record"


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
    print(f"provider_observation={'accepted' if result == 'success-read-only-provider' else 'not-accepted'}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=read-only-native-provider-observation-only")
    return 0 if result == "success-read-only-provider" else 3


if __name__ == "__main__":
    raise SystemExit(main())
