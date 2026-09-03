#!/usr/bin/env python3
"""Independently validate the symbolic stage-binding-fix DT composition."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "7b9ac63bb3924ac8785da6b0122b96ca2a880cbe75744e187b468e07907f0a99"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-postsuccess-diagnostic-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source post-success diagnostic composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("489efad963d247d3bf14b5c73193de71bfae4c56e34eaa8b9359b925bafc245e",
     "0843db113f602535e5d69d8418492ec76a5f3dcd2765668e7d7d0629ca0e519e", 1),
    ("837e9dc03c0699b1e984b4db3f7a153efb8374ab21e71d579c68649f8c951076",
     "5ad97ceddefe6546593459c8b8b7281ed23c0840b3cf6f53b20947014be2da6e", 1),
    ("959247f1300578b1ec1652eb4cb1d9a36d7c91c6a82228ccd6a2afb9f136136b",
     "ecf278518608e4fa17c05b933a75c55ec4a31fdb4ceff10bce784754822e834c", 1),
    ("cpu9-postsuccess-diagnostic-composed-dtb-independent",
     "cpu9-stage-binding-fix-composed-dtb-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding DT validation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_stage_binding_fix_dtb_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
validate = namespace["validate"]
main = namespace["main"]


if __name__ == "__main__":
    raise SystemExit(main())
