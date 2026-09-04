#!/usr/bin/env python3
"""Classify one exact MT6797 PWRAP-reset runtime frame."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BEGIN = "__GEMINI_PWRAP_SERVICEABILITY_BEGIN__"
END = "__GEMINI_PWRAP_SERVICEABILITY_END__"
RELEASE = "7.1.3-gemini-mt6797-pwrap-reset"
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
UINT = re.compile(r"^[0-9]+$")


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


def classify(text: str, recovery_boot_id: str) -> str:
    values = parse(text)
    exact(values, "kernel_release", RELEASE)
    exact(values, "architecture", "aarch64")
    boot_id = values.get("boot_id", "")
    require(bool(UUID.fullmatch(boot_id)), "boot-id")
    require(boot_id != recovery_boot_id, "unchanged-recovery-boot-id")
    for key, expected in (
        ("cpu_possible", "0-9"), ("cpu_present", "0-9"),
        ("cpu_online", "0-7"), ("cpu_offline", "8-9"),
        ("pwrap_dt_resets_hex", "0000000300000001"),
        ("pwrap_driver", "mt-pmic-pwrap"), ("pwrap_bind_count", "1"),
        ("mt6351_core_bind_count", "1"),
        ("mt6351_regulator_bind_count", "1"),
        ("mmc_driver", "mtk-msdc"), ("mmc_bind_count", "1"),
        ("vemc_3v3_count", "1"), ("vio18_count", "1"),
        ("mmc_card_count", "1"), ("mmc_card_type", "MMC"),
        ("mmcblk0_present", "1"), ("mmcblk0_partition_count", "33"),
        ("config_pwrap", "1"), ("config_mt6397", "1"),
        ("config_mt6351_regulator", "1"), ("config_mmc_mtk", "1"),
        ("config_kunit_disabled", "1"), ("config_thermal_disabled", "1"),
        ("config_cpufreq_disabled", "1"), ("config_cpuidle_disabled", "1"),
        ("config_suspend_disabled", "1"),
        ("pwrap_error_count", "0"), ("mmc_error_count", "0"),
        ("thermal_zone_count", "0"), ("cpufreq_policy_count", "0"),
        ("device_partition_reads", "none"), ("device_storage_writes", "none"),
        ("sysfs_write_request", "none"), ("cpu_trigger_request", "none"),
        ("load_request", "none"), ("thermal_value_read", "none"),
        ("reboot_request", "none"),
    ):
        exact(values, key, expected)
    for key in (
        "regulator_count", "mmcblk0_sectors", "pwrap_initcall_success_count",
        "pmic_initcall_success_count", "mt6351_regulator_success_count",
        "mmc_initcall_success_count", "mmc_card_log_count",
    ):
        positive(values, key)
    return boot_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--recovery-boot-id", required=True)
    args = parser.parse_args()
    try:
        require(bool(UUID.fullmatch(args.recovery_boot_id)), "recovery-boot-id")
        boot_id = classify(
            args.capture.read_text(encoding="utf-8", errors="replace"),
            args.recovery_boot_id,
        )
    except Rejected as error:
        print("classification=rejected")
        print(f"reason={error}")
        return 3
    print("classification=pwrap-reset-serviceability-pass")
    print("decision=permit-thermal-reset-attachment")
    print(f"boot_id={boot_id}")
    print("pwrap_reset=source-proven-set-clear")
    print("mt6351_regulators=vemc_3v3-vio18")
    print("emmc=enumerated-read-only-observation")
    print("cpu_trigger_executed=no")
    print("load_executed=no")
    print("thermal_value_read=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
