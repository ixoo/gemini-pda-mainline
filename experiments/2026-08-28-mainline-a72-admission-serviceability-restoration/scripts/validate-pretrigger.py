#!/usr/bin/env python3
"""Source-pin and retarget the exact pre-trigger frame validator."""

from __future__ import annotations
import hashlib
from pathlib import Path

SOURCE_SHA256 = "906a404932f64ec3795f666b9adda0167f49777f24c52178c20ca0aaea953715"
SCRIPT = Path(__file__).resolve(); ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/validate-pretrigger.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")
text = SOURCE.read_text(encoding="utf-8")
old = "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef"
new = "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02"
if text.count(old) != 1: raise SystemExit("unsafe pre-trigger validator derivation")
text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "serviceable_pretrigger_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
namespace["main"]()
