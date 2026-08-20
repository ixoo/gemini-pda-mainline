#!/usr/bin/env python3
"""Run the source-pinned classifier with corrected legacy-oracle accounting."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "9e29a770a0047d02d3a82dbce4c523f613b4232942642a3ab1f64a502e031c16"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


source = Path(__file__).resolve().parents[2] / (
    "2026-08-19-mainline-da921x-same-value-write-implementation/"
    "scripts/classify-runtime.py"
)
require(source.is_file() and not source.is_symlink(), "source classifier is unsafe")
require(hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256,
        "source classifier identity changed")
text = source.read_text(encoding="utf-8")
old = '("oracle_other_transfers", "0"), ("oracle_other_address_transfers", "0"),'
new = ('("oracle_other_transfers", str(writes)), '
       '("oracle_other_address_transfers", "0"),')
require(text.count(old) == 1, "source oracle accounting site changed")
text = text.replace(old, new)
namespace = {"__name__": "__main__", "__file__": str(source)}
exec(compile(text, str(source), "exec"), namespace)
