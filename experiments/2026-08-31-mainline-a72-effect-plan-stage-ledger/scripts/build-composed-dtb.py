#!/usr/bin/env python3
"""Source-pin the proven DT composer to the effect-plan stage ledger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8d9365488230bdcb2f576e492e1e2cee4232b016c58a54fcf2b836c856d8fbf7"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("c365731aeaa70c85a2df5444d8bb4dd4a4a7b9cebc707651966c8b4502f44825",
     "c0e5cc4448fa2e152b5bdfacf2cbe7d33785f73841b3497fa33372509d8915d5", 1),
    ("49609e10403ca03cb3159a62364216166a9bdbc7ee1c673e822cac585791ed37",
     "de2e447181c175e80a01afbf2794a471807b7242c8867f5b791acec8b08e2b52", 1),
    ("5ff252562aad8239ff27f0bd57b0fb19dfaa6fcdbaf16302c6f77d4ae000d894",
     "7116bc604fd732dad39e9365579d7fa0e42c185c201134364e699f5e572be964", 1),
    ("unsafe expected-MIDR model-guard repair DT derivation",
     "unsafe effect-plan stage-ledger DT derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe effect-plan stage-ledger DT derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_effect_plan_stage_ledger_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
