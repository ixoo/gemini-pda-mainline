#!/usr/bin/env python3
"""Test accepted and rejected platform/provider/protected-clock captures."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("platform_provider_clock_runtime", SCRIPT_DIR / "validate-runtime.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = MODULE.BASE


def complete(valid: int, after: int, ret: int, abi: int, generation: int) -> str:
    return (
        f"{MODULE.TAG} state=complete provider_ready_gate=passed clock_ready_gate=passed "
        f"valid={valid} clock_returned=1 after_checkpoint={after} "
        "platform_calls=1 platform_samples=2 platform_register_observations=26 "
        "provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 "
        "provider_i2c_writes=0 retained_write_attempts=2 protected_clock_calls=1 "
        f"protected_clock_ret={ret} protected_clock_abi={abi} "
        f"protected_clock_generation={generation} clock_gate_pairs=1 "
        "explicit_mmio_writes_maximum=401 explicit_mmio_reads_maximum=419 "
        "observer_retries=0 bigidvfs_reads=0 secure_calls=0 provider_acquires=0 "
        "provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0"
    )


def encoded_log(valid: int = 1, after: int = 1, ret: int = 0,
                abi: int = 2, generation: int = 1) -> str:
    raw = (
        f"driver: {MODULE.TAG} platform valid=1 spm=00000001/00000001/00000000/00000000 "
        "mp2=00000002/00000003/00000004 iso=00000000 dcm=00000005 "
        "cci=00000006/00000007/00000008 pwrap=0\n"
        f"driver: {MODULE.TAG} provider abi=1 valid=1 raw=7b/c1/00/46/46\n"
        f"driver: {MODULE.TAG} clock ret={ret} abi={abi} generation={generation} "
        "muxsel=00000001 ckdiv=00000002 pll_ll=00000003/00000004/00000005 "
        "pll_l=00000006/00000007/00000008 pll_cci=00000009/0000000a/0000000b "
        "cspm_swctrl=0000000c/0000000d/0000000e "
        "cspm_hwsta=0000000f/00000010/00000011/00000012\n"
        f"driver: {complete(valid, after, ret, abi, generation)}\n"
    ).encode()
    return base64.b64encode(raw).decode()


def capture(valid: int = 1, after: int = 1, ret: int = 0,
            abi: int = 2, generation: int = 1) -> str:
    return "\n".join((
        BASE.BEGIN,
        f"installed_full_sha256={MODULE.CANDIDATE}",
        f"kernel_release={MODULE.RELEASE}",
        "architecture=aarch64", "boot_id=12345678-1234-1234-1234-123456789abc",
        "uptime_seconds=55.25", "model=MT6797X",
        "compatible=planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible=0-9", "cpu_present=0-9", "cpu_online=0-7", "cpu_offline=8-9",
        "maxcpus8_tokens=1", "udc_devices=1", "block_mounts=0", "pstore_files=0",
        "platform_state_devices=1", "platform_state_bound=1",
        "clock_backend_devices=1", "clock_backend_bound=1",
        "bigidvfs_backend_devices=1", "bigidvfs_backend_bound=1",
        "composed_observer_devices=1", "composed_observer_bound=1",
        "provider_only_observer_devices=0", "platform_only_observer_devices=0",
        "physical_observer_devices=0", "provider_i2c_devices=1", "provider_i2c_bound=1",
        "usb_controller_status=okay", "tphy_status=okay", "i2c5_status=okay",
        "keyboard_status=okay", BASE.MARKERS_BEGIN, BASE.MARKERS_END,
        f"snapshot_log_b64={encoded_log(valid, after, ret, abi, generation)}",
        "snapshot_log_lines=4", "snapshot_failure_lines=0",
        "platform_snapshot_request=boot-observer-one-shot",
        "platform_snapshot_calls_expected=1", "platform_samples_expected=2",
        "platform_register_observations_expected=26",
        "provider_readiness_request=explicit-phandle-bound-device",
        "provider_snapshot_request=one-stable-read-only", "provider_snapshots_expected=1",
        "provider_samples_expected=2", "provider_i2c_reads_expected=10",
        "provider_i2c_writes_expected=0",
        "clock_backend_read_request=one-handoff-owned-snapshot",
        "protected_clock_calls_expected=1", "protected_clock_abi_expected=2",
        "protected_clock_generation_expected=1", "clock_gate_pairs_expected=1",
        "explicit_mmio_writes_maximum=401", "explicit_mmio_reads_maximum=419",
        "bigidvfs_backend_read_request=none", "device_partition_reads=none",
        "device_storage_writes=none", "driver_binding_changes=none",
        "regulator_action_request=none",
        "clock_action_request=one-balanced-gate-pair-and-bounded-cspm-snapshot",
        "secure_call_request=none", "provider_acquire_release_request=none",
        "observer_registration_request=dt-probe-only", "owner_registration_request=none",
        "cpu_admission_request=none", "reboot_request=none", BASE.END,
    ))


assert MODULE.classify(capture())[0] == "serviceable-platform-provider-clock-complete"
assert MODULE.classify(capture(0, 1, -5, 0, 0))[0] == "serviceable-platform-provider-clock-terminal-error"
assert MODULE.classify(capture(0, 0, 0, 2, 1))[0] == "serviceable-platform-provider-clock-after-checkpoint-failed"
assert MODULE.classify(capture(0, 1, 0, 2, 2))[0] == "serviceable-platform-provider-clock-invalid-identity"

mutations = (
    ("clock_backend_bound=1", "clock_backend_bound=0"),
    ("composed_observer_bound=1", "composed_observer_bound=0"),
    ("provider_only_observer_devices=0", "provider_only_observer_devices=1"),
    ("provider_i2c_bound=1", "provider_i2c_bound=0"),
    ("usb_controller_status=okay", "usb_controller_status=disabled"),
    ("keyboard_status=okay", "keyboard_status=disabled"),
    ("snapshot_log_lines=4", "snapshot_log_lines=3"),
    ("snapshot_failure_lines=0", "snapshot_failure_lines=1"),
    ("protected_clock_calls_expected=1", "protected_clock_calls_expected=2"),
    ("clock_gate_pairs_expected=1", "clock_gate_pairs_expected=2"),
    ("explicit_mmio_writes_maximum=401", "explicit_mmio_writes_maximum=402"),
    ("clock_action_request=one-balanced-gate-pair-and-bounded-cspm-snapshot", "clock_action_request=none"),
    ("cpu_admission_request=none", "cpu_admission_request=cpu8"),
    ("platform valid=1", "platform valid=0"),
    ("provider abi=1 valid=1", "provider abi=1 valid=0"),
    ("clock ret=0 abi=2 generation=1", "clock ret=0 abi=2 generation=2"),
    ("clock_returned=1", "clock_returned=0"),
    ("protected_clock_calls=1", "protected_clock_calls=2"),
    ("observer_retries=0", "observer_retries=1"),
)
for old, new in mutations:
    candidate = capture()
    if old in candidate:
        candidate = candidate.replace(old, new, 1)
    else:
        original = encoded_log()
        decoded = base64.b64decode(original).decode().replace(old, new, 1)
        candidate = candidate.replace(original, base64.b64encode(decoded.encode()).decode(), 1)
    try:
        MODULE.classify(candidate)
    except BASE.Classification:
        pass
    else:
        raise AssertionError(f"unsafe platform/provider/clock mutation accepted: {old}")
print("runtime_accepted_branches=4")
print(f"runtime_rejected_mutations={len(mutations)}")
print("result=pass")
