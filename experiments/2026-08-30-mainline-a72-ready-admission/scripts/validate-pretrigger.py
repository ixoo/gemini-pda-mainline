#!/usr/bin/env python3
"""Source-pin the live armed-frame validator for the READY-bound candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_SHA256 = "906a404932f64ec3795f666b9adda0167f49777f24c52178c20ca0aaea953715"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/validate-pretrigger.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")
text = SOURCE.read_text(encoding="utf-8")
old = "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef"
new = "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7"
if text.count(old) != 1:
    raise SystemExit("unsafe READY pre-trigger validator derivation")
text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "a72_ready_pretrigger_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
namespace["main"]()
