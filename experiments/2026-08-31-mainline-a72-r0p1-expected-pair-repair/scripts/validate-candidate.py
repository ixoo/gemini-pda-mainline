#!/usr/bin/env python3
"""Source-pin the independent validator to the r0p1 repair candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "51fa5a83e20e8b525355fb6793f2c4d6f41d44c66a94d1d648e8b606a33ac3ba"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("P30E post-capabilities checkpoint candidate",
     "P30E r0p1 expected-pair repair candidate", 1),
    ("KERNEL_SIZE = 4_878_366", "KERNEL_SIZE = 4_878_367", 1),
    ("cb7c886e2cb9d225c75f413217394ae64a12661b36f7c1d18048d27ad338fc0c",
     "6083935bbfba438a36c8ce23e75165b68e503fa813361828c98abfb5e741d505", 1),
    ("9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630",
     "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d", 1),
    ("b875484a9366d30889ccc823d0510d3982ea989cf03f6758817d25b61becadab",
     "f56c27ec06b02398cbb957344c539d271d6bf2d151bc379be3c7c684a937c79a", 1),
    ("a70d23c793ca41ac2a5d8043da8aba3ea432500a9f95c27d9c888db583bbef58",
     "809d910a9b93eaae8f5adea4a606229f0d8ff7bef2666f4e5c474990b2f5e50f", 1),
    ("68c57cb8c8eda745c2d42c179ef224821661940115d683e0e0d34e99ea81a0d3",
     "417111b329be60ff83a5adbca31231682728b679ca1ef23cda37ec9cee4cd617", 1),
    ("c5023a5bada66f539a4ab4c3b1c6b7b6f5c0eeba63da20284ff0f551ba5db243",
     "e31d6b12d3ec35cd736ac9e2be1203c0e29ef7c3e5393c98cbdba9ee81fdd7c1", 1),
    ("115719788a95923b3b41f7f9d2aeb4b11acf3289147f01969b3a43032429cefe",
     "1af85a3dcf598e1ff2ca7beb5ea668e30f0dbdd9f2f627f5229c3abb3927968f", 1),
    ("gemini-mt6797-a72-post-capabilities-checkpoints.boot.img",
     "gemini-mt6797-a72-r0p1-expected-pair-repair.boot.img", 1),
    ("590dbedc974c6a40f34c1d4c34e9bb571bc2a10d",
     "e0090fe57490eebe80750d2130a9411edb195e37", 1),
    ("7c 6c 9a 78 5e 2c cf 27 7e 61 a1 55 2c 4c 2f b2 19 e3 37 1b 29 21 b0 b4 1a 9e da 1d 2f 7e a6 90",
     "74 69 23 c7 8b bf a6 63 4a 3d 5 92 55 7c ae ea 53 ee 82 5d cc e1 e4 b5 4b f2 17 6e 7d 88 44 d2", 1),
    ("validation=a72-post-capabilities-checkpoints-independent",
     "validation=a72-r0p1-expected-pair-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe r0p1 validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_r0p1_expected_pair_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
