#!/usr/bin/env python3
"""Run the source-pinned composed-DT mutation rejection suite."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "253aeeea024b5da8d1f3dab28c7b38d2f43e5874f96e5c88b7c267d443d3d876"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic"
    / "scripts/test-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT mutation suite changed")

namespace = {"__file__": str(SCRIPT), "__name__": "__main__"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
