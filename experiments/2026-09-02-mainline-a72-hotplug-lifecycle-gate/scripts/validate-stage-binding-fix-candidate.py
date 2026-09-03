#!/usr/bin/env python3
"""Independently validate the symbolic stage-binding-fix boot container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "ae2f8a1fb3c9132eb3e38331cab51ee5f1f1a34014d60b5ee3b2f9e9afe0d210"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-postsuccess-diagnostic-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source post-success diagnostic candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("fd015493b0e1df550d2da500b82e9009c96dbcabe867c411846d8dd06e4ae14f",
     "09c4f0b7ebc733286446b586ce397f7f93ded832c4ccd96e48077e363bb995ae", 1),
    ("fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671",
     "c84aea47c6dc4a9745687536b3a99c4e434af5826b10a5a83bae3f8171a81271", 1),
    ("084c2e8176b86a2037d8f2bcf11006daaf211c794694df0f2be2935d65e43b33",
     "0314890897c3c4ed60777a3b0e233670c01e3bbb9add3d662d1efb51d85ca2d3", 1),
    ("84b221e659586e8fd56f805abc0b2a2618d9737aac6f51865d32fc80a02b55ce",
     "5ca5ea6da69b8a4625a3e94b395c15d2f5aeb12f9c01348ba3b5ebab40d5c77f", 1),
    ("959247f1300578b1ec1652eb4cb1d9a36d7c91c6a82228ccd6a2afb9f136136b",
     "ecf278518608e4fa17c05b933a75c55ec4a31fdb4ceff10bce784754822e834c", 1),
    ("9094abdc86db61ef0c4a06670cbce1ef350a8f0b02817fd3b9e5621e2105f89a",
     "3bd51a38ba7931a66d39db455aaa08b587c8b5d8b22368c565f5473c2b0c84e4", 1),
    ("09ab1511459efd84c0a01d994cc237ea1957fa94ec25550ff386c7b8791537a8",
     "0a4434843507ef43c7c2e0b16ca2b453e758d32d8fd198c2c757ee1af128f820", 1),
    ("gemini-mt6797-a72-postsuccess-diagnostic.boot.img",
     "gemini-mt6797-a72-stage-binding-fix.boot.img", 1),
    ('b"gemini-a72post"', 'b"gemini-a72sym"', 1),
    ("35170505f3c42fcdfa6a79c843f8492b9da0fd52",
     "8ae7643c3be90349fbad17e97c9babbb75747f12", 1),
    ("validation=a72-postsuccess-diagnostic-independent",
     "validation=a72-stage-binding-fix-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_stage_binding_fix_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
