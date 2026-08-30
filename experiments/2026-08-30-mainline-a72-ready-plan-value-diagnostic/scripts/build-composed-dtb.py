#!/usr/bin/env python3
"""Source-pin the proven composer to the exact value-diagnostic record."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "07f97288de189ef319da286114ff313892444ae0f7af0277f875ea1452043219"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT builder changed")

namespace = {
    "__file__": str(SOURCE),
    "__name__": "a72_ready_plan_value_diagnostic_dtb_builder",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
implementation = namespace["implementation"]
implementation["PACKAGE_DTB_SHA256"] = (
    "1461c89dcb002e185d060f765f1ca773aa111841eb8f9ef92205083a022d35af"
)
implementation["RECORD_JSON_SHA256"] = (
    "411faff54e19385565f8e16ff975383445c123a4035f73e1c2c405e45d6a778e"
)
implementation["OUTPUT_SHA256"] = (
    "5e0baee1743961e381496e8ce31239bd10879c425716c2b42222695732be8b7c"
)


if __name__ == "__main__":
    raise SystemExit(implementation["main"]())
