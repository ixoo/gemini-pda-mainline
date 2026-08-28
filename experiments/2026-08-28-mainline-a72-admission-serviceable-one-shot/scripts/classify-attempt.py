#!/usr/bin/env python3
"""Derive the three-branch classifier for the action's observed wire format."""

from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_SHA256 = "274b950c8c0dbd2ca3eb6fa7933fe692251de70bf7aadf735bc98d5c12d2886e"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/classify-attempt.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_source_attempt_classifier"}
text = SOURCE.read_text(encoding="utf-8")
exec(compile(text, str(SOURCE), "exec"), namespace)
old_commit = ("trigger_commit=yes "
              "token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f")
new_commit = ("trigger_commit=yes\n"
              "token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f")
if namespace.get("COMMIT") != old_commit:
    raise SystemExit("unsafe attempt-classifier derivation")
namespace["COMMIT"] = new_commit
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
