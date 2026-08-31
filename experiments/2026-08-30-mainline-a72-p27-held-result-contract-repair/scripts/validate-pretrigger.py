#!/usr/bin/env python3
"""Validate the exact held-result repair candidate before its one trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "4513c845db329390eb778c07b866e723b3fba1638033536fcf5333958caef7a2"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-p27-runtime-attribution"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80"
new_candidate = "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe held-result repair pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "_p27_held_result_repair_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
