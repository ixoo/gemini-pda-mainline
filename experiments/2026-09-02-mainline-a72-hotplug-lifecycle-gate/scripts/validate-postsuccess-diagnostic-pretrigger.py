#!/usr/bin/env python3
"""Fail closed unless the post-success diagnostic is ready and pristine."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "514e5ac72572be00665f1187a7949eae36814e8a6700bd498ac898d36919ee8e"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-p30e-rearm-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source P30E-rearm pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d",
     "fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671", 1),
    ("d43e019475841a26097c49e39fabe0b45e6859848b21c3e3df62d13611a18d10",
     "4f5365b97cabd44e8e4275def7884bcb3533ca4f06001267d4d7b3f2319d5be4", 1),
    ("__A72_P30E_REARM_PRETRIGGER_BEGIN__",
     "__A72_POSTSUCCESS_DIAGNOSTIC_PRETRIGGER_BEGIN__", 1),
    ("__A72_P30E_REARM_PRETRIGGER_END__",
     "__A72_POSTSUCCESS_DIAGNOSTIC_PRETRIGGER_END__", 1),
    ("__A72_P30E_REARM_LATE_PROFILE_BEGIN__",
     "__A72_POSTSUCCESS_DIAGNOSTIC_LATE_PROFILE_BEGIN__", 1),
    ("__A72_P30E_REARM_LATE_PROFILE_END__",
     "__A72_POSTSUCCESS_DIAGNOSTIC_LATE_PROFILE_END__", 1),
    ("exact-p30e-rearm-identity-ready-pristine-physical-contract",
     "exact-postsuccess-diagnostic-identity-ready-pristine-physical-contract", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-success pre-trigger derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_postsuccess_diagnostic_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items()
                  if not key.startswith("__")})


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
