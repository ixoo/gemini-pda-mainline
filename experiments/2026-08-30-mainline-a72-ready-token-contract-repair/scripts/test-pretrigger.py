#!/usr/bin/env python3
"""Exercise the repaired candidate pre-trigger gate and its mutations."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "484192668ff27582447ce78668e8e06f6ca2c1e3815c560bda359284efb26c95"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/test-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger mutation test changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_ready_contract_pretrigger_test"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
validator = namespace["validator"]
frame = namespace["frame"]
for old, new in (
    ("failure_stage=0", "failure_stage=2"),
    ("derive_stage=0", "derive_stage=2"),
):
    try:
        validator.classify(frame().replace(old, new, 1))
    except validator.Classification:
        pass
    else:
        raise AssertionError(f"unsafe repaired pre-trigger mutation accepted: {old}")

print("pretrigger_repair_mutations_rejected=2")
print("result=pass")
