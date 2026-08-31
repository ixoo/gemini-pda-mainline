#!/usr/bin/env python3
"""Source-pin the validator to the effect-plan stage-ledger candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "63245c22fe6069605f4169fb09c9c0bd119023025ca83c95bd4980cc95feceba"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("556540ed817e19105bf5a4a059dd3fef9eb6d02dc0ca525c0b23a15598c7a248",
     "3a8adb13b24e6842a35feca1ac3ca8779a1574331a6b7413c2f597d93152e6b5", 1),
    ("P30E expected-MIDR model-guard repair candidate",
     "P30E effect-plan stage-ledger candidate", 1),
    ("KERNEL_SIZE = 4_878_798", "KERNEL_SIZE = 4_879_270", 1),
    ("bf7ebec8193e6139cc544b0d3952154cdaabf895cd477d6552139245854ce83e",
     "37de54a0e8ef61b9b7f9e5a05bcec1a2f2ea869c1e38b509ddf20b27c4098496", 1),
    ("5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69",
     "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1", 1),
    ("bc552777470280765ff40101ac55d82764fb8ebe5e84253e65e4621fb0f978d1",
     "777bd911f0fcbd8f931a8dbbc11deb32270bb80a5361db8d6223b2c0790a7eb7", 1),
    ("a9c6eeb178283a49248b36bba86d50499ec49543058c7a73923a9214cb9c5fc3",
     "3e46f12cb6d899de3f00b277c7e18bf79fb765bd76667be20bf4211ff68d02ad", 1),
    ("5ff252562aad8239ff27f0bd57b0fb19dfaa6fcdbaf16302c6f77d4ae000d894",
     "7116bc604fd732dad39e9365579d7fa0e42c185c201134364e699f5e572be964", 1),
    ("3d28d47dbdbca0674581dbd8132876240dcea0c547e3dbf4b0f260c528bd2373",
     "9070b3140c9af07922ef75b3d309ebec767afc76fd5702b4212d9382e26f2455", 1),
    ("ee5eefe99d8940598a0a4218a34b16a460fab684daf580d4ae8b5f0813d5c22b",
     "58124fd3397e82e4bb6c5568875b2326bc72ef43513b6b281e479777184f60b5", 1),
    ("gemini-mt6797-a72-expected-midr-model-guard-repair.boot.img",
     "gemini-mt6797-a72-effect-plan-stage-ledger.boot.img", 1),
    ("8810735dd86f88122821c3309e7a5be5386cd9b6",
     "6382feb58423c529d4c46ae98253661c158b7bc9", 1),
    ("88 c2 33 35 c6 89 7f d e6 aa df 7d ed 3d 7a 1f 42 aa 4f 13 df 14 1b 18 b4 3c 7 b2 fb 17 e9 85",
     "ef c5 25 ae 46 a8 d9 55 9a ad e5 14 9 73 80 bc 26 a8 20 d3 e3 a8 74 3 fb 1b 4b 9e 44 a8 2d 48", 1),
    ("validation=a72-expected-midr-model-guard-repair-independent",
     "validation=a72-effect-plan-stage-ledger-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe effect-plan validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_effect_plan_stage_ledger_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
