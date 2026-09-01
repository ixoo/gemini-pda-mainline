#!/usr/bin/env python3
"""Run DT mutations against the CPU9 progress errno diagnostic validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "63b1d3dbc959572761dde59b67e34214bb06756c1a15f25dafbffd339fc6ee84"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/test-mapping-fix-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source mapping-fix CPU9 DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('Path(__file__).with_name("validate-mapping-fix-composed-dtb.py")',
     'Path(__file__).with_name('
     '"validate-progress-errno-diagnostic-composed-dtb.py")', 1),
    ("cpu9-mapping-fix-dtb-mutations",
     "cpu9-progress-errno-diagnostic-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress errno CPU9 DT mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_errno_diagnostic_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
