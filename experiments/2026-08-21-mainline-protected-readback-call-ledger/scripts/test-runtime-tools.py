#!/usr/bin/env python3
"""Offline positive, mutation, and static tests for call-ledger runtime tools."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
CLASSIFIER = SCRIPT_DIR / "classify-retained.py"
VALIDATOR = SCRIPT_DIR / "validate-runtime.sh"
PROBE = SCRIPT_DIR / "remote-runtime-probe.sh"
COLLECTOR = SCRIPT_DIR / "collect-runtime.sh"
CANDIDATE = "3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a"
TAG = "GEMINI_PROTECTED_READBACK_V1"


spec = importlib.util.spec_from_file_location("retained_classifier", CLASSIFIER)
assert spec and spec.loader
retained = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retained)


def clock() -> str:
    return (
        f"[    2.000000] {TAG} clock ret=0 abi=1 generation=1 "
        "muxsel=0x00000001 ckdiv=0x00000002 "
        "pll_ll=0x00000003,0x00000004,0x00000005 "
        "pll_l=0x00000006,0x00000007,0x00000008 "
        "pll_cci=0x00000009,0x0000000a,0x0000000b "
        "cspm_swctrl=0x0000000c,0x0000000d,0x0000000e "
        "cspm_hwsta=0x0000000f,0x00000010,0x00000011,0x00000012"
    )


def bigidvfs() -> str:
    return (
        f"[    2.000001] {TAG} bigidvfs ret=0 abi=1 generation=1 "
        "pll_pcw=0x00000013 pll_enable_posdiv=0x00000014 "
        "sram_selector=0x00000015 control=0x00000016"
    )


def usb_capture(*, release: str = "7.1.3-gemini-protected-readback-ledger") -> str:
    complete = (
        f"[    2.000002] {TAG} state=complete attempts=1 clock_calls=1 "
        "bigidvfs_calls=1 cpu_requests=0 owner_registration=0"
    )
    lines = [
        "__PROTECTED_READBACK_RUNTIME_BEGIN__",
        f"installed_full_sha256={CANDIDATE}",
        f"kernel_release={release}",
        "architecture=aarch64",
        "boot_id=11111111-2222-3333-4444-555555555555",
        "uptime_seconds=12.34",
        "cpu_possible=0-9",
        "cpu_present=0-9",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "cmdline=console=ttyS0 maxcpus=8 rdinit=/init",
        "model=Planet Computers Gemini PDA (protected readback observer)",
        "clock_record_count=1",
        "bigidvfs_record_count=1",
        "completion_record_count=1",
        "__PROTECTED_READBACK_DMESG_BEGIN__",
        clock(),
        bigidvfs(),
        complete,
        "__PROTECTED_READBACK_DMESG_END__",
        "device_partition_reads=none",
        "device_storage_writes=none",
        "driver_binding_changes=none",
        "secure_write_request=none",
        "owner_registration_request=none",
        "cpu_admission_request=none",
        "reboot_request=none",
        "__PROTECTED_READBACK_RUNTIME_END__",
    ]
    return "\n".join(lines) + "\n"


def test_retained_classifier() -> None:
    assert retained.classify_payload(b"")[:2] == (
        "neither",
        "observer-entry-or-ledger-gate-not-established",
    )
    assert retained.classify_payload(retained.BEFORE)[:2] == (
        "before-clock-only",
        "protected-clock-call-did-not-return",
    )
    assert retained.classify_payload(retained.BEFORE + retained.AFTER)[:2] == (
        "before-and-after-clock",
        "clock-returned-failure-at-or-after-bigidvfs",
    )
    assert retained.classify_payload(retained.AFTER)[0] == "rejected-attribution"
    assert retained.classify_payload(retained.BEFORE * 2)[0] == "rejected-attribution"
    assert retained.classify_payload(retained.PREFIX + b"foreign\n")[0] == "rejected-attribution"


def test_usb_validator() -> None:
    with tempfile.TemporaryDirectory() as directory:
        capture = Path(directory) / "runtime.txt"
        capture.write_text(usb_capture(), encoding="utf-8")
        accepted = subprocess.run(
            [str(VALIDATOR), str(capture)], capture_output=True, text=True, check=False
        )
        assert accepted.returncode == 0, accepted.stdout + accepted.stderr
        assert "runtime_classification=success-protected-readback" in accepted.stdout
        capture.write_text(usb_capture(release="wrong"), encoding="utf-8")
        rejected = subprocess.run(
            [str(VALIDATOR), str(capture)], capture_output=True, text=True, check=False
        )
        assert rejected.returncode == 3
        assert "runtime_classification=rejected-attribution" in rejected.stdout


def test_static_contracts() -> None:
    probe = PROBE.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    assert CANDIDATE in probe and CANDIDATE in collector
    assert "/bin/busybox dmesg" in probe
    for forbidden in ("/dev/mmc", "systemctl", "poweroff", "shutdown", ">/sys", "> /sys"):
        assert forbidden not in probe, f"probe contains forbidden action: {forbidden}"
    help_result = subprocess.run(
        [str(COLLECTOR), "--help"], capture_output=True, text=True, check=True
    )
    assert "protected-readback-call-ledger-attempt-N" in (
        help_result.stdout + help_result.stderr
    )


def main() -> None:
    test_retained_classifier()
    test_usb_validator()
    test_static_contracts()
    print("validation=protected-readback-call-ledger-runtime-tools-offline")
    print("retained_decision_branches=3")
    print("retained_negative_mutations_rejected=3")
    print("usb_positive_classification=pass")
    print("usb_negative_mutations_rejected=1")
    print("runtime_probe_read_only_contract=pass")
    print("device_access=none")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
