#!/usr/bin/env python3
"""Source-pin the proven DT composer to the SRAM/P28 diagnostic package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "49bad24ec51da08901adf25668aa211485e2c372c68804c2ac4306316f029ebf"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("3cff093ffc182d4870858a70f8a1fac8d14ebd8d4cf2402459c3a2a07353bc86",
     "1da2e7a0a00c60e242be077200fe708384cfa066bd149bc975f460de1a09cbeb", 1),
    ("24676031cf019d78fa6319708a069ea45e05c8314c872447f6c8a9207c51eb33",
     "5a40fc6a50a9b5fe20b670861491d4e20e0391ea32d0797fb44901500ca26733", 1),
    ("57fb4aae9cf3f5767e7b3d8ae95238d806e3ed55bfe2298d587f7fc550a3c7dd",
     "8346f271280739437a013e04a3f9992981adbaa302e2c44add844008f832902d", 1),
    ("unsafe isolation-result repair DT derivation",
     "unsafe SRAM/P28 diagnostic DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe SRAM/P28 diagnostic DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_sram_p28_diagnostic_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
