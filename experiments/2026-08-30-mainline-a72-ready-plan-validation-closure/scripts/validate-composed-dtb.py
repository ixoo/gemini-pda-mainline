#!/usr/bin/env python3
"""Source-pin the independent DT validator to the post-0437 identities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


SOURCE_SHA256 = "b76e7fa49f6f02c948a7563613c502d67ef287f0cba0db224d17f312427fe438"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/validate-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT validator changed")

namespace: dict[str, Any] = {
    "__file__": str(SOURCE),
    "__name__": "a72_ready_plan_closure_dtb_validator",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
namespace["PACKAGE_DTB_SHA256"] = (
    "701a2377650a4f1cbaf2d156aae8fb62fb4f103f007bb3f90fafc5062349c082"
)
namespace["RECORD_JSON_SHA256"] = (
    "a703a105c2903168875193b1ca5f9e54e2d68523553ac6c679cce023f4cfbb5f"
)
namespace["COMPOSED_SHA256"] = (
    "bfd735bb7e20550f70a586a82536eaa6366db4f3079d16af926833fcb2414174"
)


def validate(*args: Any, **kwargs: Any) -> None:
    namespace["validate"](*args, **kwargs)


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
