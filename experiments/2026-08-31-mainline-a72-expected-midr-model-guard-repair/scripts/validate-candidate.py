#!/usr/bin/env python3
"""Source-pin the independent validator to the expected-MIDR guard candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "65dc4df87bd831c19d28af498728a668f1ee2636442392820a0235bcef4ec836"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("replacements = (\n",
     "replacements = (\n"
     "    (\"5d7b936aebcfdc73af86ae3158fba672532da6c567eb0628e1ea3c1bc0821659\",\n"
     "     \"556540ed817e19105bf5a4a059dd3fef9eb6d02dc0ca525c0b23a15598c7a248\", 1),\n",
     1),
    ("P30E r0p1 expected-pair repair candidate",
     "P30E expected-MIDR model-guard repair candidate", 1),
    ("KERNEL_SIZE = 4_878_367", "KERNEL_SIZE = 4_878_798", 1),
    ("6083935bbfba438a36c8ce23e75165b68e503fa813361828c98abfb5e741d505",
     "bf7ebec8193e6139cc544b0d3952154cdaabf895cd477d6552139245854ce83e", 1),
    ("b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d",
     "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69", 1),
    ("f56c27ec06b02398cbb957344c539d271d6bf2d151bc379be3c7c684a937c79a",
     "bc552777470280765ff40101ac55d82764fb8ebe5e84253e65e4621fb0f978d1", 1),
    ("809d910a9b93eaae8f5adea4a606229f0d8ff7bef2666f4e5c474990b2f5e50f",
     "a9c6eeb178283a49248b36bba86d50499ec49543058c7a73923a9214cb9c5fc3", 1),
    ("417111b329be60ff83a5adbca31231682728b679ca1ef23cda37ec9cee4cd617",
     "5ff252562aad8239ff27f0bd57b0fb19dfaa6fcdbaf16302c6f77d4ae000d894", 1),
    ("e31d6b12d3ec35cd736ac9e2be1203c0e29ef7c3e5393c98cbdba9ee81fdd7c1",
     "3d28d47dbdbca0674581dbd8132876240dcea0c547e3dbf4b0f260c528bd2373", 1),
    ("1af85a3dcf598e1ff2ca7beb5ea668e30f0dbdd9f2f627f5229c3abb3927968f",
     "ee5eefe99d8940598a0a4218a34b16a460fab684daf580d4ae8b5f0813d5c22b", 1),
    ("gemini-mt6797-a72-r0p1-expected-pair-repair.boot.img",
     "gemini-mt6797-a72-expected-midr-model-guard-repair.boot.img", 1),
    ("e0090fe57490eebe80750d2130a9411edb195e37",
     "8810735dd86f88122821c3309e7a5be5386cd9b6", 1),
    ("74 69 23 c7 8b bf a6 63 4a 3d 5 92 55 7c ae ea 53 ee 82 5d cc e1 e4 b5 4b f2 17 6e 7d 88 44 d2",
     "88 c2 33 35 c6 89 7f d e6 aa df 7d ed 3d 7a 1f 42 aa 4f 13 df 14 1b 18 b4 3c 7 b2 fb 17 e9 85", 1),
    ("validation=a72-r0p1-expected-pair-repair-independent",
     "validation=a72-expected-midr-model-guard-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe model-guard validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_expected_midr_model_guard_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
