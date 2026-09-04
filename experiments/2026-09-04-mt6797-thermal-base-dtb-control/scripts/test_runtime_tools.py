#!/usr/bin/env python3
"""Offline positive and rejection tests for the base-DT runtime tools."""

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
RECOVERY = "11111111-2222-3333-4444-555555555555"
MAINLINE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def load_classifier():
    spec = importlib.util.spec_from_file_location("base_dtb_classifier", CLASSIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame() -> str:
    values = {
        "kernel_release": "7.1.3-gemini-mt6797-thermal-stage-ledger",
        "architecture": "aarch64", "boot_id": MAINLINE,
        "cpu_possible": "0-9", "cpu_present": "0-9",
        "cpu_online": "0-7", "cpu_offline": "8-9",
        "console_active": "tty0 ttyS0", "dt_model": "Planet Computers Gemini PDA",
        "thermal_dt_status": "disabled", "auxadc_dt_status": "disabled",
        "thermal_zone_node": "absent", "pwrap_driver": "mt-pmic-pwrap",
        "pwrap_bind_count": "1", "mt6351_core_bind_count": "1",
        "mt6351_regulator_bind_count": "1", "thermal_driver": "none",
        "thermal_bind_count": "0", "mmc_driver": "mtk-msdc",
        "mmc_bind_count": "1", "vemc_3v3_count": "1", "vio18_count": "1",
        "mmc_card_count": "1", "mmc_card_type": "MMC",
        "mmcblk0_present": "1", "mmcblk0_partition_count": "33",
        "thermal_zone_count": "0", "config_thermal": "1",
        "config_thermal_ledger": "1", "config_cpufreq_disabled": "1",
        "config_cpuidle_disabled": "1", "config_suspend_disabled": "1",
        "pwrap_error_count": "0", "mmc_error_count": "0",
        "thermal_error_count": "0", "device_partition_reads": "none",
        "device_storage_writes": "none", "retained_ram_write_request": "none",
        "temperature_read_request": "none", "cpu_trigger_request": "none",
        "load_request": "none", "cpufreq_request": "none", "idle_request": "none",
        "suspend_request": "none", "reboot_request": "none",
    }
    lines = ["__GEMINI_THERMAL_BASE_DTB_CONTROL_BEGIN__"]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.extend(("dmesg_excerpt_begin", "log: baseline", "dmesg_excerpt_end"))
    lines.append("__GEMINI_THERMAL_BASE_DTB_CONTROL_END__")
    return "\n".join(lines) + "\n"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"fixture token not unique: {old}")
    return text.replace(old, new)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declared_hash(text: str, name: str) -> str:
    match = re.search(rf"^readonly {name}=([0-9a-f]{{64}})$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing pinned hash: {name}")
    return match.group(1)


def main() -> int:
    module = load_classifier()
    good = frame()
    if module.classify(good, RECOVERY) != MAINLINE:
        raise AssertionError("positive fixture failed")
    mutations = (
        ("service-dt", "dt_model=Planet Computers Gemini PDA", "dt_model=Planet Computers Gemini PDA (thermal serviceability)"),
        ("thermal-enabled", "thermal_dt_status=disabled", "thermal_dt_status=okay"),
        ("thermal-bound", "thermal_bind_count=0", "thermal_bind_count=1"),
        ("cpu-loss", "cpu_online=0-7", "cpu_online=0-6"),
        ("console-loss", "console_active=tty0 ttyS0", "console_active=ttyS0"),
        ("pwrap-loss", "pwrap_bind_count=1", "pwrap_bind_count=0"),
        ("emmc-loss", "mmc_bind_count=1", "mmc_bind_count=0"),
        ("storage-write", "device_storage_writes=none", "device_storage_writes=one"),
        ("retained-write", "retained_ram_write_request=none", "retained_ram_write_request=one"),
        ("boot-id", f"boot_id={MAINLINE}", f"boot_id={RECOVERY}"),
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
    for required in ("device_storage_writes=none", "temperature_read_request=none", "retained_ram_write_request=none"):
        if required not in remote:
            raise AssertionError(f"remote observer token absent: {required}")
    collector = COLLECTOR.read_text(encoding="utf-8")
    if declared_hash(collector, "REMOTE_SHA256") != digest(REMOTE):
        raise AssertionError("collector remote hash changed")
    if declared_hash(collector, "CLASSIFIER_SHA256") != digest(CLASSIFIER):
        raise AssertionError("collector classifier hash changed")
    installer = INSTALLER.read_text(encoding="utf-8")
    if installer.count('of="$target"') != 1:
        raise AssertionError("installer target-write count changed")
    for required in (
        "PARTNAME) partname=$value", "partition_backup_created=no",
        "full boot2 readback mismatch", "shutdown_requested=yes-after-verified-readback",
        "experiment revision is not published at origin/main",
    ):
        if required not in installer:
            raise AssertionError(f"installer safety token absent: {required}")
    for forbidden in ("boot2-before.img", 'of="$backup"', "/dev/mmcblk0p30"):
        if forbidden in installer:
            raise AssertionError(f"installer gained forbidden path: {forbidden}")
    print("positive_cases=1")
    print(f"rejection_cases={rejected}")
    print("remote_observer=read-only-static-pass")
    print("collector=source-hashes-pinned")
    print("installer=live-GPT-single-write-static-pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
