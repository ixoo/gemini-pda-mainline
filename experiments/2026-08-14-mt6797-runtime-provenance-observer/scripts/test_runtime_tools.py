#!/usr/bin/env python3
"""Offline positive and mutation tests for runtime and installer tooling."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate-runtime.py"
PROBE = SCRIPT_DIR / "remote-runtime-probe.sh"
COLLECTOR = SCRIPT_DIR / "collect-runtime.sh"
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
CANDIDATE = "ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02"

spec = importlib.util.spec_from_file_location("runtime_validator", VALIDATOR)
assert spec and spec.loader
runtime_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime_validator)


def snapshot(**changes: str) -> list[str]:
    values = {
        "abi": "1",
        "state": "available",
        "observation_complete": "1",
        "variant_id": "273",
        "observer_generation": "9",
        "table_epoch": "1",
        "calibration_handle": "2",
        "ppm_expected_cluster_count": "3",
        "ppm_cluster_mask": "0x00000007",
        "eem_required_bank_mask": "0x0000003b",
        "eem_calibration_bank_mask": "0x0000003b",
        "table_commit_count": "3",
        "calibration_bank_publish_count": "5",
        "calibration_publish_count": "1",
        "calibration_invalidate_count": "0",
        "owner_handle": "0",
        "transition_handle": "0",
        "coherent_transition_owner": "0",
        "provider": "none",
        "hardware_write": "none",
        "cpu8_cpu9_admission": "closed",
    }
    values.update(changes)
    return [f"{key}={value}" for key, value in values.items()]


def capture(first: list[str] | None = None, second: list[str] | None = None, **outer_changes: str) -> str:
    outer = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": "3.18.79-gemini-provenance-observer+",
        "architecture": "aarch64",
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "state_path": "/sys/kernel/debug/gemini_dvfsp_provenance/state",
        "state_access": "readable",
        "state_mode": "444",
    }
    outer.update(outer_changes)
    first = snapshot() if first is None else first
    second = list(first) if second is None else second
    lines = [runtime_validator.BEGIN]
    lines.extend(f"{key}={value}" for key, value in outer.items())
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_1_BEGIN__")
    lines.extend(first)
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_1_END__")
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_2_BEGIN__")
    lines.extend(second)
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_2_END__")
    lines.extend(
        [
            "device_partition_reads=none",
            "device_storage_writes=none",
            "hardware_write=none",
            "reboot_request=none",
            runtime_validator.END,
        ]
    )
    return "\n".join(lines) + "\n"


def outcome(text: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "runtime.txt"
        path.write_text(text)
        try:
            return runtime_validator.classify(path)
        except runtime_validator.Classification as result:
            return result.result, result.reason


def require(actual: tuple[str, str], expected: str) -> None:
    assert actual[0] == expected, f"expected {expected}, got {actual}"


def test_classifier() -> None:
    require(outcome(capture()), "success")
    require(outcome(capture(kernel_release="wrong")), "rejected-attribution")
    require(outcome(capture(state_access="absent-or-unreadable")), "service-failure")
    require(outcome(capture(first=snapshot(observation_complete="0", state="unavailable"))), "inconclusive")
    require(outcome(capture(second=snapshot(observer_generation="10"))), "inconclusive")
    require(outcome(capture(first=snapshot(owner_handle="1"))), "rejected-safety")
    require(outcome(capture(first=snapshot(state="fault", observation_complete="0"))), "rejected-safety")
    require(outcome(capture(cpu_online="0-9")), "rejected-safety")


def test_tool_contracts() -> None:
    probe = PROBE.read_text()
    collector = COLLECTOR.read_text()
    installer = INSTALLER.read_text()
    assert CANDIDATE in probe and CANDIDATE in collector and CANDIDATE in installer
    assert "cat \"$STATE\"" in probe and probe.count("cat \"$STATE\"") == 2
    for forbidden in ("/dev/mmc", "systemctl", "/sbin/reboot", "poweroff", "shutdown"):
        assert forbidden not in probe
    assert "nc -4 -b" in collector and "device_partition_reads=none" in collector
    assert "runtime_probe_transport=stdin-pipe-no-device-file" in collector
    for required in (
        "PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT",
        "/dev/disk/by-partlabel/boot2",
        "/dev/mmcblk0p29",
        "blockdev --flushbufs",
        "full-partition checksum mismatch",
        "independent readback byte mismatch",
        "systemctl poweroff",
        "shutdown=confirmed-unreachable",
        "fresh_predecessor_backup=no",
    ):
        assert required in installer, f"installer lacks gate: {required}"
    assert "EXPECTED_PREDECESSOR_SHA256" not in installer
    assert "reboot" not in installer.replace("reboot=no", "").replace("never a reboot", "")
    assert "backup-device-mmc" not in installer


def main() -> None:
    test_classifier()
    test_tool_contracts()
    print("validation=runtime-tools-offline")
    print("positive_classification=pass")
    print("negative_mutations_rejected_or-distinguished=7")
    print("installer_static_contract=pass")


if __name__ == "__main__":
    main()
