#!/usr/bin/env python3
"""Offline positive, mutation, and static tests for checkpoint tooling."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate-runtime.py"
PROBE = SCRIPT_DIR / "remote-runtime-probe.sh"
COLLECTOR = SCRIPT_DIR / "collect-runtime.sh"
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
CANDIDATE = "ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348"
MARKER = "GEMINI_MAINLINE_POST_RAMOOPS_20260815_A"

spec = importlib.util.spec_from_file_location("post_ramoops_validator", VALIDATOR)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def capture(*, dmesg: list[str] | None = None, **changes: str) -> str:
    marker = f"[    0.500000] {MARKER} checkpoint=ramoops-registered"
    dmesg = [marker] if dmesg is None else dmesg
    values = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": "7.1.3-gemini-postram-a",
        "architecture": "aarch64",
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "cmdline": "bootopt=64S3,32N2,64N2",
        "checkpoint_marker_count": str(sum(MARKER in line for line in dmesg)),
    }
    values.update(changes)
    lines = [validator.BEGIN]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.append(validator.DMESG_BEGIN)
    lines.extend(dmesg)
    lines.append(validator.DMESG_END)
    lines.extend(
        [
            "device_partition_reads=none",
            "device_storage_writes=none",
            "driver_binding_changes=none",
            "hardware_write_request=none",
            "cpu_admission_request=none",
            "reboot_request=none",
            validator.END,
        ]
    )
    return "\n".join(lines) + "\n"


def outcome(text: str) -> tuple[str, str]:
    try:
        return validator.classify_text(text)
    except validator.Classification as result:
        return result.result, result.reason


def require(text: str, expected: str) -> None:
    result = outcome(text)
    assert result[0] == expected, f"expected {expected}, got {result}"


def test_classifier() -> None:
    require(capture(), "success-post-ramoops-checkpoint")
    require(capture(kernel_release="wrong"), "rejected-attribution")
    require(capture(dmesg=[], checkpoint_marker_count="0"), "checkpoint-failure")
    require(capture(dmesg=[MARKER, MARKER], checkpoint_marker_count="2"), "checkpoint-failure")
    require(capture(cpu_online="0-9", cpu_offline=""), "rejected-safety")
    require(
        capture(dmesg=[MARKER, "da921x-observer-v1 event=bound"], checkpoint_marker_count="1"),
        "rejected-control",
    )


def test_tool_contracts() -> None:
    probe = PROBE.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")
    assert CANDIDATE in probe and CANDIDATE in collector and CANDIDATE in installer
    assert MARKER in probe
    for forbidden in ("/dev/mmc", "systemctl", "poweroff", "shutdown", ">/sys", "> /sys"):
        assert forbidden not in probe, f"probe contains forbidden action: {forbidden}"
    assert "nc -4 -b" in collector
    assert "WAIT_SECONDS=3600" in collector
    assert "runtime_probe_transport=stdin-pipe-no-device-file" in collector
    help_result = subprocess.run(
        [str(INSTALLER), "--help"], check=True, capture_output=True, text=True
    )
    assert "post-ramoops-checkpoint-deployment-N" in help_result.stdout
    assert "No fresh partition backup is made" in help_result.stdout


def main() -> None:
    test_classifier()
    test_tool_contracts()
    print("validation=post-ramoops-checkpoint-runtime-tools-offline")
    print("positive_classification=pass")
    print("negative_mutations_rejected_or_distinguished=5")
    print("runtime_probe_read_only_contract=pass")
    print("collector_wait_seconds=3600")
    print("installer_guarded_shutdown_contract=pass")


if __name__ == "__main__":
    main()
