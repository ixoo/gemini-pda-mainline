#!/usr/bin/env python3
"""Source-pin the independent container validator to the repaired image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "aeaeae04d10e167509be929f80c3c2d66425e841d524e8426a29e202f1bfbd60"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-value-diagnostic"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("READY-plan value-diagnostic candidate", "repaired READY-plan candidate", 1),
    ("KERNEL_SIZE = 4_873_484", "KERNEL_SIZE = 4_873_492", 1),
    ("42f760a7e66a1e0d55c8d148699ba01160d3545d26f5ff99b0bc5156ecbc9df3", "982c4b50d3bdbe9d1a0d0218ded5c2a4bcd4b39e859d79b3048c1eab14ce3e0b", 1),
    ("1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", "9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", 1),
    ("0b65b23388a03c4114e76f935013dfdcda21f764eb1000829bcbc38b9c1a64b8", "31e78157ff0522ef8e2269f16f49de4e66cf45034c56c20b817d70340d81eb9d", 1),
    ("2c82e22419db7571b4dccef8d633fe2dfb65786d682b47a0a8195ce2597e50ed", "a7e1b036ed2aa225b1b1b7be46176cf4945a18cb6cdbe257b241d6002741552e", 1),
    ("5e0baee1743961e381496e8ce31239bd10879c425716c2b42222695732be8b7c", "0732a2cf00e04a71034a563dcb35a8a3e3414620cdf8d511767a17f9b552fcba", 1),
    ("1c0a04c7ccf95603c072694c5d58f2c85bb45a5d4ac60a48eddb29797ca657e2", "6bd498c321726f21f3e39adf22ccd0c5c10b6f932bd64a6ae2fe13cbc6e867dc", 1),
    ("10848fb119857b1906ba820507205a77dcb11e0f9e2aecf674274445bc351ee8", "44666a9cbc566cd5757311c8a01f787240195ad62ac42a882f5c998cd92f4fc6", 1),
    ("7568d7733b12e5c0ccbbad9f62c58ae51d92ee60246361f9f2f456a306beb6de", "7057b19fe6bdc4e2de15e6e0f86beeae6d5554c275a693a5a6a1e5b0a0dfcc67", 1),
    ("gemini-mt6797-a72-ready-plan-value-diagnostic.boot.img", "gemini-mt6797-a72-ready-plan-expectation-repair.boot.img", 1),
    ("e33dfbce2a5f0050403e827ff4b105790069848b", "a07d9c453e2ceaa3666db124ed1ebb712d00d07c", 1),
    ("ca 78 d9 92 82 ff 97 11 f1 f3 20 bb f5 40 db 3 a6 5b e3 f4 19 b4 f4 f3 6c 1a 8d d8 63 cf 48 36", "ab 16 41 2a fe 28 33 e0 58 bf a 14 3 52 a6 f9 4a 79 29 12 a7 a9 4c ae dd 39 8 e0 ee 92 7c e2", 1),
    ("validation=a72-ready-plan-value-diagnostic-independent", "validation=a72-ready-plan-expectation-repair-independent", 1),
    ("unsafe value-diagnostic validator derivation", "unsafe READY-repair validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-repair validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_plan_expectation_repair_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
