#!/usr/bin/env python3
"""Bind the proven READY-frame validator to the post-0437 boot2 image."""

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
old = "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a"
new = "726b622ab503e844e2faddb33fe357250df329510d5b3ab5877687f4db7bfcb0"
if text.count(old) != 1:
    raise SystemExit("unsafe READY-plan pre-trigger validator derivation")
text = text.replace(old, new)

_derived_namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_plan_closure_pretrigger_validator",
}
exec(compile(text, str(SOURCE), "exec"), _derived_namespace)
globals().update({
    key: value for key, value in _derived_namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(_derived_namespace["main"]())
