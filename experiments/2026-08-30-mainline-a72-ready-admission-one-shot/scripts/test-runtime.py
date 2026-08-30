#!/usr/bin/env python3
"""Run the trace-aware mutation suite against the exact READY live boot."""

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
    raise SystemExit("source trace-aware runtime tests changed")
text = SOURCE.read_text(encoding="utf-8")
old = "boot_id=12345678-1234-1234-1234-123456789abc"
new = "boot_id=2ec43fd0-3afb-4a56-bf9f-92bacff303ba"
if text.count(old) != 1:
    raise SystemExit("unsafe READY runtime-test boot binding")
namespace = {"__file__": str(SCRIPT), "__name__": __name__}
exec(compile(text.replace(old, new), str(SOURCE), "exec"), namespace)
