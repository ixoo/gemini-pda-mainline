#!/usr/bin/env python3
"""Test accepted and rejected platform-snapshot live captures."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("platform_snapshot_runtime", SCRIPT_DIR / "validate-runtime.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = MODULE.BASE


def encoded_log() -> str:
    raw = (
        f"driver: {MODULE.TAG} valid=1 spm=00000001/00000001/00000000/00000000 "
        "mp2=00000002/00000003/00000004 iso=00000000 dcm=00000005 "
        "cci=00000006/00000007/00000008 pwrap=0\n"
        f"driver: {MODULE.COMPLETE}\n"
    ).encode()
    return base64.b64encode(raw).decode()


def capture() -> str:
    return "\n".join((
        BASE.BEGIN,
        f"installed_full_sha256={MODULE.CANDIDATE}",
        f"kernel_release={MODULE.RELEASE}",
        "architecture=aarch64",
        "boot_id=12345678-1234-1234-1234-123456789abc",
        "uptime_seconds=55.25",
        "model=MT6797X",
        "compatible=planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible=0-9", "cpu_present=0-9", "cpu_online=0-7", "cpu_offline=8-9",
        "maxcpus8_tokens=1", "udc_devices=1", "block_mounts=0", "pstore_files=0",
        "platform_state_devices=1", "platform_state_bound=1",
        "clock_backend_devices=1", "clock_backend_bound=1",
        "bigidvfs_backend_devices=1", "bigidvfs_backend_bound=1",
        "snapshot_observer_devices=1", "snapshot_observer_bound=1",
        "physical_observer_devices=0",
        "usb_controller_status=okay", "tphy_status=okay",
        "i2c5_status=okay", "keyboard_status=okay",
        BASE.MARKERS_BEGIN, BASE.MARKERS_END,
        f"snapshot_log_b64={encoded_log()}", "snapshot_log_lines=2",
        "snapshot_failure_lines=0", "platform_snapshot_request=boot-observer-one-shot",
        "platform_snapshot_calls_expected=1", "stable_samples_expected=2",
        "register_observations_expected=26", "clock_backend_read_request=none",
        "bigidvfs_backend_read_request=none", "device_partition_reads=none",
        "device_storage_writes=none", "driver_binding_changes=none",
        "regulator_action_request=none", "clock_action_request=none",
        "secure_call_request=none", "observer_registration_request=dt-probe-only",
        "owner_registration_request=none", "cpu_admission_request=none",
        "reboot_request=none", BASE.END,
    ))


assert MODULE.classify(capture())[0] == "serviceable-platform-snapshot-complete"
mutations = (
    ("platform_state_bound=1", "platform_state_bound=0"),
    ("clock_backend_bound=1", "clock_backend_bound=0"),
    ("bigidvfs_backend_bound=1", "bigidvfs_backend_bound=0"),
    ("snapshot_observer_devices=1", "snapshot_observer_devices=0"),
    ("snapshot_observer_bound=1", "snapshot_observer_bound=0"),
    ("physical_observer_devices=0", "physical_observer_devices=1"),
    ("usb_controller_status=okay", "usb_controller_status=disabled"),
    ("tphy_status=okay", "tphy_status=disabled"),
    ("i2c5_status=okay", "i2c5_status=disabled"),
    ("keyboard_status=okay", "keyboard_status=disabled"),
    ("snapshot_log_lines=2", "snapshot_log_lines=1"),
    ("snapshot_failure_lines=0", "snapshot_failure_lines=1"),
    ("platform_snapshot_calls_expected=1", "platform_snapshot_calls_expected=2"),
    ("register_observations_expected=26", "register_observations_expected=25"),
    (MODULE.COMPLETE, MODULE.COMPLETE.replace("retries=0", "retries=1")),
    ("valid=1", "valid=0"),
)
for old, new in mutations:
    candidate = capture()
    if old in candidate:
        candidate = candidate.replace(old, new, 1)
    else:
        decoded = base64.b64decode(encoded_log()).decode().replace(old, new, 1)
        candidate = candidate.replace(encoded_log(), base64.b64encode(decoded.encode()).decode(), 1)
    try:
        MODULE.classify(candidate)
    except BASE.Classification:
        pass
    else:
        raise AssertionError(f"unsafe platform-snapshot mutation accepted: {old}")
print("runtime_accepted_branches=1")
print("runtime_rejected_mutations=16")
print("result=pass")
