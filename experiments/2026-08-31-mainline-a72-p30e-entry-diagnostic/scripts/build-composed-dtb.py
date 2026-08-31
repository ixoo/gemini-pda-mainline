#!/usr/bin/env python3
"""Source-pin the proven DT composer to the P30E publication repair package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "e911edaa24cdc4cf43dbf34650e2e1e61a415e25556e3b43756f8e8fb50c97aa"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-selector-mask-contract-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("259f8d6eb7fafc0ebfb3984e98700a6f6b2cd02a85c452e13ce3110ccf2a1392",
     "57d60f16206238c694202a71ff56fae2e291d0e22bde58ebe149297c24e2ec5c", 1),
    ("85d2d063aeee082af6aaf0cf366912abfdb13fbbce02612818c3d6d54c4caa85",
     "babf618dbb1c39e6fa25d9260a92c5fcf664c0862aec59aeb117982890f1db2f", 1),
    ("9e0445cc404cd76aff96cfbfb7a9305b91cd1ff71918aaf6ca451f6f11780be3",
     "461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3", 1),
    ("unsafe selector-mask repair DT derivation",
     "unsafe P30E publication repair DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E publication repair DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p30e_publication_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
