#!/usr/bin/env python3
"""Source-pin the proven composition helper to the repaired CPU8 package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a7971af3bd1c7cf5f619a5a985703f38031e800cd54cf359b189341d80ad4f9f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("d3197c6870aa025840f6dc330e83e7871e78cce56e4b314e03085d7879c6954f",
     "0e926c85bda4d23eae366260182df23d0095304212d3d1b729efd9916f8c729c", 1),
    ("05a3e54a412e02bc224138056552451b706111d2d98d6e1363597efeecada93d",
     "658fa1b5068189cf419a44375db1108b54d5813f8d6c754820fbbb560cc07cff", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2",
     "7f3a23acec8060642b7c0d52a16b30cdfb7d52a55a70c984a008becb35a09c99", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repaired DT derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_live_a34_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
