#!/usr/bin/env python3
"""Test accepted and rejected Stage-27 minimum platform-state captures."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("stage27_platform_runtime", SCRIPT_DIR / "validate-runtime.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = MODULE.BASE.BASE


def capture(bound: str = "1") -> str:
    return "\n".join((
        BASE.BEGIN,
        f"installed_full_sha256={MODULE.CANDIDATE}",
        f"kernel_release={BASE.RELEASE}",
        "architecture=aarch64",
        "boot_id=12345678-1234-1234-1234-123456789abc",
        "uptime_seconds=55.25",
        "model=MT6797X",
        "compatible=planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible=0-9", "cpu_present=0-9", "cpu_online=0-7", "cpu_offline=8-9",
        "maxcpus8_tokens=1", "udc_devices=1", "block_mounts=0", "pstore_files=0",
        "platform_state_devices=1", f"platform_state_bound={bound}",
        "clock_backend_devices=0", "bigidvfs_backend_devices=0", "physical_observer_devices=0",
        "usb_controller_status=okay ", "tphy_status=okay ", "i2c5_status=okay ", "keyboard_status=okay ",
        BASE.MARKERS_BEGIN, BASE.MARKERS_END,
        "platform_snapshot_request=none", "device_partition_reads=none", "device_storage_writes=none",
        "driver_binding_changes=none", "regulator_action_request=none", "clock_action_request=none",
        "secure_call_request=none", "observer_registration_request=none",
        "owner_registration_request=none", "cpu_admission_request=none", "reboot_request=none",
        BASE.END,
    ))


assert MODULE.classify(capture("1"))[0] == "serviceable-platform-state-bound"
assert MODULE.classify(capture("0"))[0] == "serviceable-platform-state-unbound"
for old, new in (
    ("usb_controller_status=okay ", "usb_controller_status=disabled "),
    ("tphy_status=okay ", "tphy_status=disabled "),
    ("i2c5_status=okay ", "i2c5_status=disabled "),
    ("keyboard_status=okay ", "keyboard_status=disabled "),
):
    try:
        MODULE.classify(capture().replace(old, new, 1))
    except MODULE.BASE.BASE.Classification:
        pass
    else:
        raise AssertionError(f"unsafe Stage-27 state mutation accepted: {old}")
print("runtime_accepted_branches=2")
print("inherited_provider_mutations_rejected=7")
print("stage27_state_mutations_rejected=4")
print("result=pass")
