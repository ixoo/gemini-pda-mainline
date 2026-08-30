#!/usr/bin/env python3
"""Source-pin the independent validator to the repaired CPU8 candidate."""

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
    ("provenance/serviceability CPU8 candidate", "repaired live-A34 CPU8 candidate", 1),
    ("RAW_SIZE = 6_948_864", "RAW_SIZE = 6_955_008", 1),
    ("KERNEL_SIZE = 4_872_077", "KERNEL_SIZE = 4_877_022", 1),
    ("1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa", "8fb8194b975989700f0c48b5ce1ab621feed515e4a5174fd36f4fd2039698a80", 1),
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", 1),
    ("68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", "f9210bf11c6861977427f3af0d748c515c71ed70f935ba7e90ef2f8567bdb76d", 1),
    ("2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", "717302bda5819b3ad5e0e824c28726d10f0099c8072b86b71df97a87425eb22c", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2", "7f3a23acec8060642b7c0d52a16b30cdfb7d52a55a70c984a008becb35a09c99", 1),
    ("073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", "e883aee92a5f53a57142d6ad850d0d101e95e62c9945760919cff7aa68518a9f", 1),
    ("45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", "4ee372c3b481a46f40ca548a5f7c0afa3db9eb26bdcf3016dec03de00ae376c7", 1),
    ("388c099eaab6c4660db869fedf61e7e4b49c97de88b754c0dd407d4a88606f44", "0085efd39fd5c62ad56dfe18108ba7e4f70221a1e6a26d785f66b2cf7fb3680d", 1),
    ("gemini-mt6797-a72-provenance-serviceability.boot.img", "gemini-mt6797-a72-live-a34-predicate-repair.boot.img", 1),
    ("5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", "f361a704af745e503388bdaf63c4e161c7bb50fe", 1),
    ("68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a", "a6 90 59 5f 89 c9 b4 e8 f2 27 ea c6 eb 8b fc 98 1b a9 f2 e 6c 61 8b 67 60 96 38 8e f1 b7 43 ca", 1),
    ("validation=a72-provenance-serviceability-independent", "validation=a72-live-a34-predicate-repair-independent", 1),
    ("unsafe candidate-validator derivation", "unsafe live-A34-repair validator derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe live-A34-repair validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_live_a34_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
