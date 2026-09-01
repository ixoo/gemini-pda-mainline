#!/usr/bin/env python3
"""Source-pin the provenance composer to the CPU9 production package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "a7971af3bd1c7cf5f619a5a985703f38031e800cd54cf359b189341d80ad4f9f"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/build-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("d3197c6870aa025840f6dc330e83e7871e78cce56e4b314e03085d7879c6954f",
     "347274878f91d872cef6e20892b79303bb035e1b56fea7743c86ce06a6ba6475", 1),
    ("05a3e54a412e02bc224138056552451b706111d2d98d6e1363597efeecada93d",
     "8bb4eeb23948610f0de04032e6610d9ecfb74a15eb5f8d6c5fa4d2718188cadb", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2",
     "603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b", 1),
    ("provenance-serviceability-composed-dtb",
     "cpu9-controller-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 DT derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_composed_dtb_builder"}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
