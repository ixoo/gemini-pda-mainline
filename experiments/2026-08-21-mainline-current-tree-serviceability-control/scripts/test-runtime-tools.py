#!/usr/bin/env python3
"""Offline tests for the current-tree serviceability runtime tooling."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "current_service_runtime_validator", SCRIPT_DIR / "validate-runtime.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fixture() -> str:
    return """noise
__CURRENT_SERVICE_CONTROL_RUNTIME_BEGIN__
installed_full_sha256=7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3
kernel_release=7.1.3-gemini-service-ctl
architecture=aarch64
boot_id=12345678-1234-1234-1234-123456789abc
uptime_seconds=42.50
cmdline=console=ttyS0 maxcpus=8 rdinit=/init
model=MT6797X
cpu_possible=0-9
cpu_present=0-9
cpu_online=0-7
cpu_offline=8-9
udc_devices=1
keyboard_matrix_inputs=1
da921x_i2c_clients=1
same_value_write_attributes=0
clock_backend_devices=0
bigidvfs_backend_devices=0
protected_readback_devices=0
block_mounts=0
pstore_files=0
device_partition_reads=none
device_storage_writes=none
driver_binding_changes=none
same_value_action_request=none
protected_read_request=none
secure_call_request=none
owner_registration_request=none
cpu_admission_request=none
reboot_request=none
__CURRENT_SERVICE_CONTROL_RUNTIME_END__
trailing noise
"""


def expect_rejected(text: str, *, safety: bool | None = None) -> None:
    try:
        VALIDATOR.classify_text(text)
    except VALIDATOR.Classification as result:
        if safety is True:
            require(result.result == "rejected-safety", f"expected safety rejection: {result.reason}")
        elif safety is False:
            require(
                result.result == "rejected-attribution",
                f"expected attribution rejection: {result.reason}",
            )
        return
    raise AssertionError("mutated runtime fixture was accepted")


def main() -> None:
    valid = fixture()
    require(
        VALIDATOR.classify_text(valid)
        == ("serviceable-control-pass", "exact-read-only-serviceability-oracle-complete"),
        "valid runtime fixture failed",
    )

    safety_mutations = {
        "cpu_online=0-7": "cpu_online=0-8",
        "cpu_offline=8-9": "cpu_offline=9",
        "same_value_write_attributes=0": "same_value_write_attributes=1",
        "clock_backend_devices=0": "clock_backend_devices=1",
        "bigidvfs_backend_devices=0": "bigidvfs_backend_devices=1",
        "protected_readback_devices=0": "protected_readback_devices=1",
        "block_mounts=0": "block_mounts=1",
        "device_storage_writes=none": "device_storage_writes=unknown",
        "same_value_action_request=none": "same_value_action_request=sent",
        "protected_read_request=none": "protected_read_request=sent",
        "secure_call_request=none": "secure_call_request=sent",
        "owner_registration_request=none": "owner_registration_request=sent",
        "cpu_admission_request=none": "cpu_admission_request=sent",
        "reboot_request=none": "reboot_request=sent",
        "maxcpus=8": "maxcpus=9",
    }
    for old, new in safety_mutations.items():
        expect_rejected(valid.replace(old, new, 1), safety=True)

    attribution_mutations = {
        "7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3": "0" * 64,
        "7.1.3-gemini-service-ctl": "7.1.3-wrong",
        "architecture=aarch64": "architecture=x86_64",
        "boot_id=12345678-1234-1234-1234-123456789abc": "boot_id=invalid",
        "uptime_seconds=42.50": "uptime_seconds=invalid",
        "model=MT6797X": "model=wrong",
        "cpu_possible=0-9": "cpu_possible=0-7",
        "cpu_present=0-9": "cpu_present=0-7",
        "udc_devices=1": "udc_devices=0",
        "keyboard_matrix_inputs=1": "keyboard_matrix_inputs=0",
        "da921x_i2c_clients=1": "da921x_i2c_clients=0",
        "pstore_files=0": "pstore_files=invalid",
        "device_partition_reads=none": "device_partition_reads=unknown",
    }
    for old, new in attribution_mutations.items():
        expect_rejected(valid.replace(old, new, 1), safety=False)

    expect_rejected(valid + valid, safety=False)
    expect_rejected(valid.replace("kernel_release=", "kernel_release=wrong\nkernel_release=", 1), safety=False)
    expect_rejected(valid.replace(VALIDATOR.END, "", 1), safety=False)

    probe = (SCRIPT_DIR / "remote-runtime-probe.sh").read_text(encoding="utf-8")
    require("/bin/reboot" not in probe, "remote read-only probe gained a reboot action")
    require("same_value_write_attributes=" in probe, "probe lost action-path absence check")
    require("device_storage_writes=none" in probe, "probe lost storage closure")
    collector = (SCRIPT_DIR / "collect-runtime.sh").read_text(encoding="utf-8")
    classify_at = collector.index('python3 "$validator" "$runtime"')
    reboot_at = collector.index("printf '/bin/reboot")
    require(classify_at < reboot_at, "collector reboot is not gated by classification")
    require(collector.count("printf '/bin/reboot") == 1, "collector reboot count changed")

    print("validation=current-tree-serviceability-runtime-tools")
    print(f"safety_mutations_rejected={len(safety_mutations)}")
    print(f"attribution_mutations_rejected={len(attribution_mutations) + 3}")
    print("native_reboot=only-after-exact-pass")
    print("result=pass")


if __name__ == "__main__":
    main()
