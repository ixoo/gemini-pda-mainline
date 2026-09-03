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
     "24f2caac69f196dc316e627224f67a1fa5f0c26d4ef68e6f84461ba5492d7096", 1),
    ("5fe8c059961f3d2bfc6e8461a9b8148e610821701f9cfac81eff2425c0ee39f6",
     "9d7c84593e44683f943f1f64e2d811da825f32dfc56f4169b97843897cfc6a53", 1),
    ("2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9",
     "99415ca8c13fd6f30b34b805214ebbbbc1230951fae0c943c7cbaf6c1603439d", 1),
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
