#!/usr/bin/env python3
"""Validate the exact P27 diagnostic candidate before its one trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-token-contract-repair"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179"
new_candidate = "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe P27 diagnostic pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {"__file__": str(SCRIPT), "__name__": "_p27_diagnostic_pretrigger"}
exec(compile(text, str(SOURCE), "exec"), namespace)
old_armed = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
    "trigger_executions=0 operation_ret=-115 core_consumed=0 "
    "entry_trace_ret=0 terminal_trace_ret=0 failure_stage=0 derive_stage=0 "
    "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0"
)
diagnostic = (
    " binder_snapshot_ret=0 binder_abi=1 lifecycle=0 terminal=0 last_stage=0 "
    "stage_errno=0 rollback_errno=0 checkpoint_errno=0 attempted=0 "
    "watchdog_armed=0 p27_owned=0 rollback_mask=0x0 retained_mask=0x0 "
    "p27a_op=0 p27a_error=0 p27a_attempted=0x0 p27a_completed=0x0 "
    "p27a_spm_before=0x0 p27a_spm_after=0x0 p27a_bpll=0x0 "
    "p27a_owned=0 p27a_sealed=0 p27r_op=0 p27r_error=0 "
    "p27r_attempted=0x0 p27r_completed=0x0 p27r_spm_before=0x0 "
    "p27r_spm_after=0x0 p27r_bpll=0x0 p27r_owned=0 p27r_sealed=0"
)
if namespace.get("ARMED") != old_armed:
    raise SystemExit("source armed status changed")
new_armed = old_armed + diagnostic
namespace["ARMED"] = new_armed
classify = namespace.get("classify")
if not callable(classify) or classify.__globals__.get("ARMED") != old_armed:
    raise SystemExit("source validator globals changed")
classify.__globals__["ARMED"] = new_armed
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
