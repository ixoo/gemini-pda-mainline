#!/usr/bin/env python3
"""Source-pin the independent validator to the isolation-result repair image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "2f673e6897985b8542d93db63b5df609e0e6b084a1a8bbf7545bbfc9c037c67a"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("held-result repair CPU8 candidate", "isolation-result repair CPU8 candidate", 1),
    ("KERNEL_SIZE = 4_879_437", "KERNEL_SIZE = 4_879_429", 1),
    ("df243481ab19dec4d6899c3478391140cc6602f5a5435e11229f7afb0d68ebb3", "53b52ffcbe700866e4d96c3ae84e6cc98910ae0dc45a000c815f212a4ba9662f", 1),
    ("fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),
    ("335e89cc31c99b85d891c2e54566024e5789f90437335e17d75fba493d959fc4", "d806a4900bc005c02a2470c2617700493b3e6a0c7ceed89e1e903b39227d6368", 1),
    ("9c9a160644106e03cc6be4e86190f9156cde3adbc9d6e8c28a99d4d862ba1eac", "387a36725b7769a87228408c2735ae883e0b1f9393f99e61674136832fceae22", 1),
    ("ded617adef441801834d37256c9ef954f035a089bf9b2eb0c4faacd2c0acc8d2", "57fb4aae9cf3f5767e7b3d8ae95238d806e3ed55bfe2298d587f7fc550a3c7dd", 1),
    ("3d093478a19b54c89c25c904beb29558b031f0912a8561e1ba7f52edab251c08", "9cd410101eb8e3e7470b9d2b777bf8fa96a9bc0050f3f55d7bf57fd7a0a936cc", 1),
    ("6d07112316ae6098c3a0d44bbd6f52b764fd921b52724204f4e71d56487e57f4", "bb206991024a8b9f0b477b326b07bd61e880ebac964ed331495cf857f0225636", 1),
    ("b3cbb2817acdc4ed3be4c5ba465a41acbbb6f5f76b6cc20d6752c8e7b6869e19", "4d1607238546ef4d01e8f15ee0d787108b24b220edc181f21f9fcb68cd92f64d", 1),
    ("gemini-mt6797-a72-p27-held-result-contract-repair.boot.img", "gemini-mt6797-a72-isolation-held-result-contract-repair.boot.img", 1),
    ("870980dd907856f62c021ddbf8b1b9e7d4c3658e", "62557cd201438802cbbc0034e7635f16a716b191", 1),
    ("f8 7a b4 d9 ed 83 d 42 64 68 38 28 65 94 4e f8 d9 7c bd 40 a4 fc b5 96 15 a2 b4 aa 6b b6 f6 46", "29 5d 1b 4e b6 2c bf 1f ad d2 c2 c8 3c db 15 12 a4 52 1a 23 4d 72 84 27 13 21 f9 48 a1 9e ce 16", 1),
    ("validation=a72-p27-held-result-contract-repair-independent", "validation=a72-isolation-held-result-contract-repair-independent", 1),
    ("unsafe held-result repair validator derivation", "unsafe isolation-result repair validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe isolation-result repair validator derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_isolation_held_result_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
