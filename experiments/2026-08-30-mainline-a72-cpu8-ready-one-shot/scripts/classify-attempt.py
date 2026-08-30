#!/usr/bin/env python3
"""Source-pin the reviewed three-branch CPU8 terminal classifier."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6bc47b78562d9ff9ce8ad1527ac6a2f0f143944fd7fb497dff547fbb290b50bf"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-admission-one-shot"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source one-shot classifier changed")

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_cpu8_ready_one_shot_attempt_classifier",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
