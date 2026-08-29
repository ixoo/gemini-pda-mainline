#!/usr/bin/env python3
"""Assemble the pmsg-witness child with the pinned Android-v0 contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "ed7d52e4bb5f6137c587b446171dfd3fafc8f78fa70e59dacd19b251c7ca5701"
KERNEL_FIELD_SHA256 = "b056043221ba934dc970eb7f22a8444a05aba4a58a25ba66412f7d12735c54e7"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-28-a72-target-register-capsule"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned target-register Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("target_register_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned target-register assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
