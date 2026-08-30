#!/usr/bin/env python3
"""Source-pin the proven composer to the exact predicate-diagnostic record."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "d54ba50a046a65154148fdbc49b65bacc2ec7a024d2aea1d30d614e2d0599e3c"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-validation-closure"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT builder changed")

outer = {
    "__file__": str(SOURCE),
    "__name__": "a72_ready_plan_predicate_diagnostic_dtb_builder",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), outer)
implementation = outer["namespace"]
implementation["PACKAGE_DTB_SHA256"] = (
    "cbc311e5cb3aaa94186122d94b1b53252c4d22273b8bb599ffa75a8416c838e6"
)
implementation["RECORD_JSON_SHA256"] = (
    "d0099e86033582b8b5aa47d6791bc00b23c11116e58f08e3073d7cc0f3dd1536"
)
implementation["OUTPUT_SHA256"] = (
    "818dece52aa4361840d99525e3f439476a10d32bfa6a67db3f8c7479f89d69df"
)


if __name__ == "__main__":
    raise SystemExit(implementation["main"]())
