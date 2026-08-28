#!/usr/bin/env python3
"""Source-pin the three-branch terminal classifier."""

from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_SHA256 = "274b950c8c0dbd2ca3eb6fa7933fe692251de70bf7aadf735bc98d5c12d2886e"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/classify-attempt.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

namespace = {"__file__": str(SCRIPT), "__name__": __name__}
text = SOURCE.read_text(encoding="utf-8")
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items() if key != "__builtins__"})
