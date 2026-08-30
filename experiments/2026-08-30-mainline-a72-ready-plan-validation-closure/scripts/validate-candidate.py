#!/usr/bin/env python3
"""Source-pin the independent container validator to the post-0437 image."""

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
    ("provenance/serviceability CPU8 candidate", "post-0437 READY-plan CPU8 candidate", 1),
    ("KERNEL_SIZE = 4_872_077", "KERNEL_SIZE = 4_872_101", 1),
    ("1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa", "648a75ff3a243b447d975c51db471b542472c9b4f80da77d1924e153dee036b4", 1),
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "726b622ab503e844e2faddb33fe357250df329510d5b3ab5877687f4db7bfcb0", 1),
    ("68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", "7a26881cb089e9da04fa4b274898ff4d01795064157d104e2b7ccc36282e1d01", 1),
    ("2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", "efa19cc80be0c1e2460d49ecfe280d68d8c22f8e5d44ade93ff94c897ec2c534", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2", "bfd735bb7e20550f70a586a82536eaa6366db4f3079d16af926833fcb2414174", 1),
    ("073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", "773fbef20ec9a47028fa7fbc70cb95d0fc59b07175ecd41e383161ab028535b0", 1),
    ("45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", "e418dccd54e85fe68fa82965fa4bfbd29eb9fe77e326e089383d3c3980308f73", 1),
    ("388c099eaab6c4660db869fedf61e7e4b49c97de88b754c0dd407d4a88606f44", "c003a34d3c84b70d0c0b387951c255dbfdc2d8c22247ce02a712f2d85a76026e", 1),
    ("gemini-mt6797-a72-provenance-serviceability.boot.img", "gemini-mt6797-a72-ready-plan-closure.boot.img", 1),
    ("5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", "a4b9fc5bfba069369d3ef30bb9c996b7144c5d06", 1),
    ("68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a", "8d 6 de 23 4f 5f b5 ed c c 9c 75 6e 5d dd 2e 41 40 26 a6 8a 11 70 60 7f 33 af 33 32 26 a9 2f", 1),
    ("validation=a72-provenance-serviceability-independent", "validation=a72-ready-plan-closure-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-plan validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "a72_ready_plan_closure_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
