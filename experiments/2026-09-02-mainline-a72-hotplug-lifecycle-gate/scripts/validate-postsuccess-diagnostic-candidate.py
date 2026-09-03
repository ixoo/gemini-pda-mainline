#!/usr/bin/env python3
"""Independently validate the post-success diagnostic boot container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "bde4ea2349e5f1a03a98eac54fbd82f5a3be0330e4fca026a6646499e7c3cae6"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-p30e-rearm-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source P30E-rearm candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("RAW_SIZE = 6_981_632", "RAW_SIZE = 6_983_680", 1),
    ("KERNEL_SIZE = 4_904_941", "KERNEL_SIZE = 4_905_290", 1),
    ("c1cf7d7ae7734e3a540b68bc119c82669ad177e63212dee32219e1e442d30294",
     "fd015493b0e1df550d2da500b82e9009c96dbcabe867c411846d8dd06e4ae14f", 1),
    ("7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d",
     "fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671", 1),
    ("e1b58f196a25e2a05b456d645ba34d0c35eae313e69ec44f964cd11ca3df926e",
     "084c2e8176b86a2037d8f2bcf11006daaf211c794694df0f2be2935d65e43b33", 1),
    ("a04aafbb670a833cd72952cd9397e311344db971d400782b15d2a2a04f26e843",
     "84b221e659586e8fd56f805abc0b2a2618d9737aac6f51865d32fc80a02b55ce", 1),
    ("1396b2e81dd23f4298df86dd3449acf7dfa519d3655b280d79b64c03595b0933",
     "959247f1300578b1ec1652eb4cb1d9a36d7c91c6a82228ccd6a2afb9f136136b", 1),
    ("1850874148e045ee429c797d11ba57c66b4186efbf4942c5707fa71d866b09c9",
     "3575c11feb630252edd5bf3e13319a8c597994f4ff349164a2a43a4bb638a4e3", 1),
    ("ebb46a9910b567e5d70a3897768aa48ed5f575d42a8308bc5734099f8527b8b3",
     "9094abdc86db61ef0c4a06670cbce1ef350a8f0b02817fd3b9e5621e2105f89a", 1),
    ("c8e73b255162e8fbe3cfe9f5c6e600b705d6c63333b8a4451c47c4492b85edd8",
     "09ab1511459efd84c0a01d994cc237ea1957fa94ec25550ff386c7b8791537a8", 1),
    ("gemini-mt6797-a72-p30e-rearm.boot.img",
     "gemini-mt6797-a72-postsuccess-diagnostic.boot.img", 1),
    ('b"gemini-a72p30e"', 'b"gemini-a72post"', 1),
    ("d2161a1eb166d469e5b5e690e5eb4bf3ff2b4f9d",
     "35170505f3c42fcdfa6a79c843f8492b9da0fd52", 1),
    ("validation=a72-p30e-rearm-independent",
     "validation=a72-postsuccess-diagnostic-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-success candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_postsuccess_diagnostic_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
