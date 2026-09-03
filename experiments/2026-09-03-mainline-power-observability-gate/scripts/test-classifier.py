#!/usr/bin/env python3
"""Mutation tests for the redacted power-observability classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
CLASSIFIER = HERE / "classify-observation.py"
BOOT_ID = "22222222-2222-4222-8222-222222222222"
RECOVERY_BOOT_ID = "11111111-1111-4111-8111-111111111111"


def load():
    specification = importlib.util.spec_from_file_location("power_classifier", CLASSIFIER)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def fixture(module) -> str:
    values = {
        "kernel_release": module.RELEASE,
        "architecture": "aarch64",
        "boot_id": BOOT_ID,
        "cpu_possible": "0-9", "cpu_present": "0-9",
        "cpu_online": "0-7", "cpu_offline": "8-9",
        "controller_bound": "1", "binder_bound": "1",
        "platform_state_bound": "1", "status_mode": "444",
        "trigger_mode": "200", "sysfs_options": "ro,nosuid,nodev,noexec",
        "record_identity": module.RECORD_IDENTITY,
        "live_status": (
            "state=armed trigger_consumed=0 trigger_executions=0 operation_ret=-115 "
            "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0"
        ),
        "atag_property_present": "1", "atag_property_bytes": "412",
        "atag_property_sha256": "a" * 64,
        "provider_dt_compatible": "mediatek,mt6797-atag-devinfo",
        "provider_dt_read_only": "1", "provider_platform_bind_count": "1",
        "provider_platform_device": "firmware:atag-devinfo",
        "provider_driver": "mediatek-mt6797-atag-devinfo",
        "nvmem_provider_count": "1",
        "nvmem_provider_name": "mt6797-atag-calibration0",
        "nvmem_binary_content_read": "no",
        "thermal_dt_status": "disabled", "auxadc_dt_status": "disabled",
        "thermal_zone_count": "0", "cpufreq_policy_count": "0",
        "device_partition_reads": "none", "device_storage_writes": "none",
        "sysfs_write_request": "none", "cpu_admission_request": "none",
        "cpu_off_request": "none", "nvmem_payload_output": "none",
        "calibration_value_output": "none", "retry_request": "none",
        "reboot_request": "none",
    }
    lines = [module.BEGIN]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.append(module.END)
    return "\n".join(lines) + "\n"


def main() -> int:
    module = load()
    good = fixture(module)
    assert module.classify(good, RECOVERY_BOOT_ID)[0] == BOOT_ID
    mutations = (
        ("412", "411"),
        ("provider_platform_bind_count=1", "provider_platform_bind_count=0"),
        ("nvmem_binary_content_read=no", "nvmem_binary_content_read=yes"),
        ("thermal_dt_status=disabled", "thermal_dt_status=okay"),
        ("cpufreq_policy_count=0", "cpufreq_policy_count=1"),
        ("trigger_executions=0", "trigger_executions=1"),
        ("device_storage_writes=none", "device_storage_writes=one"),
        (BOOT_ID, RECOVERY_BOOT_ID),
        (BOOT_ID, "415bab0d-a6cf-453b-a3e1-a9fb5d467fe7"),
        (module.END, ""),
    )
    for old, new in mutations:
        changed = good.replace(old, new, 1)
        assert changed != good
        try:
            module.classify(changed, RECOVERY_BOOT_ID)
        except module.Rejected:
            continue
        raise SystemExit(f"mutation accepted: {old} -> {new}")
    print(f"mutations_rejected={len(mutations)}")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
