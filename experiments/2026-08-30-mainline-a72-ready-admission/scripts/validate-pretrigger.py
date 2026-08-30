#!/usr/bin/env python3
"""Source-pin the trace-aware armed-frame validator for the READY candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_SHA256 = "9188f8b96bdfeedc1921df5043eeb6e0120b2383b9a8fa454c50b5ef1ed64f0a"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/validate-pretrigger.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")
text = SOURCE.read_text(encoding="utf-8")
replacements = (
    (
        "83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
        "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7",
        1,
    ),
    (
        "7.1.3-gemini-a72-admission-softtrace",
        "7.1.3-gemini-a72-admission-live",
        1,
    ),
    (
        "exact-softtrace-identity-and-armed-contract",
        "exact-ready-identity-and-armed-contract",
        1,
    ),
)
for old, new, count in replacements:
    if text.count(old) != count:
        raise SystemExit(f"unsafe READY pre-trigger validator derivation: {old}")
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "a72_ready_pretrigger_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
