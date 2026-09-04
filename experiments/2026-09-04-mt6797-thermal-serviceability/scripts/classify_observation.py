#!/usr/bin/env python3
"""Classify one exact MT6797 thermal-serviceability runtime frame."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BEGIN = "__GEMINI_THERMAL_SERVICEABILITY_BEGIN__"
END = "__GEMINI_THERMAL_SERVICEABILITY_END__"
RELEASE = "7.1.3-gemini-mt6797-thermal-serviceability"
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
UINT = re.compile(r"^[0-9]+$")
SINT = re.compile(r"^-?[0-9]+$")


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


def exact(values: dict[str, str], key: str, expected: str) -> None:
    require(values.get(key) == expected, key)


def positive(values: dict[str, str], key: str) -> None:
    value = values.get(key, "")
    require(bool(UINT.fullmatch(value)) and int(value) >= 1, key)


def plausible_temperature(values: dict[str, str], key: str) -> int:
    value = values.get(key, "")
    require(bool(SINT.fullmatch(value)), key)
    temperature = int(value)
    require(temperature != 0 and -20_000 <= temperature <= 150_000, key)
    return temperature


def classify(text: str, recovery_boot_id: str) -> tuple[str, tuple[int, int, int]]:
    values = parse(text)
    exact(values, "kernel_release", RELEASE)
    exact(values, "architecture", "aarch64")
    boot_id = values.get("boot_id", "")
    require(bool(UUID.fullmatch(boot_id)), "boot-id")
    require(boot_id != recovery_boot_id, "unchanged-recovery-boot-id")
    for key, expected in (
        ("cpu_possible", "0-9"), ("cpu_present", "0-9"),
        ("cpu_online", "0-7"), ("cpu_offline", "8-9"),
        ("dt_model", "Planet Computers Gemini PDA (thermal serviceability)"),
        ("pwrap_dt_resets_hex", "0000000d00000001"),
        ("thermal_dt_resets_hex", "0000000d00000000"),
        ("thermal_dt_status", "okay"),
        ("thermal_nvmem_cell_names", "calibration-data"),
        ("auxadc_dt_status", "disabled"),
        ("provider_dt_compatible", "mediatek,mt6797-atag-devinfo"),
        ("provider_dt_read_only", "1"),
        ("pwrap_driver", "mt-pmic-pwrap"), ("pwrap_bind_count", "1"),
        ("mt6351_core_bind_count", "1"),
        ("mt6351_regulator_bind_count", "1"),
        ("thermal_driver", "mtk-thermal"), ("thermal_bind_count", "1"),
        ("standalone_auxadc_bind_count", "0"),
        ("mmc_driver", "mtk-msdc"), ("mmc_bind_count", "1"),
        ("provider_platform_bind_count", "1"),
        ("provider_platform_device", "firmware:atag-devinfo"),
        ("provider_driver", "mediatek-mt6797-atag-devinfo"),
        ("nvmem_provider_count", "1"),
        ("nvmem_binary_content_read", "no"),
        ("vemc_3v3_count", "1"), ("vio18_count", "1"),
        ("mmc_card_count", "1"), ("mmc_card_type", "MMC"),
        ("mmcblk0_present", "1"), ("mmcblk0_partition_count", "33"),
        ("thermal_zone_count", "1"), ("thermal_zone_name", "thermal_zone0"),
        ("thermal_zone_type", "soc-thermal"),
        ("thermal_zone_device", "1100b000.thermal"),
        ("cpufreq_policy_count", "0"),
        ("config_pwrap", "1"), ("config_mt6351_regulator", "1"),
        ("config_mmc_mtk", "1"), ("config_thermal", "1"),
        ("config_thermal_of", "1"), ("config_mtk_thermal", "1"),
        ("config_nvmem", "1"), ("config_atag_nvmem", "1"),
        ("config_kunit_disabled", "1"), ("config_cpufreq_disabled", "1"),
        ("config_cpuidle_disabled", "1"), ("config_suspend_disabled", "1"),
        ("pwrap_error_count", "0"), ("mmc_error_count", "0"),
        ("provider_error_count", "0"), ("thermal_error_count", "0"),
        ("device_partition_reads", "none"), ("device_storage_writes", "none"),
        ("sysfs_write_request", "none"), ("cpu_trigger_request", "none"),
        ("load_request", "none"), ("cpufreq_request", "none"),
        ("idle_request", "none"), ("suspend_request", "none"),
        ("nvmem_binary_content_output", "none"), ("reboot_request", "none"),
    ):
        exact(values, key, expected)
    require("tty0" in values.get("console_active", "").split(), "console-active")
    require(values.get("nvmem_provider_name", "").startswith("mt6797-atag-calibration"),
            "nvmem-provider-name")
    for key in ("regulator_count", "mmcblk0_sectors"):
        positive(values, key)
    temperatures = tuple(
        plausible_temperature(values, f"temperature_{index}_millicelsius")
        for index in range(1, 4)
    )
    return boot_id, temperatures  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--recovery-boot-id", required=True)
    args = parser.parse_args()
    try:
        require(bool(UUID.fullmatch(args.recovery_boot_id)), "recovery-boot-id")
        boot_id, temperatures = classify(
            args.capture.read_text(encoding="utf-8", errors="replace"),
            args.recovery_boot_id,
        )
    except Rejected as error:
        print("classification=rejected")
        print(f"reason={error}")
        return 3
    print("classification=mt6797-thermal-serviceability-pass")
    print("decision=accept-thermal-prerequisite-and-advance-cpu8-cpu9-chain")
    print(f"boot_id={boot_id}")
    print("temperatures_millicelsius=" + ",".join(str(value) for value in temperatures))
    print("calibration_provider=bound-read-only")
    print("thermal_driver=bound-one-zone-three-plausible-reads")
    print("pwrap_mt6351_emmc=serviceable")
    print("cpu_trigger_executed=no")
    print("load_executed=no")
    print("storage_write_executed=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
