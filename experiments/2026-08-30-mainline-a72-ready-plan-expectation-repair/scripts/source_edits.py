#!/usr/bin/env python3
"""Apply the exact post-0439 Gemini READY-plan expectation repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/mt6797_psci.c")
PARENT_SHA256 = "08f3be5c1de1a5d60a7179baa684ca1812e0dab7fba34a4ba0f0a253f4928939"

PRESENT_OLD = r'''static const u16 mt6797_a72_present_caps[] __initconst = {
	ARM64_HAS_AMU_EXTN,
	ARM64_HW_DBM,
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};'''

PRESENT_NEW = r'''static const u16 mt6797_a72_present_caps[] __initconst = {
	ARM64_HAS_AMU_EXTN,
	ARM64_HW_DBM,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};'''

EARLY_OLD = r'''static const u16 mt6797_a72_early_caps[] __initconst = {
	ARM64_HAS_AMU_EXTN,
	ARM64_HW_DBM,
};'''

EARLY_NEW = r'''static const u16 mt6797_a72_early_caps[] __initconst = {
	ARM64_HAS_AMU_EXTN,
	ARM64_HW_DBM,
	ARM64_WORKAROUND_845719,
};'''

REQUIRED_OLD = r'''static const u16 mt6797_a72_required_caps[] __initconst = {
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};'''

REQUIRED_NEW = r'''static const u16 mt6797_a72_required_caps[] __initconst = {
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};'''

POLICY_OLD = r'''static bool __init
mt6797_a72_policy_evidence_exact(const struct arm64_late_cpu_target_policy_evidence *policy)
{
	return policy->valid == ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK &&
	       policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_SMC &&
	       !policy->mitigations_off && !policy->nospectre_v2 &&
	       policy->spectre_v4_policy == ARM64_LATE_CPU_V4_POLICY_DYNAMIC;
}'''

POLICY_NEW = r'''static bool __init
mt6797_a72_policy_evidence_exact(const struct arm64_late_cpu_target_policy_evidence *policy)
{
	return policy->valid == ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK &&
	       policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_NONE &&
	       !policy->mitigations_off && !policy->nospectre_v2 &&
	       policy->spectre_v4_policy == ARM64_LATE_CPU_V4_POLICY_DYNAMIC;
}'''

DIAG_OLD = "\t\tif (policy->smccc_conduit != ARM64_LATE_CPU_SMCCC_SMC)"
DIAG_NEW = "\t\tif (policy->smccc_conduit != ARM64_LATE_CPU_SMCCC_NONE)"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise SystemExit("target source is missing or unsafe")
    if sha256(path) != PARENT_SHA256:
        raise SystemExit("parent mt6797_psci.c changed")
    text = path.read_text(encoding="utf-8")
    replacements = (
        (PRESENT_OLD, PRESENT_NEW, "present capability contract"),
        (EARLY_OLD, EARLY_NEW, "early capability contract"),
        (REQUIRED_OLD, REQUIRED_NEW, "required capability contract"),
        (POLICY_OLD, POLICY_NEW, "production policy contract"),
        (DIAG_OLD, DIAG_NEW, "production policy diagnostic"),
    )
    for old, new, label in replacements:
        if text.count(old) != 1:
            raise SystemExit(f"{label} anchor changed")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
