#!/usr/bin/env python3
"""Source-pin the proven DT composer to the held-result repair package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "9bb02306605343076a6ff728afa21fd01365b76da1d2c66e9b8dc7351099adda"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-p27-runtime-attribution"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("2206ebf079e6242acccc9a2ef6455007638fffc49b389ef45f955bc6aa7a90b9",
     "c1c0d45aacaa37b447edab27859502d5a43f3a0fa729031e772b316577ec869d", 1),
    ("54321aed62ff4ea61f1f9ae58d32e7a1a018423e599580e519c692a2c235e85e",
     "ed18689c4a2ee2a670a8746fd598d9ac8f4caa1d32f55828046e64680eb348b6", 1),
    ("7c2f1f76dfc7ab1645c0563a6d93bfd6e9c48a39c570c0d2f06beef8f796e0a7",
     "ded617adef441801834d37256c9ef954f035a089bf9b2eb0c4faacd2c0acc8d2", 1),
    ("unsafe P27 diagnostic DT derivation",
     "unsafe held-result repair DT derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe held-result repair DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p27_held_result_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
