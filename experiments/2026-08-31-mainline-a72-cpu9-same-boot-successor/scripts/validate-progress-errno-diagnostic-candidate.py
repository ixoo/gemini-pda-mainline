#!/usr/bin/env python3
"""Independently validate the CPU9 progress errno diagnostic container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a3d306bed662bfad4a7a1188245274dd7ad0796613efa328ac1c19a82f4822b5"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-mapping-fix-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source mapping-fix CPU9 candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("CPU9 progress reader-mapping repair candidate",
     "CPU9 progress errno diagnostic candidate", 1),
    ("a7290cdb2e131f64b8483615e3dd613c92fe2b46d2c0e731b42971a9a1fe4d11",
     "32d304dcd478bdc4069f41252120cc2feb866324794b18a6b67490afeccd0570", 1),
    ("c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0",
     "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8", 1),
    ("d03981881acbfe8d75c7f638849bd4433dc63bfbbadfec7b1e8a4ec70bee2e48",
     "e348f2cc678eb9ae65cf7e4b1450d9e15f63f467568c1fcf43aea2838484108f", 1),
    ("bd2224a8b92352fc5b53ab964ce627ac4cd311be7d99f15c85480878968d6c62",
     "6d98a45b7bb2c0feaed906af3127a01530154e34cca6c8da85c5fd6185d49d99", 1),
    ("f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d",
     "f54e94498b91c8216142d245f2652b7f480534e1fc2c6a05e1477d455790e312", 1),
    ("21c594120e9103d4a76c7f5b9f7721f960bd1c311428c4a9e292abeb685eef01",
     "a31332ce57c992c52fd8b67048d91918b53b1dabae5ac83c767e45e861166889", 1),
    ("5bae6aa70b27390b1c18a8310648afe7fa67796a7bed51eabb2b438abae5751a",
     "3e1ca9603abb8e3f5171a6fa832da59b4ec1546a9ef5c53b89af969246940081", 1),
    ("6f72e3ddd64610274886009324bc025064a2731c",
     "adfa6b85f4324e24130da45ec28ccc3ce3d8769f", 1),
    ("ef d3 6c 8e e7 68 ad 7d a1 68 7a 62 64 b af 65 e3 85 58 74 c5 28 7c 69 38 a3 dc 31 be fd 1f 39",
     "65 d0 97 24 a7 a7 50 4f 24 52 bd 55 b 0 1d 8f 50 59 ed de ca f 5a 1c e 32 55 6 f8 83 92 d1", 1),
    ("validation=a72-cpu9-mapping-fix-independent",
     "validation=a72-cpu9-progress-errno-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress errno candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_errno_diagnostic_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
