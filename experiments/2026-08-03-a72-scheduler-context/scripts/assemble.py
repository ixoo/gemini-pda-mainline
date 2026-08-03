#!/usr/bin/env python3
"""Assemble corrected pair-v7 with the pinned pair-v6 Android-v0 contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "9938defe0e4b83d0845135c4a27b534f5d28fafa5eac4bbe345f7badf2405094"
KERNEL_FIELD_SHA256 = "f3b021cc8036a2b3ac205a16a6ff135dbeb70210cda27c639b1543b7a385449e"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-cpu9-parallel-disjoint-load"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned pair-v6 Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("parallel_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned pair-v6 assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
