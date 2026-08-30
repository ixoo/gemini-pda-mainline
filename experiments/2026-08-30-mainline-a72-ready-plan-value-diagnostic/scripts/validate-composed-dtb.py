#!/usr/bin/env python3
"""Source-pin the independent DT validator to the value identities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


SOURCE_SHA256 = "85ad4f1689cf77e44618121af446e151b79448f54c58b911e600932a32f5c4a3"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic"
    / "scripts/validate-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT validator changed")

namespace: dict[str, Any] = {
    "__file__": str(SOURCE),
    "__name__": "a72_ready_plan_value_diagnostic_dtb_validator",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
implementation = namespace["implementation"]
implementation["PACKAGE_DTB_SHA256"] = (
    "1461c89dcb002e185d060f765f1ca773aa111841eb8f9ef92205083a022d35af"
)
implementation["RECORD_JSON_SHA256"] = (
    "411faff54e19385565f8e16ff975383445c123a4035f73e1c2c405e45d6a778e"
)
implementation["COMPOSED_SHA256"] = (
    "5e0baee1743961e381496e8ce31239bd10879c425716c2b42222695732be8b7c"
)


def validate(*args: Any, **kwargs: Any) -> None:
    implementation["validate"](*args, **kwargs)


if __name__ == "__main__":
    raise SystemExit(implementation["main"]())
