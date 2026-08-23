#!/usr/bin/env python3
"""Derive negative tests for the coexistence live and retained classifiers."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "3f9bdeec8a273809c088e4a2e59e60f64944a8827a10bdbb35e6f82721a72bef"
source = (
    Path(__file__).resolve().parents[3]
    / "experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry"
    / "scripts/test-runtime-tools.py"
)
if (
    not source.is_file()
    or source.is_symlink()
    or hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256
):
    raise SystemExit("source runtime test is missing, unsafe, or changed")

text = source.read_text(encoding="utf-8")
replacements = (
    ("Reject unsafe clock-entry live and retained-recovery mutations.",
     "Reject unsafe clock/CSPM coexistence and retained-recovery mutations.", 1),
    ("gemini-clock-entry-retained-test.", "gemini-clock-cspm-retained-test.", 1),
    ("clock-backend-first-dmesg-live-pass",
     "clock-backend-cspm-coexistence-live-pass", 1),
    ("clock-entry-direct-retention-only", "clock-cspm-direct-retention-only", 1),
    ("clock-entry-cross-version-enumeration-pass",
     "clock-cspm-cross-version-enumeration-pass", 1),
    ("validation=clock-backend-first-dmesg-runtime-tools",
     "validation=clock-backend-cspm-coexistence-runtime-tools", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe runtime test derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old = '''        "protected_readback_devices": "0",
'''
new = old + '''        "handoff_bound": "1",
        "i2c6_bound": "1",
        "clock_backend_bound": "1",
        "handoff_state": "ready",
        "i2c6_handoff_ready_count": "1",
        "cspm_range_count": "1",
        "cspm_handoff_owner_count": "1",
        "mcumixed_clock_owner_count": "1",
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime test derivation: resource fixture gate changed")
text = text.replace(old, new)

old = '''        "clock_prefix_count": "3",
'''
new = old + '''        "coexistence_exact_count": "1",
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime test derivation: marker fixture gate changed")
text = text.replace(old, new)

old = '''        "first_dmesg_prefix_count": "0",
'''
new = old + '''        "owner_exact_count": "1",
        "handoff_ebusy_count": "0",
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime test derivation: owner fixture gate changed")
text = text.replace(old, new)

old = '''        live.replace("protected_readback_devices=0", "protected_readback_devices=1", 1),
'''
new = old + '''        live.replace("handoff_bound=1", "handoff_bound=0", 1),
        live.replace("i2c6_bound=1", "i2c6_bound=0", 1),
        live.replace("clock_backend_bound=1", "clock_backend_bound=0", 1),
        live.replace("handoff_state=ready", "handoff_state=failed", 1),
        live.replace("i2c6_handoff_ready_count=1", "i2c6_handoff_ready_count=0", 1),
        live.replace("cspm_range_count=1", "cspm_range_count=2", 1),
        live.replace("cspm_handoff_owner_count=1", "cspm_handoff_owner_count=0", 1),
        live.replace("mcumixed_clock_owner_count=1", "mcumixed_clock_owner_count=0", 1),
        live.replace("coexistence_exact_count=1", "coexistence_exact_count=0", 1),
        live.replace("owner_exact_count=1", "owner_exact_count=0", 1),
        live.replace("handoff_ebusy_count=0", "handoff_ebusy_count=1", 1),
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime test derivation: mutation gate changed")
text = text.replace(old, new)

old = '''    for required in ("$BB dmesg", "probe_complete_exact_count", "clock_backend_devices"):
'''
new = '''    for required in ("$BB dmesg", "probe_complete_exact_count", "clock_backend_devices",
                     "coexistence_exact_count", "cspm_handoff_owner_count", "handoff_state"):
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime test derivation: probe audit gate changed")
text = text.replace(old, new)

exec(compile(text, str(source), "exec"), globals())
