#!/usr/bin/env python3
"""Classify one topology-preserving CPU8/CPU9 lifecycle transaction."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__A72_TOPOLOGY_REPEAT_TRIGGER_BEGIN__"
END = "__A72_TOPOLOGY_REPEAT_TRIGGER_END__"
SYSFS_BEGIN = "__A72_TOPOLOGY_REPEAT_SYSFS_BEGIN__"
SYSFS_END = "__A72_TOPOLOGY_REPEAT_SYSFS_END__"
BINDER = (
    "GEMINI_A72_HOTPLUG_BINDING_V1 ret=0 terminal=5 last_stage=18 "
    "stage_errno=0 publication_errno=0 add_cpu_ret=0 "
    "restore_validation_attempted=1 restore_transaction_valid=1 "
    "down_completed=1 restore_completed=1 completed=1 "
    "result_ledger_active=1 ledger_active=0 ledger_terminal=1 "
    "restore_lifecycle=14 restore_terminal=2 restore_last_stage=18 "
    "restore_stage_errno=0 restore_publication_errno=0 p30e_rearmed=1 "
    "cpu8_online=1 cpu9_online=1"
)


class Rejected(ValueError):
    """The capture did not prove the selected success predicate."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def bounded(text: str, begin: str, end: str) -> str:
    require(text.count(begin) == 1 and text.count(end) == 1, "capture-boundary")
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    require(start < finish, "capture-order")
    return text[start:finish]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--boot-id", required=True)
    args = parser.parse_args()
    try:
        require(bool(re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", args.boot_id)), "expected-boot-id")
        frame = bounded(args.capture.read_text(encoding="utf-8", errors="replace"), BEGIN, END)
        required_once = (
            "kernel_release=7.1.3-gemini-a72-hotplug-physical",
            f"boot_id={args.boot_id}",
            "trigger_commit=yes",
            "token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f",
            "trigger_write_status=0",
            "remount_ro_status=0",
            "cpu_online=0-9",
            "cpu_offline=",
            "device_storage_reads=none",
            "device_storage_writes=none",
            "load_probe=none",
            "retry_request=none",
            "reboot_request=none",
        )
        for line in required_once:
            require(frame.count(line + "\n") == 1, f"missing-or-duplicate-{line.split('=', 1)[0]}")
        require("trigger_commit=no" not in frame, "trigger-rejected")
        post = next((line for line in frame.splitlines() if line.startswith("post_status=")), "")
        for exact in (
            "state=terminal trigger_consumed=1 trigger_executions=1 operation_ret=0 core_consumed=1",
            "cpu_requests=1 cpu9_requests=1",
            "retries=0",
        ):
            require(exact in post, "post-status")
        topology = bounded(frame, SYSFS_BEGIN, SYSFS_END)
        clusters = {cpu: "0-3" for cpu in range(4)}
        clusters.update({cpu: "4-7" for cpu in range(4, 8)})
        clusters.update({8: "8-9", 9: "8-9"})
        core_ids = (0, 1, 2, 3, 0, 1, 2, 3, 0, 1)
        for cpu in range(10):
            expected = (
                f"cpu{cpu}_physical_package_id=0",
                f"cpu{cpu}_core_id={core_ids[cpu]}",
                f"cpu{cpu}_core_siblings=0-9",
                f"cpu{cpu}_cluster_cpus={clusters[cpu]}",
                f"cpu{cpu}_thread_siblings={cpu}",
            )
            for line in expected:
                require(topology.count(line + "\n") == 1, f"topology-cpu{cpu}")
        require(frame.count("CPU8: Booted secondary processor 0x0000000200 [0x410fd081]") == 1, "cpu8-entry-count")
        require(frame.count("CPU9: Booted secondary processor 0x0000000201 [0x410fd081]") == 2, "cpu9-entry-count")
        require(frame.count(BINDER) == 1, "binder-terminal")
    except Rejected as error:
        print("runtime_classification=rejected")
        print(f"runtime_reason={error}")
        return 3
    print("runtime_classification=stage18-repeat-and-mt6797-4+4+2-topology-pass")
    print(f"boot_id={args.boot_id}")
    print("cpu_online=0-9")
    print("binder_ret=0")
    print("binder_completed=1")
    print("restore_stage=18")
    print("cpu_map=0-3,4-7,8-9")
    print("load_probe=none")
    print("trigger_retries=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
