#!/usr/bin/env python3
"""Classify one exact thermal-ledger live-model repair runtime frame."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BEGIN = "__GEMINI_THERMAL_LEDGER_LIVE_MODEL_REPAIR_BEGIN__"
END = "__GEMINI_THERMAL_LEDGER_LIVE_MODEL_REPAIR_END__"
RELEASE = "7.1.3-gemini-mt6797-thermal-stage-ledger"
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
SINT = re.compile(r"^-?[0-9]+$")
THERMAL_DEFER = re.compile(r"^log: \[[^\n]+\] probe of 1100b000\.thermal returned -517 after [0-9]+ usecs$", re.MULTILINE)
THERMAL_SUCCESS = re.compile(r"^log: \[[^\n]+\] probe of 1100b000\.thermal returned 0 after [0-9]+ usecs$", re.MULTILINE)


class Rejected(Exception):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def parse(text: str) -> tuple[dict[str, str], str]:
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
    return values, body


def classify(text: str, recovery_boot_id: str) -> tuple[str, tuple[int, int, int]]:
    values, body = parse(text)
    expected = {
        "kernel_release": RELEASE, "architecture": "aarch64",
        "cpu_possible": "0-9", "cpu_present": "0-9",
        "cpu_online": "0-7", "cpu_offline": "8-9",
        "console_active": "ttyS0", "dt_model": "MT6797X",
        "pwrap_dt_resets_hex": "0000000300000001",
        "thermal_dt_resets_hex": "0000000300000000",
        "thermal_dt_phandle_hex": "0000002e",
        "thermal_dt_status": "okay", "thermal_nvmem_cell_names": "calibration-data",
        "auxadc_dt_status": "disabled", "provider_dt_compatible": "mediatek,mt6797-atag-devinfo",
        "provider_dt_read_only": "1", "usb_controller_dt_status": "okay",
        "usb_phy_dt_status": "okay", "keyboard_dt_status": "okay", "simplefb_dt_present": "1",
        "pwrap_driver": "mt-pmic-pwrap", "pwrap_bind_count": "1",
        "mt6351_core_bind_count": "1", "mt6351_regulator_bind_count": "1",
        "thermal_driver": "mtk-thermal", "thermal_bind_count": "1",
        "standalone_auxadc_bind_count": "0", "mmc_driver": "mtk-msdc", "mmc_bind_count": "1",
        "provider_platform_bind_count": "1", "provider_platform_device": "firmware:atag-devinfo",
        "nvmem_provider_count": "1", "nvmem_binary_content_read": "no",
        "vemc_3v3_count": "1", "vio18_count": "1", "mmc_card_count": "1",
        "mmc_card_type": "MMC", "mmcblk0_present": "1", "mmcblk0_partition_count": "33",
        "thermal_zone_count": "1", "thermal_zone_name": "thermal_zone0",
        # Thermal class zones are virtual devices here and expose no child
        # `device` symlink. The unique bound mtk-thermal platform device, one
        # zone, its exact type, successful probe, and live temperatures provide
        # the attribution instead.
        "thermal_zone_type": "soc-thermal", "thermal_zone_device": "none",
        "config_thermal": "1", "config_mtk_thermal": "1", "config_thermal_ledger": "1",
        "config_cpufreq_disabled": "1", "config_cpuidle_disabled": "1", "config_suspend_disabled": "1",
        "pwrap_error_count": "0", "mmc_error_count": "0", "thermal_error_count": "1",
        "device_partition_reads": "none", "device_storage_writes": "none",
        "retained_ram_read_request": "none", "sysfs_write_request": "none",
        "cpu_trigger_request": "none", "load_request": "none", "cpufreq_request": "none",
        "idle_request": "none", "suspend_request": "none",
        "nvmem_binary_content_output": "none", "reboot_request": "none",
    }
    for key, expected_value in expected.items():
        require(values.get(key) == expected_value, key)
    require(values.get("nvmem_provider_name", "").startswith("mt6797-atag-calibration"), "nvmem-provider-name")
    boot_id = values.get("boot_id", "")
    require(bool(UUID.fullmatch(boot_id)), "boot-id")
    require(boot_id != recovery_boot_id, "unchanged-recovery-boot-id")
    defers = list(THERMAL_DEFER.finditer(body))
    successes = list(THERMAL_SUCCESS.finditer(body))
    require(len(defers) == 1, "thermal-defer-count")
    require(len(successes) == 1, "thermal-success-count")
    require(defers[0].start() < successes[0].start(), "thermal-probe-order")
    require("probe of 1100b000.thermal returned 19" not in body, "thermal-enodev")
    temperatures = []
    for index in range(1, 4):
        value = values.get(f"temperature_{index}_millicelsius", "")
        require(bool(SINT.fullmatch(value)), f"temperature-{index}")
        temperature = int(value)
        require(temperature != 0 and -20_000 <= temperature <= 150_000, f"temperature-{index}")
        temperatures.append(temperature)
    return boot_id, tuple(temperatures)  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--recovery-boot-id", required=True)
    args = parser.parse_args()
    try:
        require(bool(UUID.fullmatch(args.recovery_boot_id)), "recovery-boot-id")
        boot_id, temperatures = classify(args.capture.read_text(encoding="utf-8", errors="replace"), args.recovery_boot_id)
    except Rejected as error:
        print("classification=rejected")
        print(f"reason={error}")
        return 3
    print("classification=mt6797-thermal-ledger-live-model-repair-pass")
    print("decision=thermal-runtime-prerequisite-passed")
    print(f"boot_id={boot_id}")
    print("temperatures_millicelsius=" + ",".join(str(value) for value in temperatures))
    print("thermal_probe_sequence=defer-517-then-success")
    print("serviceability=usb-console-pwrap-mt6351-emmc")
    print("cpu_trigger_executed=no")
    print("load_executed=no")
    print("storage_write_executed=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
