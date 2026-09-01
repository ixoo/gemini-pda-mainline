#!/usr/bin/env python3
"""Independently validate the CPU9 progress reader-mapping repair container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "f1d8c73c954a64d33f405107d93e8f8e45c4172a0db92b2d71a21afcb80d54aa"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-progress-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress CPU9 candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("CPU9 progress-ledger diagnostic candidate",
     "CPU9 progress reader-mapping repair candidate", 1),
    ("KERNEL_SIZE = 4_886_744", "KERNEL_SIZE = 4_886_697", 1),
    ("85d3b591cdee4635cf0e5b889011459a4cb7e48f4ddd3ac2df0c20720e1c8833",
     "a7290cdb2e131f64b8483615e3dd613c92fe2b46d2c0e731b42971a9a1fe4d11", 1),
    ("ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72",
     "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0", 1),
    ("c4e84c90a9843b8d5a7beaf8ce6c7874d1d8e972f14fa91a4e837800ecd0b5f6",
     "d03981881acbfe8d75c7f638849bd4433dc63bfbbadfec7b1e8a4ec70bee2e48", 1),
    ("4c4f43328c6c824045d118510183b1d7f2fdacd92ddeaf4f6b75a59ad76cf9b8",
     "bd2224a8b92352fc5b53ab964ce627ac4cd311be7d99f15c85480878968d6c62", 1),
    ("08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd",
     "f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d", 1),
    ("a657dd5c033d18b3d7638875e6603c6c9486fd9b13c2f9d9f4a9c60c82875534",
     "83183c4f2dfe62e541f8da0905cbcf1ac51262755400c81cb7dab4a3fa9966b6", 1),
    ("e262795a456a933a16b0658edb699bb3ea444e04bfa842488cf04d794f545a28",
     "21c594120e9103d4a76c7f5b9f7721f960bd1c311428c4a9e292abeb685eef01", 1),
    ("e398c2b9156c31f02cb126be40204608b17f9df8a44a0f2268e05545d40448e2",
     "5bae6aa70b27390b1c18a8310648afe7fa67796a7bed51eabb2b438abae5751a", 1),
    ("630350185c9126f2c96be7295216c5ff1ee08c83",
     "6f72e3ddd64610274886009324bc025064a2731c", 1),
    ("ed 3a 4b f0 85 10 bd d5 c1 7 c1 10 18 3b 1c e9 85 df c5 59 4c 8a fa e5 4b df fe 0 6f b5 66 6",
     "ef d3 6c 8e e7 68 ad 7d a1 68 7a 62 64 b af 65 e3 85 58 74 c5 28 7c 69 38 a3 dc 31 be fd 1f 39", 1),
    ("validation=a72-cpu9-progress-independent",
     "validation=a72-cpu9-mapping-fix-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 mapping-fix candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_mapping_fix_candidate_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
