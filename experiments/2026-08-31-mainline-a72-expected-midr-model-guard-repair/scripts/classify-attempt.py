#!/usr/bin/env python3
"""Classify one expected-MIDR model-guard CPU8 trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a237f2d8f251661caa5cdd37aeda97c269129bb1c411f4d44be67f888192f6f0"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_model_guard_classifier"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
