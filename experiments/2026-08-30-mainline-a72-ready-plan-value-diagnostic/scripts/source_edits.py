#!/usr/bin/env python3
"""Apply the exact post-0438 Gemini READY-plan value observer."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/mt6797_psci.c")
PARENT_SHA256 = "a850c6b5d40dbee5a6ec083a88ec3d3b66cf4f33fbb006484d1ffdab26d2e7ac"

OLD = r'''static int __init
mt6797_a72_validate_cap_plan(const struct arm64_late_cpu_plan *plan)
{
	int ret;

	ret = mt6797_a72_validate_cap_plan_contract(plan);
#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	if (ret)
		pr_info("A72_READY_PLAN_DIAG_V1 ret=%d plan=%#llx evidence=%#llx\n",
			ret,
			(unsigned long long)
			mt6797_a72_plan_validation_diagnostic(plan),
			(unsigned long long)
			mt6797_a72_evidence_diag(plan ? &plan->evidence : NULL));
#endif
	return ret;
}'''

NEW = r'''static int __init
mt6797_a72_validate_cap_plan(const struct arm64_late_cpu_plan *plan)
{
	int ret;

	ret = mt6797_a72_validate_cap_plan_contract(plan);
#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	if (ret) {
		pr_info("A72_READY_PLAN_DIAG_V1 ret=%d plan=%#llx evidence=%#llx\n",
			ret,
			(unsigned long long)
			mt6797_a72_plan_validation_diagnostic(plan),
			(unsigned long long)
			mt6797_a72_evidence_diag(plan ? &plan->evidence : NULL));
		if (plan)
			pr_info("A72_READY_PLAN_VALUES_V1 %u %*pb %*pb %*pb %*pb %*pb %u %u\n",
				ARM64_NCAPS,
				ARM64_NCAPS, plan->early_local_caps,
				ARM64_NCAPS, plan->target_local_caps,
				ARM64_NCAPS, plan->required_local_caps,
				ARM64_NCAPS, plan->target[0].local_caps,
				ARM64_NCAPS, plan->target[1].local_caps,
				plan->evidence.target_policy[0].smccc_conduit,
				plan->evidence.target_policy[1].smccc_conduit);
	}
#endif
	return ret;
}'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise SystemExit("target source is missing or unsafe")
    if sha256(path) != PARENT_SHA256:
        raise SystemExit("parent mt6797_psci.c changed")
    text = path.read_text(encoding="utf-8")
    if text.count(OLD) != 1 or "A72_READY_PLAN_VALUES_V1" in text:
        raise SystemExit("value-observer source anchor changed")
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
