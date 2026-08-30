#!/usr/bin/env python3
"""Exercise closure READY acceptance and decision-changing rejections."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "classification_closure_runtime", SCRIPT_DIR / "validate-ready.py"
)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def frame() -> str:
    return "\n".join((
        validator.BEGIN,
        f"installed_full_sha256={validator.CANDIDATE}",
        f"kernel_release={validator.RELEASE}",
        "architecture=aarch64",
        "boot_id=12345678-1234-1234-1234-123456789abc",
        "uptime_seconds=157.33",
        "model=MT6797X",
        "compatible=planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible=0-9",
        "cpu_present=0-9",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "maxcpus8_tokens=1",
        "provenance_node=1",
        "provenance_compatible=planet,gemini-a72-runtime-binding-v1,",
        "runtime_identity_verified_count=1",
        "runtime_identity_invalid_count=0",
        "runtime_identity_mismatch_count=0",
        "runtime_identity_unconfigured_count=0",
        "profile_blocked_count=0",
        "ready_plan_diag_count=0",
        "ready_plan_diag_line=",
        "ready_plan_values_count=0",
        "ready_plan_values_line=",
        "proof_mask_24000_count=1",
        "udc_devices=1",
        "block_mounts=0",
        "controller_devices=1",
        "controller_bound=1",
        "group_present=1",
        "status_mode=444",
        "status_uid=0",
        "trigger_mode=200",
        "trigger_uid=0",
        "sysfs_options=ro,nosuid,nodev,noexec,relatime",
        f"live_status={validator.ARMED}",
        "device_partition_reads=none",
        "device_storage_writes=none",
        "sysfs_write_request=none",
        "supplier_resolution_request=none",
        "cpu_admission_request=none",
        "cpu_off_request=none",
        "retry_request=none",
        "reboot_request=none",
        validator.END,
    ))


classification, boot_id = validator.classify(frame())
assert classification == "serviceable-armed-zero-execution"
assert boot_id == "12345678-1234-1234-1234-123456789abc"

mutations = (
    ("installed_full_sha256=2245c1c4", "installed_full_sha256=00000000"),
    ("runtime_identity_verified_count=1", "runtime_identity_verified_count=0"),
    ("profile_blocked_count=0", "profile_blocked_count=1"),
    ("ready_plan_diag_count=0", "ready_plan_diag_count=1"),
    ("ready_plan_values_count=0", "ready_plan_values_count=1"),
    ("proof_mask_24000_count=1", "proof_mask_24000_count=0"),
    ("cpu_online=0-7", "cpu_online=0-8"),
    ("cpu_offline=8-9", "cpu_offline=9"),
    ("trigger_consumed=0", "trigger_consumed=1"),
    ("cpu_requests=0 cpu9_requests=0", "cpu_requests=1 cpu9_requests=0"),
    ("sysfs_options=ro,", "sysfs_options=rw,"),
    ("device_storage_writes=none", "device_storage_writes=boot2"),
    ("cpu_admission_request=none", "cpu_admission_request=cpu8"),
)
for old, new in mutations:
    candidate = frame().replace(old, new, 1)
    if candidate == frame():
        raise AssertionError(f"mutation anchor absent: {old}")
    try:
        validator.classify(candidate)
    except validator.Classification:
        pass
    else:
        raise AssertionError(f"unsafe READY mutation accepted: {old}")

print("ready_accepted_branches=1")
print(f"ready_mutations_rejected={len(mutations)}")
print("result=pass")
