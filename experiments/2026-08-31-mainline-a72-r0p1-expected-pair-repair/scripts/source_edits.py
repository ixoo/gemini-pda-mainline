#!/usr/bin/env python3
"""Apply the exact Gemini A72 r0p1 expected-pair repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/mt6797_psci.c")
PARENT_SHA256 = "db06b8ad0f8552c908c4f29f7cda4a86745efceea27e0d8a15cd68dfe93c7265"
OLD = "\t.midr = MIDR_CORTEX_A72,"
NEW = "\t.midr = MIDR_CORTEX_A72 | MIDR_CPU_VAR_REV(0, 1),"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_parent(text: str) -> None:
    if text.count(OLD) != 1:
        raise SystemExit("expected-pair MIDR parent anchor changed")
    if text.count(NEW) != 0:
        raise SystemExit("r0p1 expected-pair repair is already present")
    for token in (
        "evidence->expected_target_midr[0] = MIDR_CORTEX_A72;",
        "evidence->expected_target_midr[1] = MIDR_CORTEX_A72;",
        "target_cap->registers.midr = MIDR_CORTEX_A72;",
    ):
        if text.count(token) != 1:
            raise SystemExit(f"revision-neutral model anchor changed: {token}")


def validate_result(text: str) -> None:
    if text.count(OLD) != 0 or text.count(NEW) != 1:
        raise SystemExit("exact r0p1 expected-pair initializer changed")
    for token in (
        "evidence->expected_target_midr[0] = MIDR_CORTEX_A72;",
        "evidence->expected_target_midr[1] = MIDR_CORTEX_A72;",
        "target_cap->registers.midr = MIDR_CORTEX_A72;",
    ):
        if text.count(token) != 1:
            raise SystemExit(f"revision-neutral model check changed: {token}")


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise SystemExit("target source is missing or unsafe")
    actual = sha256(path)
    if actual != PARENT_SHA256:
        raise SystemExit(f"parent mt6797_psci.c changed: {actual}")
    text = path.read_text(encoding="utf-8")
    validate_parent(text)
    result = text.replace(OLD, NEW, 1)
    validate_result(result)
    path.write_text(result, encoding="utf-8")
