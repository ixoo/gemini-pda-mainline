#!/usr/bin/env python3
"""Source-pin the diagnostic composer to the symbolic stage-binding fix."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "552df2da4791c7aac67a2939d897bc03e89f56a3adb2b3ee6360a5e9a575d97b"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/build-postsuccess-diagnostic-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source post-success diagnostic composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("489efad963d247d3bf14b5c73193de71bfae4c56e34eaa8b9359b925bafc245e",
     "0843db113f602535e5d69d8418492ec76a5f3dcd2765668e7d7d0629ca0e519e", 1),
    ("837e9dc03c0699b1e984b4db3f7a153efb8374ab21e71d579c68649f8c951076",
     "5ad97ceddefe6546593459c8b8b7281ed23c0840b3cf6f53b20947014be2da6e", 1),
    ("959247f1300578b1ec1652eb4cb1d9a36d7c91c6a82228ccd6a2afb9f136136b",
     "ecf278518608e4fa17c05b933a75c55ec4a31fdb4ceff10bce784754822e834c", 1),
    ("cpu9-postsuccess-diagnostic-composed-dtb",
     "cpu9-stage-binding-fix-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_stage_binding_fix_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
