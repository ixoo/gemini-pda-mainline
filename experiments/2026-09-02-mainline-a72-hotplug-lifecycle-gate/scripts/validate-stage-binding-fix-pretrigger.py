#!/usr/bin/env python3
"""Fail closed unless the symbolic stage-binding fix is ready and pristine."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "2023787a92ef3e03c75a0e1799ba1083e5d356d1821a9a5fa6d3b7aabb2c28da"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-postsuccess-diagnostic-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source post-success diagnostic pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671",
     "c84aea47c6dc4a9745687536b3a99c4e434af5826b10a5a83bae3f8171a81271", 1),
    ("4f5365b97cabd44e8e4275def7884bcb3533ca4f06001267d4d7b3f2319d5be4",
     "d4940602e7ad9cbc947376bfb9dc4222ef5a671faa15eb42a821df1852af9ba4", 1),
    ("__A72_POSTSUCCESS_DIAGNOSTIC_PRETRIGGER_BEGIN__",
     "__A72_STAGE_BINDING_FIX_PRETRIGGER_BEGIN__", 1),
    ("__A72_POSTSUCCESS_DIAGNOSTIC_PRETRIGGER_END__",
     "__A72_STAGE_BINDING_FIX_PRETRIGGER_END__", 1),
    ("__A72_POSTSUCCESS_DIAGNOSTIC_LATE_PROFILE_BEGIN__",
     "__A72_STAGE_BINDING_FIX_LATE_PROFILE_BEGIN__", 1),
    ("__A72_POSTSUCCESS_DIAGNOSTIC_LATE_PROFILE_END__",
     "__A72_STAGE_BINDING_FIX_LATE_PROFILE_END__", 1),
    ("exact-postsuccess-diagnostic-identity-ready-pristine-physical-contract",
     "exact-stage-binding-fix-identity-ready-pristine-physical-contract", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding pre-trigger derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_stage_binding_fix_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items()
                  if not key.startswith("__")})


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
