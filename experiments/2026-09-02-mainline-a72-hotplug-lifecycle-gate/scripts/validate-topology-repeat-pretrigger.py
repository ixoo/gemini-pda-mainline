#!/usr/bin/env python3
"""Fail closed unless the topology-repeat candidate is ready and pristine."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "9dabf111ee86cf45edcd6bb47ea086ca0db885c00bba8967af9c52d7223291b7"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/"
    "scripts/validate-stage-binding-fix-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source stage-binding-fix pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("c84aea47c6dc4a9745687536b3a99c4e434af5826b10a5a83bae3f8171a81271",
     "6ba8c9538dcff6559066088da943d96aaa8ad32d10a93b34c8bbeddc97464f75", 1),
    ("__A72_STAGE_BINDING_FIX_PRETRIGGER_BEGIN__",
     "__A72_TOPOLOGY_REPEAT_PRETRIGGER_BEGIN__", 1),
    ("__A72_STAGE_BINDING_FIX_PRETRIGGER_END__",
     "__A72_TOPOLOGY_REPEAT_PRETRIGGER_END__", 1),
    ("__A72_STAGE_BINDING_FIX_LATE_PROFILE_BEGIN__",
     "__A72_TOPOLOGY_REPEAT_LATE_PROFILE_BEGIN__", 1),
    ("__A72_STAGE_BINDING_FIX_LATE_PROFILE_END__",
     "__A72_TOPOLOGY_REPEAT_LATE_PROFILE_END__", 1),
    ("exact-stage-binding-fix-identity-ready-pristine-physical-contract",
     "exact-topology-repeat-identity-ready-pristine-physical-contract", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology-repeat pre-trigger derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_topology_repeat_pretrigger",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items()
                  if not key.startswith("__")})


if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
