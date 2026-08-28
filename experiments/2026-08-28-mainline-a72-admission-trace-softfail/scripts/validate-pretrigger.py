#!/usr/bin/env python3
"""Validate the durable live frame before the trace-softfail CPU8 trigger."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__GEMINI_A72_LIVE_PRETRIGGER_BEGIN__"
END = "__GEMINI_A72_LIVE_PRETRIGGER_END__"
CANDIDATE = "83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0"
RELEASE = "7.1.3-gemini-a72-admission-softtrace"
ARMED = ("GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
         "trigger_executions=0 operation_ret=-115 core_consumed=0 "
         "entry_trace_ret=0 terminal_trace_ret=0 cpu_requests=0 "
         "cpu9_requests=0 cpu_off_requests=0 retries=0")


class Classification(RuntimeError):
    """A live frame failed attribution or safety validation."""


def values(text: str) -> dict[str, str]:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise Classification("non-unique-pretrigger-frame")
    section = text[text.index(BEGIN) + len(BEGIN):text.index(END)].replace("\r", "")
    result: dict[str, str] = {}
    for raw in section.splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in result:
            raise Classification("malformed-or-duplicate-key")
        result[key] = value
    return result


def classify(text: str) -> tuple[str, str]:
    observed = values(text)
    expected = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "model": "MT6797X",
        "compatible": "planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible": "0-9", "cpu_present": "0-9",
        "cpu_online": "0-7", "cpu_offline": "8-9",
        "maxcpus8_tokens": "1", "udc_devices": "1", "block_mounts": "0",
        "controller_devices": "1", "controller_bound": "1",
        "group_present": "1", "status_mode": "444", "status_uid": "0",
        "trigger_mode": "200", "trigger_uid": "0", "live_status": ARMED,
        "device_partition_reads": "none", "device_storage_writes": "none",
        "sysfs_write_request": "none", "supplier_resolution_request": "none",
        "cpu_admission_request": "none", "cpu_off_request": "none",
        "retry_request": "none", "reboot_request": "none",
    }
    for key, required in expected.items():
        if observed.get(key) != required:
            raise Classification(f"{key}-mismatch")
    if "ro" not in observed.get("sysfs_options", "").split(","):
        raise Classification("sysfs-not-read-only")
    boot_id = observed.get("boot_id", "")
    if re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot_id) is None:
        raise Classification("boot-id-malformed")
    if re.fullmatch(r"\d+(?:\.\d+)?", observed.get("uptime_seconds", "")) is None:
        raise Classification("uptime-malformed")
    return "serviceable-armed-zero-execution", boot_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, boot_id = classify(args.capture.read_text(encoding="utf-8", errors="replace"))
        reason = "exact-softtrace-identity-and-armed-contract"
    except Classification as error:
        result, boot_id, reason = "rejected", "unknown", str(error)
    print(f"pretrigger_classification={result}")
    print(f"pretrigger_reason={reason}")
    print(f"boot_id={boot_id}")
    print("trigger_executions=0")
    print("cpu8_requests=0")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    return 0 if result == "serviceable-armed-zero-execution" else 3


if __name__ == "__main__":
    raise SystemExit(main())
