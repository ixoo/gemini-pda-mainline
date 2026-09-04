#!/usr/bin/env python3
"""Mutation tests for the production thermal/frequency pre-trigger gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / "validate-production-pretrigger.py"
SPEC = importlib.util.spec_from_file_location("production_pretrigger", VALIDATOR)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

DEPLOYMENT_BOOT = "11111111-1111-4111-8111-111111111111"
RUNTIME_BOOT = "22222222-2222-4222-8222-222222222222"
STATUS = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
    "trigger_executions=0 operation_ret=-115 core_consumed=0 "
    "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0 "
    "binder_snapshot_ret=0 binder_abi=5 lifecycle=0 terminal=0 "
    "last_stage=0 attempted=0 watchdog_armed=0 "
    "cpu9_controller_consumed=0 cpu9_operation_ret=-115 "
    "cpu9_attempted=0 cpu9_membership_published=0 cpu9_cpu_requests=0 "
    "cpu9_cpu_off_requests=0 cpu9_retries=0"
)


def deployment() -> str:
    return "\n".join((
        "target_logical_name=boot2",
        "root=/dev/mmcblk0p29",
        f"candidate_sha256={validator.CANDIDATE}",
        f"readback_sha256={validator.CANDIDATE}",
        "fresh_predecessor_backup=no",
        "temporary_readback_removed=yes",
        "post_shutdown_reachability=unreachable",
        "reboot=no",
        f"boot_id={DEPLOYMENT_BOOT}",
        "",
    ))


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
        "frequency_observer_count": "1",
        "frequency_observer_mode": "444",
        "frequency_log_count": "0",
        "thermal_zone_count": "1",
        "thermal_zone_type": "soc-thermal",
        "thermal_temperature_millicelsius": "36500",
    }
    lines = [validator.BEGIN]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.extend((validator.LATE_BEGIN,
                  f"[ 1.0] {validator.READY_LINE}",
                  validator.LATE_END))
    for key in ("device_storage_reads", "device_storage_writes",
                "frequency_observation_request", "sysfs_write_request",
                "cpu_admission_request", "cpu_off_request",
                "retry_request", "reboot_request"):
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
    validator.validate_deployment(deployment())
    validator.validate_capture(good, DEPLOYMENT_BOOT)
    mutations = {
        "old-record": good.replace(validator.RECORD_IDENTITY, "00" * 32, 1),
        "same-boot": good.replace(RUNTIME_BOOT, DEPLOYMENT_BOOT, 1),
        "cpu8-online": good.replace("cpu_online=0-7", "cpu_online=0-8", 1),
        "already-consumed": good.replace("trigger_consumed=0", "trigger_consumed=1", 1),
        "observer-attempt": good.replace("frequency_log_count=0", "frequency_log_count=1", 1),
        "observer-missing": good.replace("frequency_observer_count=1", "frequency_observer_count=0", 1),
        "observer-writable": good.replace("frequency_observer_mode=444", "frequency_observer_mode=644", 1),
        "thermal-zone": good.replace("thermal_zone_count=1", "thermal_zone_count=0", 1),
        "thermal-type": good.replace("thermal_zone_type=soc-thermal", "thermal_zone_type=wrong", 1),
        "thermal-range": good.replace("thermal_temperature_millicelsius=36500", "thermal_temperature_millicelsius=130000", 1),
        "missing-ready": good.replace(validator.READY_LINE, "profile not ready", 1),
        "writable-sysfs": good.replace("sysfs_options=ro,", "sysfs_options=rw,", 1),
    }
    for name, text in mutations.items():
        if not rejected(text):
            raise SystemExit(f"unsafe mutation accepted: {name}")
        print(f"mutation={name} result=rejected")
    print("validation=mt6797-a72-frequency-production-pretrigger")
    print(f"mutations_rejected={len(mutations)}")
    print("observer_reads=0")
    print("device_writes=0")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
