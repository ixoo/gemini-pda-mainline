#!/usr/bin/env python3
"""Offline positive, mutation, and static tests for runtime/deployment tools."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate-runtime.py"
PROBE = SCRIPT_DIR / "remote-runtime-probe.sh"
COLLECTOR = SCRIPT_DIR / "collect-runtime.sh"
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
SOURCE_INSTALLER = (
    SCRIPT_DIR.parent.parent
    / "2026-08-14-mt6797-runtime-provenance-observer"
    / "scripts/install-boot2.sh"
)
CANDIDATE = "7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564"

spec = importlib.util.spec_from_file_location("runtime_validator", VALIDATOR)
assert spec and spec.loader
runtime_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime_validator)


def marker(*, writes: int = 0, microvolts: int = 720000) -> str:
    return (
        "[    2.000000] da9213-legacy-regulator 1-0068: "
        "da921x-observer-v1 event=bound valid=1 identity_reads=14 providers=2 "
        "provider_read_attempts=4 provider_read_completed=4 "
        f"register_data_writes={writes} buck0_selector=42 buck0_uv={microvolts} "
        "buck0_enabled=1 buck1_selector=70 buck1_uv=1000000 buck1_enabled=1"
    )


def capture(*, dmesg: list[str] | None = None, **changes: str) -> str:
    dmesg = [marker()] if dmesg is None else dmesg
    values = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": "7.1.3-gemini-da921x-observer",
        "architecture": "aarch64",
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "cmdline": "bootopt=64S3,32N2,64N2",
        "bound_marker_count": str(sum("event=bound" in line for line in dmesg)),
        "cleanup_marker_count": str(sum("event=unbind" in line or "event=failed-probe" in line for line in dmesg)),
        "failure_marker_count": str(sum("read-only observation failed" in line for line in dmesg)),
    }
    values.update(changes)
    lines = [runtime_validator.BEGIN]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.append(runtime_validator.DMESG_BEGIN)
    lines.extend(dmesg)
    lines.append(runtime_validator.DMESG_END)
    lines.extend(
        [
            "device_partition_reads=none",
            "device_storage_writes=none",
            "driver_binding_changes=none",
            "hardware_write_request=none",
            "cpu_admission_request=none",
            "reboot_request=none",
            runtime_validator.END,
        ]
    )
    return "\n".join(lines) + "\n"


def outcome(text: str) -> tuple[str, str]:
    try:
        return runtime_validator.classify_text(text)
    except runtime_validator.Classification as result:
        return result.result, result.reason


def require(text: str, expected: str) -> None:
    result = outcome(text)
    assert result[0] == expected, f"expected {expected}, got {result}"


def test_classifier() -> None:
    require(capture(), "success-read-only-provider")
    require(capture(kernel_release="wrong"), "rejected-attribution")
    require(capture(dmesg=[]), "service-failure")
    require(
        capture(dmesg=["[ 2.0] da921x-observer-v1 event=failed-probe providers_released=2 register_data_writes=0"]),
        "provider-failure",
    )
    require(capture(dmesg=["[ 2.0] read-only observation failed: -5"]), "provider-failure")
    require(capture(dmesg=[marker(writes=1)]), "rejected-safety")
    require(capture(cpu_online="0-9", cpu_offline=""), "rejected-safety")
    require(capture(dmesg=[marker(microvolts=710000)]), "rejected-attribution")
    require(capture(dmesg=[marker(), marker()]), "rejected-attribution")


def test_tool_contracts() -> None:
    probe = PROBE.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")
    source_installer = SOURCE_INSTALLER.read_text(encoding="utf-8")
    assert CANDIDATE in probe and CANDIDATE in collector and CANDIDATE in installer
    assert "/bin/busybox dmesg" in probe
    assert "da921x-observer-v1" in probe
    for forbidden in ("/dev/mmc", "systemctl", "poweroff", "shutdown", ">/sys", "> /sys"):
        assert forbidden not in probe, f"probe contains forbidden action: {forbidden}"
    assert "nc -4 -b" in collector
    assert "runtime_probe_transport=stdin-pipe-no-device-file" in collector
    for required in (
        "SOURCE_SHA256=deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8",
        "candidate-da921x-readonly-observer-1a55a25b",
        "136469317f099c2fea7d3c22cabde6cfb6d2c80fb692d9ea7066b43b7cafe0ed",
    ):
        assert required in installer, f"installer wrapper lacks contract: {required}"
    for required in (
        "PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT",
        "/dev/disk/by-partlabel/boot2",
        "/dev/mmcblk0p29",
        "blockdev --flushbufs",
        "independent readback byte mismatch",
        "fresh_predecessor_backup=no",
        "systemctl poweroff",
        "shutdown=confirmed-unreachable",
    ):
        assert required in source_installer, f"source installer lacks contract: {required}"
    help_result = subprocess.run(
        [str(INSTALLER), "--help"], check=True, capture_output=True, text=True
    )
    assert "da921x-readonly-observer-deployment-N" in help_result.stdout
    assert "No fresh partition backup is made" in help_result.stdout


def main() -> None:
    test_classifier()
    test_tool_contracts()
    print("validation=da921x-readonly-observer-runtime-tools-offline")
    print("positive_classification=pass")
    print("negative_mutations_rejected_or_distinguished=8")
    print("installer_source_pinned_derivation=pass")
    print("runtime_probe_read_only_contract=pass")


if __name__ == "__main__":
    main()
