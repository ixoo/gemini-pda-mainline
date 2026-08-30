#!/usr/bin/env python3
"""Deterministic source edits for the named-device expectation activation."""

from __future__ import annotations

import hashlib
from pathlib import Path


PROFILE = "arch/arm64/kernel/mt6797_psci.c"
PARENT_HASHES = {
    PROFILE: "0c1fe8775c154c18ce54ef178d19f488a5a0840cfe73cd128b28a7d988d66e9c",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"edit anchor count changed for {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"parent source absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"parent source changed: {relative}: {actual} != {expected}")


OLD_BLOCKERS = r'''#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
#define MT6797_A72_EFFECT_BLOCKER	0
#else
#define MT6797_A72_EFFECT_BLOCKER	ARM64_LATE_CPU_BLOCK_EFFECT_PLAN
#endif

#define MT6797_A72_PROFILE_BLOCKERS					\
	(ARM64_LATE_CPU_BLOCK_CONFIGURATION |				\
	 ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY |			\
	 ARM64_LATE_CPU_BLOCK_FIRMWARE_WA1 |				\
	 ARM64_LATE_CPU_BLOCK_FIRMWARE_WA2 |				\
	 ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3 |				\
	 ARM64_LATE_CPU_BLOCK_ID_REGISTERS |				\
	 ARM64_LATE_CPU_BLOCK_CACHE_TYPE |				\
	 ARM64_LATE_CPU_BLOCK_ASID |					\
	 ARM64_LATE_CPU_BLOCK_GRANULE |				\
	 ARM64_LATE_CPU_BLOCK_VA_MODE |				\
	 ARM64_LATE_CPU_BLOCK_GIC |					\
	 ARM64_LATE_CPU_BLOCK_HWCAP |					\
	 ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |			\
	 MT6797_A72_EFFECT_BLOCKER |					\
	 ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING |			\
	 ARM64_LATE_CPU_BLOCK_COMMIT_PATH)
'''


NEW_BLOCKERS = r'''#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
#define MT6797_A72_PROFILE_BLOCKERS					\
	(ARM64_LATE_CPU_BLOCK_CONFIGURATION |				\
	 ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY |			\
	 ARM64_LATE_CPU_BLOCK_FIRMWARE_WA1 |				\
	 ARM64_LATE_CPU_BLOCK_FIRMWARE_WA2 |				\
	 ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3 |				\
	 ARM64_LATE_CPU_BLOCK_ID_REGISTERS |				\
	 ARM64_LATE_CPU_BLOCK_CACHE_TYPE |				\
	 ARM64_LATE_CPU_BLOCK_ASID |					\
	 ARM64_LATE_CPU_BLOCK_GRANULE |				\
	 ARM64_LATE_CPU_BLOCK_VA_MODE |				\
	 ARM64_LATE_CPU_BLOCK_GIC |					\
	 ARM64_LATE_CPU_BLOCK_HWCAP |					\
	 ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |			\
	 ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING |			\
	 ARM64_LATE_CPU_BLOCK_COMMIT_PATH)
#else
/* Slices 1-8 own every gate except final verification and READY. */
#define MT6797_A72_PROFILE_BLOCKERS					\
	(ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |			\
	 ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)
#endif
'''


EXPECTED_PAIR = r'''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
/* Prior-cycle Gemian capsule stream; never a current-boot observation. */
static const struct arm64_late_cpu_expected_pair mt6797_a72_expected_pair __initconst = {
	.abi = ARM64_LATE_CPU_EXPECTED_PAIR_ABI,
	.target_count = ARM64_LATE_CPU_MAX_TARGETS,
	.valid = ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK,
	.source_identity = {
		0x04bd7f060613719e, 0x7836415f9dfbbc19,
		0xdc1d97ee847eb811, 0xf765c5e8a01667cc,
	},
	.capsule_identity = {
		0xe35596c52bc8b40b, 0x600c5e2d6733661d,
	},
	.mpidr = { 0x200, 0x201 },
	.midr = MIDR_CORTEX_A72,
	.revidr = 0,
	.cntfrq = 0x00c65d40,
	.ctr = 0x8444c004,
	.dczid = 0x00000004,
	.clidr_el1 = 0x000000000a200023,
	.id_aa64dfr0 = 0x0000000010305106,
	.id_aa64isar0 = 0x0000000000011120,
	.id_aa64isar1 = 0x0000000000000000,
	.id_aa64mmfr0 = 0x0000000000001124,
	.id_aa64mmfr1 = 0x0000000000000000,
	.id_aa64pfr0 = 0x0000000001002222,
	.id_aa64pfr1 = 0x0000000000000000,
	.id_isar0 = 0x02101110,
	.id_isar1 = 0x13112111,
	.id_isar2 = 0x21232042,
	.id_isar3 = 0x01112131,
	.id_isar4 = 0x00011142,
	.id_isar5 = 0x00011121,
	.id_mmfr0 = 0x10201105,
	.id_mmfr1 = 0x40000000,
	.id_mmfr2 = 0x01260000,
	.id_mmfr3 = 0x02102211,
	.id_pfr0 = 0x00000131,
	.id_pfr1 = 0x10011011,
};
#endif

'''


OLD_CONFIG_END = r'''static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
	0x699f14786e1d64eb, 0x3811f0b6c481c31d,
	0x9e0e77fc96b64eb4, 0xd12ebbbfde3b23b0,
};
#endif

'''


ACTIVE_CAPS_OLD = r'''static const u16 mt6797_a72_present_caps[] __initconst = {
	ARM64_HAS_AMU_EXTN,
	ARM64_HW_DBM,
#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
#endif
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};
'''


ACTIVE_CAPS_NEW = r'''static const u16 mt6797_a72_present_caps[] __initconst = {
	ARM64_HAS_AMU_EXTN,
	ARM64_HW_DBM,
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};
'''


UNRESOLVED_CAPS = r'''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
static const u16 mt6797_a72_unresolved_caps[] __initconst = {
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
};
#endif

'''


REQUIRED_CAPS_OLD = r'''static const u16 mt6797_a72_required_caps[] __initconst = {
#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
#endif
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};
'''


REQUIRED_CAPS_NEW = r'''static const u16 mt6797_a72_required_caps[] __initconst = {
	ARM64_MISMATCHED_CACHE_TYPE,
	ARM64_SPECTRE_V2,
	ARM64_SPECTRE_V4,
	ARM64_SPECTRE_BHB,
	ARM64_WORKAROUND_1742098,
	ARM64_WORKAROUND_SPECULATIVE_AT,
};
'''


TARGET_POLICY_EMPTY = r'''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
static bool __init
mt6797_a72_target_policy_empty(
	const struct arm64_late_cpu_target_policy_evidence *policy)
{
	return !policy->valid && !policy->smccc_conduit &&
	       !policy->mitigations_off &&
	       !policy->nospectre_v2 &&
	       !policy->spectre_v4_policy;
}
#endif

'''


OLD_EXPECTED_ONLY = r'''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
static bool __init
mt6797_a72_binding_empty(const struct arm64_late_cpu_runtime_binding *binding)
{
	return !binding->valid && !binding->origin &&
	       mt6797_a72_identity_empty(binding->expected_config_identity) &&
	       mt6797_a72_identity_empty(binding->running_config_identity) &&
	       mt6797_a72_identity_empty(binding->expected_build_id_identity) &&
	       mt6797_a72_identity_empty(binding->running_build_id_identity) &&
	       mt6797_a72_identity_empty(binding->expected_cmdline_identity) &&
	       mt6797_a72_identity_empty(binding->running_cmdline_identity);
}

static bool __init
mt6797_a72_binding_is_runtime(const struct arm64_late_cpu_runtime_binding *binding)
{
	return binding->valid == ARM64_LATE_CPU_BIND_VALID_MASK &&
	       binding->origin == ARM64_LATE_CPU_BINDING_RUNTIME &&
	       !mt6797_a72_identity_empty(binding->expected_config_identity) &&
	       !mt6797_a72_identity_empty(binding->running_config_identity) &&
	       !mt6797_a72_identity_empty(binding->expected_build_id_identity) &&
	       !mt6797_a72_identity_empty(binding->running_build_id_identity) &&
	       !mt6797_a72_identity_empty(binding->expected_cmdline_identity) &&
	       !mt6797_a72_identity_empty(binding->running_cmdline_identity) &&
	       !memcmp(binding->expected_config_identity,
		       binding->running_config_identity,
		       sizeof(binding->expected_config_identity)) &&
	       !memcmp(binding->expected_build_id_identity,
		       binding->running_build_id_identity,
		       sizeof(binding->expected_build_id_identity)) &&
	       !memcmp(binding->expected_cmdline_identity,
		       binding->running_cmdline_identity,
		       sizeof(binding->expected_cmdline_identity));
}

static bool __init
mt6797_a72_evidence_is_expected_only(const struct arm64_late_cpu_evidence *evidence)
{
	u64 required_blockers = MT6797_A72_PROFILE_BLOCKERS;
	bool runtime_bound;
	unsigned int i;

	runtime_bound = mt6797_a72_binding_is_runtime(&evidence->binding);
	if (runtime_bound)
		required_blockers &= ~ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING;

	if (evidence->abi != ARM64_LATE_CPU_PLAN_ABI ||
	    memcmp(evidence->source_parent_identity,
		   mt6797_a72_source_parent_identity,
		   sizeof(evidence->source_parent_identity)) ||
	    memcmp(evidence->config_input_identity,
		   mt6797_a72_config_input_identity,
		   sizeof(evidence->config_input_identity)) ||
	    (evidence->blocker_mask & required_blockers) !=
		    required_blockers ||
	    evidence->blocker_mask &
		    ~(required_blockers |
		      ARM64_LATE_CPU_BLOCK_TOPOLOGY) ||
	    evidence->expected_target_mpidr[0] != 0x200 ||
	    evidence->expected_target_mpidr[1] != 0x201 ||
	    evidence->expected_target_midr[0] != MIDR_CORTEX_A72 ||
	    evidence->expected_target_midr[1] != MIDR_CORTEX_A72 ||
	    evidence->target_cpu[0] != 8 || evidence->target_cpu[1] != 9 ||
	    (!runtime_bound &&
	     !mt6797_a72_binding_empty(&evidence->binding)))
		return false;

	for (i = 0; i < ARM64_LATE_CPU_MAX_TARGETS; i++)
		if (evidence->observed_target_mpidr[i] ||
		    evidence->observed_target_midr[i] ||
		    evidence->observed_target_revidr[i] ||
		    evidence->target_cap[i].valid ||
		    !mt6797_a72_target_policy_empty(&evidence->target_policy[i]))
			return false;
	if (!mt6797_a72_identity_empty(evidence->evidence_identity))
		return false;

	return !evidence->system_cap.valid;
}
#endif
'''


NEW_EXPECTED_ONLY = r'''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
static bool __init
mt6797_a72_binding_is_runtime(const struct arm64_late_cpu_runtime_binding *binding)
{
	return binding->valid == ARM64_LATE_CPU_BIND_VALID_MASK &&
	       binding->origin == ARM64_LATE_CPU_BINDING_RUNTIME &&
	       !mt6797_a72_identity_empty(binding->expected_config_identity) &&
	       !mt6797_a72_identity_empty(binding->running_config_identity) &&
	       !mt6797_a72_identity_empty(binding->expected_build_id_identity) &&
	       !mt6797_a72_identity_empty(binding->running_build_id_identity) &&
	       !mt6797_a72_identity_empty(binding->expected_cmdline_identity) &&
	       !mt6797_a72_identity_empty(binding->running_cmdline_identity) &&
	       !memcmp(binding->expected_config_identity,
		       binding->running_config_identity,
		       sizeof(binding->expected_config_identity)) &&
	       !memcmp(binding->expected_build_id_identity,
		       binding->running_build_id_identity,
		       sizeof(binding->expected_build_id_identity)) &&
	       !memcmp(binding->expected_cmdline_identity,
		       binding->running_cmdline_identity,
		       sizeof(binding->expected_cmdline_identity));
}

static bool __init
mt6797_a72_system_evidence_exact(const struct arm64_late_cpu_system_cap_evidence *system)
{
	return system->valid == ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK &&
	       system->ctr_strict_mask == ~GENMASK_ULL(15, 14) &&
	       !(system->ctr_sys_val & ~GENMASK_ULL(31, 0)) &&
	       system->ctr_sys_val & BIT(31) && !system->ssbs &&
	       system->spectre_v2_state ==
		       ARM64_LATE_CPU_MITIGATION_UNAFFECTED &&
	       system->spectre_v4_state ==
		       ARM64_LATE_CPU_MITIGATION_UNAFFECTED &&
	       system->bhb_state == ARM64_LATE_CPU_BHB_STATE_UNAFFECTED &&
	       !system->bhb_matcher_loop_count && !system->bhb_system_method &&
	       !system->gicv5_legacy && !system->ich_hcr_tdir;
}

static bool __init
mt6797_a72_policy_evidence_exact(const struct arm64_late_cpu_target_policy_evidence *policy)
{
	return policy->valid == ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK &&
	       policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_SMC &&
	       !policy->mitigations_off && !policy->nospectre_v2 &&
	       policy->spectre_v4_policy == ARM64_LATE_CPU_V4_POLICY_DYNAMIC;
}

static bool __init
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
	    evidence->expected_target_mpidr[0] != 0x200 ||
	    evidence->expected_target_mpidr[1] != 0x201 ||
	    evidence->expected_target_midr[0] != MIDR_CORTEX_A72 ||
	    evidence->expected_target_midr[1] != MIDR_CORTEX_A72 ||
	    evidence->target_cpu[0] != 8 || evidence->target_cpu[1] != 9 ||
	    !mt6797_a72_system_evidence_exact(&evidence->system_cap) ||
	    !mt6797_a72_identity_empty(evidence->evidence_identity))
		return false;

	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		if (evidence->observed_target_mpidr[target] ||
		    evidence->observed_target_midr[target] ||
		    evidence->observed_target_revidr[target] ||
		    memchr_inv(&evidence->target_cap[target], 0,
			       sizeof(evidence->target_cap[target])) ||
		    !mt6797_a72_policy_evidence_exact(&evidence->target_policy[target]))
			return false;

	return !memcmp(&evidence->target_policy[0],
		       &evidence->target_policy[1],
		       sizeof(evidence->target_policy[0]));
}
#endif
'''


PRODUCTION_VALIDATE_OLD = r'''#else
	if (plan->local_caps_planned || plan->effects_planned ||
	    plan->hwcaps_planned ||
	    !mt6797_a72_evidence_is_expected_only(&plan->evidence) ||
	    !mt6797_a72_effects_empty(&plan->effects) ||
	    memchr_inv(plan->expected_elf_hwcap, 0,
		       sizeof(plan->expected_elf_hwcap)) ||
	    plan->expected_compat_hwcap || plan->expected_compat_hwcap2)
		return -EINVAL;
#endif
'''


PRODUCTION_VALIDATE_NEW = r'''#else
	if (!plan->local_caps_planned || !plan->effects_planned ||
	    !plan->hwcaps_planned ||
	    !mt6797_a72_evidence_is_bound_expectation(&plan->evidence) ||
	    mt6797_a72_effects_empty(&plan->effects) ||
	    !memchr_inv(plan->expected_elf_hwcap, 0,
			    sizeof(plan->expected_elf_hwcap)))
		return -EINVAL;
#endif
'''


UNRESOLVED_LOOPS = r'''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
		for (i = 0; i < ARRAY_SIZE(mt6797_a72_unresolved_caps); i++)
			if (test_bit(mt6797_a72_unresolved_caps[i],
				     plan->target[target].classified_local_caps) ||
			    test_bit(mt6797_a72_unresolved_caps[i],
				     plan->target[target].local_caps))
				return -EINVAL;
#endif
'''


UNRESOLVED_GLOBAL = r'''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	for (i = 0; i < ARRAY_SIZE(mt6797_a72_unresolved_caps); i++)
		if (test_bit(mt6797_a72_unresolved_caps[i],
			     plan->classified_local_caps) ||
		    test_bit(mt6797_a72_unresolved_caps[i],
			     plan->target_local_caps))
			return -EINVAL;
#endif
'''


RETURN_OLD = r'''#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	return 0;
#else
	return -EAGAIN;
#endif
'''


PREPARE_ANCHOR = r'''	evidence->expected_target_midr[0] = MIDR_CORTEX_A72;
	evidence->expected_target_midr[1] = MIDR_CORTEX_A72;
	evidence->blocker_mask = MT6797_A72_PROFILE_BLOCKERS;
'''


PREPARE_ACTIVE = r'''	evidence->expected_target_midr[0] = MIDR_CORTEX_A72;
	evidence->expected_target_midr[1] = MIDR_CORTEX_A72;
#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	evidence->expected_pair = mt6797_a72_expected_pair;
#endif
	evidence->blocker_mask = MT6797_A72_PROFILE_BLOCKERS;
'''


def apply(root: Path) -> None:
    validate_parent(root)
    profile = root / PROFILE
    replace_once(profile, OLD_BLOCKERS, NEW_BLOCKERS)
    replace_once(profile, OLD_CONFIG_END, OLD_CONFIG_END + EXPECTED_PAIR)
    replace_once(profile, ACTIVE_CAPS_OLD, ACTIVE_CAPS_NEW)
    replace_once(profile, UNRESOLVED_CAPS, "")
    replace_once(profile, REQUIRED_CAPS_OLD, REQUIRED_CAPS_NEW)
    replace_once(profile, TARGET_POLICY_EMPTY, "")
    replace_once(profile, OLD_EXPECTED_ONLY, NEW_EXPECTED_ONLY)
    replace_once(profile, PRODUCTION_VALIDATE_OLD, PRODUCTION_VALIDATE_NEW)
    replace_once(profile, UNRESOLVED_LOOPS, "")
    replace_once(profile, UNRESOLVED_GLOBAL, "")
    replace_once(profile, RETURN_OLD, "\treturn 0;\n")
    replace_once(profile, PREPARE_ANCHOR, PREPARE_ACTIVE)
