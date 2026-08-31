#!/usr/bin/env python3
"""Source-pin the independent validator to the P30E READY-identity repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "fb84196cf790c14f13b35c309d93f64f3ffdb7a0ceb5411665632ea77b2b7aab"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("P30E entry-publication diagnostic candidate", "P30E READY-identity repair candidate", 1),
    ("b80dfc49dd22a7830afdadbe3138c0e5131a2da1cbca7012d6c90ad09002e463", "417d911fa11b746e4ee2ba3c279e24c7308659b00b5af3c7a9572131f047eaba", 1),
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", 1),
    ("c59324bcd04b358a4563bd39d1dcb9c03a47ecef087b57a6b1d5b4cf03f4a82b", "12b8781c203858b5442e9774e98eed4d1825c92e7adb379bc2716a72a9972d07", 1),
    ("f629b74a5dc999d2e353bd25be4710d7bf696bc7dcc9b9558bda9e2f1edded74", "eef224a19223886721ff6e58225dab26039c52080bf4e267fc1acb02df052e49", 1),
    ("461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3", "614556198ae2459459d849d6428347009f343582a678f056802b7775224c3137", 1),
    ("7f5bf270c09b7f603c4f449a3c0e28fd63e6145c3a053bf36119c58753e399aa", "50b8f400dd672ae1ebb584c125eca88c11c64c89a9ec8cd97a03b6a1ff6ab238", 1),
    ("28b5e3eff190e5299da9594cd3ac5de8ad48b0787fc1c913195e74375a88c3e1", "c98b9e676236d59339ff7939f8cd723310c04474ffda924296f07879177f90e2", 1),
    ("gemini-mt6797-a72-p30e-entry-diagnostic.boot.img", "gemini-mt6797-a72-p30e-ready-identity-repair.boot.img", 1),
    ("23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51", "8fa0757b9e0c2e926906d3ac15ece2a7673b5b47", 1),
    ("96 fe 21 66 17 bc fb 42 15 94 f4 d1 f9 60 ef f9 62 ae 8a 92 2 11 cf 41 16 9b 30 f7 ed 55 94 55", "bb 56 3 f 37 5 71 7 9b d2 21 ad f4 9d d8 f3 2f 6b e7 25 1f 13 40 6b 90 d4 a0 61 58 27 40 9a", 1),
    ("validation=a72-p30e-entry-diagnostic-independent", "validation=a72-p30e-ready-identity-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E READY-identity validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p30e_ready_identity_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
