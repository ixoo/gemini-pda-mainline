#!/usr/bin/env python3
"""Validate the exact checkpoint candidate before its one CPU8 trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "05accc9657be8268b0602216324919efa193243c61ad2ae78bdc2a6e3734304d"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-p30e-ready-identity-repair"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16"
new_candidate = "6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe checkpoint pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {"__file__": str(SCRIPT), "__name__": "_checkpoint_pretrigger"}
exec(compile(text, str(SOURCE), "exec"), namespace)
old_armed = namespace.get("ARMED")
if not isinstance(old_armed, str) or old_armed.count("binder_abi=3") != 1:
    raise SystemExit("source ABI-3 armed contract changed")
reason_boundary = " p30e_target_state=0 p30e_target_sequence=0"
if old_armed.count(reason_boundary) != 1:
    raise SystemExit("source P30E armed field order changed")
new_armed = old_armed.replace("binder_abi=3", "binder_abi=4", 1).replace(
    reason_boundary,
    " p30e_target_state=0 p30e_target_reason=0 p30e_target_sequence=0",
    1,
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
