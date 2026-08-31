#!/usr/bin/env python3
"""Validate the exact isolation-result repair candidate before its one trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "4bc91d5bf53ebf45328d3b57838823a16b691cc6e0a2064bf6c3dad872915b25"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5"
new_candidate = "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe isolation-result repair pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "_isolation_held_result_repair_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
