#!/usr/bin/env python3
"""Validate a silent, unblocked, armed READY frame with zero CPU action."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c617550e84260388144e702bb3361d44291ed62f0ef0bb425b80b08555705406"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
anchor = '''        "profile_blocked_count": "0",
'''
insert = anchor + '''        "ready_plan_diag_count": "0",
        "ready_plan_diag_line": "",
        "ready_plan_values_count": "0",
        "ready_plan_values_line": "",
        "proof_mask_24000_count": "1",
'''
replacements = (
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", 1),
    (anchor, insert, 1),
    ("exact-package-provenance-runtime-identity-verified-unblocked-armed-contract", "exact-repaired-ready-silent-unblocked-armed-zero-execution-contract", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-repair validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_plan_expectation_repair_runtime_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
