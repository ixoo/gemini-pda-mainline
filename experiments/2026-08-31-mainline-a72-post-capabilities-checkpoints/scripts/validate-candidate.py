#!/usr/bin/env python3
"""Source-pin the independent validator to the post-capabilities candidate."""

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
    ("P30E entry-publication diagnostic candidate",
     "P30E post-capabilities checkpoint candidate", 1),
    ("RAW_SIZE = 6_955_008", "RAW_SIZE = 6_957_056", 1),
    ("KERNEL_SIZE = 4_878_149", "KERNEL_SIZE = 4_878_366", 1),
    ("b80dfc49dd22a7830afdadbe3138c0e5131a2da1cbca7012d6c90ad09002e463",
     "cb7c886e2cb9d225c75f413217394ae64a12661b36f7c1d18048d27ad338fc0c", 1),
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453",
     "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630", 1),
    ("c59324bcd04b358a4563bd39d1dcb9c03a47ecef087b57a6b1d5b4cf03f4a82b",
     "b875484a9366d30889ccc823d0510d3982ea989cf03f6758817d25b61becadab", 1),
    ("f629b74a5dc999d2e353bd25be4710d7bf696bc7dcc9b9558bda9e2f1edded74",
     "a70d23c793ca41ac2a5d8043da8aba3ea432500a9f95c27d9c888db583bbef58", 1),
    ("461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3",
     "68c57cb8c8eda745c2d42c179ef224821661940115d683e0e0d34e99ea81a0d3", 1),
    ("135703294fb2dfdecbf200b83e6dfb5d4e49241cbe64a27712d6e055772b35bc",
     "5d7b936aebcfdc73af86ae3158fba672532da6c567eb0628e1ea3c1bc0821659", 1),
    ("7f5bf270c09b7f603c4f449a3c0e28fd63e6145c3a053bf36119c58753e399aa",
     "c5023a5bada66f539a4ab4c3b1c6b7b6f5c0eeba63da20284ff0f551ba5db243", 1),
    ("28b5e3eff190e5299da9594cd3ac5de8ad48b0787fc1c913195e74375a88c3e1",
     "115719788a95923b3b41f7f9d2aeb4b11acf3289147f01969b3a43032429cefe", 1),
    ("gemini-mt6797-a72-p30e-entry-diagnostic.boot.img",
     "gemini-mt6797-a72-post-capabilities-checkpoints.boot.img", 1),
    ("23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51",
     "590dbedc974c6a40f34c1d4c34e9bb571bc2a10d", 1),
    ("96 fe 21 66 17 bc fb 42 15 94 f4 d1 f9 60 ef f9 62 ae 8a 92 2 11 cf 41 16 9b 30 f7 ed 55 94 55",
     "7c 6c 9a 78 5e 2c cf 27 7e 61 a1 55 2c 4c 2f b2 19 e3 37 1b 29 21 b0 b4 1a 9e da 1d 2f 7e a6 90", 1),
    (
        'for symbol in ("arm64_mt6797_a72_p30e_arm", "arm64_mt6797_a72_p30e_readback", "arm64_mt6797_a72_p30e_target_claim", "arm64_mt6797_a72_p30e_target_publish"):',
        'for symbol in ("arm64_mt6797_a72_p30e_arm", "arm64_mt6797_a72_p30e_readback", "arm64_mt6797_a72_p30e_target_claim", "arm64_mt6797_a72_p30e_target_checkpoint", "arm64_mt6797_a72_p30e_target_publish"):',
        1,
    ),
    ("validation=a72-p30e-entry-diagnostic-independent",
     "validation=a72-post-capabilities-checkpoints-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-capabilities validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_post_capabilities_checkpoint_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
