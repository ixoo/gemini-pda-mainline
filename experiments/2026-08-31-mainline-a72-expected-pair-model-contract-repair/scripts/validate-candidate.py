#!/usr/bin/env python3
"""Source-pin the validator to the expected-pair model repair candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "562eb009cbfb9e9205a1e56d4c9f6cec5cb9f00fcb21eb8a152fe322673e4001"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-effect-plan-stage-ledger"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("3a8adb13b24e6842a35feca1ac3ca8779a1574331a6b7413c2f597d93152e6b5",
     "228ef7be660b62e43a5debce8b0bf496673b612312218968b94e51aab0d22697", 1),
    ("P30E effect-plan stage-ledger candidate",
     "P30E expected-pair model-contract repair candidate", 1),
    ("KERNEL_SIZE = 4_879_270", "KERNEL_SIZE = 4_879_258", 1),
    ("37de54a0e8ef61b9b7f9e5a05bcec1a2f2ea869c1e38b509ddf20b27c4098496",
     "c66c24c626decb416d1bdeb9818d0bb379ae464f812e323c39a415a9313a1fe1", 1),
    ("b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1",
     "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee", 1),
    ("777bd911f0fcbd8f931a8dbbc11deb32270bb80a5361db8d6223b2c0790a7eb7",
     "68c0fb09b8ad32c4c32921f7d05e57ea991c133df31094644d9fdc180562e7c2", 1),
    ("3e46f12cb6d899de3f00b277c7e18bf79fb765bd76667be20bf4211ff68d02ad",
     "d847bd0ccd3800ea0f2e32964303103ea64c0dbeef7c9b63df2d748addc4811a", 1),
    ("7116bc604fd732dad39e9365579d7fa0e42c185c201134364e699f5e572be964",
     "cab076e835a98fc7fe247ddb502df1cb7cec8e971552c5f6ef7fb5a5153314ff", 1),
    ("9070b3140c9af07922ef75b3d309ebec767afc76fd5702b4212d9382e26f2455",
     "dd4705b7d4fbaea5f4d30e47d8f20ef91e40195e6ecfe832f470c2a683fb5c76", 1),
    ("58124fd3397e82e4bb6c5568875b2326bc72ef43513b6b281e479777184f60b5",
     "25ef693ecaa6b1bf214d2f5948f146e1d95674cc8108562b7a48b1d687208474", 1),
    ("gemini-mt6797-a72-effect-plan-stage-ledger.boot.img",
     "gemini-mt6797-a72-expected-pair-model-contract-repair.boot.img", 1),
    ("6382feb58423c529d4c46ae98253661c158b7bc9",
     "aa2efd3f00f9b632a5a2c570e4319e6c987e3d90", 1),
    ("ef c5 25 ae 46 a8 d9 55 9a ad e5 14 9 73 80 bc 26 a8 20 d3 e3 a8 74 3 fb 1b 4b 9e 44 a8 2d 48",
     "2d 48 ba f8 66 62 d8 13 a c2 76 b6 d8 22 65 8b 47 8f 1e 6c 87 33 f0 a6 c8 2d 92 8c c4 b1 e1 bc", 1),
    ("validation=a72-effect-plan-stage-ledger-independent",
     "validation=a72-expected-pair-model-contract-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe expected-pair candidate validator derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_expected_pair_model_contract_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
