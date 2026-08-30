#!/usr/bin/env python3
"""Apply the exact post-0437 Gemini READY-plan predicate diagnostic."""

from __future__ import annotations

import hashlib
from pathlib import Path


TARGET = Path("arch/arm64/kernel/mt6797_psci.c")
PARENT_SHA256 = "bfa1f825a9a835a07b26403ef4c8944f728a931204957edc554c80068ff116f2"

EVIDENCE_ANCHOR = r'''static bool __init
mt6797_a72_evidence_is_bound_expectation(const struct arm64_late_cpu_evidence *evidence)
'''

EVIDENCE_DIAGNOSTIC = r'''enum mt6797_a72_evidence_diag_bit {
	A72_EVD_ABI = 0,
	A72_EVD_PARENT,
	A72_EVD_CONFIG,
	A72_EVD_PAIR,
	A72_EVD_BINDING,
	A72_EVD_BLOCKERS,
	A72_EVD_EXPECTED_MPIDR,
	A72_EVD_EXPECTED_MIDR,
	A72_EVD_TARGET_CPU,
	A72_EVD_SYSTEM_VALID,
	A72_EVD_CTR_MASK,
	A72_EVD_CTR_WIDTH,
	A72_EVD_CTR_RES1,
	A72_EVD_SSBS,
	A72_EVD_SPECTRE_V2,
	A72_EVD_SPECTRE_V4,
	A72_EVD_BHB_STATE,
	A72_EVD_BHB_DETAIL,
	A72_EVD_GIC_POLICY,
	A72_EVD_IDENTITY,
	A72_EVD_OBSERVED_MPIDR,
	A72_EVD_OBSERVED_MIDR,
	A72_EVD_OBSERVED_REVIDR,
	A72_EVD_TARGET_CAP,
	A72_EVD_POLICY_VALID,
	A72_EVD_POLICY_CONDUIT,
	A72_EVD_POLICY_FLAGS,
	A72_EVD_POLICY_V4,
	A72_EVD_POLICY_PAIR,
};

static u64 __init
mt6797_a72_evidence_diag(const struct arm64_late_cpu_evidence *evidence)
{
	const u64 allowed_blockers = ARM64_LATE_CPU_BLOCK_CONFIGURATION |
		ARM64_LATE_CPU_BLOCK_TOPOLOGY;
	const struct arm64_late_cpu_target_policy_evidence *policy;
	u64 mask = 0;
	unsigned int target;

	if (!evidence)
		return BIT_ULL(63);
	if (evidence->abi != ARM64_LATE_CPU_PLAN_ABI)
		mask |= BIT_ULL(A72_EVD_ABI);
	if (memcmp(evidence->source_parent_identity,
		   mt6797_a72_source_parent_identity,
		   sizeof(evidence->source_parent_identity)))
		mask |= BIT_ULL(A72_EVD_PARENT);
	if (memcmp(evidence->config_input_identity,
		   mt6797_a72_config_input_identity,
		   sizeof(evidence->config_input_identity)))
		mask |= BIT_ULL(A72_EVD_CONFIG);
	if (memcmp(&evidence->expected_pair, &mt6797_a72_expected_pair,
		   sizeof(evidence->expected_pair)))
		mask |= BIT_ULL(A72_EVD_PAIR);
	if (!mt6797_a72_binding_is_runtime(&evidence->binding))
		mask |= BIT_ULL(A72_EVD_BINDING);
	if (evidence->blocker_mask & ~allowed_blockers)
		mask |= BIT_ULL(A72_EVD_BLOCKERS);
	if (evidence->expected_target_mpidr[0] != 0x200 ||
	    evidence->expected_target_mpidr[1] != 0x201)
		mask |= BIT_ULL(A72_EVD_EXPECTED_MPIDR);
	if (evidence->expected_target_midr[0] != MIDR_CORTEX_A72 ||
	    evidence->expected_target_midr[1] != MIDR_CORTEX_A72)
		mask |= BIT_ULL(A72_EVD_EXPECTED_MIDR);
	if (evidence->target_cpu[0] != 8 || evidence->target_cpu[1] != 9)
		mask |= BIT_ULL(A72_EVD_TARGET_CPU);
	if (evidence->system_cap.valid != ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK)
		mask |= BIT_ULL(A72_EVD_SYSTEM_VALID);
	if (evidence->system_cap.ctr_strict_mask != ~GENMASK_ULL(15, 14))
		mask |= BIT_ULL(A72_EVD_CTR_MASK);
	if (evidence->system_cap.ctr_sys_val & ~GENMASK_ULL(31, 0))
		mask |= BIT_ULL(A72_EVD_CTR_WIDTH);
	if (!(evidence->system_cap.ctr_sys_val & BIT(31)))
		mask |= BIT_ULL(A72_EVD_CTR_RES1);
	if (evidence->system_cap.ssbs)
		mask |= BIT_ULL(A72_EVD_SSBS);
	if (evidence->system_cap.spectre_v2_state !=
	    ARM64_LATE_CPU_MITIGATION_UNAFFECTED)
		mask |= BIT_ULL(A72_EVD_SPECTRE_V2);
	if (evidence->system_cap.spectre_v4_state !=
	    ARM64_LATE_CPU_MITIGATION_UNAFFECTED)
		mask |= BIT_ULL(A72_EVD_SPECTRE_V4);
	if (evidence->system_cap.bhb_state !=
	    ARM64_LATE_CPU_BHB_STATE_UNAFFECTED)
		mask |= BIT_ULL(A72_EVD_BHB_STATE);
	if (evidence->system_cap.bhb_matcher_loop_count ||
	    evidence->system_cap.bhb_system_method)
		mask |= BIT_ULL(A72_EVD_BHB_DETAIL);
	if (evidence->system_cap.gicv5_legacy ||
	    evidence->system_cap.ich_hcr_tdir)
		mask |= BIT_ULL(A72_EVD_GIC_POLICY);
	if (!mt6797_a72_identity_empty(evidence->evidence_identity))
		mask |= BIT_ULL(A72_EVD_IDENTITY);

	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {
		if (evidence->observed_target_mpidr[target])
			mask |= BIT_ULL(A72_EVD_OBSERVED_MPIDR);
		if (evidence->observed_target_midr[target])
			mask |= BIT_ULL(A72_EVD_OBSERVED_MIDR);
		if (evidence->observed_target_revidr[target])
			mask |= BIT_ULL(A72_EVD_OBSERVED_REVIDR);
		if (memchr_inv(&evidence->target_cap[target], 0,
			       sizeof(evidence->target_cap[target])))
			mask |= BIT_ULL(A72_EVD_TARGET_CAP);
		policy = &evidence->target_policy[target];
		if (policy->valid != ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK)
			mask |= BIT_ULL(A72_EVD_POLICY_VALID);
		if (policy->smccc_conduit != ARM64_LATE_CPU_SMCCC_SMC)
			mask |= BIT_ULL(A72_EVD_POLICY_CONDUIT);
		if (policy->mitigations_off || policy->nospectre_v2)
			mask |= BIT_ULL(A72_EVD_POLICY_FLAGS);
		if (policy->spectre_v4_policy !=
		    ARM64_LATE_CPU_V4_POLICY_DYNAMIC)
			mask |= BIT_ULL(A72_EVD_POLICY_V4);
	}
	if (memcmp(&evidence->target_policy[0], &evidence->target_policy[1],
		   sizeof(evidence->target_policy[0])))
		mask |= BIT_ULL(A72_EVD_POLICY_PAIR);

	return mask;
}

'''

EVIDENCE_END = r'''	return !memcmp(&evidence->target_policy[0],
		       &evidence->target_policy[1],
		       sizeof(evidence->target_policy[0]));
}
#endif
'''

PLAN_DIAGNOSTIC = r'''	return !memcmp(&evidence->target_policy[0],
		       &evidence->target_policy[1],
		       sizeof(evidence->target_policy[0]));
}

enum mt6797_a72_plan_diag_bit {
	A72_PVD_NULL = 0,
	A72_PVD_ABI,
	A72_PVD_PROFILE,
	A72_PVD_TARGET_WEIGHT,
	A72_PVD_CPU8,
	A72_PVD_CPU9,
	A72_PVD_COMPILED_CAPS,
	A72_PVD_EARLY_CAPS,
	A72_PVD_TARGET_CAPS,
	A72_PVD_REQUIRED_CAPS,
	A72_PVD_CONFLICT_CAPS,
	A72_PVD_CLASSIFIED_WEIGHT,
	A72_PVD_LOCAL_PLANNED,
	A72_PVD_EFFECTS_PLANNED,
	A72_PVD_HWCAPS_PLANNED,
	A72_PVD_EVIDENCE,
	A72_PVD_EFFECTS_EMPTY,
	A72_PVD_HWCAP_EMPTY,
	A72_PVD_TARGET_CLASSIFIED_WEIGHT,
	A72_PVD_TARGET_LOCAL_EXACT,
	A72_PVD_TARGET_SUBSET,
	A72_PVD_TARGET_PRESENT_CAP,
	A72_PVD_TARGET_ABSENT_CLASSIFIED,
	A72_PVD_TARGET_ABSENT_PRESENT,
	A72_PVD_GLOBAL_PRESENT_CAP,
	A72_PVD_GLOBAL_ABSENT_CLASSIFIED,
	A72_PVD_IDENTITY,
};

static u64 __init
mt6797_a72_plan_validation_diagnostic(const struct arm64_late_cpu_plan *plan)
{
	u64 mask = 0;
	unsigned int target;
	unsigned int i;

	if (!plan)
		return BIT_ULL(A72_PVD_NULL);
	if (plan->abi != ARM64_LATE_CPU_PLAN_ABI)
		mask |= BIT_ULL(A72_PVD_ABI);
	if (strcmp(plan->profile_id, "mt6797-a53-a72-a41-v7"))
		mask |= BIT_ULL(A72_PVD_PROFILE);
	if (cpumask_weight(&plan->target_cpus) != 2)
		mask |= BIT_ULL(A72_PVD_TARGET_WEIGHT);
	if (!cpumask_test_cpu(8, &plan->target_cpus))
		mask |= BIT_ULL(A72_PVD_CPU8);
	if (!cpumask_test_cpu(9, &plan->target_cpus))
		mask |= BIT_ULL(A72_PVD_CPU9);
	if (!mt6797_a72_bitmap_exact(plan->compiled_local_caps,
				     mt6797_a72_compiled_caps,
				     ARRAY_SIZE(mt6797_a72_compiled_caps)))
		mask |= BIT_ULL(A72_PVD_COMPILED_CAPS);
	if (!mt6797_a72_bitmap_exact(plan->early_local_caps,
				     mt6797_a72_early_caps,
				     ARRAY_SIZE(mt6797_a72_early_caps)))
		mask |= BIT_ULL(A72_PVD_EARLY_CAPS);
	if (!mt6797_a72_bitmap_exact(plan->target_local_caps,
				     mt6797_a72_present_caps,
				     ARRAY_SIZE(mt6797_a72_present_caps)))
		mask |= BIT_ULL(A72_PVD_TARGET_CAPS);
	if (!mt6797_a72_bitmap_exact(plan->required_local_caps,
				     mt6797_a72_required_caps,
				     ARRAY_SIZE(mt6797_a72_required_caps)))
		mask |= BIT_ULL(A72_PVD_REQUIRED_CAPS);
	if (!bitmap_empty(plan->conflicting_local_caps, ARM64_NCAPS))
		mask |= BIT_ULL(A72_PVD_CONFLICT_CAPS);
	if (bitmap_weight(plan->classified_local_caps, ARM64_NCAPS) !=
	    ARRAY_SIZE(mt6797_a72_present_caps) +
	    ARRAY_SIZE(mt6797_a72_absent_caps))
		mask |= BIT_ULL(A72_PVD_CLASSIFIED_WEIGHT);
	if (!plan->local_caps_planned)
		mask |= BIT_ULL(A72_PVD_LOCAL_PLANNED);
	if (!plan->effects_planned)
		mask |= BIT_ULL(A72_PVD_EFFECTS_PLANNED);
	if (!plan->hwcaps_planned)
		mask |= BIT_ULL(A72_PVD_HWCAPS_PLANNED);
	if (!mt6797_a72_evidence_is_bound_expectation(&plan->evidence))
		mask |= BIT_ULL(A72_PVD_EVIDENCE);
	if (mt6797_a72_effects_empty(&plan->effects))
		mask |= BIT_ULL(A72_PVD_EFFECTS_EMPTY);
	if (!memchr_inv(plan->expected_elf_hwcap, 0,
			    sizeof(plan->expected_elf_hwcap)))
		mask |= BIT_ULL(A72_PVD_HWCAP_EMPTY);

	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {
		if (bitmap_weight(plan->target[target].classified_local_caps,
				  ARM64_NCAPS) !=
		    ARRAY_SIZE(mt6797_a72_present_caps) +
		    ARRAY_SIZE(mt6797_a72_absent_caps))
			mask |= BIT_ULL(A72_PVD_TARGET_CLASSIFIED_WEIGHT);
		if (!mt6797_a72_bitmap_exact(plan->target[target].local_caps,
			    mt6797_a72_present_caps,
			    ARRAY_SIZE(mt6797_a72_present_caps)))
			mask |= BIT_ULL(A72_PVD_TARGET_LOCAL_EXACT);
		if (!bitmap_subset(plan->target[target].local_caps,
				   plan->target[target].classified_local_caps,
				   ARM64_NCAPS))
			mask |= BIT_ULL(A72_PVD_TARGET_SUBSET);
		for (i = 0; i < ARRAY_SIZE(mt6797_a72_present_caps); i++)
			if (!test_bit(mt6797_a72_present_caps[i],
				      plan->target[target].local_caps))
				mask |= BIT_ULL(A72_PVD_TARGET_PRESENT_CAP);
		for (i = 0; i < ARRAY_SIZE(mt6797_a72_absent_caps); i++) {
			if (!test_bit(mt6797_a72_absent_caps[i],
				      plan->target[target].classified_local_caps))
				mask |= BIT_ULL(A72_PVD_TARGET_ABSENT_CLASSIFIED);
			if (test_bit(mt6797_a72_absent_caps[i],
				     plan->target[target].local_caps))
				mask |= BIT_ULL(A72_PVD_TARGET_ABSENT_PRESENT);
		}
	}
	for (i = 0; i < ARRAY_SIZE(mt6797_a72_present_caps); i++)
		if (!test_bit(mt6797_a72_present_caps[i],
			      plan->classified_local_caps))
			mask |= BIT_ULL(A72_PVD_GLOBAL_PRESENT_CAP);
	for (i = 0; i < ARRAY_SIZE(mt6797_a72_absent_caps); i++)
		if (!test_bit(mt6797_a72_absent_caps[i],
			      plan->classified_local_caps))
			mask |= BIT_ULL(A72_PVD_GLOBAL_ABSENT_CLASSIFIED);
	for (i = 0; i < ARRAY_SIZE(plan->identity); i++)
		if (plan->identity[i])
			mask |= BIT_ULL(A72_PVD_IDENTITY);

	return mask;
}
#endif
'''

CONTRACT_OLD = r'''static int __init
mt6797_a72_validate_cap_plan(const struct arm64_late_cpu_plan *plan)
'''
CONTRACT_NEW = r'''static int __init
mt6797_a72_validate_cap_plan_contract(const struct arm64_late_cpu_plan *plan)
'''

WRAPPER_ANCHOR = r'''	/* The core owns canonical identities after this pure validation. */
	return 0;
}

static bool __init mt6797_a72_profile_config_gates_match(void)
'''

WRAPPER = r'''	/* The core owns canonical identities after this pure validation. */
	return 0;
}

static int __init
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
}

static bool __init mt6797_a72_profile_config_gates_match(void)
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1 or new in text:
        raise RuntimeError(f"diagnostic edit anchor changed: {label}")
    return text.replace(old, new, 1)


def apply(root: Path) -> None:
    path = root / TARGET
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"parent source absent or unsafe: {TARGET}")
    if sha256(path) != PARENT_SHA256:
        raise RuntimeError(f"parent source changed: {sha256(path)}")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text, EVIDENCE_ANCHOR, EVIDENCE_DIAGNOSTIC + EVIDENCE_ANCHOR,
        "evidence diagnostic",
    )
    text = replace_once(text, EVIDENCE_END, PLAN_DIAGNOSTIC, "plan diagnostic")
    text = replace_once(text, CONTRACT_OLD, CONTRACT_NEW, "contract rename")
    text = replace_once(text, WRAPPER_ANCHOR, WRAPPER, "return wrapper")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit("source_edits.py is imported by the generator")
