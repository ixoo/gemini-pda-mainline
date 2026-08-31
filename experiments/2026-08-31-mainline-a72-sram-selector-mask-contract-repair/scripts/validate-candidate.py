#!/usr/bin/env python3
"""Source-pin the independent validator to the selector-mask repair image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "d037587d8c3f892cdc37719c2f4003ae7cb8abdce4853f0e394f2b8c04721a08"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("SRAM/P28 terminal diagnostic CPU8 candidate", "SRAM selector-mask repair CPU8 candidate", 1),
    ("KERNEL_SIZE = 4_878_208", "KERNEL_SIZE = 4_877_909", 1),
    ("0e1be4e07472e5050ab52e91558bd6cf89a5fa509a009c5746085547dc6599f1", "add111acedb0850983371efed982c1b569adc8fc181cad86402643d426371942", 1),
    ("7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", 1),
    ("4325c2fe7119bffc2f8f199c11b6193bb4d7d579889b4c9d479a87d90fc8d8be", "6fb2dabde0d8056011d0b3ef166ec4e7cf621e7c016ce1ff06b0e76b933adb88", 1),
    ("09887d8091b565c91d84663585b4338276141ff2442543ab99e286f3ac92893e", "d9b45182645c4a37a7f38d37597c54c59d8d6749db672331c2dfadc1b1eb2b6f", 1),
    ("8346f271280739437a013e04a3f9992981adbaa302e2c44add844008f832902d", "9e0445cc404cd76aff96cfbfb7a9305b91cd1ff71918aaf6ca451f6f11780be3", 1),
    ("299b5d527b5c0136aec32ac78254fa1cb6a7059bffc5df3163951f70dfbfa564", "795f8d1066ca39eaa6ee750aa9a13ba9e61d3705959d266dc07f6fb928f69f92", 1),
    ("d07f2eccbc332b1b12894967e96c90b56f6b08bc1cf764bb979a008a180dd69a", "339e3d0e7254798abcda39258595623dc826e0982330754e481f8027e410f3d9", 1),
    ("a4fcb4e6465b2dec5a1e52fabeb9e6f69230cef7472e7cba981b5c6f8ce3df10", "ab432d011f00788c7a85c4bb8a1a980d3e1a50d4a2904c28d2d9cd6031a96cf0", 1),
    ("gemini-mt6797-a72-sram-p28-terminal-diagnostic.boot.img", "gemini-mt6797-a72-sram-selector-mask-contract-repair.boot.img", 1),
    ("3508f303275c461c728a500c307ad0d9d2074f28", "2d682d8a48c7169a8f5ab5928ff6d61263e5fa64", 1),
    ("fe 81 d bc e4 86 b6 b9 77 53 58 79 b3 72 d3 21 6b 5e c5 76 55 1c fc af 1c 4a c4 55 3f 35 63 42", "91 d3 28 ee 1 ba c2 16 64 e0 ae fc 68 9d 69 1 c5 5a b1 6a 97 3e d6 1b 66 30 99 4d f1 1 49 65", 1),
    ("validation=a72-sram-p28-terminal-diagnostic-independent", "validation=a72-sram-selector-mask-contract-repair-independent", 1),
    ("unsafe SRAM/P28 diagnostic validator derivation", "unsafe selector-mask repair validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe selector-mask repair validator derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_selector_mask_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
