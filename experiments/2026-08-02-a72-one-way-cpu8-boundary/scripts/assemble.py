#!/usr/bin/env python3
"""Assemble one-way CPU8 kernel with the pinned Gemian boot contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3"
KERNEL_FIELD_SHA256 = "e65a74cf5445a9e22a537b760e566a5a21d3d314e81689dd01c52bd11e7c6676"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-02-gemian-a72-bounded-observer-boot"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned parent Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("bounded_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned parent assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
