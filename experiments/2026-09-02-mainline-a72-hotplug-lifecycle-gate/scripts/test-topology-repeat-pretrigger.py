#!/usr/bin/env python3
"""Mutation tests for the topology-repeat pre-trigger gate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8aa8cb96ec6f46416f54478ee606ba6e3ef2711ee606e3ad21c9d70fd8bb49f7"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/test-stage-binding-fix-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source stage-binding-fix pre-trigger mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-stage-binding-fix-pretrigger.py"',
     '"validate-topology-repeat-pretrigger.py"', 1),
    ("stage_binding_fix_pretrigger", "topology_repeat_pretrigger", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology-repeat pre-trigger mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_topology_repeat_pretrigger_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
