#!/usr/bin/env python3
"""Mutation tests for the post-success diagnostic pre-trigger gate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c20bf876d8a8d8ae6e089fb91a0df182ce1d7b7eec6cc7a5d6fcbb53bfaac568"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/test-p30e-rearm-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source P30E-rearm pre-trigger mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-p30e-rearm-pretrigger.py"',
     '"validate-postsuccess-diagnostic-pretrigger.py"', 1),
    ("p30e_rearm_pretrigger", "postsuccess_diagnostic_pretrigger", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-success pre-trigger mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_postsuccess_diagnostic_pretrigger_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
