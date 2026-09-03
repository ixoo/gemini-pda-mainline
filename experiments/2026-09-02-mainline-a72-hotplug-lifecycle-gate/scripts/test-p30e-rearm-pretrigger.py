#!/usr/bin/env python3
"""Mutation tests for the exact P30E-rearm pre-trigger gate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "d42bc4a0dd2edac8addd467b54473d87ab6ce2ad6baf1f22d746c943cf6a3eb2"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/test-physical-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source physical-hotplug pre-trigger mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-physical-pretrigger.py"',
     '"validate-p30e-rearm-pretrigger.py"', 1),
    ("physical_pretrigger", "p30e_rearm_pretrigger", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E-rearm pre-trigger mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_p30e_rearm_pretrigger_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
