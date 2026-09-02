#!/usr/bin/env python3
"""Classify one CPU9 membership-begin lock-repair runtime attempt."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "af527d6c8cb515751271842bf71d94a0fd72521484fdcb2ce788aa64c9b30003"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-cpu-on-progress-attempt.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU_ON progress attempt classifier changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645",
     "bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88", 1),
    ("validate-cpu-on-progress-pretrigger.py",
     "validate-membership-lock-repair-pretrigger.py", 1),
    ("CPU9 CPU_ON progress", "CPU9 membership-lock repair", 2),
    ("cpu9_cpu_on_progress_pretrigger",
     "cpu9_membership_lock_repair_pretrigger", 1),
    ("CPU9-CPU-ON-progress-failure-shape-changed",
     "CPU9-membership-lock-repair-failure-shape-changed", 1),
    ("cpu9_cpu_on_progress_attempt_classifier",
     "cpu9_membership_lock_repair_attempt_classifier", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock classifier derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_membership_lock_repair_attempt_classifier",
}
exec(compile(text, str(SOURCE), "exec"), namespace)

if __name__ == "__main__":
    raise SystemExit(namespace["namespace"]["namespace"]["progress"].main())
