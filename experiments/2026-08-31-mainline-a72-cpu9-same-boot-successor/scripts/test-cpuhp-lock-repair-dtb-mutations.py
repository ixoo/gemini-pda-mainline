#!/usr/bin/env python3
"""Run DT mutations against the CPU9 CPUHP lock-repair validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "cef635ca48185c09636802ded99b7a65bbe81ea9a133d75770897b8605c2a198"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/test-progress-raw-lane-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress raw-lane DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-progress-raw-lane-composed-dtb.py"',
     '"validate-cpuhp-lock-repair-composed-dtb.py"', 1),
    ("cpu9-progress-raw-lane-dtb-mutations",
     "cpu9-cpuhp-lock-repair-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPUHP lock-repair DT mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpuhp_lock_repair_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
