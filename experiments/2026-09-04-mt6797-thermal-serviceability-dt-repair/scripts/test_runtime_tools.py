#!/usr/bin/env python3
"""Offline positive and rejection tests for repaired thermal runtime tools."""

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
RECOVERY_TOOL = SCRIPT_DIR / "request_native_recovery.sh"
RECOVERY = "11111111-2222-3333-4444-555555555555"
MAINLINE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
CAPTURED_MAINLINE = "3e6d06e4-b89f-4db5-b292-c5df56dc6372"


def load_classifier():
    spec = importlib.util.spec_from_file_location("thermal_dt_repair_classifier", CLASSIFIER)
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
        "console_active": "tty0 ttyS0",
        "dt_model": "Planet Computers Gemini PDA (thermal serviceability)",
        "pwrap_dt_resets_hex": "0000000300000001",
        "thermal_dt_resets_hex": "0000000300000000",
        "thermal_dt_phandle_hex": "0000002e", "thermal_dt_status": "okay",
        "thermal_nvmem_cell_names": "calibration-data",
        "auxadc_dt_status": "disabled",
        "provider_dt_compatible": "mediatek,mt6797-atag-devinfo",
        "provider_dt_read_only": "1", "usb_controller_dt_status": "okay",
        "usb_phy_dt_status": "okay", "keyboard_dt_status": "okay",
        "simplefb_dt_present": "1", "pwrap_driver": "mt-pmic-pwrap",
        "pwrap_bind_count": "1", "mt6351_core_bind_count": "1",
        "mt6351_regulator_bind_count": "1", "thermal_driver": "mtk-thermal",
        "thermal_bind_count": "1", "standalone_auxadc_bind_count": "0",
        "mmc_driver": "mtk-msdc", "mmc_bind_count": "1",
        "provider_platform_bind_count": "1",
        "provider_platform_device": "firmware:atag-devinfo",
        "nvmem_provider_count": "1",
        "nvmem_provider_name": "mt6797-atag-calibration0",
        "nvmem_binary_content_read": "no", "vemc_3v3_count": "1",
        "vio18_count": "1", "mmc_card_count": "1", "mmc_card_type": "MMC",
        "mmcblk0_present": "1", "mmcblk0_partition_count": "33",
        "thermal_zone_count": "1", "thermal_zone_name": "thermal_zone0",
        "thermal_zone_type": "soc-thermal",
        "thermal_zone_device": "1100b000.thermal",
        "temperature_1_millicelsius": "38000",
        "temperature_2_millicelsius": "39000",
        "temperature_3_millicelsius": "38500", "config_thermal": "1",
        "config_mtk_thermal": "1", "config_thermal_ledger": "1",
        "config_cpufreq_disabled": "1", "config_cpuidle_disabled": "1",
        "config_suspend_disabled": "1", "pwrap_error_count": "0",
        "mmc_error_count": "0", "thermal_error_count": "0",
        "device_partition_reads": "none", "device_storage_writes": "none",
        "retained_ram_read_request": "none", "sysfs_write_request": "none",
        "cpu_trigger_request": "none", "load_request": "none",
        "cpufreq_request": "none", "idle_request": "none",
        "suspend_request": "none", "nvmem_binary_content_output": "none",
        "reboot_request": "none",
    }
    lines = ["__GEMINI_THERMAL_DT_REPAIR_BEGIN__"]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.extend(("dmesg_excerpt_begin", "log: baseline", "dmesg_excerpt_end"))
    lines.append("__GEMINI_THERMAL_DT_REPAIR_END__")
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
    expected = (MAINLINE, (38_000, 39_000, 38_500))
    if module.classify(good, RECOVERY) != expected:
        raise AssertionError("positive fixture failed")
    mutations = (
        ("base-dt", "dt_model=Planet Computers Gemini PDA (thermal serviceability)", "dt_model=Planet Computers Gemini PDA"),
        ("pwrap-reset", "pwrap_dt_resets_hex=0000000300000001", "pwrap_dt_resets_hex=0000000300000040"),
        ("thermal-reset", "thermal_dt_resets_hex=0000000300000000", "thermal_dt_resets_hex=missing"),
        ("usb-disabled", "usb_controller_dt_status=okay", "usb_controller_dt_status=disabled"),
        ("thermal-unbound", "thermal_bind_count=1", "thermal_bind_count=0"),
        ("zone-missing", "thermal_zone_count=1", "thermal_zone_count=0"),
        ("zero-temperature", "temperature_2_millicelsius=39000", "temperature_2_millicelsius=0"),
        ("cpu-loss", "cpu_online=0-7", "cpu_online=0-6"),
        ("console-loss", "console_active=tty0 ttyS0", "console_active=ttyS0"),
        ("emmc-loss", "mmc_bind_count=1", "mmc_bind_count=0"),
        ("storage-write", "device_storage_writes=none", "device_storage_writes=one"),
        ("sysfs-write", "sysfs_write_request=none", "sysfs_write_request=one"),
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
    for required in (
        "device_storage_writes=none", "retained_ram_read_request=none",
        "sysfs_write_request=none", "temperature_3_millicelsius=%s",
    ):
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
        "shutdown_tcp22_closed_samples=3",
    ):
        if required not in installer:
            raise AssertionError(f"installer safety token absent: {required}")
    for forbidden in ("boot2-before.img", 'of="$backup"', "/dev/mmcblk0p30"):
        if forbidden in installer:
            raise AssertionError(f"installer gained forbidden path: {forbidden}")
    if 'if ! ssh -n "${ssh_options[@]}" "$TARGET" true' in installer:
        raise AssertionError("installer mistakes command-channel failure for poweroff")
    if "ServerAliveInterval=2" not in collector or "ServerAliveCountMax=2" not in collector:
        raise AssertionError("collector Gemian probe is not bounded after authentication")
    recovery_tool = RECOVERY_TOOL.read_text(encoding="utf-8")
    for required in (
        f"readonly MAINLINE_BOOT_ID={CAPTURED_MAINLINE}",
        "readonly INSTALLED_FULL_SHA256=ca3c25889b92673aa341fa97fc347c3469bc3b532d81045659a3afa1f563636a",
        "readonly FRAME_SHA256=969735f26636c12fb06eb96f2f484f2eb6dfb02f2e7369f2d5501630e88fa364",
        "device_partition_reads=none device_storage_writes=none",
        "request_count=1",
    ):
        if required not in recovery_tool:
            raise AssertionError(f"native recovery safety token absent: {required}")
    for forbidden in ("/dev/mmcblk", "poweroff", "reboot -f"):
        if forbidden in recovery_tool:
            raise AssertionError(f"native recovery gained forbidden token: {forbidden}")
    print("positive_cases=1")
    print(f"rejection_cases={rejected}")
    print("remote_observer=read-only-static-pass")
    print("collector=source-hashes-pinned")
    print("installer=live-GPT-single-write-static-pass")
    print("native_recovery=exact-failed-frame-no-partition-static-pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
