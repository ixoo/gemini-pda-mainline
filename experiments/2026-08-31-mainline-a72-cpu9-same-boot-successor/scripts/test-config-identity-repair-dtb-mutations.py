#!/usr/bin/env python3
"""Run DT mutations against the configuration-identity repair validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8238ade4d47adeba67b23f910f82f30f32272f69051337d44bbcd819729ff188"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/"
    "scripts/test-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('Path(__file__).with_name("validate-composed-dtb.py")',
     'Path(__file__).with_name("validate-config-identity-repair-composed-dtb.py")', 1),
    ("provenance-serviceability-dtb-mutations",
     "cpu9-config-identity-repair-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repaired CPU9 DT mutation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_repair_dtb_mutations"}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
