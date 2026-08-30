#!/usr/bin/env python3
"""Bind the complete READY validator to the exact fresh mainline boot."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "2ac884e8c9db3f152572ac61ae5182f9b52ae20d15d4fbc840033e93ac6d1174"
EXPECTED_BOOT_ID = "1f2dcf6a-ef45-4e7c-b1d7-7655d4bda4cf"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-classification-universe-closure"
    / "scripts/validate-ready.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source complete READY validator changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_cpu8_ready_boot_validator"}
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
