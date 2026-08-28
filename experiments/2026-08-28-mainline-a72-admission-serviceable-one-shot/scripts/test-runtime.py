#!/usr/bin/env python3
"""Source-pin the runtime mutation suite and bind its fixture boot ID."""

from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_SHA256 = "bf6f977c3603ae8bb0d3707178c6652290cd811347de77ca0b614c3f8cdf52a7"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/test-runtime.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source runtime tests changed")

text = SOURCE.read_text(encoding="utf-8")
old = "boot_id=12345678-1234-1234-1234-123456789abc"
new = "boot_id=21bb6547-a5cd-494c-8900-d92884c0c6a5"
if text.count(old) != 1:
    raise SystemExit("unsafe runtime-test derivation")
text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": __name__}
exec(compile(text, str(SOURCE), "exec"), namespace)
