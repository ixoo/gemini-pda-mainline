#!/usr/bin/env python3
"""Build the exact topology-plus-provenance serviceability DT."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a7971af3bd1c7cf5f619a5a985703f38031e800cd54cf359b189341d80ad4f9f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/"
    "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source provenance composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c",
     "4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923", 1),
    ("d3197c6870aa025840f6dc330e83e7871e78cce56e4b314e03085d7879c6954f",
     "51fefc506400df2da28998d3970fef8d09c21e2ece7d6d08d5ecef7370705e7c", 1),
    ("05a3e54a412e02bc224138056552451b706111d2d98d6e1363597efeecada93d",
     "da39dc43999f0790a0237e68ad86efa86c3634d97db6cac59d4cae9a7f840267", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2",
     "01c60771e1fc21c47a5a094482a555b286f8f5d046c009ba3e06d7e0212c6ac7", 1),
    ("validation=provenance-serviceability-composed-dtb",
     "validation=mt6797-cpu-map-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology/provenance composer derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "mt6797_cpu_map_composed_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
