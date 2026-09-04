#!/usr/bin/env python3
"""Offline positive and rejection tests for the runtime classifier."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CLASSIFIER = SCRIPT_DIR / "classify_observation.py"
REMOTE = SCRIPT_DIR / "remote_observe.sh"
INSTALLER = SCRIPT_DIR / "install_boot2.sh"
REBOOT = SCRIPT_DIR / "request_native_reboot.sh"
RECOVERY = "11111111-2222-3333-4444-555555555555"
MAINLINE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def load_classifier():
    spec = importlib.util.spec_from_file_location("pwrap_classifier", CLASSIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame() -> str:
    values = {
        "kernel_release": "7.1.3-gemini-mt6797-pwrap-reset",
        "architecture": "aarch64",
        "boot_id": MAINLINE,
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "pwrap_dt_resets_hex": "0000000300000001",
        "pwrap_driver": "mt-pmic-pwrap",
        "pwrap_bind_count": "1",
        "mt6351_core_bind_count": "1",
        "mt6351_regulator_bind_count": "1",
        "mmc_driver": "mtk-msdc",
        "mmc_bind_count": "1",
        "regulator_count": "27",
        "vemc_3v3_count": "1",
        "vio18_count": "1",
        "mmc_card_count": "1",
        "mmc_card_type": "MMC",
        "mmcblk0_present": "1",
        "mmcblk0_partition_count": "33",
        "mmcblk0_sectors": "122142720",
        "config_pwrap": "1",
        "config_mt6397": "1",
        "config_mt6351_regulator": "1",
        "config_mmc_mtk": "1",
        "config_kunit_disabled": "1",
        "config_thermal_disabled": "1",
        "config_cpufreq_disabled": "1",
        "config_cpuidle_disabled": "1",
        "config_suspend_disabled": "1",
        "pwrap_initcall_success_count": "1",
        "pmic_initcall_success_count": "1",
        "mt6351_regulator_success_count": "1",
        "mmc_initcall_success_count": "1",
        "mmc_card_log_count": "1",
        "pwrap_error_count": "0",
        "mmc_error_count": "0",
        "thermal_zone_count": "0",
        "cpufreq_policy_count": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "sysfs_write_request": "none",
        "cpu_trigger_request": "none",
        "load_request": "none",
        "thermal_value_read": "none",
        "reboot_request": "none",
    }
    lines = ["__GEMINI_PWRAP_SERVICEABILITY_BEGIN__"]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.extend(("dmesg_excerpt_begin", "log: probe returned 0", "dmesg_excerpt_end"))
    lines.append("__GEMINI_PWRAP_SERVICEABILITY_END__")
    return "\n".join(lines) + "\n"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"fixture token is not unique: {old}")
    return text.replace(old, new)


def main() -> int:
    module = load_classifier()
    good = frame()
    if module.classify(good, RECOVERY) != MAINLINE:
        raise AssertionError("positive classifier fixture failed")
    mutations = (
        ("reset-id", "pwrap_dt_resets_hex=0000000300000001", "pwrap_dt_resets_hex=0000000300000040"),
        ("pwrap-unbound", "pwrap_bind_count=1", "pwrap_bind_count=0"),
        ("regulator-missing", "vemc_3v3_count=1", "vemc_3v3_count=0"),
        ("emmc-error", "mmc_error_count=0", "mmc_error_count=1"),
        ("cpu-loss", "cpu_online=0-7", "cpu_online=0-6"),
        ("storage-write", "device_storage_writes=none", "device_storage_writes=one"),
        ("thermal-surface", "thermal_zone_count=0", "thermal_zone_count=1"),
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
    if '[ "$($BB basename "$item")" = module ] && continue' not in remote:
        raise AssertionError("driver binding count does not exclude module symlink")
    installer = INSTALLER.read_text(encoding="utf-8")
    if installer.count('of="$target"') != 1:
        raise AssertionError("installer target-write count changed")
    for required in (
        "PARTNAME) partname=$value",
        "partition_backup_created=no",
        "full boot2 readback mismatch",
        "shutdown_requested=yes-after-verified-readback",
    ):
        if required not in installer:
            raise AssertionError(f"installer safety token absent: {required}")
    for forbidden in ("boot2-before.img", 'of="$backup"', "/dev/mmcblk0p30"):
        if forbidden in installer:
            raise AssertionError(f"installer gained forbidden fixed/backup path: {forbidden}")
    reboot = REBOOT.read_text(encoding="utf-8")
    if "/dev/mmc" in reboot or "device_partition_reads=none" not in reboot:
        raise AssertionError("native reboot path gained partition access")
    for required in (
        "/request_authorized=yes$/",
        "exit yes != 1 || no != 0",
    ):
        if required not in reboot:
            raise AssertionError("native reboot parser lost prompt-tolerant exact gate")
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "frame.txt"
        path.write_text(good, encoding="utf-8")
        if module.classify(path.read_text(encoding="utf-8"), RECOVERY) != MAINLINE:
            raise AssertionError("serialized fixture failed")
    print("positive_cases=1")
    print(f"rejection_cases={rejected}")
    print("remote_observer=read-only-static-pass")
    print("installer=live-GPT-single-write-static-pass")
    print("native_reboot=no-partition-static-pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
