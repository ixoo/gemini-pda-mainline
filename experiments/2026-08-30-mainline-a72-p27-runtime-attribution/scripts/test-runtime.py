#!/usr/bin/env python3
"""Exercise boot attribution and exact P27 diagnostic classifications."""

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


PRE = load("p27_pretrigger_test", "validate-pretrigger.py")
ATTEMPT = load("p27_attempt_test", "classify-attempt.py")


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


def diagnostic(*, lifecycle: int, terminal: int, stage: int,
               stage_errno: int, rollback_errno: int) -> str:
    return (
        f"binder_snapshot_ret=0 binder_abi=1 lifecycle={lifecycle} "
        f"terminal={terminal} last_stage={stage} stage_errno={stage_errno} "
        f"rollback_errno={rollback_errno} checkpoint_errno=0 attempted=1 "
        "watchdog_armed=1 p27_owned=0 rollback_mask=0x1 retained_mask=0x0 "
        "p27a_op=1 p27a_error=-5 p27a_attempted=0x7 p27a_completed=0x3 "
        "p27a_spm_before=0x0 p27a_spm_after=0x1 p27a_bpll=0x1 "
        "p27a_owned=1 p27a_sealed=0 p27r_op=2 p27r_error=0 "
        "p27r_attempted=0x1f p27r_completed=0x1f p27r_spm_before=0x1 "
        "p27r_spm_after=0x0 p27r_bpll=0x1 p27r_owned=0 p27r_sealed=1"
    )


def status(ret: int, requests: int, failure: int, derive: int,
           detail: str) -> str:
    return (
        "GEMINI_A72_ADMISSION_LIVE_V1 state=terminal trigger_consumed=1 "
        f"trigger_executions=1 operation_ret={ret} core_consumed=1 "
        "entry_trace_ret=-5 terminal_trace_ret=-5 "
        f"failure_stage={failure} derive_stage={derive} cpu_requests={requests} "
        f"cpu9_requests=0 cpu_off_requests=0 retries=0 {detail}"
    )


def trigger(post_status: str, online: str, offline: str, *, complete: bool = True) -> str:
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
            f"post_status={post_status}",
            f"cpu_online={online}",
            f"cpu_offline={offline}",
            "cpu9_request=none",
            "cpu_off_request=none",
            "retry_request=none",
            "reboot_request=none",
            ATTEMPT.END,
        ))
    return "\n".join(lines)


success = status(0, 1, 0, 0, diagnostic(
    lifecycle=6, terminal=5, stage=9, stage_errno=0, rollback_errno=0
))
pre_request_error = status(-1, 0, 2, 2, diagnostic(
    lifecycle=6, terminal=3, stage=2, stage_errno=-5, rollback_errno=-71
))
request_error = status(-5, 1, 7, 6, diagnostic(
    lifecycle=6, terminal=3, stage=2, stage_errno=-5, rollback_errno=0
))

assert PRE.classify(pretrigger())[0] == "serviceable-armed-zero-execution"
assert ATTEMPT.classify(pretrigger(), trigger(success, "0-8", "9"))[0] == "cpu8-online"
assert ATTEMPT.classify(pretrigger(), trigger(pre_request_error, "0-7", "8-9"))[0] == "terminal-pre-request-error"
assert ATTEMPT.classify(pretrigger(), trigger(request_error, "0-7", "8-9"))[0] == "terminal-request-bearing-error"
assert ATTEMPT.classify(pretrigger(), trigger("", "", "", complete=False))[0] == "trigger-boundary-transport-loss"

accepted = trigger(success, "0-8", "9")
mutations = (
    (f"boot_id={BOOT_ID}", "boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    ("binder_snapshot_ret=0", "binder_snapshot_ret=malformed"),
    ("stage_errno=0", "stage_errno=malformed"),
    ("p27a_attempted=0x7", "p27a_attempted=invalid"),
    ("p27r_completed=0x1f", "p27r_completed=invalid"),
    ("cpu_requests=1 cpu9_requests=0", "cpu_requests=1 cpu9_requests=1"),
    ("cpu_online=0-8", "cpu_online=0-7"),
    ("reboot_request=none", "reboot_request=yes"),
)
for old, new in mutations:
    candidate = accepted.replace(old, new, 1)
    assert candidate != accepted, f"attempt mutation anchor absent: {old}"
    try:
        ATTEMPT.classify(pretrigger(), candidate)
    except ATTEMPT.Classification:
        pass
    else:
        raise AssertionError(f"unsafe attempt mutation accepted: {old}")

armed_mutation = pretrigger().replace("p27a_op=0", "p27a_op=1", 1)
try:
    PRE.classify(armed_mutation)
except PRE.Classification:
    pass
else:
    raise AssertionError("non-pristine P27 armed status accepted")

print("attempt_accepted_branches=4")
print(f"attempt_mutations_rejected={len(mutations)}")
print("armed_diagnostic_mutations_rejected=1")
print("boot_bound_transport_loss=yes")
print("result=pass")
