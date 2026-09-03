#!/usr/bin/env python3
"""Classify a redacted current-candidate power-observability capture."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BEGIN = "__GEMINI_POWER_OBSERVABILITY_BEGIN__"
END = "__GEMINI_POWER_OBSERVABILITY_END__"
RELEASE = "7.1.3-gemini-a72-hotplug-physical"
RECORD_IDENTITY = "d4940602e7ad9cbc947376bfb9dc4222ef5a671faa15eb42a821df1852af9ba4"
PRIOR_MAINLINE_BOOT_IDS = {
    "c1bd9a56-919f-4ba1-8404-1287148b334a",
    "415bab0d-a6cf-453b-a3e1-a9fb5d467fe7",
}
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
HEX256 = re.compile(r"^[0-9a-f]{64}$")


class Rejected(Exception):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def parse(text: str) -> dict[str, str]:
    require(text.count(BEGIN) == 1, "begin-marker")
    require(text.count(END) == 1, "end-marker")
    require(text.index(BEGIN) < text.index(END), "marker-order")
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    values: dict[str, str] = {}
    for line in body.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        require(key not in values, f"duplicate-{key}")
        values[key] = value.strip()
    return values


def exact(values: dict[str, str], key: str, expected: str) -> None:
    require(values.get(key) == expected, key)


def classify(text: str, recovery_boot_id: str) -> tuple[str, str]:
    values = parse(text)
    exact(values, "kernel_release", RELEASE)
    exact(values, "architecture", "aarch64")
    boot_id = values.get("boot_id", "")
    require(bool(UUID.fullmatch(boot_id)), "boot-id")
    require(boot_id != recovery_boot_id, "unchanged-recovery-boot-id")
    require(boot_id not in PRIOR_MAINLINE_BOOT_IDS, "previous-mainline-boot-id")
    for key, expected in (
        ("cpu_possible", "0-9"), ("cpu_present", "0-9"),
        ("cpu_online", "0-7"), ("cpu_offline", "8-9"),
        ("controller_bound", "1"), ("binder_bound", "1"),
        ("platform_state_bound", "1"), ("status_mode", "444"),
        ("trigger_mode", "200"), ("record_identity", RECORD_IDENTITY),
        ("atag_property_present", "1"), ("atag_property_bytes", "412"),
        ("provider_dt_compatible", "mediatek,mt6797-atag-devinfo"),
        ("provider_dt_read_only", "1"),
        ("provider_platform_bind_count", "1"),
        ("provider_driver", "mediatek-mt6797-atag-devinfo"),
        ("nvmem_provider_count", "1"),
        ("nvmem_binary_content_read", "no"),
        ("thermal_dt_status", "disabled"), ("auxadc_dt_status", "disabled"),
        ("thermal_zone_count", "0"), ("cpufreq_policy_count", "0"),
        ("device_partition_reads", "none"), ("device_storage_writes", "none"),
        ("sysfs_write_request", "none"), ("cpu_admission_request", "none"),
        ("cpu_off_request", "none"), ("nvmem_payload_output", "none"),
        ("calibration_value_output", "none"), ("retry_request", "none"),
        ("reboot_request", "none"),
    ):
        exact(values, key, expected)
    require("ro" in values.get("sysfs_options", "").split(","), "sysfs-not-read-only")
    status = values.get("live_status", "")
    for token in (
        "state=armed", "trigger_consumed=0", "trigger_executions=0",
        "cpu_requests=0", "cpu9_requests=0", "cpu_off_requests=0", "retries=0",
    ):
        require(token in status.split(), f"live-status-{token}")
    require(bool(HEX256.fullmatch(values.get("atag_property_sha256", ""))),
            "atag-property-sha256")
    require(values.get("provider_platform_device", "none") != "none",
            "provider-platform-device")
    require(values.get("nvmem_provider_name", "").startswith("mt6797-atag-calibration"),
            "nvmem-provider-name")
    return boot_id, values["atag_property_sha256"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--recovery-boot-id", required=True)
    args = parser.parse_args()
    try:
        require(bool(UUID.fullmatch(args.recovery_boot_id)), "recovery-boot-id")
        boot_id, atag_sha = classify(
            args.capture.read_text(encoding="utf-8", errors="replace"),
            args.recovery_boot_id,
        )
    except Rejected as error:
        print("classification=rejected")
        print(f"reason={error}")
        return 3
    print("classification=calibration-provider-bound-power-observability-absent")
    print("decision=implement-observability-before-more-load")
    print(f"boot_id={boot_id}")
    print(f"atag_property_sha256={atag_sha}")
    print("thermal_interface=absent-by-disabled-config-and-DT")
    print("cpufreq_interface=absent-by-disabled-config-and-missing-OPP-contract")
    print("cpu_trigger_executed=no")
    print("load_executed=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
