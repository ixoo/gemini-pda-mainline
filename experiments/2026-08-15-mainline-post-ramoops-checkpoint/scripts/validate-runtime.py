#!/usr/bin/env python3
"""Classify one exact post-ramoops checkpoint USB capture."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__POST_RAMOOPS_CHECKPOINT_RUNTIME_BEGIN__"
END = "__POST_RAMOOPS_CHECKPOINT_RUNTIME_END__"
DMESG_BEGIN = "__POST_RAMOOPS_CHECKPOINT_DMESG_BEGIN__"
DMESG_END = "__POST_RAMOOPS_CHECKPOINT_DMESG_END__"
CANDIDATE = "ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348"
RELEASE = "7.1.3-gemini-postram-a"
MARKER = "GEMINI_MAINLINE_POST_RAMOOPS_20260815_A"


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
    if values.get("checkpoint_marker_count") != "1":
        reject("checkpoint-failure", "non-unique-checkpoint-marker-count")
    if sum(MARKER in line for line in dmesg.splitlines()) != 1:
        reject("checkpoint-failure", "non-unique-checkpoint-marker-record")
    if "da921x-observer-v1" in dmesg:
        reject("rejected-control", "observer-marker-present")
    return "success-post-ramoops-checkpoint", "exact-kernel-reached-ramoops-registration"


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
    print(f"post_ramoops_checkpoint={'accepted' if result == 'success-post-ramoops-checkpoint' else 'not-accepted'}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=post-ramoops-localization-only")
    return 0 if result == "success-post-ramoops-checkpoint" else 3


if __name__ == "__main__":
    raise SystemExit(main())
