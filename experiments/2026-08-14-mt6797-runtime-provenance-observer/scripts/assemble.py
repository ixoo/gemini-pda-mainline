#!/usr/bin/env python3
"""Assemble the full-vendor provenance observer with the pinned LK contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3"
KERNEL_FIELD_SHA256 = "d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-02-gemian-a72-bounded-observer-boot"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("pinned_lk_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned Android-v0 assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
