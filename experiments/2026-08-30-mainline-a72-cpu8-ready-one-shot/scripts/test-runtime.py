#!/usr/bin/env python3
"""Exercise the exact boot-bound READY and one-shot terminal contracts."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRE = load("cpu8_ready_pretrigger_test", "validate-pretrigger.py")
ATTEMPT = load("cpu8_ready_attempt_test", "classify-attempt.py")


def pretrigger() -> str:
    return "\n".join((
        PRE.BEGIN,
        f"installed_full_sha256={PRE.CANDIDATE}",
        f"kernel_release={PRE.RELEASE}",
        "architecture=aarch64",
        f"boot_id={PRE.EXPECTED_BOOT_ID}",
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
        "proof_mask_24000_count=0",
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
        f"live_status={PRE.ARMED}",
        "device_partition_reads=none",
        "device_storage_writes=none",
        "sysfs_write_request=none",
        "supplier_resolution_request=none",
        "cpu_admission_request=none",
        "cpu_off_request=none",
        "retry_request=none",
        "reboot_request=none",
        PRE.END,
    ))


def trigger(status: str, online: str, offline: str, complete: bool = True) -> str:
    lines = [ATTEMPT.BEGIN, f"pre_status={PRE.ARMED}", ATTEMPT.COMMIT]
    if complete:
        lines.extend((
            "trigger_write_status=0",
            "remount_ro_status=0",
            f"post_status={status}",
            f"cpu_online={online}",
            f"cpu_offline={offline}",
            "cpu9_request=none",
            "cpu_off_request=none",
            "retry_request=none",
            "reboot_request=none",
            ATTEMPT.END,
        ))
    return "\n".join(lines)


success = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=terminal trigger_consumed=1 "
    "trigger_executions=1 operation_ret=0 core_consumed=1 "
    "entry_trace_ret=-5 terminal_trace_ret=-5 cpu_requests=1 "
    "cpu9_requests=0 cpu_off_requests=0 retries=0"
)
error = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=terminal trigger_consumed=1 "
    "trigger_executions=1 operation_ret=-19 core_consumed=1 "
    "entry_trace_ret=-5 terminal_trace_ret=-5 cpu_requests=0 "
    "cpu9_requests=0 cpu_off_requests=0 retries=0"
)
assert PRE.classify(pretrigger())[0] == "serviceable-armed-zero-execution"
assert ATTEMPT.classify(pretrigger(), trigger(success, "0-8", "9"))[0] == "cpu8-online"
assert ATTEMPT.classify(pretrigger(), trigger(error, "0-7", "8-9"))[0] == "terminal-admission-error"
assert ATTEMPT.classify(pretrigger(), trigger("", "", "", complete=False))[0] == "trigger-boundary-transport-loss"

pretrigger_mutations = (
    ("installed_full_sha256=2245c1c4", "installed_full_sha256=00000000"),
    (f"boot_id={PRE.EXPECTED_BOOT_ID}", "boot_id=00000000-0000-0000-0000-000000000000"),
    ("runtime_identity_verified_count=1", "runtime_identity_verified_count=0"),
    ("profile_blocked_count=0", "profile_blocked_count=1"),
    ("ready_plan_diag_count=0", "ready_plan_diag_count=1"),
    ("ready_plan_values_count=0", "ready_plan_values_count=1"),
    ("proof_mask_24000_count=0", "proof_mask_24000_count=1"),
    ("cpu_online=0-7", "cpu_online=0-8"),
    ("cpu_offline=8-9", "cpu_offline=9"),
    ("trigger_consumed=0", "trigger_consumed=1"),
    ("cpu_requests=0 cpu9_requests=0", "cpu_requests=1 cpu9_requests=0"),
    ("sysfs_options=ro,", "sysfs_options=rw,"),
    ("cpu_admission_request=none", "cpu_admission_request=cpu8"),
)
for old, new in pretrigger_mutations:
    candidate = pretrigger().replace(old, new, 1)
    assert candidate != pretrigger(), f"pre-trigger mutation anchor absent: {old}"
    try:
        PRE.classify(candidate)
    except PRE.Classification:
        pass
    else:
        raise AssertionError(f"unsafe pre-trigger mutation accepted: {old}")

attempt_mutations = (
    (ATTEMPT.COMMIT, "trigger_commit=no"),
    ("cpu_online=0-8", "cpu_online=0-7"),
    ("cpu_offline=9", "cpu_offline=8-9"),
    ("cpu_requests=1 cpu9_requests=0", "cpu_requests=1 cpu9_requests=1"),
    ("entry_trace_ret=-5", "entry_trace_ret=unavailable"),
    ("retry_request=none", "retry_request=yes"),
    ("reboot_request=none", "reboot_request=yes"),
)
for old, new in attempt_mutations:
    candidate = trigger(success, "0-8", "9").replace(old, new, 1)
    assert candidate != trigger(success, "0-8", "9"), f"attempt mutation anchor absent: {old}"
    try:
        ATTEMPT.classify(pretrigger(), candidate)
    except ATTEMPT.Classification:
        pass
    else:
        raise AssertionError(f"unsafe attempt mutation accepted: {old}")

print("pretrigger_accepted_branches=1")
print("attempt_accepted_branches=3")
print(f"pretrigger_mutations_rejected={len(pretrigger_mutations)}")
print(f"attempt_mutations_rejected={len(attempt_mutations)}")
print("result=pass")
