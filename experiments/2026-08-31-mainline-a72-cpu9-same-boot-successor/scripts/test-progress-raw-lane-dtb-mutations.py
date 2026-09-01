#!/usr/bin/env python3
"""Run DT mutations against the CPU9 progress raw-lane repair validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6e9a7f72464972d6151701e814a3c80569947ea132d672c8419eee36ecd19b96"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/test-progress-errno-diagnostic-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress errno CPU9 DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-progress-errno-diagnostic-composed-dtb.py"',
     '"validate-progress-raw-lane-composed-dtb.py"', 1),
    ("cpu9-progress-errno-diagnostic-dtb-mutations",
     "cpu9-progress-raw-lane-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress raw-lane CPU9 DT mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_raw_lane_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
