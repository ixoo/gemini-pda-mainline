#!/usr/bin/env python3
"""Source-pin the proven DT composer to the r0p1 repair package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "13eee8381b90f2eafbbd73aeb041bfbb29ca5ef3793ea569bcc8749678b3a3aa"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source DT composer changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("a7d14b3819b728958bcbf89dde6ade3b6a17159b11df5fbf0a0ec75c391da4cf",
     "7970125baf9ba884aab2319d50ab882bfe59009cde6da20799cc729d0642cb37", 1),
    ("7bc9b5e73c478e6fd7a892845ffef283c3d0d86dcef5719555b46876579046e3",
     "5ecb733cb6b5a9251d11dc0c8b414dfe22155d5648903ffb6f17102cb83d14ab", 1),
    ("68c57cb8c8eda745c2d42c179ef224821661940115d683e0e0d34e99ea81a0d3",
     "417111b329be60ff83a5adbca31231682728b679ca1ef23cda37ec9cee4cd617", 1),
    ("unsafe post-capabilities checkpoint DT derivation",
     "unsafe r0p1 expected-pair repair DT derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe r0p1 expected-pair repair DT derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_r0p1_expected_pair_repair_dtb_composer",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
