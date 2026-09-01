#!/usr/bin/env python3
"""Independently validate the CPU9 progress raw-lane repair container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "be66ee891a4e9d7a3d03ef48a524d1dee9d357e87980358603dbd9bbdfa64a01"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-progress-errno-diagnostic-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress errno CPU9 candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("replacements = (\n",
     "replacements = (\n"
     "    (\"KERNEL_SIZE = 4_886_697\", \"KERNEL_SIZE = 4_886_748\", 1),\n"
     "    (\"83183c4f2dfe62e541f8da0905cbcf1ac51262755400c81cb7dab4a3fa9966b6\",\n"
     "     \"f071de2dabc93e561a9712ba2e85f2b3843d84ee84d4b3483b2cbfc5f2b98702\", 1),\n", 1),
    ("CPU9 progress errno diagnostic candidate",
     "CPU9 progress raw-lane repair candidate", 1),
    ("32d304dcd478bdc4069f41252120cc2feb866324794b18a6b67490afeccd0570",
     "243ddc6e7a6a3e32cc0a86f98c3a3f7c2f33632acb2c2563f3a4e58b48d729a0", 1),
    ("4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8",
     "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7", 1),
    ("e348f2cc678eb9ae65cf7e4b1450d9e15f63f467568c1fcf43aea2838484108f",
     "3a8d9e5ae2a235124de9dba5c3b8091dfefc4d20d5557b595846f5d4b247fa13", 1),
    ("6d98a45b7bb2c0feaed906af3127a01530154e34cca6c8da85c5fd6185d49d99",
     "a3079f57f151eb8f75740413d3bdef99ffba397e31a03cc24ed677e598f08872", 1),
    ("f54e94498b91c8216142d245f2652b7f480534e1fc2c6a05e1477d455790e312",
     "fc0b45188882166184a0db429cb486392fdc607af28dab09eccc212943f5783b", 1),
    ("a31332ce57c992c52fd8b67048d91918b53b1dabae5ac83c767e45e861166889",
     "bd7fb619765d11c1fa4bd8bb3622041fdab29c2c8a0be06ef85b1fe28282179a", 1),
    ("3e1ca9603abb8e3f5171a6fa832da59b4ec1546a9ef5c53b89af969246940081",
     "099757f497ee4e94ce5518c1d2c3974a2952df307bf82fb692f24cd949e5f422", 1),
    ("adfa6b85f4324e24130da45ec28ccc3ce3d8769f",
     "5bf048358148598de3d90b7af47ec01110666c5a", 1),
    ("65 d0 97 24 a7 a7 50 4f 24 52 bd 55 b 0 1d 8f 50 59 ed de ca f 5a 1c e 32 55 6 f8 83 92 d1",
     "83 cb 90 52 d5 c3 3b 1a 73 f be 64 b4 1d 99 ed 35 21 f8 6 f2 61 97 d8 80 e5 c4 db 68 1d 7b 5", 1),
    ("validation=a72-cpu9-progress-errno-independent",
     "validation=a72-cpu9-progress-raw-lane-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress raw-lane candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_raw_lane_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
