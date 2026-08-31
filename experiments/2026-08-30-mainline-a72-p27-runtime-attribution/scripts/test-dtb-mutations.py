#!/usr/bin/env python3
"""Run the proven composed-DT mutation suite against the P27 validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "ef5267c207dbde0f96b7f2019801f2fc43d843b80913f802d99e4adbfe18b5bf"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-token-contract-repair"
    / "scripts/test-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT mutation suite changed")

namespace = {"__file__": str(SCRIPT), "__name__": "__main__"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
