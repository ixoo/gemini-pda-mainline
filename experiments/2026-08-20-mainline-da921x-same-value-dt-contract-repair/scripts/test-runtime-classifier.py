#!/usr/bin/env python3
"""Run source-pinned classifier tests with write-aware oracle fixtures."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "c13aef4ff7cd940dd76a59245a332fda7af44ee8e22d4fa54f15d349f2cde1a0"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


wrapper = Path(__file__).resolve()
source = wrapper.parents[2] / (
    "2026-08-19-mainline-da921x-same-value-write-implementation/"
    "scripts/test-runtime-classifier.py"
)
require(source.is_file() and not source.is_symlink(), "source classifier test is unsafe")
require(hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256,
        "source classifier test identity changed")
text = source.read_text(encoding="utf-8")
replacements = (
    ('"oracle_other_transfers=0 oracle_other_address_transfers=0"),',
     'f"oracle_other_transfers={writes} oracle_other_address_transfers=0"),', 1),
    ('("reset-failure", "transaction_reset_failures=0", "transaction_reset_failures=1"),',
     '("oracle-write-class", "oracle_other_transfers=1", "oracle_other_transfers=0"),\n'
     '            ("reset-failure", "transaction_reset_failures=0", '
     '"transaction_reset_failures=1"),', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    require(actual == count,
            f"unsafe classifier-test derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
namespace = {"__name__": "__main__", "__file__": str(wrapper)}
exec(compile(text, str(source), "exec"), namespace)
