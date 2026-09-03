#!/usr/bin/env python3
"""Fail closed unless the exact P30E-rearm candidate is ready and pristine."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c9764eb35190ee29a614eba63f638fa620fc13bb41cdec250c0d0bd3763530d0"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-physical-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source physical-hotplug pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("44e1b42c2dbec86c5da4a3f6cdc0ac1a06d47405b953bdc5401d01facf1d7d09",
     "7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d", 1),
    ("4b19fb832a587c0dc389fe8f4c15edec4b2fa40e8ae0c50d993212878b50883d",
     "d43e019475841a26097c49e39fabe0b45e6859848b21c3e3df62d13611a18d10", 1),
    ("__A72_PHYSICAL_REPAIR_PRETRIGGER_BEGIN__",
     "__A72_P30E_REARM_PRETRIGGER_BEGIN__", 1),
    ("__A72_PHYSICAL_REPAIR_PRETRIGGER_END__",
     "__A72_P30E_REARM_PRETRIGGER_END__", 1),
    ("__A72_PHYSICAL_REPAIR_LATE_PROFILE_BEGIN__",
     "__A72_P30E_REARM_LATE_PROFILE_BEGIN__", 1),
    ("__A72_PHYSICAL_REPAIR_LATE_PROFILE_END__",
     "__A72_P30E_REARM_LATE_PROFILE_END__", 1),
    ("exact-repaired-identity-ready-pristine-physical-contract",
     "exact-p30e-rearm-identity-ready-pristine-physical-contract", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E-rearm pre-trigger derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_p30e_rearm_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items()
                  if not key.startswith("__")})


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
