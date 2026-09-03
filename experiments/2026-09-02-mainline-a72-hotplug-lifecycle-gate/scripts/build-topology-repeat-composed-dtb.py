#!/usr/bin/env python3
"""Compose the successful kernel identity over the proven 4+4+2 DT base."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a94f9115658a8803470928889b22ca45d422c02d866e4b274eac0b2f32532049"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-mt6797-cpu-map/"
    "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source topology/provenance composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("51fefc506400df2da28998d3970fef8d09c21e2ece7d6d08d5ecef7370705e7c",
     "0843db113f602535e5d69d8418492ec76a5f3dcd2765668e7d7d0629ca0e519e", 1),
    ("da39dc43999f0790a0237e68ad86efa86c3634d97db6cac59d4cae9a7f840267",
     "5ad97ceddefe6546593459c8b8b7281ed23c0840b3cf6f53b20947014be2da6e", 1),
    ("01c60771e1fc21c47a5a094482a555b286f8f5d046c009ba3e06d7e0212c6ac7",
     "1f34ddb965a1f14ef1e4cd3f68589b7a93d8186c8045c2804bd16beed9bc92c7", 1),
    ("validation=mt6797-cpu-map-composed-dtb",
     "validation=a72-topology-repeat-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology-repeat DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_topology_repeat_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
