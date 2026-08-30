#!/usr/bin/env python3
"""Run the proven composed-DT mutation suite against the repaired validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8238ade4d47adeba67b23f910f82f30f32272f69051337d44bbcd819729ff188"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/test-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT mutation suite changed")

namespace = {"__file__": str(SCRIPT), "__name__": "__main__"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
