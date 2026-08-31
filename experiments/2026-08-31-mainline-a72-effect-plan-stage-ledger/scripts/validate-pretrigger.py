#!/usr/bin/env python3
"""Validate the exact stage-ledger candidate before any CPU8 trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "323b49071d93c0a13fc25a957c80ba5a82ba9b0f94c1ee5e3197a12d056c408e"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69"
new_candidate = "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe stage-ledger pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {"__file__": str(SCRIPT), "__name__": "_effect_plan_stage_pretrigger"}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
