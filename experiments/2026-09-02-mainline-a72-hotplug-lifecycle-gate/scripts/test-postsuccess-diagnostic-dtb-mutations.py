#!/usr/bin/env python3
"""Run DT mutations against the post-success diagnostic validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "47304ebc29ecb9669dcd8c6a354d26e27a8bde6d3ed94cd0467d853d858791a9"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/test-p30e-rearm-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source P30E-rearm DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-p30e-rearm-composed-dtb.py"',
     '"validate-postsuccess-diagnostic-composed-dtb.py"', 1),
    ("cpu9-p30e-rearm-dtb-mutations",
     "cpu9-postsuccess-diagnostic-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-success DT mutation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_postsuccess_diagnostic_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
