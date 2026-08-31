#!/usr/bin/env python3
"""Classify one selector-mask repair CPU8 trigger on its accepted boot."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6f2063d9254ff4d956f30faefe36481392b60011083b4980c5583a2b68ae39f5"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

text = SOURCE.read_text(encoding="utf-8")
old = "Classify one SRAM/P28 diagnostic CPU8 trigger on its accepted boot."
new = "Classify one selector-mask repair CPU8 trigger on its accepted boot."
if text.count(old) != 1:
    raise SystemExit("unsafe selector-mask repair classifier derivation")
text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "_selector_mask_repair_classifier",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
