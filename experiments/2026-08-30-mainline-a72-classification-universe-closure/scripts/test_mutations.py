#!/usr/bin/env python3
"""Reject decision-changing mutations of the classified universe."""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

import source_edits
import validate_source


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor changed: {old}")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve() / source_edits.TARGET
    text = source.read_text(encoding="utf-8")
    cap = "\tARM64_MISMATCHED_CACHE_TYPE,\n"
    present = "static const u16 mt6797_a72_present_caps[] __initconst = {\n\tARM64_HAS_AMU_EXTN,\n"
    required = "static const u16 mt6797_a72_required_caps[] __initconst = {\n"
    mutations = (
        (source_edits.ABSENT_NEW, source_edits.ABSENT_OLD),
        (source_edits.ABSENT_NEW,
         source_edits.ABSENT_NEW.replace(cap, cap + cap, 1)),
        (present, present.replace("\tARM64_HAS_AMU_EXTN,\n",
                                  cap + "\tARM64_HAS_AMU_EXTN,\n", 1)),
        (required, required + cap),
    )
    rejected = 0
    for old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="a72-classified-mutation-") as name:
            root = Path(name)
            target = root / source_edits.TARGET
            target.parent.mkdir(parents=True)
            target.write_text(replace_once(text, old, new), encoding="utf-8")
            try:
                validate_source.validate(root)
            except validate_source.ValidationError:
                rejected += 1
            else:
                raise SystemExit("unsafe classified-universe mutation accepted")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
