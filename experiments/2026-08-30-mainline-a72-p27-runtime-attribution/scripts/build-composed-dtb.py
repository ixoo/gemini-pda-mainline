#!/usr/bin/env python3
"""Source-pin the proven DT composer to the P27 diagnostic package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "491f8d91a0d2d097d357dd5a451a2a10f3448dff3d5250d3c7b8293fdf64fa4b"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-token-contract-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("2f5e10f88d010d9e66bbaee677d46fcd5a83abcfc7f6953c6c70f66e3de53a6f",
     "2206ebf079e6242acccc9a2ef6455007638fffc49b389ef45f955bc6aa7a90b9", 1),
    ("3af4f670ea553338553d829a5abf1d8e4bc802b628ce4f6e65bdb40a8b081509",
     "54321aed62ff4ea61f1f9ae58d32e7a1a018423e599580e519c692a2c235e85e", 1),
    ("11eb595964b191d83f08b33260462fae1dba3dfba0d26e99ce1552a444864526",
     "7c2f1f76dfc7ab1645c0563a6d93bfd6e9c48a39c570c0d2f06beef8f796e0a7", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 diagnostic DT derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p27_diagnostic_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
