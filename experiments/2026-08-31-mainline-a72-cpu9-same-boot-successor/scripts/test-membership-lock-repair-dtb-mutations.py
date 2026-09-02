#!/usr/bin/env python3
"""Run DT mutations against the CPU9 membership-lock repair validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "e93f789f9346373f76186b54b5d985d13daf009770f03df50254e9e14cd2930d"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/test-cpu-on-progress-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU_ON progress DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-cpu-on-progress-composed-dtb.py"',
     '"validate-membership-lock-repair-composed-dtb.py"', 1),
    ("cpu9-cpu-on-progress-dtb-mutations",
     "cpu9-membership-lock-repair-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock DT mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_membership_lock_repair_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
