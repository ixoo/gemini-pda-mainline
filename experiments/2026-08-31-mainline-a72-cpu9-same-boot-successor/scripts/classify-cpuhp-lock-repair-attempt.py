#!/usr/bin/env python3
"""Classify one CPU9 CPUHP lock-repair runtime attempt."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "453ee0a46804d4d5c797037fbf6b1093eca0cb925785bcbe778a8048748158ec"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-progress-raw-lane-attempt.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress raw-lane attempt classifier changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4",
     "09bdca67375272870ce27e325368d86967a104f224dcd61bc7c38848f8f9370d", 1),
    ("validate-progress-raw-lane-pretrigger.py",
     "validate-cpuhp-lock-repair-pretrigger.py", 1),
    ("CPU9 progress raw-lane repair",
     "CPU9 CPUHP lock repair", 1),
    ("cpu9_progress_raw_lane_pretrigger",
     "cpu9_cpuhp_lock_repair_pretrigger", 1),
    ("CPU9-progress-raw-lane-failure-shape-changed",
     "CPU9-CPUHP-lock-repair-failure-shape-changed", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPUHP lock-repair classifier derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpuhp_lock_repair_attempt_classifier",
}
exec(compile(text, str(SOURCE), "exec"), namespace)

if __name__ == "__main__":
    raise SystemExit(namespace["progress"].main())
