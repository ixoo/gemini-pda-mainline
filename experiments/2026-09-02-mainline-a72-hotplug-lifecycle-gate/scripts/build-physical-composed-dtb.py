#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the physical hotplug candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "3f3f67eb3758b914f7cec67f748a41b3344134653da3c3f3846f790f39640952"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-completion-lock-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source completion-lock composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("9212c8b03df973362307902573980ec27071f89ef3728ed44064f6319a9edf37",
     "c5658e2d703a43b1d86b29003e4054679d8650fca13c3a0aa76ca06ff0264dda", 1),
    ("5fe8c059961f3d2bfc6e8461a9b8148e610821701f9cfac81eff2425c0ee39f6",
     "91a2dde7034690685d30431f81993335c31d61220ce5967fe1f81fb3283e0058", 1),
    ("2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9",
     "902762c2a1badd9e71ebb25c842b0135fbf0076837956da1da73b42a38bbedcd", 1),
    ("cpu9-completion-lock-repair-composed-dtb",
     "cpu9-physical-hotplug-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe physical-hotplug DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_physical_hotplug_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
