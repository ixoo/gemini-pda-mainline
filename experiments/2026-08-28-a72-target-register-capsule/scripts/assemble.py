#!/usr/bin/env python3
"""Assemble the register-capsule child with the pinned Android-v0 contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "0605ef23fce46a376b779b77c3085d6ff1ef9695b6c4bff14dba67668b21ee9e"
KERNEL_FIELD_SHA256 = "de81aa06953bf1f6a24a97c88f10f1406f6af0b100f0b3f7b34674240eeefdfa"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-scheduler-context"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned scheduler Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("scheduler_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned scheduler assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
