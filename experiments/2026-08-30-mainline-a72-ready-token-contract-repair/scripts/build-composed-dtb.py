#!/usr/bin/env python3
"""Source-pin the proven DT composer to the repaired READY-token package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "9a7afff13b96c66c8140be644e268a1eb92b7082317efa28a6fa8f0f26ce4534"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-live-a34-predicate-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("0e926c85bda4d23eae366260182df23d0095304212d3d1b729efd9916f8c729c",
     "2f5e10f88d010d9e66bbaee677d46fcd5a83abcfc7f6953c6c70f66e3de53a6f", 1),
    ("658fa1b5068189cf419a44375db1108b54d5813f8d6c754820fbbb560cc07cff",
     "3af4f670ea553338553d829a5abf1d8e4bc802b628ce4f6e65bdb40a8b081509", 1),
    ("7f3a23acec8060642b7c0d52a16b30cdfb7d52a55a70c984a008becb35a09c99",
     "11eb595964b191d83f08b33260462fae1dba3dfba0d26e99ce1552a444864526", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-contract DT derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_contract_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
