#!/usr/bin/env python3
"""Run DT mutations against the CPU9 P30E-rearm validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "b8dbabf11d68584a75055cc5ee35c79fbdd8ad1d69acb826313b716c5a1cdfc6"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/test-physical-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source physical-hotplug DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-physical-composed-dtb.py"',
     '"validate-p30e-rearm-composed-dtb.py"', 1),
    ("cpu9-physical-hotplug-dtb-mutations",
     "cpu9-p30e-rearm-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E-rearm DT mutation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_p30e_rearm_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
