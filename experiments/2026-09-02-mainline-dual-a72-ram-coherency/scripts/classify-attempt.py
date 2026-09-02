#!/usr/bin/env python3
"""Classify one bounded CPU8/CPU9 RAM-backed integrity transcript."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BEGIN = "__GEMINI_A72_RAM_COHERENCY_BEGIN__"
END = "__GEMINI_A72_RAM_COHERENCY_END__"
PAYLOAD_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
PAYLOAD_SIZE = "1914704"


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"error: {message}")


def fields_from_capture(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace").replace("\r", "")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        fail("capture does not contain one complete bounded probe frame")
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    fields: dict[str, str] = {}
    for line in body.splitlines():
        match = re.fullmatch(r"([a-z0-9_]+)=(.*)", line.strip())
        if not match:
            continue
        key, value = match.groups()
        if key in fields:
            fail(f"duplicate field: {key}")
        fields[key] = value
    return fields


def require_exact(fields: dict[str, str], key: str, value: str) -> None:
    if fields.get(key) != value:
        fail(f"{key} changed: expected {value!r}, got {fields.get(key)!r}")


def parse_stat(fields: dict[str, str], key: str, cpu: int) -> list[int]:
    value = fields.get(key, "")
    match = re.fullmatch(rf"cpu{cpu}(?: [0-9]+){{10}}", value)
    if not match:
        fail(f"{key} is malformed")
    return [int(item) for item in value.split()[1:]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--boot-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", args.boot_id):
        fail("expected boot ID is malformed")

    fields = fields_from_capture(args.capture)
    exact = {
        "boot_id": args.boot_id,
        "kernel_release": "7.1.3-gemini-cpu9-progress",
        "cpu_online": "0-9",
        "cpu_offline": "",
        "root_entries": "1",
        "root_source": "rootfs",
        "root_fstype": "rootfs",
        "run_mount_entries": "0",
        "block_mounts": "0",
        "cpu8_core_siblings": "8-9",
        "cpu9_core_siblings": "8-9",
        "cpu8_thread_siblings": "8",
        "cpu9_thread_siblings": "9",
        "cpu8_affinity": "8",
        "cpu9_affinity": "9",
        "cpu8_processor": "8",
        "cpu9_processor": "9",
        "source_cpu8_sha256": PAYLOAD_SHA256,
        "source_cpu9_sha256": PAYLOAD_SHA256,
        "file8_size": PAYLOAD_SIZE,
        "file8_writer_cpu8_sha256": PAYLOAD_SHA256,
        "file8_reader_cpu9_sha256": PAYLOAD_SHA256,
        "file9_size": PAYLOAD_SIZE,
        "file9_writer_cpu9_sha256": PAYLOAD_SHA256,
        "file9_reader_cpu8_sha256": PAYLOAD_SHA256,
        "cleanup_file8": "absent",
        "cleanup_file9": "absent",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
        "probe_result": "pass",
    }
    for key, value in exact.items():
        require_exact(fields, key, value)
    if "probe_failure" in fields:
        fail("probe reported a failure")

    numeric = ("cpu8_core_id", "cpu9_core_id", "cpu8_package_id", "cpu9_package_id")
    for key in numeric:
        if not re.fullmatch(r"-?[0-9]+", fields.get(key, "")):
            fail(f"{key} is missing or non-numeric")
    if fields["cpu8_core_id"] == fields["cpu9_core_id"]:
        fail("CPU8 and CPU9 reported the same core ID")
    if fields["cpu8_package_id"] != fields["cpu9_package_id"]:
        fail("CPU8 and CPU9 reported different package IDs")

    deltas: dict[int, int] = {}
    for cpu in (8, 9):
        before = parse_stat(fields, f"cpu{cpu}_stat_before", cpu)
        after = parse_stat(fields, f"cpu{cpu}_stat_after", cpu)
        if any(final < initial for initial, final in zip(before, after)):
            fail(f"CPU{cpu} accounting moved backwards")
        delta = sum(after) - sum(before)
        if delta <= 0:
            fail(f"CPU{cpu} accounting did not advance")
        deltas[cpu] = delta

    print("runtime_classification=dual-a72-ram-integrity-pass")
    print(f"boot_id={args.boot_id}")
    print(f"cpu8_package_id={fields['cpu8_package_id']}")
    print(f"cpu9_package_id={fields['cpu9_package_id']}")
    print(f"cpu8_core_id={fields['cpu8_core_id']}")
    print(f"cpu9_core_id={fields['cpu9_core_id']}")
    print(f"cpu8_accounting_delta={deltas[8]}")
    print(f"cpu9_accounting_delta={deltas[9]}")
    print(f"payload_sha256={PAYLOAD_SHA256}")
    print("bidirectional_cross_cpu_checksums=4-of-4")
    print("device_storage_writes=none")
    print("cpu_off_requests=0")
    print("retries=0")
    print("reboot_requested=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
