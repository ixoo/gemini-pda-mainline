#!/usr/bin/env python3
"""Assemble pair-v6 with the pinned pair-v5 Android-v0 contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "a7e14b94947aca21038668463b307bbcf59304d55e329e6d7278b4ae2778ea1d"
KERNEL_FIELD_SHA256 = "8bbbc62e997c7140f2648d5da2d825622ef19cb0eba94684218ab4d049a96e0a"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-cpu9-multiline-integrity"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned pair-v5 Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("multiline_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned pair-v5 assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
