#!/usr/bin/env python3
"""Source-pin the proven DT composer to the expected-pair model repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c26aa67767981e39c93ac56c9e79b08ba3f103165bf6fe3405144b1df663778e"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-effect-plan-stage-ledger"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("c0e5cc4448fa2e152b5bdfacf2cbe7d33785f73841b3497fa33372509d8915d5",
     "4b62f81bd328281bcd025d5cd17e404fc791e8d1b0c74021e52b03e13d17bee7", 1),
    ("de2e447181c175e80a01afbf2794a471807b7242c8867f5b791acec8b08e2b52",
     "73b0a7d696cddace08752ffc0c5f158c6e01e3fd16f5dce86cc219b4c4551dcd", 1),
    ("7116bc604fd732dad39e9365579d7fa0e42c185c201134364e699f5e572be964",
     "cab076e835a98fc7fe247ddb502df1cb7cec8e971552c5f6ef7fb5a5153314ff", 1),
    ("unsafe effect-plan stage-ledger DT derivation",
     "unsafe expected-pair model-contract repair DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe expected-pair model repair DT derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_expected_pair_model_contract_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
