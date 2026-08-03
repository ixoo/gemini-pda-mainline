#!/usr/bin/env python3
"""Assemble the CPU9 kernel with the pinned late-CPU8 boot contract."""

import hashlib
import importlib.util
from pathlib import Path


PARENT_SHA256 = "231f916492bc8477064f792e6bb07ea0d5362b60aa364af44912fb0b205d5ce4"
KERNEL_FIELD_SHA256 = "7a592d62d837fa61b7c57ec2e8be65d4a25203685b4936f2848fc3600563039a"
PARENT = (
    Path(__file__).resolve().parents[2]
    / "2026-08-03-a72-cpu8-late-hold"
    / "scripts"
    / "assemble.py"
)


def main() -> int:
    parent_bytes = PARENT.read_bytes()
    if hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise SystemExit("error: pinned late-CPU8 Android-v0 assembler changed")
    spec = importlib.util.spec_from_file_location("late_assembler", PARENT)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load pinned late-CPU8 assembler")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256
    return assembler.main()


if __name__ == "__main__":
    raise SystemExit(main())
