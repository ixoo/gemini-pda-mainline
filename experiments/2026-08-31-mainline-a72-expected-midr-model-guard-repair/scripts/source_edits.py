#!/usr/bin/env python3
"""Apply the exact Cortex-A72 expected-policy model-guard repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/proton-pack.c")
PARENT_SHA256 = "414038771febf064a4574ad587d51b4d075c495cc906a7f5b846a20ddf2173dc"
OLD = "\t       expected->midr == MIDR_CORTEX_A72;"
NEW = (
    "\t       (expected->midr & MIDR_CPU_MODEL_MASK) == "
    "MIDR_CORTEX_A72;"
)
EXISTING_TARGET_GUARD = (
    "\t       (target->registers.midr & MIDR_CPU_MODEL_MASK) ==\n"
    "\t\t       MIDR_CORTEX_A72 &&"
)

MIDR_CPU_MODEL_MASK = 0xFF0FFFF0
MIDR_CORTEX_A72 = 0x410FD080
MIDR_CORTEX_A53 = 0x410FD030


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_matches(midr: int, model: int) -> bool:
    return (midr & MIDR_CPU_MODEL_MASK) == model


def validate_model_semantics() -> None:
    a72_r0p1 = MIDR_CORTEX_A72 | 0x1
    a72_r15p15 = MIDR_CORTEX_A72 | 0xF0000F
    a53_r0p1 = MIDR_CORTEX_A53 | 0x1
    if a72_r0p1 == MIDR_CORTEX_A72:
        raise SystemExit("r0p1 fixture does not distinguish literal equality")
    if not model_matches(a72_r0p1, MIDR_CORTEX_A72):
        raise SystemExit("A72 r0p1 model match failed")
    if not model_matches(a72_r15p15, MIDR_CORTEX_A72):
        raise SystemExit("A72 all-revision model match failed")
    if model_matches(a53_r0p1, MIDR_CORTEX_A72):
        raise SystemExit("different CPU model was accepted")


def validate_parent(text: str) -> None:
    if text.count(OLD) != 1 or text.count(NEW) != 0:
        raise SystemExit("expected-policy parent guard changed")
    if text.count(EXISTING_TARGET_GUARD) != 1:
        raise SystemExit("existing target-evidence model guard changed")
    if text.count("late_cpu_expected_field_valid(") != 7:
        raise SystemExit("expected-field call graph changed")
    validate_model_semantics()


def validate_result(text: str) -> None:
    if text.count(OLD) != 0 or text.count(NEW) != 1:
        raise SystemExit("expected-policy model guard changed")
    if text.count(EXISTING_TARGET_GUARD) != 1:
        raise SystemExit("target-evidence model guard changed")
    if text.count("MIDR_CPU_MODEL_MASK") != 4:
        raise SystemExit("model-mask use count changed")
    if text.count("late_cpu_expected_field_valid(") != 7:
        raise SystemExit("expected-field call graph changed")
    validate_model_semantics()


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise SystemExit("target source is missing or unsafe")
    actual = sha256(path)
    if actual != PARENT_SHA256:
        raise SystemExit(f"parent proton-pack.c changed: {actual}")
    text = path.read_text(encoding="utf-8")
    validate_parent(text)
    result = text.replace(OLD, NEW, 1)
    validate_result(result)
    path.write_text(result, encoding="utf-8")
