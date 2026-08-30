#!/usr/bin/env python3
"""Apply the exact post-0440 classified-universe closure."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/mt6797_psci.c")
PARENT_SHA256 = "3179b9f3ddebe7d244fda8d77259a12288c0695e236482e9eee5eb428493c922"
ABSENT_OLD = r'''static const u16 mt6797_a72_absent_caps[] __initconst = {
	ARM64_HAS_GICV5_LEGACY,'''
ABSENT_NEW = r'''static const u16 mt6797_a72_absent_caps[] __initconst = {
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_HAS_GICV5_LEGACY,'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise SystemExit("target source is missing or unsafe")
    if sha256(path) != PARENT_SHA256:
        raise SystemExit("post-0440 mt6797_psci.c changed")
    text = path.read_text(encoding="utf-8")
    if text.count(ABSENT_OLD) != 1:
        raise SystemExit("absent capability anchor changed")
    path.write_text(text.replace(ABSENT_OLD, ABSENT_NEW, 1), encoding="utf-8")
