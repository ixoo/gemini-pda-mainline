#!/usr/bin/env python3
"""Validate the exact read-only ATAG-prerequisite pre-trigger frame."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__A72_ATAG_PRETRIGGER_QUALIFICATION_BEGIN__"
END = "__A72_ATAG_PRETRIGGER_QUALIFICATION_END__"
EXPECTED_BOOT_ID = "515b4618-5bf7-4125-9c08-38db55d6cc27"
EXPECTED = {
    "installed_full_sha256": "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0",
    "kernel_release": "7.1.3-gemini-a72-admission-live",
    "architecture": "aarch64",
    "boot_id": EXPECTED_BOOT_ID,
    "cpu_possible": "0-9",
    "cpu_present": "0-9",
    "cpu_online": "0-7",
    "cpu_offline": "8-9",
    "udc_devices": "1",
    "block_mounts": "0",
    "config_nvmem": "CONFIG_NVMEM=y",
    "config_nvmem_mtk_atag_devinfo": "CONFIG_NVMEM_MTK_ATAG_DEVINFO=y",
    "nvmem_bus_devices": "1",
    "nvmem_device_names": "mt6797-atag-calibration0,",
    "atag_devinfo_device": "present",
    "atag_devinfo_driver": "mediatek-mt6797-atag-devinfo",
    "dvfsp_handoff_device": "present",
    "dvfsp_handoff_driver": "mt6797-dvfsp-handoff",
    "i2c6_device": "present",
    "i2c6_driver": "i2c-mt65xx",
    "clock_backend_device": "present",
    "clock_backend_driver": "mt6797-dvfsp-clock-backend",
    "bigidvfs_backend_device": "present",
    "bigidvfs_backend_driver": "mt6797-bigidvfs-backend",
    "platform_state_device": "present",
    "platform_state_driver": "mt6797-a72-platform-state",
    "a72_binder_device": "present",
    "a72_binder_driver": "mt6797-a72-binder",
    "admission_controller_device": "present",
    "admission_controller_driver": "mt6797-a72-admission-controller",
    "da921x_device": "present",
    "da921x_driver": "da9213-legacy-regulator",
    "controller_status": "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 trigger_executions=0 operation_ret=-115 core_consumed=0 cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0",
    "sysfs_options": "ro,nosuid,nodev,noexec,relatime",
    "device_partition_reads": "none",
    "device_storage_writes": "none",
    "nvmem_cell_reads": "none",
    "sysfs_writes": "none",
    "trigger_session": "none",
    "cpu_admission_request": "none",
    "cpu_off_request": "none",
    "retry_request": "none",
    "reboot_request": "none",
    "visible_console_framebuffer": "owner-reports-frozen-boot-image",
    "control_channel": "exact-live-usb-netcat",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"runtime rejected: {message}")


def parse(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="strict").replace("\r", "")
    text = text.replace("GEMINI-AC-USB# ", "")
    require(text.count(BEGIN) == 1 and text.count(END) == 1, "frame markers changed")
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    values: dict[str, str] = {}
    for raw in body.splitlines():
        line = raw.strip()
        while line.startswith("> "):
            line = line[2:]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key):
            continue
        require(key not in values, f"duplicate key: {key}")
        values[key] = value
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    values = parse(args.capture)
    expected_keys = set(EXPECTED) | {"uptime_seconds"}
    require(set(values) == expected_keys, "field inventory changed")
    for key, expected in EXPECTED.items():
        require(values[key] == expected, f"{key} changed")
    require(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", values["uptime_seconds"]) is not None,
            "uptime is malformed")
    require(float(values["uptime_seconds"]) > 0, "uptime is not positive")
    require(EXPECTED_BOOT_ID not in {
        "21bb6547-a5cd-494c-8900-d92884c0c6a5",
        "09ed19d3-6ad9-4e65-b2d3-46ad56bc9bb7",
    }, "boot ID did not change across the transition")
    print("validation=a72-admission-atag-prerequisite-runtime")
    print(f"boot_id={EXPECTED_BOOT_ID}")
    print("complete_prerequisite_graph=bound")
    print("controller_state=armed-zero-execution")
    print("cpu_online=0-7")
    print("cpu_offline=8-9")
    print("trigger_requests=0")
    print("device_storage_writes=0")
    print("visible_console_framebuffer=frozen-boot-image")
    print("control_channel=exact-live-usb-netcat")
    print("result=pass")


if __name__ == "__main__":
    main()
