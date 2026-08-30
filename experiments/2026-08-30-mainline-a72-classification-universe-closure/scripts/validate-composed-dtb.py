#!/usr/bin/env python3
"""Source-pin the independent DT validator to the closure identities."""

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
    "__name__": "a72_classification_universe_closure_dtb_validator",
}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
namespace["PACKAGE_DTB_SHA256"] = (
    "f3c40d825f338c3d3ff424b080930cfeda73ee1cb98ef2b03118548c16e088ec"
)
namespace["RECORD_JSON_SHA256"] = (
    "80f9377e1c390eabbac09846abeb6f0bac2a3850fb1804754624aef5784e80ae"
)
namespace["COMPOSED_SHA256"] = (
    "a30dce8d957a2f8d79a244d599f899de15ea696129096e576260e17a0ac9f352"
)


def validate(*args: Any, **kwargs: Any) -> None:
    namespace["validate"](*args, **kwargs)


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
