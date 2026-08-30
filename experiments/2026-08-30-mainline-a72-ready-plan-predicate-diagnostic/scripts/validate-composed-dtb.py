#!/usr/bin/env python3
"""Source-pin the independent DT validator to the diagnostic identities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


SOURCE_SHA256 = "4c188399daa016e0aec2954ecb6a08f1f0463cc2daa99bc5dce81e4558c185fe"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-validation-closure"
    / "scripts/validate-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT validator changed")

outer: dict[str, Any] = {
    "__file__": str(SOURCE),
    "__name__": "a72_ready_plan_predicate_diagnostic_dtb_validator",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), outer)
implementation = outer["namespace"]
implementation["PACKAGE_DTB_SHA256"] = (
    "cbc311e5cb3aaa94186122d94b1b53252c4d22273b8bb599ffa75a8416c838e6"
)
implementation["RECORD_JSON_SHA256"] = (
    "d0099e86033582b8b5aa47d6791bc00b23c11116e58f08e3073d7cc0f3dd1536"
)
implementation["COMPOSED_SHA256"] = (
    "818dece52aa4361840d99525e3f439476a10d32bfa6a67db3f8c7479f89d69df"
)


def validate(*args: Any, **kwargs: Any) -> None:
    implementation["validate"](*args, **kwargs)


if __name__ == "__main__":
    raise SystemExit(implementation["main"]())
