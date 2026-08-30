#!/usr/bin/env python3
"""Apply the exact post-0436 Gemini plan-validator repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/mt6797_psci.c")
PARENT_SHA256 = "da53972143bd303b7759dc39593e3cd6f7d0e8b3d52e21832150970b3f266d49"

OLD = r'''static bool __init
mt6797_a72_evidence_is_bound_expectation(const struct arm64_late_cpu_evidence *evidence)
{
	const u64 allowed_blockers = ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |
		ARM64_LATE_CPU_BLOCK_CONFIGURATION |
		ARM64_LATE_CPU_BLOCK_TOPOLOGY;
	unsigned int target;

	if (evidence->abi != ARM64_LATE_CPU_PLAN_ABI ||
	    memcmp(evidence->source_parent_identity,
		   mt6797_a72_source_parent_identity,
		   sizeof(evidence->source_parent_identity)) ||
	    memcmp(evidence->config_input_identity,
		   mt6797_a72_config_input_identity,
		   sizeof(evidence->config_input_identity)) ||
	    memcmp(&evidence->expected_pair, &mt6797_a72_expected_pair,
		   sizeof(evidence->expected_pair)) ||
	    !mt6797_a72_binding_is_runtime(&evidence->binding) ||
	    !(evidence->blocker_mask &
	      ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS) ||
	    evidence->blocker_mask & ~allowed_blockers ||
'''

NEW = r'''static bool __init
mt6797_a72_evidence_is_bound_expectation(const struct arm64_late_cpu_evidence *evidence)
{
	const u64 allowed_blockers = ARM64_LATE_CPU_BLOCK_CONFIGURATION |
		ARM64_LATE_CPU_BLOCK_TOPOLOGY;
	unsigned int target;

	if (evidence->abi != ARM64_LATE_CPU_PLAN_ABI ||
	    memcmp(evidence->source_parent_identity,
		   mt6797_a72_source_parent_identity,
		   sizeof(evidence->source_parent_identity)) ||
	    memcmp(evidence->config_input_identity,
		   mt6797_a72_config_input_identity,
		   sizeof(evidence->config_input_identity)) ||
	    memcmp(&evidence->expected_pair, &mt6797_a72_expected_pair,
		   sizeof(evidence->expected_pair)) ||
	    !mt6797_a72_binding_is_runtime(&evidence->binding) ||
	    evidence->blocker_mask & ~allowed_blockers ||
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"parent source absent or unsafe: {TARGET}")
    if sha256(path) != PARENT_SHA256:
        raise RuntimeError(f"parent source changed: {sha256(path)}")
    text = path.read_text(encoding="utf-8")
    if text.count(OLD) != 1 or NEW in text:
        raise RuntimeError("stale-validator edit anchor changed")
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit("source_edits.py is imported by the generator")
