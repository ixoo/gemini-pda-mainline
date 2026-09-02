#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the CPU_ON progress package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "4ba968930aeabcc788c5c52ca091d1a8f5502d5010e50872b73c0fb50c4f4e67"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-cpuhp-lock-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPUHP lock-repair composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("9cadf8291992e47910dfca39618a6e508b896b7bd3db3d873a64b064b6ac7942",
     "9d90a0f8c38f1a5ae090eacef8663fa383ec6e8eaaa46d21665c84e111a1a56d", 1),
    ("9704d2e765740b0511d98986162acda351e6e122d7c056b4c133bd07dcdb1331",
     "a29ae6a68eacc95e07c34469473cc169cd75eb709500b733ddaaaf7bf859684c", 1),
    ("aef34db5009b0b4b6fc69eb62a7f8385b7f975abbd67967243910504bf14f672",
     "0ff1de298acf885c4952d452f8fcef2cb8d18375befe7efa963d09f079612afa", 1),
    ("cpu9-cpuhp-lock-repair-composed-dtb",
     "cpu9-cpu-on-progress-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpu_on_progress_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
