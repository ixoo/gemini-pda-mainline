#!/usr/bin/env python3
"""Validate the exact repaired READY-token candidate before its one trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c617550e84260388144e702bb3361d44291ed62f0ef0bb425b80b08555705406"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a"
new_candidate = "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe READY-contract pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {"__file__": str(SCRIPT), "__name__": "_ready_contract_pretrigger"}
exec(compile(text, str(SOURCE), "exec"), namespace)
old_armed = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
    "trigger_executions=0 operation_ret=-115 core_consumed=0 "
    "entry_trace_ret=0 terminal_trace_ret=0 cpu_requests=0 "
    "cpu9_requests=0 cpu_off_requests=0 retries=0"
)
new_armed = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
    "trigger_executions=0 operation_ret=-115 core_consumed=0 "
    "entry_trace_ret=0 terminal_trace_ret=0 failure_stage=0 derive_stage=0 "
    "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0"
)
if namespace.get("ARMED") != old_armed:
    raise SystemExit("source armed status changed")
namespace["ARMED"] = new_armed
inner = namespace.get("namespace")
if not isinstance(inner, dict) or inner.get("ARMED") != old_armed:
    raise SystemExit("source validator namespace changed")
inner["ARMED"] = new_armed
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__", "namespace"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
