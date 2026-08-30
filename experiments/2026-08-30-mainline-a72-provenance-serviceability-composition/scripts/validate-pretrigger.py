#!/usr/bin/env python3
"""Validate positive runtime identity, no blocker, and armed zero execution."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "9188f8b96bdfeedc1921df5043eeb6e0120b2383b9a8fa454c50b5ef1ed64f0a"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/validate-pretrigger.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
anchor = '''        "maxcpus8_tokens": "1", "udc_devices": "1", "block_mounts": "0",
'''
insert = anchor + '''        "provenance_node": "1",
        "provenance_compatible": "planet,gemini-a72-runtime-binding-v1,",
        "runtime_identity_verified_count": "1",
        "runtime_identity_invalid_count": "0",
        "runtime_identity_mismatch_count": "0",
        "runtime_identity_unconfigured_count": "0",
        "profile_blocked_count": "0",
'''
replacements = (
    ("83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
     "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", 1),
    ("7.1.3-gemini-a72-admission-softtrace",
     "7.1.3-gemini-a72-admission-live", 1),
    (anchor, insert, 1),
    ("exact-softtrace-identity-and-armed-contract",
     "exact-package-provenance-runtime-identity-verified-unblocked-armed-contract", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe identity-aware validator derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "a72_identity_aware_pretrigger_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
