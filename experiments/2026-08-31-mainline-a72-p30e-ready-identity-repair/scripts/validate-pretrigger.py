#!/usr/bin/env python3
"""Validate the exact READY-identity repair before its one P30E trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "f3f4067fdb365ea0fc5eee7c2b0176ddb45c69c5ddf68ddf886aad64e3995a7f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453"
new_candidate = "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe P30E READY-identity pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {"__file__": str(SCRIPT), "__name__": "_p30e_ready_identity_pretrigger"}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
