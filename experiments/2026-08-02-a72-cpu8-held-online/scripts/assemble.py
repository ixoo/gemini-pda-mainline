#!/usr/bin/env python3
"""Assemble the held-online CPU8 kernel with the pinned Gemian boot contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "2c6e59da67357c946f1ce6e4300fadaf732add0e124f25ba84aefe2a222bbb4b"
KERNEL_FIELD_SHA256 = "9158af17b17e483ec68257378e5c4bd923b254e7242b5ba338f1324eec5f960b"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-02-a72-one-way-cpu8-boundary"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned one-way Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("one_way_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned one-way assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
