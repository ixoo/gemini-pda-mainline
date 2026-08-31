#!/usr/bin/env python3
"""Source-pin the independent validator to the P27 diagnostic image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6a0405935bd9a129873636e8ebfed09c2a767367c429f6286ce19b346e695e53"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-token-contract-repair"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
size_anchor = '("KERNEL_SIZE = 4_877_022", "KERNEL_SIZE = 4_877_003", 1),'
size_replacement = (
    '("RAW_SIZE = 6_955_008", "RAW_SIZE = 6_959_104", 1),\n'
    "    " + size_anchor
)
replacements = (
    ("repaired READY-token CPU8 candidate", "P27 runtime-attribution CPU8 candidate", 1),
    (size_anchor, size_replacement, 1),
    ("KERNEL_SIZE = 4_877_003", "KERNEL_SIZE = 4_880_409", 1),
    ("efe47cb1140c1aacc97e2b6405432514c35a7ef546068f47150d6139d03a2464", "fbc299b0589de4cf19586436972c8d7219242d14b72589f15d8a2948db1859c3", 1),
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 1),
    ("118e0d8106330055b09d63085cfe27bf8818747bedc9402fbd48d3095e0384ee", "a49cadcdb2443a3167e5b93504340ce13f32c57bcfa1622da552acc823815870", 1),
    ("7553356a12a068c2bf5d917609936b98e7747dc54ce992c9b833121d9756d2c3", "a89ef31c81a6bc14974023bef037ae72aeca225c2b0279cd95e349d05fbf99ea", 1),
    ("11eb595964b191d83f08b33260462fae1dba3dfba0d26e99ce1552a444864526", "7c2f1f76dfc7ab1645c0563a6d93bfd6e9c48a39c570c0d2f06beef8f796e0a7", 1),
    ("671e5cf88bb81c1a8c2990d84ca100640875630d6dcb6886e83811af9b7a65e0", "dc185ae753a4dad86c3d84db8382e3d96cad183bc9120eaafe5fba949ad843a6", 1),
    ("022aa79d1ee3a279fb5c62ca7b5608701fb09a8fefa4c575b5396d9f107bf5ec", "a3bd117ee2b6d225f9704f3ad75f481d6951b22698e4ceab4546ccc20f74f5f6", 1),
    ("3109e145e478890797f67e07ac55d11f17769862c80978d797efb32305bc59c1", "d5b84687a4c30f1fbb772aa8d807973e0c64f32f6b51d631c2e43b72ffb6b4fe", 1),
    ("gemini-mt6797-a72-ready-token-contract-repair.boot.img", "gemini-mt6797-a72-p27-runtime-attribution.boot.img", 1),
    ("8dc8e806331b1617795eb02aff27df559521e508", "b2ca2e5050d38e060aec61b841fde3d395ff589c", 1),
    ("c8 6 14 f4 58 18 15 36 8 80 32 93 9f c3 2a 1a b9 29 48 ce bd 95 3d ed 37 93 df 97 d3 4a 27 96", "16 5f 1b 6d 48 8f 7e 3b 87 a0 3b 68 a1 d8 b4 5 dd 23 44 29 3 a4 fb c4 84 7b 12 14 56 86 1 d5", 1),
    ("validation=a72-ready-token-contract-repair-independent", "validation=a72-p27-runtime-attribution-independent", 1),
    ("unsafe READY-contract validator derivation", "unsafe P27 diagnostic validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 diagnostic validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p27_runtime_attribution_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
