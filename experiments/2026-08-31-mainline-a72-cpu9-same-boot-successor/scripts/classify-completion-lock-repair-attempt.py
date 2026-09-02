#!/usr/bin/env python3
"""Classify one CPU9 completion-path lock-repair runtime attempt."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "5a866a7bd782e8518f6980aa0dd7ff14c266cdf42d2c3b8a50ec6a21ba7c8853"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-membership-lock-repair-attempt.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source membership-lock attempt classifier changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88",
     "d86e78db5996f96b0e11efebd044454719ca8f0a6636671e72a405e1047499aa", 1),
    ("validate-membership-lock-repair-pretrigger.py",
     "validate-completion-lock-repair-pretrigger.py", 1),
    ("CPU9 membership-lock repair", "CPU9 completion-lock repair", 1),
    ("CPU9-membership-lock-repair-failure-shape-changed",
     "CPU9-completion-lock-repair-failure-shape-changed", 1),
    ("cpu9_membership_lock_repair_attempt_classifier",
     "cpu9_completion_lock_repair_attempt_classifier", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock classifier derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_completion_lock_repair_attempt_classifier",
}
exec(compile(text, str(SOURCE), "exec"), namespace)

if __name__ == "__main__":
    raise SystemExit(
        namespace["namespace"]["namespace"]["namespace"]["progress"].main()
    )
