#!/usr/bin/env python3
"""Source-pin the independent container validator to the value image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "0a538c44a4a0f0354fb6781769a990dbe78716a138063864848b9a5f3e28d0d3"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("READY-plan predicate-diagnostic candidate", "READY-plan value-diagnostic candidate", 1),
    ("KERNEL_SIZE = 4_873_309", "KERNEL_SIZE = 4_873_484", 1),
    ("08eec751391a48b59a32abdac8a5c2ff1aefd970395d444a94a6f003ea45626d", "42f760a7e66a1e0d55c8d148699ba01160d3545d26f5ff99b0bc5156ecbc9df3", 1),
    ("7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", 1),
    ("8f195d672ad6a5cc85ec6cb2bfdac2d406b956521145696914cb2343023a6a08", "0b65b23388a03c4114e76f935013dfdcda21f764eb1000829bcbc38b9c1a64b8", 1),
    ("48dd68028ad3121b900156b3f86cab8cec1075332e39741050c7df2f2815d353", "2c82e22419db7571b4dccef8d633fe2dfb65786d682b47a0a8195ce2597e50ed", 1),
    ("818dece52aa4361840d99525e3f439476a10d32bfa6a67db3f8c7479f89d69df", "5e0baee1743961e381496e8ce31239bd10879c425716c2b42222695732be8b7c", 1),
    ("8cd85c3ff004d7545217f4bc352e41c61562ccda54ebdfa2ba2629c4faf6b8c8", "1c0a04c7ccf95603c072694c5d58f2c85bb45a5d4ac60a48eddb29797ca657e2", 1),
    ("df4cfec102d5032abec3ee1ccb8c4d076eb0939e20adc343da4b18f205680069", "10848fb119857b1906ba820507205a77dcb11e0f9e2aecf674274445bc351ee8", 1),
    ("7c1fe27a46cd4280b54ece13b29b4309a47e14c0827fa140d49a26195413c050", "7568d7733b12e5c0ccbbad9f62c58ae51d92ee60246361f9f2f456a306beb6de", 1),
    ("gemini-mt6797-a72-ready-plan-predicate-diagnostic.boot.img", "gemini-mt6797-a72-ready-plan-value-diagnostic.boot.img", 1),
    ("1df0f12f2e9a4b976e03ec4de674b1185e7d90ba", "e33dfbce2a5f0050403e827ff4b105790069848b", 1),
    ("4e 40 c2 f1 ce 53 2c ac df 9 79 8d 52 4e e4 8b b9 e1 93 d3 98 a8 26 aa c3 a9 db 24 3c 44 2f 49", "ca 78 d9 92 82 ff 97 11 f1 f3 20 bb f5 40 db 3 a6 5b e3 f4 19 b4 f4 f3 6c 1a 8d d8 63 cf 48 36", 1),
    ("validation=a72-ready-plan-predicate-diagnostic-independent", "validation=a72-ready-plan-value-diagnostic-independent", 1),
    ("unsafe predicate-diagnostic validator derivation", "unsafe value-diagnostic validator derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe value-diagnostic validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_plan_value_diagnostic_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
