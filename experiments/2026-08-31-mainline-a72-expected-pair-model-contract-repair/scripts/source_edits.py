#!/usr/bin/env python3
"""Apply the generic late-CPU expected-pair model-contract repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/late_cpu_profile.c")
PARENT_SHA256 = "16ed56a3cc805001640f7c34ae43f1908061d68ef85bad6cde7d3773a85350e3"
OLD = (
    "\t\t    expected->midr !=\n"
    "\t\t\t    plan->evidence.expected_target_midr[target])"
)
NEW = (
    "\t\t    (expected->midr & MIDR_CPU_MODEL_MASK) !=\n"
    "\t\t\t    plan->evidence.expected_target_midr[target])"
)
EXACT_TARGET_COMPARE = (
    "\tlate_expected_target_compare(pair->midr, info->reg_midr,\n"
    "\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_MIDR, &mismatches,"
)

MIDR_CPU_MODEL_MASK = 0xFF0FFFF0
MIDR_CORTEX_A72 = 0x410FD080
MIDR_CORTEX_A53 = 0x410FD030


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair_matches_model(pair_midr: int, target_model: int) -> bool:
    return (pair_midr & MIDR_CPU_MODEL_MASK) == target_model


def validate_semantics() -> None:
    a72_r0p1 = MIDR_CORTEX_A72 | 0x1
    a72_r15p15 = MIDR_CORTEX_A72 | 0xF0000F
    a53_r0p1 = MIDR_CORTEX_A53 | 0x1
    if not pair_matches_model(a72_r0p1, MIDR_CORTEX_A72):
        raise SystemExit("A72 r0p1 model contract failed")
    if not pair_matches_model(a72_r15p15, MIDR_CORTEX_A72):
        raise SystemExit("A72 other-revision model contract failed")
    if pair_matches_model(a53_r0p1, MIDR_CORTEX_A72):
        raise SystemExit("different CPU model was accepted")
    if pair_matches_model(a72_r0p1, a72_r0p1):
        raise SystemExit("revision-bearing target model was accepted")


def validate_parent(text: str) -> None:
    if text.count(OLD) != 1 or text.count(NEW) != 0:
        raise SystemExit("expected-pair completeness parent changed")
    if text.count(EXACT_TARGET_COMPARE) != 1:
        raise SystemExit("exact late-target MIDR comparison changed")
    validate_semantics()


def validate_result(text: str) -> None:
    if text.count(OLD) != 0 or text.count(NEW) != 1:
        raise SystemExit("expected-pair model comparison changed")
    if text.count(EXACT_TARGET_COMPARE) != 1:
        raise SystemExit("exact late-target MIDR comparison changed")
    if text.count("MIDR_CPU_MODEL_MASK") != 1:
        raise SystemExit("unexpected model-mask use in late CPU profile")
    validate_semantics()


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise SystemExit("target source is missing or unsafe")
    actual = sha256(path)
    if actual != PARENT_SHA256:
        raise SystemExit(f"parent late_cpu_profile.c changed: {actual}")
    text = path.read_text(encoding="utf-8")
    validate_parent(text)
    result = text.replace(OLD, NEW, 1)
    validate_result(result)
    path.write_text(result, encoding="utf-8")
