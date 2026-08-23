#!/usr/bin/env python3
"""Derive changed-ID Gemian validation for the exact coexistence candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "caebd9f33cff7ba7c7ac71575b094fc22a193e59d3f4c52b707f4bd27054cc1b"
source = (
    Path(__file__).resolve().parents[3]
    / "experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry"
    / "scripts/validate-retained.py"
)
if (
    not source.is_file()
    or source.is_symlink()
    or hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256
):
    raise SystemExit("source retained validator is missing, unsafe, or changed")

text = source.read_text(encoding="utf-8")
replacements = (
    ("Classify changed-ID Gemian recovery of exact clock-entry records 1 and 2.",
     "Classify changed-ID Gemian recovery for the exact coexistence candidate.", 1),
    ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4",
     "ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7", 1),
    ("clock-entry-cross-version-enumeration-pass",
     "clock-cspm-cross-version-enumeration-pass", 2),
    ("clock-entry-direct-retention-only",
     "clock-cspm-direct-retention-only", 2),
    ("claim_scope=clock-entry-first-dmesg-warm-retention-and-recovery-only",
     "claim_scope=coexistence-candidate-entry-retention-and-recovery-only", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe retained validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

exec(compile(text, str(source), "exec"), globals())
