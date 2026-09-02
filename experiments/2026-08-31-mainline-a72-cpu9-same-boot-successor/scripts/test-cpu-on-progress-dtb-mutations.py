#!/usr/bin/env python3
"""Run DT mutations against the CPU9 CPU_ON progress validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "4228dcdadbbae784f2a5e6a6fccc89a5cba6e1659cfe3261777dec162a86ab21"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/test-cpuhp-lock-repair-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPUHP lock-repair DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-cpuhp-lock-repair-composed-dtb.py"',
     '"validate-cpu-on-progress-composed-dtb.py"', 1),
    ("cpu9-cpuhp-lock-repair-dtb-mutations",
     "cpu9-cpu-on-progress-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress DT mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpu_on_progress_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
