#!/usr/bin/env python3
"""Validate the exact P30E entry candidate before its one trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a22f33457be8bae80b32f60ff01026dbe49410368d73c76c1da74a57c21ae04d"
ARMED_SHA256 = "a7a9cb8045fd265032ed15596f94ae0f99c1ea2f9b4dd39c21dd95b76316b6dc"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-selector-mask-contract-repair"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743"
new_candidate = "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe P30E pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {"__file__": str(SCRIPT), "__name__": "_p30e_entry_pretrigger"}
exec(compile(text, str(SOURCE), "exec"), namespace)
old_armed = namespace.get("ARMED")
if not isinstance(old_armed, str) or hashlib.sha256(old_armed.encode()).hexdigest() != ARMED_SHA256:
    raise SystemExit("source armed contract changed")
new_armed = old_armed.replace("binder_abi=2", "binder_abi=3", 1) + (
    " p30e_prepare_attempted=0 p30e_prepare_ret=0 p30e_arm_attempted=0"
    " p30e_arm_ret=0 p30e_armed=0 p30e_readback_attempted=0"
    " p30e_readback_ret=0 p30e_controller_state=0 p30e_target_state=0"
    " p30e_target_sequence=0 p30e_controller_sequence=0"
)
namespace["ARMED"] = new_armed
classify = namespace.get("classify")
if not callable(classify) or classify.__globals__.get("ARMED") != old_armed:
    raise SystemExit("source classifier globals changed")
classify.__globals__["ARMED"] = new_armed
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
