#!/usr/bin/env python3
"""Classify one exact MT6797 topology and bounded RAM transcript."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re


SOURCE_SHA256 = "a5892bfb0d72d176344c93f2ec389e35c5c5f8d7253ac40b61a11d645c39d888"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-dual-a72-ram-coherency/"
    "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source dual-A72 RAM classifier changed")

spec = importlib.util.spec_from_file_location("dual_a72_ram_classifier", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--boot-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", args.boot_id):
        source.fail("expected boot ID is malformed")

    fields = source.fields_from_capture(args.capture)
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
        "cpu8_affinity": "8",
        "cpu9_affinity": "9",
        "cpu8_processor": "8",
        "cpu9_processor": "9",
        "source_cpu8_sha256": source.PAYLOAD_SHA256,
        "source_cpu9_sha256": source.PAYLOAD_SHA256,
        "file8_size": source.PAYLOAD_SIZE,
        "file8_writer_cpu8_sha256": source.PAYLOAD_SHA256,
        "file8_reader_cpu9_sha256": source.PAYLOAD_SHA256,
        "file9_size": source.PAYLOAD_SIZE,
        "file9_writer_cpu9_sha256": source.PAYLOAD_SHA256,
        "file9_reader_cpu8_sha256": source.PAYLOAD_SHA256,
        "cleanup_file8": "absent",
        "cleanup_file9": "absent",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
        "probe_result": "pass",
    }
    for cpu in range(10):
        if cpu < 4:
            cluster, core = "0-3", str(cpu)
        elif cpu < 8:
            cluster, core = "4-7", str(cpu - 4)
        else:
            cluster, core = "8-9", str(cpu - 8)
        exact.update({
            f"cpu{cpu}_core_id": core,
            f"cpu{cpu}_package_id": "0",
            f"cpu{cpu}_core_siblings": "0-9",
            f"cpu{cpu}_cluster_cpus": cluster,
            f"cpu{cpu}_thread_siblings": str(cpu),
        })
    for key, value in exact.items():
        source.require_exact(fields, key, value)
    if "probe_failure" in fields:
        source.fail("probe reported a failure")

    deltas: dict[int, int] = {}
    for cpu in (8, 9):
        before = source.parse_stat(fields, f"cpu{cpu}_stat_before", cpu)
        after = source.parse_stat(fields, f"cpu{cpu}_stat_after", cpu)
        if any(final < initial for initial, final in zip(before, after)):
            source.fail(f"CPU{cpu} accounting moved backwards")
        delta = sum(after) - sum(before)
        if delta <= 0:
            source.fail(f"CPU{cpu} accounting did not advance")
        deltas[cpu] = delta

    print("runtime_classification=mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass")
    print(f"boot_id={args.boot_id}")
    print("package_siblings=0-9")
    print("cluster0_cpus=0-3")
    print("cluster1_cpus=4-7")
    print("cluster2_cpus=8-9")
    print(f"cpu8_accounting_delta={deltas[8]}")
    print(f"cpu9_accounting_delta={deltas[9]}")
    print(f"payload_sha256={source.PAYLOAD_SHA256}")
    print("bidirectional_cross_cpu_checksums=4-of-4")
    print("device_storage_writes=none")
    print("cpu_off_requests=0")
    print("retries=0")
    print("reboot_requested=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
