#!/usr/bin/env python3
"""Source-pin the proven DT composer to the selector-mask repair package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "f5aceec488953e5767e17de803bc01659f003e92a1f3ce54243de0d061fb5149"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("1da2e7a0a00c60e242be077200fe708384cfa066bd149bc975f460de1a09cbeb",
     "259f8d6eb7fafc0ebfb3984e98700a6f6b2cd02a85c452e13ce3110ccf2a1392", 1),
    ("5a40fc6a50a9b5fe20b670861491d4e20e0391ea32d0797fb44901500ca26733",
     "85d2d063aeee082af6aaf0cf366912abfdb13fbbce02612818c3d6d54c4caa85", 1),
    ("8346f271280739437a013e04a3f9992981adbaa302e2c44add844008f832902d",
     "9e0445cc404cd76aff96cfbfb7a9305b91cd1ff71918aaf6ca451f6f11780be3", 1),
    ("unsafe SRAM/P28 diagnostic DT derivation",
     "unsafe selector-mask repair DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe selector-mask repair DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_selector_mask_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
