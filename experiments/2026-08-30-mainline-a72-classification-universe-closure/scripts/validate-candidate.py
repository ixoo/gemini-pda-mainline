#!/usr/bin/env python3
"""Source-pin the independent container validator to the closure image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8ec65465c1ed5e8b270bdf0466f067e2799d021494f6066b06fe552b06f097e8"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-expectation-repair"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("repaired READY-plan candidate", "classification-closure READY candidate", 1),
    ("982c4b50d3bdbe9d1a0d0218ded5c2a4bcd4b39e859d79b3048c1eab14ce3e0b", "9caea8fe255214dd5d36b2d6a975e41b143b00d757cc54e7ccead9d1b5c62c6c", 1),
    ("9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", "2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", 1),
    ("31e78157ff0522ef8e2269f16f49de4e66cf45034c56c20b817d70340d81eb9d", "5293d9be0ff42439faa1c1b27b18c37e3e47edf4a1c7cd367e34bce9fc2b9e75", 1),
    ("a7e1b036ed2aa225b1b1b7be46176cf4945a18cb6cdbe257b241d6002741552e", "22bd67b98c6bf0d2fbd6c8dd1d33d9d74b1a121ac0ee33d5564534cb3c404a8f", 1),
    ("0732a2cf00e04a71034a563dcb35a8a3e3414620cdf8d511767a17f9b552fcba", "a30dce8d957a2f8d79a244d599f899de15ea696129096e576260e17a0ac9f352", 1),
    ("6bd498c321726f21f3e39adf22ccd0c5c10b6f932bd64a6ae2fe13cbc6e867dc", "c10171ccea82cb163e7a58f49462a3b8ddfa06ca820a4ba68df79e342b75b254", 1),
    ("44666a9cbc566cd5757311c8a01f787240195ad62ac42a882f5c998cd92f4fc6", "64b3634a751b8b2c4816a2178189b3d85e9a1d1a38b78991acbf46e4046526a5", 1),
    ("7057b19fe6bdc4e2de15e6e0f86beeae6d5554c275a693a5a6a1e5b0a0dfcc67", "545535d3e8f0637e7704118911da95581c98326cffc203a569bdbb409053e24a", 1),
    ("gemini-mt6797-a72-ready-plan-expectation-repair.boot.img", "gemini-mt6797-a72-classification-universe-closure.boot.img", 1),
    ("a07d9c453e2ceaa3666db124ed1ebb712d00d07c", "787ff75a7d9c624a7f25abf69b50a45cfd8ebcc7", 1),
    ("ab 16 41 2a fe 28 33 e0 58 bf a 14 3 52 a6 f9 4a 79 29 12 a7 a9 4c ae dd 39 8 e0 ee 92 7c e2", "6e 41 9e 90 42 96 5e 11 62 4b ab c5 17 e3 62 93 40 c4 79 8d b a5 2 5c c5 ac 39 54 8 b4 db 9c", 1),
    ("validation=a72-ready-plan-expectation-repair-independent", "validation=a72-classification-universe-closure-independent", 1),
    ("unsafe READY-repair validator derivation", "unsafe classification-closure validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe classification-closure validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_classification_universe_closure_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
