#!/usr/bin/env python3
"""Source-pin the proven DT composer to the P30E READY-identity repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c3a176971d6071d523a1315635e1313cba86d0dacfc02b78defa052bf6049d0f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("57d60f16206238c694202a71ff56fae2e291d0e22bde58ebe149297c24e2ec5c",
     "86674d0624fd78d5aa6683432d4dba9e6ee8b643cb9d4767865c23e7b89e18d4", 1),
    ("babf618dbb1c39e6fa25d9260a92c5fcf664c0862aec59aeb117982890f1db2f",
     "ae732f872bc9f5ed653e25dce2fd9e1bff1bf8134383ed0f48e58ffb1ee24a7b", 1),
    ("461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3",
     "614556198ae2459459d849d6428347009f343582a678f056802b7775224c3137", 1),
    ("unsafe P30E publication repair DT derivation",
     "unsafe P30E READY-identity repair DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E READY-identity DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p30e_ready_identity_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
