#!/usr/bin/env python3
"""Source-pin the independent validator to the repaired READY-token image."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "68c52e7d8404decafcd984a5c6ffd89ae0c76ab27b9d0b215906c6fb63a05207"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-live-a34-predicate-repair"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("repaired live-A34 CPU8 candidate", "repaired READY-token CPU8 candidate", 1),
    ("KERNEL_SIZE = 4_877_022", "KERNEL_SIZE = 4_877_003", 1),
    ("8fb8194b975989700f0c48b5ce1ab621feed515e4a5174fd36f4fd2039698a80", "efe47cb1140c1aacc97e2b6405432514c35a7ef546068f47150d6139d03a2464", 1),
    ("7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", 1),
    ("f9210bf11c6861977427f3af0d748c515c71ed70f935ba7e90ef2f8567bdb76d", "118e0d8106330055b09d63085cfe27bf8818747bedc9402fbd48d3095e0384ee", 1),
    ("717302bda5819b3ad5e0e824c28726d10f0099c8072b86b71df97a87425eb22c", "7553356a12a068c2bf5d917609936b98e7747dc54ce992c9b833121d9756d2c3", 1),
    ("7f3a23acec8060642b7c0d52a16b30cdfb7d52a55a70c984a008becb35a09c99", "11eb595964b191d83f08b33260462fae1dba3dfba0d26e99ce1552a444864526", 1),
    ("e883aee92a5f53a57142d6ad850d0d101e95e62c9945760919cff7aa68518a9f", "671e5cf88bb81c1a8c2990d84ca100640875630d6dcb6886e83811af9b7a65e0", 1),
    ("4ee372c3b481a46f40ca548a5f7c0afa3db9eb26bdcf3016dec03de00ae376c7", "022aa79d1ee3a279fb5c62ca7b5608701fb09a8fefa4c575b5396d9f107bf5ec", 1),
    ("0085efd39fd5c62ad56dfe18108ba7e4f70221a1e6a26d785f66b2cf7fb3680d", "3109e145e478890797f67e07ac55d11f17769862c80978d797efb32305bc59c1", 1),
    ("gemini-mt6797-a72-live-a34-predicate-repair.boot.img", "gemini-mt6797-a72-ready-token-contract-repair.boot.img", 1),
    ("f361a704af745e503388bdaf63c4e161c7bb50fe", "8dc8e806331b1617795eb02aff27df559521e508", 1),
    ("a6 90 59 5f 89 c9 b4 e8 f2 27 ea c6 eb 8b fc 98 1b a9 f2 e 6c 61 8b 67 60 96 38 8e f1 b7 43 ca", "c8 6 14 f4 58 18 15 36 8 80 32 93 9f c3 2a 1a b9 29 48 ce bd 95 3d ed 37 93 df 97 d3 4a 27 96", 1),
    ("validation=a72-live-a34-predicate-repair-independent", "validation=a72-ready-token-contract-repair-independent", 1),
    ("unsafe live-A34-repair validator derivation", "unsafe READY-contract validator derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-contract validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_contract_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
