#!/usr/bin/env python3
"""Bind the trace-aware READY validator to the exact live mainline boot."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "b012426e2e3bc912da63655dc9e325b4d3113d8db73e41959b1746e2815aae80"
EXPECTED_BOOT_ID = "2ec43fd0-3afb-4a56-bf9f-92bacff303ba"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-admission"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source READY pre-trigger validator changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_ready_boot_validator"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
source_classify = namespace["classify"]


def classify(text: str) -> tuple[str, str]:
    result, boot_id = source_classify(text)
    if boot_id != EXPECTED_BOOT_ID:
        raise namespace["Classification"]("boot-id-changed")
    return result, boot_id


namespace["classify"] = classify
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__", "classify"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
