#!/usr/bin/env python3
"""Source-pin the independent validator to the entry-checkpoint candidate."""

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
    ("P30E entry-publication diagnostic candidate", "P30E secondary-entry checkpoint candidate", 1),
    ("KERNEL_SIZE = 4_878_149", "KERNEL_SIZE = 4_878_274", 1),
    ("b80dfc49dd22a7830afdadbe3138c0e5131a2da1cbca7012d6c90ad09002e463", "fdf302e80ea4bb9dc9c0766151a4d3d6fe7ffb7e9f43dc13b3dcec481a9956be", 1),
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", "6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f", 1),
    ("c59324bcd04b358a4563bd39d1dcb9c03a47ecef087b57a6b1d5b4cf03f4a82b", "01ad6f80d3e12b25a7d6bd46cc988ee1fa04b98bbb14d9665b1904a83af67644", 1),
    ("f629b74a5dc999d2e353bd25be4710d7bf696bc7dcc9b9558bda9e2f1edded74", "b588e88e2d285da4935c8604d35ae1db37f62ecd3e30004de2073e238c5a97c0", 1),
    ("461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3", "1bc12e8dacff2cef9f248276de80c4e0d37ebd50d5a4e42ed9dc0164837b4046", 1),
    ("135703294fb2dfdecbf200b83e6dfb5d4e49241cbe64a27712d6e055772b35bc", "5ac27f7a280aa87ed28644eeba756af80a02832da96725433800aebc09493e23", 1),
    ("7f5bf270c09b7f603c4f449a3c0e28fd63e6145c3a053bf36119c58753e399aa", "231c631e010ecda7ae95269862d6bac9aaebe9a9b78162ee7bb5509471365bc9", 1),
    ("28b5e3eff190e5299da9594cd3ac5de8ad48b0787fc1c913195e74375a88c3e1", "7e282c34ad9a0324f954a734209db7eb7735f72b16faadf7bafb9606057d45b0", 1),
    ("gemini-mt6797-a72-p30e-entry-diagnostic.boot.img", "gemini-mt6797-a72-secondary-entry-checkpoints.boot.img", 1),
    ("23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51", "e91394af4bae2e131fd5e56ae122c7ef765058ee", 1),
    ("96 fe 21 66 17 bc fb 42 15 94 f4 d1 f9 60 ef f9 62 ae 8a 92 2 11 cf 41 16 9b 30 f7 ed 55 94 55", "4e f5 c8 8c f6 4f 26 d6 1e 51 50 58 57 7c 85 7f 3 b1 4 9f 75 4b 28 23 47 5e 18 61 98 9a 15 82", 1),
    (
        'for symbol in ("arm64_mt6797_a72_p30e_arm", "arm64_mt6797_a72_p30e_readback", "arm64_mt6797_a72_p30e_target_claim", "arm64_mt6797_a72_p30e_target_publish"):',
        'for symbol in ("arm64_mt6797_a72_p30e_arm", "arm64_mt6797_a72_p30e_readback", "arm64_mt6797_a72_p30e_target_claim", "arm64_mt6797_a72_p30e_target_checkpoint", "arm64_mt6797_a72_p30e_target_publish"):',
        1,
    ),
    ("validation=a72-p30e-entry-diagnostic-independent", "validation=a72-secondary-entry-checkpoints-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe entry-checkpoint validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_secondary_entry_checkpoint_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
