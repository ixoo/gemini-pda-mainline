#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the configuration-identity repair build."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "1b1dbddd17dea232bdc9296b3f8faea4ffc4b031061253ac72b5bdc6bbcd2d6f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("347274878f91d872cef6e20892b79303bb035e1b56fea7743c86ce06a6ba6475",
     "afb849a4a5dc9011f5a24dad2ae22d2bae1bda1963fa2c7681e86377125c1712", 1),
    ("8bb4eeb23948610f0de04032e6610d9ecfb74a15eb5f8d6c5fa4d2718188cadb",
     "228f762c3beacad56cd8e2ec8e595fdf79927d5786c5e54b473c251e93376e5e", 1),
    ("603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b",
     "ca7e95162c9e222d47991f6580682354cbb445d994a954950455ca5e6b9c80c3", 1),
    ("cpu9-controller-composed-dtb",
     "cpu9-config-identity-repair-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repaired CPU9 DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_repair_dtb_builder"}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
