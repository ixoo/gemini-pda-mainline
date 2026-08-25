#!/usr/bin/env python3
"""Source-pinned branch and mutation tests for provider-ready recovery."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/test-recovery-tools.py"
SOURCE_SHA256 = "f4a7fdedabebee741d09a57e624f74be3babc41de81bbaaa5bee7ed1d97a2969"


if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source recovery tests changed")
text = SOURCE.read_text(encoding="utf-8")
replacements = (
    (
        '"""Reject unsafe platform/provider retained-recovery mutations."""',
        '"""Reject unsafe provider-ready retained-recovery mutations."""',
        1,
    ),
    (
        'validation=a72-platform-provider-recovery-tools',
        'validation=a72-platform-provider-ready-recovery-tools',
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe provider-ready recovery-test derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)

with tempfile.NamedTemporaryFile(
    mode="w", encoding="utf-8", prefix=".test-recovery-provider-ready.", suffix=".py", dir=SCRIPT_DIR
) as derived:
    derived.write(text)
    derived.flush()
    result = subprocess.run([sys.executable, derived.name], check=False)
raise SystemExit(result.returncode)
