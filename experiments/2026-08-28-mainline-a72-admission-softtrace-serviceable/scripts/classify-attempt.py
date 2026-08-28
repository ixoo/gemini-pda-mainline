#!/usr/bin/env python3
"""Source-pin the unchanged trace-softfail terminal classifier."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "033a80bd39a494d0b1d3d6f0773ca278112f2e98cffbd3d2fcdceab6db3b653f"
SOURCE = (
    Path(__file__).resolve().parents[1]
    / ".."
    / "2026-08-28-mainline-a72-admission-trace-softfail"
    / "scripts"
    / "classify-attempt.py"
).resolve()
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")
namespace = {"__file__": str(Path(__file__).resolve()), "__name__": "_softtrace_classifier"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
old_commit = (
    "trigger_commit=yes "
    "token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f"
)
new_commit = (
    "trigger_commit=yes\n"
    "token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f"
)
if namespace.get("COMMIT") != old_commit:
    raise SystemExit("unsafe corrected commit-wire derivation")
namespace["COMMIT"] = new_commit
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
