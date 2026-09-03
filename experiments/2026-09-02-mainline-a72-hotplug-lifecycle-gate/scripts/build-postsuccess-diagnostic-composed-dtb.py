#!/usr/bin/env python3
"""Source-pin the P30E composer to the post-success diagnostic package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "406bff64dbb83446f73007d0ac599efbf6d59f6577f19571e68534c04006a0e3"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/build-p30e-rearm-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source P30E-rearm composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("e316f94d81d456aa7cdd7e13a123d3ecdf72cc986dcebba53bc0b221ae77e4e9",
     "489efad963d247d3bf14b5c73193de71bfae4c56e34eaa8b9359b925bafc245e", 1),
    ("62201c6e2a696a767f591dcdc0aa16b95d1d68b48ce7ddd3f4300a49f3a29e6c",
     "837e9dc03c0699b1e984b4db3f7a153efb8374ab21e71d579c68649f8c951076", 1),
    ("1396b2e81dd23f4298df86dd3449acf7dfa519d3655b280d79b64c03595b0933",
     "959247f1300578b1ec1652eb4cb1d9a36d7c91c6a82228ccd6a2afb9f136136b", 1),
    ("cpu9-p30e-rearm-composed-dtb",
     "cpu9-postsuccess-diagnostic-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-success DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_postsuccess_diagnostic_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
