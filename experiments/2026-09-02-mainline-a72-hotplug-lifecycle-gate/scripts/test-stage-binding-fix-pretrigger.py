#!/usr/bin/env python3
"""Mutation tests for the symbolic stage-binding-fix pre-trigger gate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "38997e9e6c927dc53c86f748f831dd9e1b56aa06fa817be0f33219b992adc46f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/test-postsuccess-diagnostic-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source post-success diagnostic pre-trigger mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-postsuccess-diagnostic-pretrigger.py"',
     '"validate-stage-binding-fix-pretrigger.py"', 1),
    ("postsuccess_diagnostic_pretrigger", "stage_binding_fix_pretrigger", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding pre-trigger mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_stage_binding_fix_pretrigger_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
