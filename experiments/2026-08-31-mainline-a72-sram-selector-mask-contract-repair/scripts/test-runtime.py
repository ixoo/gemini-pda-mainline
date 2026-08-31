#!/usr/bin/env python3
"""Exercise selector-mask repair boot attribution and classifications."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "5f80f1a375aea2ae695be01407d671399cfcca1f3d4af7014dd75a7190e1d169"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic"
    / "scripts/test-runtime.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source runtime test changed")

text = SOURCE.read_text(encoding="utf-8")
old = "Exercise exact SRAM/P28 boot attribution and terminal classifications."
new = "Exercise selector-mask repair boot attribution and terminal classifications."
if text.count(old) != 1:
    raise SystemExit("unsafe selector-mask repair runtime test derivation")
text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "_selector_mask_repair_test"}
exec(compile(text, str(SOURCE), "exec"), namespace)
