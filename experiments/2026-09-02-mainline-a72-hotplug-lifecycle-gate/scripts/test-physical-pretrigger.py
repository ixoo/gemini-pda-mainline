#!/usr/bin/env python3
"""Mutation tests for the repaired physical-hotplug pre-trigger gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve()
VALIDATOR = SCRIPT.with_name("validate-physical-pretrigger.py")
spec = importlib.util.spec_from_file_location("physical_pretrigger", VALIDATOR)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

DEPLOYMENT_BOOT = "11111111-1111-4111-8111-111111111111"
RUNTIME_BOOT = "22222222-2222-4222-8222-222222222222"
STATUS = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
    "trigger_executions=0 operation_ret=-115 core_consumed=0 entry_trace_ret=0 "
    "terminal_trace_ret=0 failure_stage=0 derive_stage=0 cpu_requests=0 "
    "cpu9_requests=0 cpu_off_requests=0 retries=0 binder_snapshot_ret=0 "
    "binder_abi=5 lifecycle=0 terminal=0 last_stage=0 attempted=0 "
    "watchdog_armed=0 cpu9_controller_consumed=0 cpu9_operation_ret=-115 "
    "cpu9_attempted=0 cpu9_membership_published=0 cpu9_cpu_requests=0 "
    "cpu9_cpu_off_requests=0 cpu9_retries=0"
)


def baseline() -> str:
    values = {
        "kernel_release": validator.RELEASE,
        "architecture": "aarch64",
        "boot_id": RUNTIME_BOOT,
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "controller_bound": "1",
        "binder_bound": "1",
        "platform_state_bound": "1",
        "status_mode": "444",
        "trigger_mode": "200",
        "sysfs_options": "ro,nosuid,nodev,noexec,relatime",
        "record_identity": validator.RECORD_IDENTITY,
        "live_status": STATUS,
    }
    lines = [validator.BEGIN]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.extend([validator.LATE_BEGIN, f"[ 1.0] {validator.READY_LINE}", validator.LATE_END])
    for key in ("device_storage_reads", "device_storage_writes",
                "sysfs_write_request", "cpu_admission_request",
                "cpu_off_request", "retry_request", "reboot_request"):
        lines.append(f"{key}=none")
    lines.append(validator.END)
    return "\n".join(lines) + "\n"


def rejected(text: str) -> bool:
    try:
        validator.validate_capture(text, DEPLOYMENT_BOOT)
    except validator.Rejected:
        return True
    return False


def main() -> int:
    good = baseline()
    validator.validate_capture(good, DEPLOYMENT_BOOT)
    mutations = {
        "old-record": good.replace(validator.RECORD_IDENTITY, "00" * 32, 1),
        "same-boot": good.replace(RUNTIME_BOOT, DEPLOYMENT_BOOT, 1),
        "cpu8-online": good.replace("cpu_online=0-7", "cpu_online=0-8", 1),
        "already-consumed": good.replace("trigger_consumed=0", "trigger_consumed=1", 1),
        "request-count": good.replace("cpu_requests=0", "cpu_requests=1", 1),
        "missing-ready": good.replace(validator.READY_LINE, "profile not ready", 1),
        "blocked-proof-mask": good.replace(
            f"[ 1.0] {validator.READY_LINE}",
            "[ 1.0] arm64-late-cpu-profile: mt6797-a53-a72-a41-v7 blocked: configuration identity (proof mask 0x40000)",
            1,
        ),
        "writable-sysfs": good.replace("sysfs_options=ro,", "sysfs_options=rw,", 1),
    }
    for name, text in mutations.items():
        if not rejected(text):
            raise SystemExit(f"unsafe mutation accepted: {name}")
        print(f"mutation={name} result=rejected")
    print(f"mutations_rejected={len(mutations)}")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
