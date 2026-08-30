#!/usr/bin/env python3
"""Reject decision-changing mutations of the runtime diagnostic frame."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ready_plan_diagnostic", SCRIPT_DIR / "validate-diagnostic.py"
)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load diagnostic validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

FRAME = """\
__GEMINI_A72_LIVE_PRETRIGGER_BEGIN__
installed_full_sha256=7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272
kernel_release=7.1.3-gemini-a72-admission-live
architecture=aarch64
boot_id=13f81ecd-3374-42e8-ad52-c0b5b61c0f78
uptime_seconds=69.37
model=MT6797X
compatible=planet,gemini-pda,mediatek,mt6797,
cpu_possible=0-9
cpu_present=0-9
cpu_online=0-7
cpu_offline=8-9
maxcpus8_tokens=1
provenance_node=1
provenance_compatible=planet,gemini-a72-runtime-binding-v1,
runtime_identity_verified_count=1
runtime_identity_invalid_count=0
runtime_identity_mismatch_count=0
runtime_identity_unconfigured_count=0
profile_blocked_count=1
ready_plan_diag_count=1
ready_plan_diag_line=[    0.085595] mt6797-psci: A72_READY_PLAN_DIAG_V1 ret=-22 plan=0x288380 evidence=0x2000000
proof_mask_24000_count=1
udc_devices=1
block_mounts=0
controller_devices=1
controller_bound=1
group_present=1
status_mode=444
status_uid=0
trigger_mode=200
trigger_uid=0
sysfs_options=ro,nosuid,nodev,noexec,relatime
live_status=GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 trigger_executions=0 operation_ret=-115 core_consumed=0 entry_trace_ret=0 terminal_trace_ret=0 cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0
device_partition_reads=none
device_storage_writes=none
sysfs_write_request=none
supplier_resolution_request=none
cpu_admission_request=none
cpu_off_request=none
retry_request=none
reboot_request=none
__GEMINI_A72_LIVE_PRETRIGGER_END__
"""


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor count changed: {old!r}")
    return text.replace(old, new, 1)


def main() -> int:
    result, _, plan, evidence = VALIDATOR.classify(FRAME)
    if result != "attributable-predicate-diagnostic-zero-execution":
        raise SystemExit("known-good diagnostic frame was rejected")
    if plan != 0x288380 or evidence != 0x2000000:
        raise SystemExit("known-good diagnostic masks were decoded incorrectly")

    mutations = (
        ("wrong-candidate", "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "0" * 64),
        ("profile-unblocked", "profile_blocked_count=1", "profile_blocked_count=0"),
        ("missing-diagnostic", "ready_plan_diag_count=1", "ready_plan_diag_count=0"),
        ("wrong-return", "ret=-22", "ret=0"),
        ("zero-plan", "plan=0x288380", "plan=0x0"),
        ("unknown-plan-bit", "plan=0x288380", "plan=0x8000000"),
        ("unknown-evidence-bit", "evidence=0x2000000", "evidence=0x20000000"),
        ("missing-public-proof", "proof_mask_24000_count=1", "proof_mask_24000_count=0"),
        ("cpu8-online", "cpu_online=0-7", "cpu_online=0-8"),
        ("cpu-request", "cpu_requests=0 cpu9_requests=0", "cpu_requests=1 cpu9_requests=0"),
        ("trigger-consumed", "trigger_consumed=0", "trigger_consumed=1"),
        ("storage-write", "device_storage_writes=none", "device_storage_writes=boot2"),
    )
    rejected = 0
    for label, old, new in mutations:
        try:
            VALIDATOR.classify(replace_once(FRAME, old, new))
        except VALIDATOR.Classification:
            rejected += 1
        else:
            raise SystemExit(f"unsafe runtime mutation accepted: {label}")
    print(f"unsafe_runtime_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
