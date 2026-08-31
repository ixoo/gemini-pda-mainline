#!/usr/bin/env python3
"""Source-pin the proven DT composer to the post-capabilities package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6c2c8054025e22485c4d5e3a49bbb7e8a1476c3a1344d20ffa0d344e869c7072"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-secondary-entry-checkpoints"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("2208f4376bc6e0facea228237e1954c5e4e019e73d8ecae50c6a425eefaa6dd2",
     "a7d14b3819b728958bcbf89dde6ade3b6a17159b11df5fbf0a0ec75c391da4cf", 1),
    ("c3ee11108f2551d39f86955d6466d2e8cb12a7dd1f4f8416c632e28611e06026",
     "7bc9b5e73c478e6fd7a892845ffef283c3d0d86dcef5719555b46876579046e3", 1),
    ("1bc12e8dacff2cef9f248276de80c4e0d37ebd50d5a4e42ed9dc0164837b4046",
     "68c57cb8c8eda745c2d42c179ef224821661940115d683e0e0d34e99ea81a0d3", 1),
    ("unsafe P30E entry-checkpoint DT derivation",
     "unsafe post-capabilities checkpoint DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-capabilities checkpoint DT derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_post_capabilities_checkpoint_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
