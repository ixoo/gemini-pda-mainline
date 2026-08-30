#!/usr/bin/env python3
"""Run the source-pinned READY-frame mutation rejection suite."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "484192668ff27582447ce78668e8e06f6ca2c1e3815c560bda359284efb26c95"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/test-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger mutation suite changed")

namespace = {"__file__": str(SCRIPT), "__name__": "__main__"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
