#!/usr/bin/env python3
"""Exercise boot attribution and the repaired terminal-stage universe."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BOOT_ID = "11111111-2222-3333-4444-555555555555"


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRE = load("ready_contract_pretrigger_test", "validate-pretrigger.py")
ATTEMPT = load("ready_contract_attempt_test", "classify-attempt.py")


def pretrigger() -> str:
    return "\n".join((
        PRE.BEGIN,
        f"installed_full_sha256={PRE.CANDIDATE}",
        f"kernel_release={PRE.RELEASE}",
        "architecture=aarch64",
        f"boot_id={BOOT_ID}",
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


def trigger(status: str, online: str, offline: str, *, complete: bool = True) -> str:
    lines = [
        ATTEMPT.BEGIN,
        f"boot_id={BOOT_ID}",
        f"pre_status={PRE.ARMED}",
        "trigger_commit=yes",
        f"token_sha256={ATTEMPT.TOKEN_SHA256}",
    ]
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
    "entry_trace_ret=-5 terminal_trace_ret=-5 failure_stage=0 derive_stage=0 "
    "cpu_requests=1 cpu9_requests=0 cpu_off_requests=0 retries=0"
)
pre_request_error = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=terminal trigger_consumed=1 "
    "trigger_executions=1 operation_ret=-1 core_consumed=1 "
    "entry_trace_ret=-5 terminal_trace_ret=-114 failure_stage=2 derive_stage=2 "
    "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0"
)
request_error = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=terminal trigger_consumed=1 "
    "trigger_executions=1 operation_ret=-5 core_consumed=1 "
    "entry_trace_ret=-5 terminal_trace_ret=-5 failure_stage=7 derive_stage=6 "
    "cpu_requests=1 cpu9_requests=0 cpu_off_requests=0 retries=0"
)

assert PRE.classify(pretrigger())[0] == "serviceable-armed-zero-execution"
assert ATTEMPT.classify(pretrigger(), trigger(success, "0-8", "9"))[0] == "cpu8-online"
assert ATTEMPT.classify(
    pretrigger(), trigger(pre_request_error, "0-7", "8-9")
)[0] == "terminal-pre-request-error"
assert ATTEMPT.classify(
    pretrigger(), trigger(request_error, "0-7", "8-9")
)[0] == "terminal-request-bearing-error"
assert ATTEMPT.classify(
    pretrigger(), trigger("", "", "", complete=False)
)[0] == "trigger-boundary-transport-loss"

mutations = (
    (f"boot_id={BOOT_ID}", "boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    ("failure_stage=0", "failure_stage=malformed"),
    ("derive_stage=0", "derive_stage=malformed"),
    ("cpu_requests=1 cpu9_requests=0", "cpu_requests=1 cpu9_requests=1"),
    ("cpu_online=0-8", "cpu_online=0-7"),
    ("cpu_offline=9", "cpu_offline=8-9"),
    ("retry_request=none", "retry_request=yes"),
    ("reboot_request=none", "reboot_request=yes"),
)
accepted = trigger(success, "0-8", "9")
for old, new in mutations:
    candidate = accepted.replace(old, new, 1)
    assert candidate != accepted, f"attempt mutation anchor absent: {old}"
    try:
        ATTEMPT.classify(pretrigger(), candidate)
    except ATTEMPT.Classification:
        pass
    else:
        raise AssertionError(f"unsafe attempt mutation accepted: {old}")

transport_wrong_boot = trigger("", "", "", complete=False).replace(
    f"boot_id={BOOT_ID}", "boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", 1
)
try:
    ATTEMPT.classify(pretrigger(), transport_wrong_boot)
except ATTEMPT.Classification:
    pass
else:
    raise AssertionError("transport loss from a different boot was accepted")

print("attempt_accepted_branches=4")
print(f"attempt_mutations_rejected={len(mutations) + 1}")
print("boot_bound_transport_loss=yes")
print("result=pass")
