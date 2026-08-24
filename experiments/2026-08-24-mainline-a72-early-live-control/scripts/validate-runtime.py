#!/usr/bin/env python3
"""Classify one exact A72 early-initcall Stage-27-DTB live capture."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__A72_EARLY_LIVE_CONTROL_BEGIN__"
END = "__A72_EARLY_LIVE_CONTROL_END__"
MARKERS_BEGIN = "__A72_EARLY_MARKERS_BEGIN__"
MARKERS_END = "__A72_EARLY_MARKERS_END__"
CANDIDATE = "070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef"
RELEASE = "7.1.3-gemini-a72-early"
PURE = "GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f"
CORE = "GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5"
REFUSAL = "GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=primary-refused slot=2 crc32=5767e326"


class Classification(Exception):
    def __init__(self, result: str, reason: str) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason


def reject(result: str, reason: str) -> None:
    raise Classification(result, reason)


def classify_text(text: str) -> tuple[str, str, str, dict[str, int]]:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        reject("rejected-attribution", "non-unique-runtime-section")
    start = text.index(BEGIN) + len(BEGIN)
    finish = text.index(END, start)
    section = text[start:finish].replace("\r", "")
    if section.count(MARKERS_BEGIN) != 1 or section.count(MARKERS_END) != 1:
        reject("rejected-attribution", "non-unique-marker-section")
    marker_start = section.index(MARKERS_BEGIN) + len(MARKERS_BEGIN)
    marker_finish = section.index(MARKERS_END, marker_start)
    marker_text = section[marker_start:marker_finish]
    scalar_text = section[: section.index(MARKERS_BEGIN)] + section[marker_finish + len(MARKERS_END) :]

    values: dict[str, str] = {}
    for raw in scalar_text.splitlines():
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
        "compatible": "planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "maxcpus8_tokens": "1",
        "udc_devices": "1",
        "block_mounts": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "regulator_action_request": "none",
        "clock_action_request": "none",
        "secure_call_request": "none",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    safety_keys = {
        "cpu_online",
        "cpu_offline",
        "maxcpus8_tokens",
        "block_mounts",
        "device_partition_reads",
        "device_storage_writes",
        "regulator_action_request",
        "clock_action_request",
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
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", values.get("boot_id", "")
    ):
        reject("rejected-attribution", "malformed-boot-id")
    if not re.fullmatch(r"\d+(?:\.\d+)?", values.get("uptime_seconds", "")):
        reject("rejected-attribution", "malformed-uptime")
    if not re.fullmatch(r"\d+", values.get("pstore_files", "")):
        reject("rejected-attribution", "malformed-pstore-count")

    counts = {"pure": marker_text.count(PURE), "core": marker_text.count(CORE), "refusal": marker_text.count(REFUSAL)}
    present = {key for key, count in counts.items() if count}
    if "core" in present and "pure" not in present:
        reject("rejected-ledger", "core-without-pure")
    if "core" in present and "refusal" in present:
        reject("rejected-ledger", "conflicting-core-and-refusal")
    if present == {"pure", "core"}:
        ledger = "pure-plus-core-live"
    elif present == {"pure", "refusal"}:
        ledger = "pure-plus-primary-refusal-live"
    elif present == {"pure"}:
        ledger = "pure-only-live"
    elif present == {"refusal"}:
        ledger = "primary-refusal-only-live"
    elif not present:
        ledger = "no-early-record-exposed-live"
    else:
        reject("rejected-ledger", "unsupported-marker-combination")
    return "serviceable-stage27-control-pass", "exact-live-identity-through-init", ledger, counts


def classify(path: Path) -> tuple[str, str, str, dict[str, int]]:
    try:
        return classify_text(path.read_text(encoding="utf-8", errors="replace"))
    except Classification as result:
        return result.result, result.reason, "not-classified", {"pure": 0, "core": 0, "refusal": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result, reason, ledger, counts = classify(args.capture)
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts['pure']}")
    print(f"core_marker_matches={counts['core']}")
    print(f"refusal_marker_matches={counts['refusal']}")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if result == "serviceable-stage27-control-pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
