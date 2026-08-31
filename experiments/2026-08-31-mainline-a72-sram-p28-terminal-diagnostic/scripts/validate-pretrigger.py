#!/usr/bin/env python3
"""Validate the exact SRAM/P28 diagnostic candidate before its one trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c75c6c43f30f9b029b94aeb3ce17229f51fa26f20d08087b0208fed3a0926b2e"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726"
new_candidate = "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe SRAM/P28 diagnostic pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "_sram_p28_diagnostic_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
old_armed = namespace.get("ARMED")
if not isinstance(old_armed, str) or old_armed.count("binder_abi=1") != 1:
    raise SystemExit("source armed status changed")
suffix = (
    " p28_begin_attempted=0 p28_begin_ret=0 p28_begun=0 "
    "sram_returned=0 sram_ret=0 sram_match=0x0 sram_required=0xfff "
    "p28_complete_attempted=0 p28_complete_ret=0 sram_abi=0 "
    "sram_attempted=0x0 sram_completed=0x0 sram_mv=0 "
    "sram_selector_first=0x0 sram_calibration_first=0x0 "
    "sram_selector_second=0x0 sram_calibration_second=0x0 "
    "sram_attempt_id=0 sram_cookie=0 sram_error=0 "
    "sram_effect_attempted=0 sram_verified=0 sram_sealed=0"
)
new_armed = old_armed.replace("binder_abi=1", "binder_abi=2", 1) + suffix
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
