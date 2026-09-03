#!/usr/bin/env python3
"""Source-pin the physical CPU9 composer to the P30E-rearm package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a2cf144f0fcf40e954c35dbf251fb71cd9992ffe58a7299fcde47bd99079a1c9"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/build-physical-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source physical-hotplug composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("c5658e2d703a43b1d86b29003e4054679d8650fca13c3a0aa76ca06ff0264dda",
     "e316f94d81d456aa7cdd7e13a123d3ecdf72cc986dcebba53bc0b221ae77e4e9", 1),
    ("91a2dde7034690685d30431f81993335c31d61220ce5967fe1f81fb3283e0058",
     "62201c6e2a696a767f591dcdc0aa16b95d1d68b48ce7ddd3f4300a49f3a29e6c", 1),
    ("902762c2a1badd9e71ebb25c842b0135fbf0076837956da1da73b42a38bbedcd",
     "1396b2e81dd23f4298df86dd3449acf7dfa519d3655b280d79b64c03595b0933", 1),
    ("cpu9-physical-hotplug-composed-dtb",
     "cpu9-p30e-rearm-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E-rearm DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_p30e_rearm_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
