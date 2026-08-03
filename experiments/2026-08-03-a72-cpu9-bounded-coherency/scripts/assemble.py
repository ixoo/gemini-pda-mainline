#!/usr/bin/env python3
"""Assemble the bounded-coherency kernel with the pinned terminal contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "ed11b681d25ccd0c902226f04ecd3435b3dc85233adcc3274885ec08491f8145"
KERNEL_FIELD_SHA256 = "04602bc2cf61c8ca1232457eba608e347c29eebda7ce6c2d811004051748e604"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-cpu9-terminal-attribution"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned terminal Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("terminal_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned terminal assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
