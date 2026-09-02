#!/usr/bin/env python3
"""Run DT mutations against the CPU9 completion-lock repair validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "226536dc9b62daa089960ae669a5ae20ba0cf508adbfbac1c2e052d12dff7e18"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/test-membership-lock-repair-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source membership-lock DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-membership-lock-repair-composed-dtb.py"',
     '"validate-completion-lock-repair-composed-dtb.py"', 1),
    ("cpu9-membership-lock-repair-dtb-mutations",
     "cpu9-completion-lock-repair-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock DT mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_completion_lock_repair_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
