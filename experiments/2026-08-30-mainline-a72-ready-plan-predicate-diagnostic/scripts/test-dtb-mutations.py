#!/usr/bin/env python3
"""Run the source-pinned composed-DT mutation rejection suite."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "061163998622dc2bf2d4a719dc99dba086a53636aba169d37c59997128385fd5"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-validation-closure"
    / "scripts/test-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT mutation suite changed")

namespace = {"__file__": str(SCRIPT), "__name__": "__main__"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
