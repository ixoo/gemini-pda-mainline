#!/usr/bin/env python3
"""Source-pin the proven DT composer to the isolation-result repair package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "b2e31044b82434079676b91ea74a8fd3ab85d8e79f61a4490e2715a64eb37964"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("c1c0d45aacaa37b447edab27859502d5a43f3a0fa729031e772b316577ec869d",
     "3cff093ffc182d4870858a70f8a1fac8d14ebd8d4cf2402459c3a2a07353bc86", 1),
    ("ed18689c4a2ee2a670a8746fd598d9ac8f4caa1d32f55828046e64680eb348b6",
     "24676031cf019d78fa6319708a069ea45e05c8314c872447f6c8a9207c51eb33", 1),
    ("ded617adef441801834d37256c9ef954f035a089bf9b2eb0c4faacd2c0acc8d2",
     "57fb4aae9cf3f5767e7b3d8ae95238d806e3ed55bfe2298d587f7fc550a3c7dd", 1),
    ("unsafe held-result repair DT derivation",
     "unsafe isolation-result repair DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe isolation-result repair DT derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_isolation_held_result_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
