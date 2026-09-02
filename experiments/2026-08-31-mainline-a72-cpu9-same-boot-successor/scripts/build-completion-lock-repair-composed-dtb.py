#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the completion-path lock repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "319c2d25ec927b17913dce65c5778c66d1cf133836c88f4eb95d19e45a28bc64"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-membership-lock-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source membership lock-repair composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("18660eadcbd3477f9710162c1ddf6820d53e613f95ca2255d44948e4ec5eb718",
     "9212c8b03df973362307902573980ec27071f89ef3728ed44064f6319a9edf37", 1),
    ("f07f76e6a5ec29fa6807299271c0e2028ad6becb6628b11dec39215185a771da",
     "5fe8c059961f3d2bfc6e8461a9b8148e610821701f9cfac81eff2425c0ee39f6", 1),
    ("a36dfc2c2cad2a300dd89b3cd4dd8662fe86152c6c2740467d95d149c6a1d279",
     "2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9", 1),
    ("cpu9-membership-lock-repair-composed-dtb",
     "cpu9-completion-lock-repair-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_completion_lock_repair_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
