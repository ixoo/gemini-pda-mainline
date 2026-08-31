#!/usr/bin/env python3
"""Source-pin the independent validator to the held-result repair image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8a18d3a15f145adf43ccd5ea05d67c98b5868ea1cf02527c46b7d191374d6b0d"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-p27-runtime-attribution"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("P27 runtime-attribution CPU8 candidate", "held-result repair CPU8 candidate", 1),
    ("RAW_SIZE = 6_959_104", "RAW_SIZE = 6_957_056", 1),
    ("KERNEL_SIZE = 4_880_409", "KERNEL_SIZE = 4_879_437", 1),
    ("fbc299b0589de4cf19586436972c8d7219242d14b72589f15d8a2948db1859c3", "df243481ab19dec4d6899c3478391140cc6602f5a5435e11229f7afb0d68ebb3", 1),
    ("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),
    ("a49cadcdb2443a3167e5b93504340ce13f32c57bcfa1622da552acc823815870", "335e89cc31c99b85d891c2e54566024e5789f90437335e17d75fba493d959fc4", 1),
    ("a89ef31c81a6bc14974023bef037ae72aeca225c2b0279cd95e349d05fbf99ea", "9c9a160644106e03cc6be4e86190f9156cde3adbc9d6e8c28a99d4d862ba1eac", 1),
    ("7c2f1f76dfc7ab1645c0563a6d93bfd6e9c48a39c570c0d2f06beef8f796e0a7", "ded617adef441801834d37256c9ef954f035a089bf9b2eb0c4faacd2c0acc8d2", 1),
    ("dc185ae753a4dad86c3d84db8382e3d96cad183bc9120eaafe5fba949ad843a6", "3d093478a19b54c89c25c904beb29558b031f0912a8561e1ba7f52edab251c08", 1),
    ("a3bd117ee2b6d225f9704f3ad75f481d6951b22698e4ceab4546ccc20f74f5f6", "6d07112316ae6098c3a0d44bbd6f52b764fd921b52724204f4e71d56487e57f4", 1),
    ("d5b84687a4c30f1fbb772aa8d807973e0c64f32f6b51d631c2e43b72ffb6b4fe", "b3cbb2817acdc4ed3be4c5ba465a41acbbb6f5f76b6cc20d6752c8e7b6869e19", 1),
    ("gemini-mt6797-a72-p27-runtime-attribution.boot.img", "gemini-mt6797-a72-p27-held-result-contract-repair.boot.img", 1),
    ("b2ca2e5050d38e060aec61b841fde3d395ff589c", "870980dd907856f62c021ddbf8b1b9e7d4c3658e", 1),
    ("16 5f 1b 6d 48 8f 7e 3b 87 a0 3b 68 a1 d8 b4 5 dd 23 44 29 3 a4 fb c4 84 7b 12 14 56 86 1 d5", "f8 7a b4 d9 ed 83 d 42 64 68 38 28 65 94 4e f8 d9 7c bd 40 a4 fc b5 96 15 a2 b4 aa 6b b6 f6 46", 1),
    ("validation=a72-p27-runtime-attribution-independent", "validation=a72-p27-held-result-contract-repair-independent", 1),
    ("unsafe P27 diagnostic validator derivation", "unsafe held-result repair validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe held-result repair validator derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p27_held_result_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
