#!/usr/bin/env python3
"""Classify one exact MT6797 thermal base-DT control frame."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BEGIN = "__GEMINI_THERMAL_BASE_DTB_CONTROL_BEGIN__"
END = "__GEMINI_THERMAL_BASE_DTB_CONTROL_END__"
RELEASE = "7.1.3-gemini-mt6797-thermal-stage-ledger"
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


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
        if line.startswith("log: ") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        require(key not in values, f"duplicate-{key}")
        values[key] = value.strip()
    return values


def classify(text: str, recovery_boot_id: str) -> str:
    values = parse(text)
    expected = {
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "dt_model": "Planet Computers Gemini PDA",
        "thermal_dt_status": "disabled",
        "auxadc_dt_status": "disabled",
        "thermal_zone_node": "absent",
        "pwrap_driver": "mt-pmic-pwrap",
        "pwrap_bind_count": "1",
        "mt6351_core_bind_count": "1",
        "mt6351_regulator_bind_count": "1",
        "thermal_driver": "none",
        "thermal_bind_count": "0",
        "mmc_driver": "mtk-msdc",
        "mmc_bind_count": "1",
        "vemc_3v3_count": "1",
        "vio18_count": "1",
        "mmc_card_count": "1",
        "mmc_card_type": "MMC",
        "mmcblk0_present": "1",
        "mmcblk0_partition_count": "33",
        "thermal_zone_count": "0",
        "config_thermal": "1",
        "config_thermal_ledger": "1",
        "config_cpufreq_disabled": "1",
        "config_cpuidle_disabled": "1",
        "config_suspend_disabled": "1",
        "pwrap_error_count": "0",
        "mmc_error_count": "0",
        "thermal_error_count": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "retained_ram_write_request": "none",
        "temperature_read_request": "none",
        "cpu_trigger_request": "none",
        "load_request": "none",
        "cpufreq_request": "none",
        "idle_request": "none",
        "suspend_request": "none",
        "reboot_request": "none",
    }
    for key, value in expected.items():
        require(values.get(key) == value, key)
    require("tty0" in values.get("console_active", "").split(), "console-active")
    boot_id = values.get("boot_id", "")
    require(bool(UUID.fullmatch(boot_id)), "boot-id")
    require(boot_id != recovery_boot_id, "unchanged-recovery-boot-id")
    return boot_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--recovery-boot-id", required=True)
    args = parser.parse_args()
    try:
        require(bool(UUID.fullmatch(args.recovery_boot_id)), "recovery-boot-id")
        boot_id = classify(args.capture.read_text(encoding="utf-8", errors="replace"), args.recovery_boot_id)
    except Rejected as error:
        print("classification=rejected")
        print(f"reason={error}")
        return 3
    print("classification=mt6797-thermal-base-dtb-control-pass")
    print("decision=attribute-serviceability-regression-to-thermal-dt-delta")
    print(f"boot_id={boot_id}")
    print("base_serviceability=pwrap-mt6351-emmc-console-usb")
    print("thermal_controller=disabled")
    print("cpu_trigger_executed=no")
    print("load_executed=no")
    print("storage_write_executed=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
