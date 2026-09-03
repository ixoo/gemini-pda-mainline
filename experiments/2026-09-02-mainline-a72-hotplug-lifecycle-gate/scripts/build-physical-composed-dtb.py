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
     "aee4c11325a75a74a34fc06f95a78a8021b07cc3f9fc6fbacc8f405d0d126d04", 1),
    ("5fe8c059961f3d2bfc6e8461a9b8148e610821701f9cfac81eff2425c0ee39f6",
     "c4fc31cf16c790989b284e5917396855eb5331c9b1c781660285350d41a5cecc", 1),
    ("2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9",
     "48f7c1943223b652e44c55703f3d3c53ff15cceca0f4c7054169ccc346683586", 1),
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
