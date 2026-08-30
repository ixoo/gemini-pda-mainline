#!/usr/bin/env python3
"""Source-pin the independent container validator to the diagnostic image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "0e646c153a74c33018141da7fe43353347f9f0dc06296ac9a72006f1e9acbf00"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("provenance/serviceability CPU8 candidate", "READY-plan predicate-diagnostic candidate", 1),
    ("RAW_SIZE = 6_948_864", "RAW_SIZE = 6_950_912", 1),
    ("KERNEL_SIZE = 4_872_077", "KERNEL_SIZE = 4_873_309", 1),
    ("1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa", "08eec751391a48b59a32abdac8a5c2ff1aefd970395d444a94a6f003ea45626d", 1),
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", 1),
    ("68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", "8f195d672ad6a5cc85ec6cb2bfdac2d406b956521145696914cb2343023a6a08", 1),
    ("2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", "48dd68028ad3121b900156b3f86cab8cec1075332e39741050c7df2f2815d353", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2", "818dece52aa4361840d99525e3f439476a10d32bfa6a67db3f8c7479f89d69df", 1),
    ("073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", "8cd85c3ff004d7545217f4bc352e41c61562ccda54ebdfa2ba2629c4faf6b8c8", 1),
    ("45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", "df4cfec102d5032abec3ee1ccb8c4d076eb0939e20adc343da4b18f205680069", 1),
    ("388c099eaab6c4660db869fedf61e7e4b49c97de88b754c0dd407d4a88606f44", "7c1fe27a46cd4280b54ece13b29b4309a47e14c0827fa140d49a26195413c050", 1),
    ("gemini-mt6797-a72-provenance-serviceability.boot.img", "gemini-mt6797-a72-ready-plan-predicate-diagnostic.boot.img", 1),
    ("5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", "1df0f12f2e9a4b976e03ec4de674b1185e7d90ba", 1),
    ("68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a", "4e 40 c2 f1 ce 53 2c ac df 9 79 8d 52 4e e4 8b b9 e1 93 d3 98 a8 26 aa c3 a9 db 24 3c 44 2f 49", 1),
    ("validation=a72-provenance-serviceability-independent", "validation=a72-ready-plan-predicate-diagnostic-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe predicate-diagnostic validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_plan_predicate_diagnostic_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
