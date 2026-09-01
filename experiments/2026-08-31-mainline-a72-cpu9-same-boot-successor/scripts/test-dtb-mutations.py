#!/usr/bin/env python3
"""Run the source-pinned composed-DT mutation suite against CPU9."""

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
    raise SystemExit("source composed-DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_composed_dtb_mutations"}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
