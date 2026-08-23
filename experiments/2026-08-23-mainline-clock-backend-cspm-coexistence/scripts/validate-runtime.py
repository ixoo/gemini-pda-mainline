#!/usr/bin/env python3
"""Derive the exact clock/CSPM coexistence live classifier."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "dd6baafed2a1902c470caf149ee31c92a03407e85b13fe974429f09af95af0dc"
source = (
    Path(__file__).resolve().parents[3]
    / "experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry"
    / "scripts/validate-runtime.py"
)
if (
    not source.is_file()
    or source.is_symlink()
    or hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256
):
    raise SystemExit("source runtime validator is missing, unsafe, or changed")

text = source.read_text(encoding="utf-8")
replacements = (
    ("Classify the exact read-free clock-entry live result.",
     "Classify the exact read-free clock/CSPM coexistence live result.", 1),
    ("__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_BEGIN__",
     "__CLOCK_BACKEND_CSPM_COEXISTENCE_RUNTIME_BEGIN__", 1),
    ("__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_END__",
     "__CLOCK_BACKEND_CSPM_COEXISTENCE_RUNTIME_END__", 1),
    ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4",
     "ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7", 1),
    ("7.1.3-gemini-clock-entry-first-dmesg",
     "7.1.3-gemini-clock-cspm-coexist", 1),
    ("clock-backend-first-dmesg-live-pass",
     "clock-backend-cspm-coexistence-live-pass", 2),
    ("read-free-probe-complete-and-serviceability",
     "single-cspm-owner-clock-handoff-i2c6-da921x-serviceability", 1),
    ("claim_scope=clock-driver-init-and-read-free-probe-only",
     "claim_scope=read-free-clock-cspm-resource-coexistence-only", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe runtime validator derivation: expected {count}, found {actual}: {old}"
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
    raise SystemExit("unsafe runtime validator derivation: resource expectation gate changed")
text = text.replace(old, new)

old = '''        "clock_prefix_count": "3",
'''
new = old + '''        "coexistence_exact_count": "1",
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime validator derivation: marker expectation gate changed")
text = text.replace(old, new)

old = '''        "first_dmesg_prefix_count": "0",
'''
new = old + '''        "owner_exact_count": "1",
        "handoff_ebusy_count": "0",
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime validator derivation: owner expectation gate changed")
text = text.replace(old, new)

old = '''        "protected_readback_devices", "clock_prefix_count",
'''
new = '''        "protected_readback_devices", "handoff_bound", "i2c6_bound",
        "clock_backend_bound", "handoff_state", "i2c6_handoff_ready_count",
        "cspm_range_count", "cspm_handoff_owner_count",
        "mcumixed_clock_owner_count", "clock_prefix_count", "coexistence_exact_count",
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime validator derivation: safety-key gate changed")
text = text.replace(old, new)

old = '''        "first_dmesg_prefix_count", "block_mounts", "device_storage_writes",
'''
new = '''        "first_dmesg_prefix_count", "owner_exact_count", "handoff_ebusy_count",
        "block_mounts", "device_storage_writes",
'''
if text.count(old) != 1:
    raise SystemExit("unsafe runtime validator derivation: safety-key owner gate changed")
text = text.replace(old, new)

exec(compile(text, str(source), "exec"), globals())
