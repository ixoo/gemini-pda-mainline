#!/usr/bin/env python3
"""Source-pin the proven composer to the exact repaired READY package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


SOURCE_SHA256 = "a7971af3bd1c7cf5f619a5a985703f38031e800cd54cf359b189341d80ad4f9f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT builder changed")

namespace: dict[str, Any] = {
    "__file__": str(SOURCE),
    "__name__": "a72_ready_plan_expectation_repair_dtb_builder",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
namespace["PACKAGE_DTB_SHA256"] = (
    "76e88929715b52507decf94d56623666fa4087597c063bc2b5428f0f22f8d999"
)
namespace["RECORD_JSON_SHA256"] = (
    "c496f5c5dd14d286f182f9b393b60df546ec16e53fcfa7f6f937dd2947215724"
)
namespace["OUTPUT_SHA256"] = (
    "0732a2cf00e04a71034a563dcb35a8a3e3414620cdf8d511767a17f9b552fcba"
)


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
