#!/usr/bin/env python3
"""Classify one exact clock-backend entry-ledger netcat capture."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__CLOCK_BACKEND_ENTRY_RUNTIME_BEGIN__"
END = "__CLOCK_BACKEND_ENTRY_RUNTIME_END__"
CANDIDATE = "444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de"
RELEASE = "7.1.3-gemini-clock-backend-entry-ledger"
MODEL = "Planet Computers Gemini PDA (clock backend entry ledger)"


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
    runtime = text[start:finish].replace("\r", "")
    values: dict[str, str] = {}
    for raw in runtime.splitlines():
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
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "model": MODEL,
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "protected_read_request": "none",
        "secure_call_request": "none",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    for key, required in expected.items():
        if values.get(key) != required:
            result = (
                "rejected-safety"
                if key in {"cpu_online", "cpu_offline"}
                else "rejected-attribution"
            )
            reject(result, f"{key}-mismatch")
    if not re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
        values.get("boot_id", ""),
    ):
        reject("rejected-attribution", "malformed-boot-id")
    if not re.fullmatch(r"\d+(?:\.\d+)?", values.get("uptime_seconds", "")):
        reject("rejected-attribution", "malformed-uptime")
    if "maxcpus=8" not in values.get("cmdline", "").split():
        reject("rejected-safety", "maxcpus-policy-missing")
    return "serviceable-clock-entry-runtime", "exact-read-free-runtime-identity"


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
    print(
        "clock_entry_runtime="
        f"{'accepted' if result == 'serviceable-clock-entry-runtime' else 'not-accepted'}"
    )
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=clock-entry-serviceability-only-retained-records-after-cycle")
    return 0 if result == "serviceable-clock-entry-runtime" else 3


if __name__ == "__main__":
    raise SystemExit(main())
