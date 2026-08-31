#!/usr/bin/env python3
"""Classify the held-result repair CPU8 trigger on its accepted boot."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "ee53bef775ae2b3c16a77de63e916dfda06fca22cd871a62f37cf065f1badb1f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-p27-runtime-attribution"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "_p27_held_result_repair_attempt_classifier",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
