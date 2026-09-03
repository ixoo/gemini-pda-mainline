#!/usr/bin/env python3
"""Run DT mutations against the CPU9 physical-hotplug validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "045c2a42c29b9862cc479cb204b8cf32ca7829b2c2cbb1ab99aa34efdeb5735b"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/test-completion-lock-repair-dtb-mutations.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source completion-lock DT mutation suite changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ('"validate-completion-lock-repair-composed-dtb.py"',
     '"validate-physical-composed-dtb.py"', 1),
    ("cpu9-completion-lock-repair-dtb-mutations",
     "cpu9-physical-hotplug-dtb-mutations", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe physical-hotplug DT mutation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_physical_hotplug_dtb_mutations",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
