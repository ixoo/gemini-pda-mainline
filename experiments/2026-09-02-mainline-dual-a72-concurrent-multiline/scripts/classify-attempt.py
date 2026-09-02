#!/usr/bin/env python3
"""Classify one integrated concurrent multiline CPU8/CPU9 attempt."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys


PARENT_SHA256 = "97c207d41dc7d38a1f04334be34c1f6ff96973b8e6f174e96c1be8845db3cac0"
BEGIN = "__GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__"
END = "__GEMINI_A72_CONCURRENT_MULTILINE_END__"
PAYLOAD_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
PAYLOAD_SIZE = 1914704
ROUNDS = 4
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
PARENT = ROOT / (
    "experiments/2026-09-02-mainline-mt6797-cpu-map/"
    "scripts/classify-integrated-attempt.py"
)


class Classification(Exception):
    """A strict runtime predicate failed."""


def reject(reason: str) -> int:
    print("runtime_classification=rejected")
    print(f"runtime_reason={reason}")
    print("trigger_attempts=unknown")
    print("workload_sessions=1")
    print("cpu8_request_maximum=1")
    print("cpu9_request_maximum=1")
    print("cpu_off_requests=0")
    print("retries=0")
    print("native_reboot_requested=no")
    return 3


def fields_from_capture(capture: Path) -> dict[str, str]:
    text = capture.read_text(encoding="utf-8", errors="replace").replace("\r", "")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise Classification("concurrent-boundary-count-changed")
    if text.index(END) < text.index(BEGIN):
        raise Classification("concurrent-boundary-order-changed")
    body = text[text.index(BEGIN) + len(BEGIN) : text.index(END)]
    fields: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not re.fullmatch(r"[a-z0-9_-]+=[^\n]*", line):
            continue
        key, value = line.split("=", 1)
        if key in fields:
            raise Classification(f"duplicate-field:{key}")
        fields[key] = value
    return fields


def parse_stat(fields: dict[str, str], key: str, cpu: int) -> tuple[int, ...]:
    parts = fields.get(key, "").split()
    if len(parts) != 11 or parts[0] != f"cpu{cpu}":
        raise Classification(f"{key}-shape-changed")
    try:
        return tuple(int(value) for value in parts[1:])
    except ValueError as error:
        raise Classification(f"{key}-not-numeric") from error


def validate_fields(fields: dict[str, str], boot_id: str) -> dict[int, int]:
    exact = {
        "boot_id": boot_id,
        "kernel_release": "7.1.3-gemini-cpu9-progress",
        "cpu_online": "0-9",
        "cpu_offline": "",
        "root_entries": "1",
        "root_source": "rootfs",
        "root_fstype": "rootfs",
        "run_mount_entries": "0",
        "block_mounts": "0",
        "rounds": str(ROUNDS),
        "payload_size": str(PAYLOAD_SIZE),
        "payload_sha256": PAYLOAD_SHA256,
        "writer_start_barrier": "bounded-file-publication",
        "reader_start_barrier": "bounded-file-publication",
        "spin_limit": "1000000",
        "writer8_affinity": "8",
        "writer8_processor": "8",
        "writer8_rounds_completed": str(ROUNDS),
        "writer8_size": str(PAYLOAD_SIZE),
        "writer8_sha256": PAYLOAD_SHA256,
        "writer9_affinity": "9",
        "writer9_processor": "9",
        "writer9_rounds_completed": str(ROUNDS),
        "writer9_size": str(PAYLOAD_SIZE),
        "writer9_sha256": PAYLOAD_SHA256,
        "writer8_status": "0",
        "writer9_status": "0",
        "reader8_affinity": "8",
        "reader8_processor": "8",
        "reader8_rounds_completed": str(ROUNDS),
        "reader8_peer_sha256": PAYLOAD_SHA256,
        "reader9_affinity": "9",
        "reader9_processor": "9",
        "reader9_rounds_completed": str(ROUNDS),
        "reader9_peer_sha256": PAYLOAD_SHA256,
        "reader8_status": "0",
        "reader9_status": "0",
        "cleanup_file8": "absent",
        "cleanup_file9": "absent",
        "cleanup_auxiliary": "absent",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
        "concurrent_result": "pass",
    }
    for key, expected in exact.items():
        actual = fields.get(key)
        if actual != expected:
            raise Classification(f"{key}-changed:expected-{expected!r}-got-{actual!r}")

    deltas: dict[int, int] = {}
    for cpu in (8, 9):
        before = parse_stat(fields, f"cpu{cpu}_stat_before", cpu)
        after = parse_stat(fields, f"cpu{cpu}_stat_after", cpu)
        if any(final < initial for initial, final in zip(before, after)):
            raise Classification(f"CPU{cpu}-accounting-moved-backwards")
        delta = sum(after) - sum(before)
        if delta <= 0:
            raise Classification(f"CPU{cpu}-accounting-did-not-advance")
        deltas[cpu] = delta
    return deltas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", required=True, type=Path)
    parser.add_argument("--trigger", required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(PARENT.read_bytes()).hexdigest() != PARENT_SHA256:
        return reject("parent-classifier-changed")
    parent = subprocess.run(
        [
            sys.executable,
            str(PARENT),
            "--pretrigger",
            str(args.pretrigger),
            "--trigger",
            str(args.trigger),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if parent.returncode != 0:
        sys.stderr.write(parent.stderr)
        return reject("parent-topology-ram-classifier-rejected")
    if (
        "runtime_classification="
        "mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass"
        not in parent.stdout.splitlines()
    ):
        return reject("parent-topology-ram-classification-changed")

    try:
        fields = fields_from_capture(args.trigger)
        boot_ids = [
            line.split("=", 1)[1]
            for line in args.pretrigger.read_text(encoding="utf-8").splitlines()
            if line.startswith("boot_id=")
        ]
        if len(boot_ids) != 1:
            raise Classification("pretrigger-boot-id-count-changed")
        deltas = validate_fields(fields, boot_ids[0])
    except Classification as error:
        return reject(str(error))

    print("runtime_classification=mt6797-dual-a72-concurrent-disjoint-multiline-pass")
    print(f"boot_id={boot_ids[0]}")
    print(f"rounds={ROUNDS}")
    print(f"payload_size={PAYLOAD_SIZE}")
    print(f"concurrent_primary_write_bytes={2 * ROUNDS * PAYLOAD_SIZE}")
    print(f"concurrent_peer_read_bytes={2 * ROUNDS * PAYLOAD_SIZE}")
    print(f"cpu8_accounting_delta={deltas[8]}")
    print(f"cpu9_accounting_delta={deltas[9]}")
    print(f"payload_sha256={PAYLOAD_SHA256}")
    print("writer_checksums=8-of-8")
    print("peer_reader_checksums=8-of-8")
    print("device_storage_writes=none")
    print("cpu_off_requests=0")
    print("retries=0")
    print("reboot_requested=no")
    print("parent_runtime_classification=mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass")
    print("trigger_attempts=1")
    print("workload_sessions=1")
    print("native_reboot_requested=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
