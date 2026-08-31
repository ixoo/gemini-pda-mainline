#!/usr/bin/env python3
"""Source-pin the proven DT composer to the expected-MIDR guard repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "ed869e9672f0e3b385196ccbe4e7e88dcb47ecf0c475fe10a0363f39d0d12adf"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("7970125baf9ba884aab2319d50ab882bfe59009cde6da20799cc729d0642cb37",
     "c365731aeaa70c85a2df5444d8bb4dd4a4a7b9cebc707651966c8b4502f44825", 1),
    ("5ecb733cb6b5a9251d11dc0c8b414dfe22155d5648903ffb6f17102cb83d14ab",
     "49609e10403ca03cb3159a62364216166a9bdbc7ee1c673e822cac585791ed37", 1),
    ("417111b329be60ff83a5adbca31231682728b679ca1ef23cda37ec9cee4cd617",
     "5ff252562aad8239ff27f0bd57b0fb19dfaa6fcdbaf16302c6f77d4ae000d894", 1),
    ("unsafe r0p1 expected-pair repair DT derivation",
     "unsafe expected-MIDR model-guard repair DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe expected-MIDR model-guard DT derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_expected_midr_model_guard_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
