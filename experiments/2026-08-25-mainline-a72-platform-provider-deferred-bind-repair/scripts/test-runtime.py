#!/usr/bin/env python3
"""Source-pinned positive and negative tests for the provider-ready classifier."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/test-runtime.py"
SOURCE_SHA256 = "4b1ddaaf8b4aa17e78751626ac2c726d58e94db8db3dfbb393395b3bc36709f1"


if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source runtime tests changed")
text = SOURCE.read_text(encoding="utf-8")
replacements = (
    (
        '"""Test accepted and rejected platform/provider live captures."""',
        '"""Test accepted and rejected provider-ready live captures."""',
        1,
    ),
    (
        '"provider_snapshot_request=one-stable-read-only", "provider_snapshots_expected=1",',
        '"provider_readiness_request=explicit-phandle-bound-device",\n'
        '        "provider_snapshot_request=one-stable-read-only", "provider_snapshots_expected=1",',
        1,
    ),
    (
        '("provider_i2c_bound=1", "provider_i2c_bound=0"),',
        '("provider_i2c_bound=1", "provider_i2c_bound=0"),\n'
        '    ("provider_readiness_request=explicit-phandle-bound-device", "provider_readiness_request=none"),',
        1,
    ),
    (
        'print("result=pass")',
        'print("provider_ready_gate_mutation=rejected")\nprint("result=pass")',
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe provider-ready runtime test derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)

with tempfile.NamedTemporaryFile(
    mode="w", encoding="utf-8", prefix=".test-runtime-provider-ready.", suffix=".py", dir=SCRIPT_DIR
) as derived:
    derived.write(text)
    derived.flush()
    result = subprocess.run([sys.executable, derived.name], check=False)
raise SystemExit(result.returncode)
