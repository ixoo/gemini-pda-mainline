#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the membership-begin lock repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "ccd69573a1ef3dcd58c56893fd28ae7fc800e712ac8595db458a4dd63bc4563e"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-cpu-on-progress-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU_ON progress composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("9d90a0f8c38f1a5ae090eacef8663fa383ec6e8eaaa46d21665c84e111a1a56d",
     "18660eadcbd3477f9710162c1ddf6820d53e613f95ca2255d44948e4ec5eb718", 1),
    ("a29ae6a68eacc95e07c34469473cc169cd75eb709500b733ddaaaf7bf859684c",
     "f07f76e6a5ec29fa6807299271c0e2028ad6becb6628b11dec39215185a771da", 1),
    ("0ff1de298acf885c4952d452f8fcef2cb8d18375befe7efa963d09f079612afa",
     "a36dfc2c2cad2a300dd89b3cd4dd8662fe86152c6c2740467d95d149c6a1d279", 1),
    ("cpu9-cpu-on-progress-composed-dtb",
     "cpu9-membership-lock-repair-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_membership_lock_repair_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
