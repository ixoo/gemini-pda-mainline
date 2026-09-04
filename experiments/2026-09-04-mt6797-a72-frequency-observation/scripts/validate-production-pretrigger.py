#!/usr/bin/env python3
"""Fail closed unless the production candidate is exact, pristine, and ready."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


CANDIDATE = "03cbaa72eafed9077d9a6cafa33766c86eae702fdbc61decf503c16ad98c3c32"
RECORD_IDENTITY = "c5db6133ad716994008ff3cd916dbe95566547bbe02416a05cfdb396fc157602"
RELEASE = "7.1.3-gemini-a72-frequency-thermal"
READY_LINE = "arm64-late-cpu-profile: mt6797-a53-a72-a41-v7 ready"
BEGIN = "__A72_FREQUENCY_THERMAL_PRETRIGGER_BEGIN__"
END = "__A72_FREQUENCY_THERMAL_PRETRIGGER_END__"
LATE_BEGIN = "__A72_FREQUENCY_THERMAL_LATE_PROFILE_BEGIN__"
LATE_END = "__A72_FREQUENCY_THERMAL_LATE_PROFILE_END__"


class Rejected(ValueError):
    """A pre-trigger gate failed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def bounded(text: str, begin: str, end: str) -> str:
    require(text.count(begin) == 1 and text.count(end) == 1,
            "capture-boundary")
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    require(start < finish, "capture-order")
    return text[start:finish]


def fields(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[a-z][a-z0-9_]*", key):
            require(key not in parsed, f"duplicate-{key}")
            parsed[key] = value.strip()
    return parsed


def validate_deployment(text: str) -> str:
    parsed = fields(text)
    required = {
        "target_logical_name": "boot2",
        "root": "/dev/mmcblk0p29",
        "candidate_sha256": CANDIDATE,
        "readback_sha256": CANDIDATE,
        "fresh_predecessor_backup": "no",
        "temporary_readback_removed": "yes",
        "post_shutdown_reachability": "unreachable",
        "reboot": "no",
    }
    for key, expected in required.items():
        require(parsed.get(key) == expected, f"deployment-{key}")
    boot_id = parsed.get("boot_id", "")
    require(bool(re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot_id
    )), "deployment-boot-id")
    return boot_id


def validate_capture(text: str, deployment_boot_id: str) -> str:
    frame = bounded(text.replace("\r", ""), BEGIN, END)
    parsed = fields(frame)
    required = {
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "controller_bound": "1",
        "binder_bound": "1",
        "platform_state_bound": "1",
        "status_mode": "444",
        "trigger_mode": "200",
        "record_identity": RECORD_IDENTITY,
        "frequency_observer_count": "1",
        "frequency_observer_mode": "444",
        "frequency_log_count": "0",
        "thermal_zone_count": "1",
        "thermal_zone_type": "soc-thermal",
        "device_storage_reads": "none",
        "device_storage_writes": "none",
        "frequency_observation_request": "none",
        "sysfs_write_request": "none",
        "cpu_admission_request": "none",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
    }
    for key, expected in required.items():
        require(parsed.get(key) == expected, f"capture-{key}")
    require("ro" in parsed.get("sysfs_options", "").split(","),
            "sysfs-not-readonly")
    boot_id = parsed.get("boot_id", "")
    require(bool(re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot_id
    )), "capture-boot-id")
    require(boot_id != deployment_boot_id, "boot-id-did-not-change")
    temperature = parsed.get("thermal_temperature_millicelsius", "")
    require(bool(re.fullmatch(r"-?[0-9]+", temperature)),
            "thermal-temperature-shape")
    require(0 <= int(temperature) <= 120_000,
            "thermal-temperature-range")

    status = parsed.get("live_status", "")
    for exact in (
        "state=armed trigger_consumed=0 trigger_executions=0 operation_ret=-115 core_consumed=0",
        "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0",
        "binder_snapshot_ret=0 binder_abi=5 lifecycle=0 terminal=0 last_stage=0",
        "attempted=0 watchdog_armed=0",
        "cpu9_controller_consumed=0 cpu9_operation_ret=-115",
        "cpu9_attempted=0 cpu9_membership_published=0 cpu9_cpu_requests=0 cpu9_cpu_off_requests=0 cpu9_retries=0",
    ):
        require(exact in status, "controller-not-pristine")

    late = bounded(frame, LATE_BEGIN, LATE_END)
    require("blocked" not in late.lower(), "late-profile-blocked")
    require("proof mask" not in late.lower() and
            "proof_mask" not in late.lower(), "late-profile-proof-mask")
    require(late.count(READY_LINE) == 1, "late-profile-ready-missing")
    return boot_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--deployment-summary", type=Path, required=True)
    args = parser.parse_args()
    try:
        deployment_boot_id = validate_deployment(
            args.deployment_summary.read_text(
                encoding="utf-8", errors="replace")
        )
        boot_id = validate_capture(
            args.capture.read_text(encoding="utf-8", errors="replace"),
            deployment_boot_id,
        )
    except (OSError, Rejected, UnicodeError) as error:
        print("pretrigger_classification=rejected")
        print(f"pretrigger_reason={error}")
        return 3
    print("pretrigger_classification=serviceable-pristine-thermal-frequency-ready")
    print("pretrigger_reason=exact-production-identity-zero-observer-attempts")
    print(f"boot_id={boot_id}")
    print("cpu_online=0-7")
    print("frequency_observer_attempts=0-of-3")
    print("thermal_zone=soc-thermal")
    print("arm64_late_profile=ready")
    print("trigger_executions=0")
    print("cpu8_requests=0")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
