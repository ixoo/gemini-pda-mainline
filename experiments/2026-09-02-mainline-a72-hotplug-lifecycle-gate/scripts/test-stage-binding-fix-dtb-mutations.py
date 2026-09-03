#!/usr/bin/env python3
"""Run DT mutations against the symbolic stage-binding-fix validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "4c4a1fd4128eec1c97f776f9645dcb7e88c78c603d4c0fa82bbf710367b9d62f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/test-postsuccess-diagnostic-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source post-success diagnostic DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-postsuccess-diagnostic-composed-dtb.py"',
     '"validate-stage-binding-fix-composed-dtb.py"', 1),
    ("cpu9-postsuccess-diagnostic-dtb-mutations",
     "cpu9-stage-binding-fix-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding DT mutation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_stage_binding_fix_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
