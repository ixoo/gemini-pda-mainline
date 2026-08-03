#!/usr/bin/env python3
"""Assemble the terminal-attribution kernel with the pinned window contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "f6d36d5eeafe92936fb8c18bddf34eed92f28dd1b602989fb196e83206812885"
KERNEL_FIELD_SHA256 = "a55de5dab85a36ace77fddf6e0adf198627b587be6f68e45d47584a896de3a1e"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-cpu9-retention-window"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned retention-window Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("window_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned retention-window assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
