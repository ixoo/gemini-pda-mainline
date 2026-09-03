#!/usr/bin/env python3
"""Independently validate the CPU9 P30E-rearm boot container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "cd5972da9ef5cc044b83561b07aca463650fe17209abd82a2eb25ef2c39f7d0a"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-physical-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source physical-hotplug candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("RAW_SIZE = 6_983_680", "RAW_SIZE = 6_981_632", 1),
    ("KERNEL_SIZE = 4_905_091", "KERNEL_SIZE = 4_904_941", 1),
    ("f411b55d89b7343e9bd53b9087012322c969fe9344411a192262e9ae0845cdc2",
     "c1cf7d7ae7734e3a540b68bc119c82669ad177e63212dee32219e1e442d30294", 1),
    ("44e1b42c2dbec86c5da4a3f6cdc0ac1a06d47405b953bdc5401d01facf1d7d09",
     "7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d", 1),
    ("c64ead6c6d6fb31acbab558de73006a70c908ba989eace7c2757783243dfccb0",
     "e1b58f196a25e2a05b456d645ba34d0c35eae313e69ec44f964cd11ca3df926e", 1),
    ("af5dbc32273f7ee08b47cd68f0008fe47a38d5c22b6b70f00bacd2856d3f4f18",
     "a04aafbb670a833cd72952cd9397e311344db971d400782b15d2a2a04f26e843", 1),
    ("902762c2a1badd9e71ebb25c842b0135fbf0076837956da1da73b42a38bbedcd",
     "1396b2e81dd23f4298df86dd3449acf7dfa519d3655b280d79b64c03595b0933", 1),
    ("8c085cfe815581dfd4b21b940d51473af464a5e15529c20f72577a41fd41646b",
     "1850874148e045ee429c797d11ba57c66b4186efbf4942c5707fa71d866b09c9", 1),
    ("9a1cad35ff62f970c84e282ce6e9bf37c64bc1eb5ffbed5ef0708c5c21778db9",
     "ebb46a9910b567e5d70a3897768aa48ed5f575d42a8308bc5734099f8527b8b3", 1),
    ("645a9737be18640f8ecf10235043a974fc128edcd66d3982b8561e30b3844851",
     "c8e73b255162e8fbe3cfe9f5c6e600b705d6c63333b8a4451c47c4492b85edd8", 1),
    ("gemini-mt6797-a72-hotplug-physical.boot.img",
     "gemini-mt6797-a72-p30e-rearm.boot.img", 1),
    ('b"gemini-a72prov"', 'b"gemini-a72p30e"', 1),
    ("819d8f0d5a431c852ef5d7f8947585f3dcb167f6",
     "d2161a1eb166d469e5b5e690e5eb4bf3ff2b4f9d", 1),
    ("validation=a72-physical-hotplug-independent",
     "validation=a72-p30e-rearm-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E-rearm candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_p30e_rearm_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
