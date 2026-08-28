#!/usr/bin/env python3
"""Source-pin the mutation suite and bind its fixture to the ATAG boot ID."""

from __future__ import annotations
import hashlib
from pathlib import Path

SOURCE_SHA256 = "9d60eef5a572e64964c06c4f569ee0c4b29545755a00e2d63424048759bb4276"
SCRIPT = Path(__file__).resolve(); ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-serviceable-one-shot/scripts/test-runtime.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source runtime tests changed")
text = SOURCE.read_text(encoding="utf-8")
old = "boot_id=21bb6547-a5cd-494c-8900-d92884c0c6a5"
new = "boot_id=515b4618-5bf7-4125-9c08-38db55d6cc27"
if text.count(old) != 1:
    raise SystemExit("unsafe ATAG runtime-test derivation")
text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": __name__}
exec(compile(text, str(SOURCE), "exec"), namespace)
