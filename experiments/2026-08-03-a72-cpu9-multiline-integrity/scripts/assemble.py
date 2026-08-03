#!/usr/bin/env python3
"""Assemble the multiline-integrity kernel with the pinned pair-v4 contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "2121b03995070321e49293d7e895433dab7a530de095b760d359910e5598252b"
KERNEL_FIELD_SHA256 = "81f076198ae314d187790beecee8d9b5edda3c4432e51a0f36a22dbe326fc468"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-cpu9-bounded-coherency"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned pair-v4 Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("coherence_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned pair-v4 assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
