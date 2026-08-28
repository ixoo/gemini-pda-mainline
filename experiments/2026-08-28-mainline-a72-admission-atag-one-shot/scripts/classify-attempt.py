#!/usr/bin/env python3
"""Source-pin the corrected three-branch classifier for the ATAG boot."""

from __future__ import annotations
import hashlib
from pathlib import Path

SOURCE_SHA256 = "974315e58463c0430a2cdafdbdd978418e1fed866d492231d8b2cb2a658d298a"
SCRIPT = Path(__file__).resolve(); ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-serviceable-one-shot/scripts/classify-attempt.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")
namespace = {"__file__": str(SCRIPT), "__name__": "_atag_attempt_classifier"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items() if key not in {"__builtins__", "__file__", "__name__"}})
if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
