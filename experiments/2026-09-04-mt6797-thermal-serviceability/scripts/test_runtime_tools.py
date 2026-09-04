#!/usr/bin/env python3
"""Offline positive and rejection tests for thermal runtime tooling."""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CLASSIFIER = SCRIPT_DIR / "classify_observation.py"
REMOTE = SCRIPT_DIR / "remote_observe.sh"
COLLECTOR = SCRIPT_DIR / "collect_runtime.sh"
INSTALLER = SCRIPT_DIR / "install_boot2.sh"
REBOOT = SCRIPT_DIR / "request_native_reboot.sh"
RECOVERY = "11111111-2222-3333-4444-555555555555"
MAINLINE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def load_classifier():
    spec = importlib.util.spec_from_file_location("thermal_classifier", CLASSIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame() -> str:
    values = {
        "kernel_release": "7.1.3-gemini-mt6797-thermal-serviceability",
        "architecture": "aarch64",
        "boot_id": MAINLINE,
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "console_active": "tty0 ttyS0",
        "dt_model": "Planet Computers Gemini PDA (thermal serviceability)",
        "pwrap_dt_resets_hex": "0000000d00000001",
        "thermal_dt_resets_hex": "0000000d00000000",
        "thermal_dt_status": "okay",
        "thermal_nvmem_cell_names": "calibration-data",
        "auxadc_dt_status": "disabled",
        "provider_dt_compatible": "mediatek,mt6797-atag-devinfo",
        "provider_dt_read_only": "1",
        "pwrap_driver": "mt-pmic-pwrap",
        "pwrap_bind_count": "1",
        "mt6351_core_bind_count": "1",
        "mt6351_regulator_bind_count": "1",
        "thermal_driver": "mtk-thermal",
        "thermal_bind_count": "1",
        "standalone_auxadc_bind_count": "0",
        "mmc_driver": "mtk-msdc",
        "mmc_bind_count": "1",
        "provider_platform_bind_count": "1",
        "provider_platform_device": "firmware:atag-devinfo",
        "provider_driver": "mediatek-mt6797-atag-devinfo",
        "nvmem_provider_count": "1",
        "nvmem_provider_name": "mt6797-atag-calibration0",
        "nvmem_binary_content_read": "no",
        "regulator_count": "27",
        "vemc_3v3_count": "1",
        "vio18_count": "1",
        "mmc_card_count": "1",
        "mmc_card_type": "MMC",
        "mmcblk0_present": "1",
        "mmcblk0_partition_count": "33",
        "mmcblk0_sectors": "122142720",
        "thermal_zone_count": "1",
        "thermal_zone_name": "thermal_zone0",
        "thermal_zone_type": "soc-thermal",
        "thermal_zone_device": "1100b000.thermal",
        "temperature_1_millicelsius": "42000",
        "temperature_2_millicelsius": "42100",
        "temperature_3_millicelsius": "41900",
        "cpufreq_policy_count": "0",
        "config_pwrap": "1",
        "config_mt6351_regulator": "1",
        "config_mmc_mtk": "1",
        "config_thermal": "1",
        "config_thermal_of": "1",
        "config_mtk_thermal": "1",
        "config_nvmem": "1",
        "config_atag_nvmem": "1",
        "config_kunit_disabled": "1",
        "config_cpufreq_disabled": "1",
        "config_cpuidle_disabled": "1",
        "config_suspend_disabled": "1",
        "pwrap_error_count": "0",
        "mmc_error_count": "0",
        "provider_error_count": "0",
        "thermal_error_count": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "sysfs_write_request": "none",
        "cpu_trigger_request": "none",
        "load_request": "none",
        "cpufreq_request": "none",
        "idle_request": "none",
        "suspend_request": "none",
        "nvmem_binary_content_output": "none",
        "reboot_request": "none",
    }
    lines = ["__GEMINI_THERMAL_SERVICEABILITY_BEGIN__"]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.extend(("dmesg_excerpt_begin", "log: probe returned 0", "dmesg_excerpt_end"))
    lines.append("__GEMINI_THERMAL_SERVICEABILITY_END__")
    return "\n".join(lines) + "\n"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"fixture token is not unique: {old}")
    return text.replace(old, new)


def declared_hash(text: str, name: str) -> str:
    match = re.search(rf"^readonly {name}=([0-9a-f]{{64}})$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing pinned hash: {name}")
    return match.group(1)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    module = load_classifier()
    good = frame()
    boot_id, temperatures = module.classify(good, RECOVERY)
    if boot_id != MAINLINE or temperatures != (42000, 42100, 41900):
        raise AssertionError("positive classifier fixture failed")
    mutations = (
        ("thermal-reset", "thermal_dt_resets_hex=0000000d00000000", "thermal_dt_resets_hex=0000000d00000001"),
        ("auxadc-enabled", "auxadc_dt_status=disabled", "auxadc_dt_status=okay"),
        ("provider-unbound", "provider_platform_bind_count=1", "provider_platform_bind_count=0"),
        ("thermal-unbound", "thermal_bind_count=1", "thermal_bind_count=0"),
        ("zone-missing", "thermal_zone_count=1", "thermal_zone_count=0"),
        ("wrong-zone", "thermal_zone_type=soc-thermal", "thermal_zone_type=x86_pkg_temp"),
        ("zero-temperature", "temperature_1_millicelsius=42000", "temperature_1_millicelsius=0"),
        ("high-temperature", "temperature_2_millicelsius=42100", "temperature_2_millicelsius=151000"),
        ("thermal-error", "thermal_error_count=0", "thermal_error_count=1"),
        ("pwrap-loss", "pwrap_bind_count=1", "pwrap_bind_count=0"),
        ("regulator-missing", "vemc_3v3_count=1", "vemc_3v3_count=0"),
        ("emmc-error", "mmc_error_count=0", "mmc_error_count=1"),
        ("cpu-loss", "cpu_online=0-7", "cpu_online=0-6"),
        ("console-loss", "console_active=tty0 ttyS0", "console_active=ttyS0"),
        ("storage-write", "device_storage_writes=none", "device_storage_writes=one"),
    )
    rejected = 0
    for name, old, new in mutations:
        try:
            module.classify(replace_once(good, old, new), RECOVERY)
        except module.Rejected:
            rejected += 1
        else:
            raise AssertionError(f"mutation accepted: {name}")

    remote = REMOTE.read_text(encoding="utf-8")
    for forbidden in ("/dev/mmcblk", " dd ", "cpu*/online", ">/sys", "> /sys"):
        if forbidden in remote:
            raise AssertionError(f"remote observer gained forbidden token: {forbidden}")
    for required in (
        "temperature_1_millicelsius",
        "temperature_2_millicelsius",
        "temperature_3_millicelsius",
        "nvmem_binary_content_read=no",
        '[ "$($BB basename "$item")" = module ] && continue',
    ):
        if required not in remote:
            raise AssertionError(f"remote observer token absent: {required}")

    collector = COLLECTOR.read_text(encoding="utf-8")
    if declared_hash(collector, "REMOTE_SHA256") != digest(REMOTE):
        raise AssertionError("collector remote-observer hash changed")
    if declared_hash(collector, "CLASSIFIER_SHA256") != digest(CLASSIFIER):
        raise AssertionError("collector classifier hash changed")

    installer = INSTALLER.read_text(encoding="utf-8")
    if installer.count('of="$target"') != 1:
        raise AssertionError("installer target-write count changed")
    for required in (
        "PARTNAME) partname=$value",
        "partition_backup_created=no",
        "full boot2 readback mismatch",
        "shutdown_requested=yes-after-verified-readback",
        "current experiment revision is not published at origin/main",
    ):
        if required not in installer:
            raise AssertionError(f"installer safety token absent: {required}")
    for forbidden in ("boot2-before.img", 'of="$backup"', "/dev/mmcblk0p30"):
        if forbidden in installer:
            raise AssertionError(f"installer gained forbidden fixed/backup path: {forbidden}")

    reboot = REBOOT.read_text(encoding="utf-8")
    if "/dev/mmc" in reboot or "device_partition_reads=none" not in reboot:
        raise AssertionError("native reboot path gained partition access")
    if declared_hash(reboot, "CLASSIFIER_SHA256") != digest(CLASSIFIER):
        raise AssertionError("native reboot classifier hash changed")
    for required in ("/request_authorized=yes$/", "exit yes != 1 || no != 0"):
        if required not in reboot:
            raise AssertionError("native reboot parser lost prompt-tolerant exact gate")

    print("positive_cases=1")
    print(f"rejection_cases={rejected}")
    print("remote_observer=read-only-static-pass")
    print("collector=source-hashes-pinned")
    print("installer=live-GPT-single-write-static-pass")
    print("native_reboot=no-partition-static-pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
