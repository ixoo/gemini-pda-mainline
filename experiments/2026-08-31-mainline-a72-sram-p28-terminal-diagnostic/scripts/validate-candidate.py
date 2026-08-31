#!/usr/bin/env python3
"""Source-pin the independent validator to the SRAM/P28 diagnostic image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "cb6e3d8a63bd3290cb75ef3bca5721e73543f3aabb9ba9e544744b8a4d25fb20"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
size_anchor = '    ("df243481ab19dec4d6899c3478391140cc6602f5a5435e11229f7afb0d68ebb3", "53b52ffcbe700866e4d96c3ae84e6cc98910ae0dc45a000c815f212a4ba9662f", 1),'
size_replacement = (
    '    ("RAW_SIZE = 6_957_056", "RAW_SIZE = 6_955_008", 1),\n'
    + size_anchor
)
replacements = (
    ("isolation-result repair CPU8 candidate", "SRAM/P28 terminal diagnostic CPU8 candidate", 1),
    ("KERNEL_SIZE = 4_879_429", "KERNEL_SIZE = 4_878_208", 1),
    (size_anchor, size_replacement, 1),
    ("53b52ffcbe700866e4d96c3ae84e6cc98910ae0dc45a000c815f212a4ba9662f", "0e1be4e07472e5050ab52e91558bd6cf89a5fa509a009c5746085547dc6599f1", 1),
    ("510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", 1),
    ("d806a4900bc005c02a2470c2617700493b3e6a0c7ceed89e1e903b39227d6368", "4325c2fe7119bffc2f8f199c11b6193bb4d7d579889b4c9d479a87d90fc8d8be", 1),
    ("387a36725b7769a87228408c2735ae883e0b1f9393f99e61674136832fceae22", "09887d8091b565c91d84663585b4338276141ff2442543ab99e286f3ac92893e", 1),
    ("57fb4aae9cf3f5767e7b3d8ae95238d806e3ed55bfe2298d587f7fc550a3c7dd", "8346f271280739437a013e04a3f9992981adbaa302e2c44add844008f832902d", 1),
    ("9cd410101eb8e3e7470b9d2b777bf8fa96a9bc0050f3f55d7bf57fd7a0a936cc", "299b5d527b5c0136aec32ac78254fa1cb6a7059bffc5df3163951f70dfbfa564", 1),
    ("bb206991024a8b9f0b477b326b07bd61e880ebac964ed331495cf857f0225636", "d07f2eccbc332b1b12894967e96c90b56f6b08bc1cf764bb979a008a180dd69a", 1),
    ("4d1607238546ef4d01e8f15ee0d787108b24b220edc181f21f9fcb68cd92f64d", "a4fcb4e6465b2dec5a1e52fabeb9e6f69230cef7472e7cba981b5c6f8ce3df10", 1),
    ("gemini-mt6797-a72-isolation-held-result-contract-repair.boot.img", "gemini-mt6797-a72-sram-p28-terminal-diagnostic.boot.img", 1),
    ("62557cd201438802cbbc0034e7635f16a716b191", "3508f303275c461c728a500c307ad0d9d2074f28", 1),
    ("29 5d 1b 4e b6 2c bf 1f ad d2 c2 c8 3c db 15 12 a4 52 1a 23 4d 72 84 27 13 21 f9 48 a1 9e ce 16", "fe 81 d bc e4 86 b6 b9 77 53 58 79 b3 72 d3 21 6b 5e c5 76 55 1c fc af 1c 4a c4 55 3f 35 63 42", 1),
    ("validation=a72-isolation-held-result-contract-repair-independent", "validation=a72-sram-p28-terminal-diagnostic-independent", 1),
    ("unsafe isolation-result repair validator derivation", "unsafe SRAM/P28 diagnostic validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe SRAM/P28 diagnostic validator derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_sram_p28_diagnostic_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
