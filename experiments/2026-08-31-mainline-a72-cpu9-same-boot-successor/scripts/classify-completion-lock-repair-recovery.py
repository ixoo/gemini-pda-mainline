#!/usr/bin/env python3
"""Classify retained patch-0481 CPU9 completion-lock repair evidence."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_SHA256 = "64e17462c68829e993b6437a3a96c26f9ea57adc27e47a56fd8afc130939d02f"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-membership-lock-repair-recovery.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source membership-lock recovery classifier changed")

spec = importlib.util.spec_from_file_location(
    "cpu9_completion_lock_repair_recovery_base", SOURCE
)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = source
spec.loader.exec_module(source)

if __name__ == "__main__":
    raise SystemExit(source.main())
