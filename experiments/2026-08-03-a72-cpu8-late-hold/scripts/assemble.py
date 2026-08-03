#!/usr/bin/env python3
"""Assemble the late-hold CPU8 kernel with the pinned Gemian boot contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "c53c40898a25b1b4a0ddeaab310d7e8cb84e08bb4ba9edd8f0e05129fceaeccf"
KERNEL_FIELD_SHA256 = "9827c9c8c66501a913e38c255aa8a15e6eaf784f3e7c57d032d76809e80710cf"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-02-a72-cpu8-held-online"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned held-online Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("held_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned held-online assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
