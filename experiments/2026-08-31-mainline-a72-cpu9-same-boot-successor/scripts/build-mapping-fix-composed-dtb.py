#!/usr/bin/env python3
"""Source-pin the CPU9 progress composer to the mapping-fix package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6bf21202c85d1d8f068913d15328358cc6cde28a8a2473d3956fea27f11d25fd"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-progress-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress CPU9 composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("4ce1828020a672e90d0bcb3d14fe79dd16bb71eeaa05044a46daca096feaef83",
     "b8000eb5311a9a196347462825494a0203c687f6622e7a684388a13009114e98", 1),
    ("63acd089ce6ddbd649e9e06c16013879d6e0554a70c9d4dd2c8e8c27208003a1",
     "5478d710596b3ece4d222ab9ed8f0cd04bb74ed09cadf86f0e6be6a73d08a089", 1),
    ("08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd",
     "f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d", 1),
    ("cpu9-progress-composed-dtb",
     "cpu9-mapping-fix-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe mapping-fix CPU9 DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_mapping_fix_dtb_builder"}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
