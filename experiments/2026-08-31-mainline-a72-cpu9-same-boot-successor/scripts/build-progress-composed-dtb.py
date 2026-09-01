#!/usr/bin/env python3
"""Source-pin the repaired CPU9 composer to the progress package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "7ff15c83e341a4054993053f211f870a6e8ac3f41073cdd6815073a859a562f6"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-config-identity-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source repaired CPU9 composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("afb849a4a5dc9011f5a24dad2ae22d2bae1bda1963fa2c7681e86377125c1712",
     "4ce1828020a672e90d0bcb3d14fe79dd16bb71eeaa05044a46daca096feaef83", 1),
    ("228f762c3beacad56cd8e2ec8e595fdf79927d5786c5e54b473c251e93376e5e",
     "63acd089ce6ddbd649e9e06c16013879d6e0554a70c9d4dd2c8e8c27208003a1", 1),
    ("ca7e95162c9e222d47991f6580682354cbb445d994a954950455ca5e6b9c80c3",
     "08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd", 1),
    ("cpu9-config-identity-repair-composed-dtb",
     "cpu9-progress-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress CPU9 DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_progress_dtb_builder"}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
