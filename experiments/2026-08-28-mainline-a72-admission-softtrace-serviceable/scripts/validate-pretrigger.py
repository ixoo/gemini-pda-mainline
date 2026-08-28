#!/usr/bin/env python3
"""Source-pin the softtrace frame validator for the corrected candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "9188f8b96bdfeedc1921df5043eeb6e0120b2383b9a8fa454c50b5ef1ed64f0a"
SOURCE = (
    Path(__file__).resolve().parents[1]
    / ".."
    / "2026-08-28-mainline-a72-admission-trace-softfail"
    / "scripts"
    / "validate-pretrigger.py"
).resolve()
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pretrigger validator changed")
text = SOURCE.read_text(encoding="utf-8")
old = "83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0"
new = "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60"
if text.count(old) != 1:
    raise SystemExit("unsafe serviceable pretrigger validator derivation")
exec(compile(text.replace(old, new), str(SOURCE), "exec"), globals())
