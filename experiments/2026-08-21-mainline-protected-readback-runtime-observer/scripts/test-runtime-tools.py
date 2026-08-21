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
CANDIDATE = "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a"

spec = importlib.util.spec_from_file_location("runtime_validator", VALIDATOR)
assert spec and spec.loader
runtime_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime_validator)


def clock(*, ret: int = 0, generation: int = 1) -> str:
    return (
        f"[    2.000000] {runtime_validator.TAG} clock ret={ret} abi=1 "
        f"generation={generation} muxsel=0x00000001 ckdiv=0x00000002 "
        "pll_ll=0x00000003,0x00000004,0x00000005 "
        "pll_l=0x00000006,0x00000007,0x00000008 "
        "pll_cci=0x00000009,0x0000000a,0x0000000b "
        "cspm_swctrl=0x0000000c,0x0000000d,0x0000000e "
        "cspm_hwsta=0x0000000f,0x00000010,0x00000011,0x00000012"
    )


def bigidvfs(*, ret: int = 0, generation: int = 1) -> str:
    return (
        f"[    2.000001] {runtime_validator.TAG} bigidvfs ret={ret} abi=1 "
        f"generation={generation} pll_pcw=0x00000013 pll_enable_posdiv=0x00000014 "
        "sram_selector=0x00000015 control=0x00000016"
    )


def complete() -> str:
    return f"[    2.000002] {runtime_validator.COMPLETE}"


def capture(*, dmesg: list[str] | None = None, **changes: str) -> str:
    dmesg = [clock(), bigidvfs(), complete()] if dmesg is None else dmesg
    values = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": "7.1.3-gemini-protected-readback-ro",
        "architecture": "aarch64",
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "uptime_seconds": "12.34",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "cmdline": "console=ttyS0 maxcpus=8 rdinit=/init",
        "model": "Planet Computers Gemini PDA (protected readback observer)",
        "clock_record_count": str(sum(f"{runtime_validator.TAG} clock " in line for line in dmesg)),
        "bigidvfs_record_count": str(sum(f"{runtime_validator.TAG} bigidvfs " in line for line in dmesg)),
        "completion_record_count": str(sum(f"{runtime_validator.TAG} state=complete " in line for line in dmesg)),
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
            "secure_write_request=none",
            "owner_registration_request=none",
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
    require(capture(), "success-protected-readback")
    require(capture(kernel_release="wrong"), "rejected-attribution")
    require(capture(cpu_online="0-9", cpu_offline=""), "rejected-safety")
    require(capture(cmdline="console=ttyS0"), "rejected-safety")
    require(capture(dmesg=[]), "rejected-attribution")
    require(capture(dmesg=[clock(ret=-5), bigidvfs(), complete()]), "transport-failure")
    require(capture(dmesg=[clock(generation=2), bigidvfs(), complete()]), "rejected-attribution")
    require(capture(dmesg=[clock(), bigidvfs(), complete(), clock()]), "rejected-attribution")
    require(
        capture(
            dmesg=[
                clock(),
                bigidvfs(),
                complete().replace("cpu_requests=0", "cpu_requests=1"),
            ]
        ),
        "rejected-safety",
    )
    require(capture(model="Planet Computers Gemini PDA"), "rejected-attribution")


def test_tool_contracts() -> None:
    probe = PROBE.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")
    source_installer = SOURCE_INSTALLER.read_text(encoding="utf-8")
    assert CANDIDATE in probe and CANDIDATE in collector and CANDIDATE in installer
    assert "/bin/busybox dmesg" in probe
    assert runtime_validator.TAG in probe
    for forbidden in ("/dev/mmc", "systemctl", "poweroff", "shutdown", ">/sys", "> /sys"):
        assert forbidden not in probe, f"probe contains forbidden action: {forbidden}"
    assert "nc -4 -b" in collector
    assert "runtime_probe_transport=stdin-pipe-no-device-file" in collector
    for required in (
        "SOURCE_SHA256=deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8",
        "candidate-protected-readback-ro-a3cb0e1c",
        "f1ceff04a7631af3ee2c3b3614d9fd025f956a2453a75b0cc6d3fd6cde24580a",
        "EXPECTED_TEE_SHA256",
        "resolve_tee",
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
    assert "protected-readback-deployment-N" in help_result.stdout
    assert "No fresh partition backup is made" in help_result.stdout


def main() -> None:
    test_classifier()
    test_tool_contracts()
    print("validation=protected-readback-runtime-tools-offline")
    print("positive_classification=pass")
    print("negative_mutations_rejected_or_distinguished=9")
    print("installer_source_pinned_derivation=pass")
    print("live_tee_identity_gate=pass")
    print("runtime_probe_read_only_contract=pass")


if __name__ == "__main__":
    main()
