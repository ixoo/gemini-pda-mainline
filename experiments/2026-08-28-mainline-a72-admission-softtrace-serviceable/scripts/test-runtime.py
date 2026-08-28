#!/usr/bin/env python3
"""Run the trace-softfail mutation suite against the corrected local tools."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "84dc2064ed677420da66626f59d2cbce5fd77b08f0b866eb329335f56376fb38"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-28-mainline-a72-admission-trace-softfail"
    / "scripts/test-runtime.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source runtime tests changed")

namespace = {"__file__": str(SCRIPT), "__name__": __name__}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
