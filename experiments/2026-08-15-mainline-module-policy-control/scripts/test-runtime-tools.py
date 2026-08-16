#!/usr/bin/env python3
"""Offline positive, mutation, and static tests for module-policy tooling."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate-runtime.py"
PROBE = SCRIPT_DIR / "remote-runtime-probe.sh"
COLLECTOR = SCRIPT_DIR / "collect-runtime.sh"
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
CANDIDATE = "044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff"

spec = importlib.util.spec_from_file_location("module_policy_validator", VALIDATOR)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def capture(*, dmesg: list[str] | None = None, **changes: str) -> str:
    identity = (
        "[    2.000000] da9213-legacy-regulator 1-0068: "
        "DA9214 legacy direct-address identity matched; provider is read-only"
    )
    dmesg = [identity] if dmesg is None else dmesg
    values = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": "7.1.3-gemini-da921x-modctl",
        "architecture": "aarch64",
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "cmdline": "bootopt=64S3,32N2,64N2",
        "provider_identity_count": str(sum(validator.IDENTITY in line for line in dmesg)),
        "provider_failure_count": str(sum("failed" in line for line in dmesg)),
        "observer_marker_count": str(sum("da921x-observer-v1" in line for line in dmesg)),
        "bound_i2c_paths": "1-0068",
        "regulator_names": "DA9213-legacy-BUCK0 DA9213-legacy-BUCK1",
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
    require(capture(), "success-module-policy-control")
    require(capture(kernel_release="wrong"), "rejected-attribution")
    require(capture(dmesg=[], provider_identity_count="0"), "module-policy-control-failure")
    require(
        capture(
            dmesg=["[ 2.0] da921x-observer-v1 event=bound"],
            provider_identity_count="0",
            observer_marker_count="1",
        ),
        "rejected-control",
    )
    require(capture(cpu_online="0-9", cpu_offline=""), "rejected-safety")
    require(capture(bound_i2c_paths=""), "module-policy-control-failure")
    require(capture(regulator_names="DA9213-legacy-BUCK0"), "module-policy-control-failure")


def test_tool_contracts() -> None:
    probe = PROBE.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")
    assert CANDIDATE in probe and CANDIDATE in collector and CANDIDATE in installer
    assert "DA9214 legacy direct-address identity matched; provider is read-only" in probe
    assert "da921x-observer-v1" in probe
    for forbidden in ("/dev/mmc", "systemctl", "poweroff", "shutdown", ">/sys", "> /sys"):
        assert forbidden not in probe, f"probe contains forbidden action: {forbidden}"
    assert "nc -4 -b" in collector
    assert "WAIT_SECONDS=3600" in collector
    assert "runtime_probe_transport=stdin-pipe-no-device-file" in collector
    help_result = subprocess.run(
        [str(INSTALLER), "--help"], check=True, capture_output=True, text=True
    )
    assert "module-policy-control-deployment-N" in help_result.stdout
    assert "No fresh partition backup is made" in help_result.stdout


def main() -> None:
    test_classifier()
    test_tool_contracts()
    print("validation=da921x-module-policy-control-runtime-tools-offline")
    print("positive_classification=pass")
    print("negative_mutations_rejected_or_distinguished=6")
    print("runtime_probe_read_only_contract=pass")
    print("collector_wait_seconds=3600")
    print("installer_guarded_shutdown_contract=pass")


if __name__ == "__main__":
    main()
