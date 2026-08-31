#!/usr/bin/env python3
"""Validate the exact selector-mask repair candidate before its one trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "644e0253a08586eed1579e52f865a488912f5b875663fbabfb2417442dd6d54f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old = "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3"
new = "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743"
if text.count(old) != 1:
    raise SystemExit("unsafe selector-mask repair pre-trigger derivation")
text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "_selector_mask_repair_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
