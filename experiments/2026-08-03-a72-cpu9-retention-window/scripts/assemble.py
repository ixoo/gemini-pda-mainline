#!/usr/bin/env python3
"""Assemble the retention-window kernel with the pinned CPU9 boot contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "dbd00ee1f2dfbec6eb8c2d48a8e65a1f2ca888a5e6be400e05620cd04a597358"
KERNEL_FIELD_SHA256 = "97def9a894f84e316349fd01ca7a5044b9b786ea385bb34a4badf242a212c7d4"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-cpu9-cluster-reuse"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned CPU9 Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("cpu9_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned CPU9 assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
