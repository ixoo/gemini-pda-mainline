#!/usr/bin/env python3
"""Source-pin the proven DT composer to the entry-checkpoint package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a70d450215ca8198a9792d3059322838e03c2dfe28eab0c3d319e7c24d14756b"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-p30e-ready-identity-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("86674d0624fd78d5aa6683432d4dba9e6ee8b643cb9d4767865c23e7b89e18d4",
     "2208f4376bc6e0facea228237e1954c5e4e019e73d8ecae50c6a425eefaa6dd2", 1),
    ("ae732f872bc9f5ed653e25dce2fd9e1bff1bf8134383ed0f48e58ffb1ee24a7b",
     "c3ee11108f2551d39f86955d6466d2e8cb12a7dd1f4f8416c632e28611e06026", 1),
    ("614556198ae2459459d849d6428347009f343582a678f056802b7775224c3137",
     "1bc12e8dacff2cef9f248276de80c4e0d37ebd50d5a4e42ed9dc0164837b4046", 1),
    ("unsafe P30E READY-identity repair DT derivation",
     "unsafe P30E entry-checkpoint DT derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E entry-checkpoint DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p30e_entry_checkpoint_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
