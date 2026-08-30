#!/usr/bin/env python3
"""Run the proven composed-DT mutation suite against the READY validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "663aa3729f74ffa4ebfd211f113d010067e0b9cb3f282824499c0d9f4c89c265"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-live-a34-predicate-repair"
    / "scripts/test-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT mutation suite changed")

namespace = {"__file__": str(SCRIPT), "__name__": "__main__"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
