#!/usr/bin/env python3
"""Classify one CPU9 CPU_ON progress runtime attempt."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "12f93c321bae4f0e37649ea79e484dcd2ffd838c817c580ff4d6be826f921ef8"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-cpuhp-lock-repair-attempt.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPUHP lock-repair attempt classifier changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("09bdca67375272870ce27e325368d86967a104f224dcd61bc7c38848f8f9370d",
     "bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645", 1),
    ("validate-cpuhp-lock-repair-pretrigger.py",
     "validate-cpu-on-progress-pretrigger.py", 1),
    ("CPU9 CPUHP lock repair",
     "CPU9 CPU_ON progress", 1),
    ("cpu9_cpuhp_lock_repair_pretrigger",
     "cpu9_cpu_on_progress_pretrigger", 1),
    ("CPU9-CPUHP-lock-repair-failure-shape-changed",
     "CPU9-CPU-ON-progress-failure-shape-changed", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress classifier derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpu_on_progress_attempt_classifier",
}
exec(compile(text, str(SOURCE), "exec"), namespace)

if __name__ == "__main__":
    raise SystemExit(namespace["progress"].main())
