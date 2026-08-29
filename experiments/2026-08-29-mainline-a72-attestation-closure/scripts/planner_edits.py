#!/usr/bin/env python3
"""Apply deterministic pure-planner and canonical-identity edits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "af49388af7eac607f095ccd24680923bb020af3296d8d72c253704384378a1d6",
    "arch/arm64/kernel/late_cpu_profile.c":
        "e6684543b46fb4bf3c3e2d3dd82711de860a96bfbefd8aefdf476fcd4cb8662d",
    "arch/arm64/kernel/cpufeature.c":
        "eaa9cd9e9484cc7496eb5bcf70d7ad6a022fa123df26705ef6d88e1fd2bb1a82",
    "arch/arm64/kernel/mt6797_psci.c":
        "04cc165c559066375a667cc928760c0af6459d807fa4f8f13c2de44ffa5de296",
}


HWCAP_PLANNER = r'''#ifdef CONFIG_ARM64_LATE_CPU_PROFILE
static int __init
late_cpu_hwcap_register(const struct arm64_late_cpu_register_image *registers,
			u32 sys_reg, u64 *value)
{
	const struct arm64_late_cpu_aarch32_register_image *aarch32 =
		&registers->aarch32;

	switch (sys_reg) {
	case SYS_ID_AA64DFR0_EL1:
		*value = registers->id_aa64dfr0;
		break;
	case SYS_ID_AA64DFR1_EL1:
		*value = registers->id_aa64dfr1;
		break;
	case SYS_ID_AA64ISAR0_EL1:
		*value = registers->id_aa64isar0;
		break;
	case SYS_ID_AA64ISAR1_EL1:
		*value = registers->id_aa64isar1;
		break;
	case SYS_ID_AA64ISAR2_EL1:
		*value = registers->id_aa64isar2;
		break;
	case SYS_ID_AA64ISAR3_EL1:
		*value = registers->id_aa64isar3;
		break;
	case SYS_ID_AA64MMFR0_EL1:
		*value = registers->id_aa64mmfr0;
		break;
	case SYS_ID_AA64MMFR1_EL1:
		*value = registers->id_aa64mmfr1;
		break;
	case SYS_ID_AA64MMFR2_EL1:
		*value = registers->id_aa64mmfr2;
		break;
	case SYS_ID_AA64MMFR3_EL1:
		*value = registers->id_aa64mmfr3;
		break;
	case SYS_ID_AA64MMFR4_EL1:
		*value = registers->id_aa64mmfr4;
		break;
	case SYS_ID_AA64PFR0_EL1:
		*value = registers->id_aa64pfr0;
		break;
	case SYS_ID_AA64PFR1_EL1:
		*value = registers->id_aa64pfr1;
		break;
	case SYS_ID_AA64PFR2_EL1:
		*value = registers->id_aa64pfr2;
		break;
	case SYS_ID_AA64ZFR0_EL1:
		*value = registers->id_aa64zfr0;
		break;
	case SYS_ID_AA64SMFR0_EL1:
		*value = registers->id_aa64smfr0;
		break;
	case SYS_ID_AA64FPFR0_EL1:
		*value = registers->id_aa64fpfr0;
		break;
	case SYS_ID_ISAR5_EL1:
		*value = aarch32->id_isar5;
		break;
	case SYS_ID_ISAR6_EL1:
		*value = aarch32->id_isar6;
		break;
	case SYS_ID_PFR2_EL1:
		*value = aarch32->id_pfr2;
		break;
	case SYS_MVFR0_EL1:
		*value = aarch32->mvfr0;
		break;
	case SYS_MVFR1_EL1:
		*value = aarch32->mvfr1;
		break;
	default:
		return -ENOENT;
	}

	return 0;
}

static bool __init
late_cpu_hwcap_field_visible(const struct arm64_cpu_capabilities *cap)
{
	const struct arm64_ftr_reg *reg = get_arm64_ftr_reg(cap->sys_reg);

	return reg &&
	       cpuid_feature_extract_unsigned_field_width(reg->user_mask,
						  cap->field_pos,
						  cap->field_width);
}

static bool __init
late_cpu_hwcap_compat_neon(u64 mvfr1)
{
	return cpuid_feature_extract_unsigned_field(mvfr1,
						    MVFR1_EL1_SIMDSP_SHIFT) &&
	       cpuid_feature_extract_unsigned_field(mvfr1,
						    MVFR1_EL1_SIMDInt_SHIFT) &&
	       cpuid_feature_extract_unsigned_field(mvfr1,
						    MVFR1_EL1_SIMDLS_SHIFT);
}

static bool __init
late_cpu_hwcap_match_one(const struct arm64_cpu_capabilities *cap,
			 const struct arm64_late_cpu_register_image *target)
{
	bool sve_match = false;
	bool sme_match = false;
	u64 value;

#ifdef CONFIG_COMPAT
	if (cap->matches == compat_has_neon) {
		if (target) {
			if (late_cpu_hwcap_register(target, SYS_MVFR1_EL1,
						    &value))
				return false;
		} else {
			value = read_sanitised_ftr_reg(SYS_MVFR1_EL1);
		}
		return late_cpu_hwcap_compat_neon(value);
	}
#endif

#ifdef CONFIG_ARM64_SVE
	sve_match = cap->matches == has_sve_feature;
#endif
#ifdef CONFIG_ARM64_SME
	sme_match = cap->matches == has_sme_feature;
#endif

	if (cap->matches != has_user_cpuid_feature &&
	    !sve_match && !sme_match)
		return false;
	if (!late_cpu_hwcap_field_visible(cap))
		return false;
	if (target) {
		if (late_cpu_hwcap_register(target, cap->sys_reg, &value))
			return false;
	} else {
		value = read_sanitised_ftr_reg(cap->sys_reg);
	}

	if (sve_match) {
		u64 pfr0;

		if (target) {
			if (late_cpu_hwcap_register(target, SYS_ID_AA64PFR0_EL1,
						    &pfr0))
				return false;
		} else {
			pfr0 = read_sanitised_ftr_reg(SYS_ID_AA64PFR0_EL1);
		}
		if (!cpuid_feature_extract_unsigned_field(pfr0,
						      ID_AA64PFR0_EL1_SVE_SHIFT))
			return false;
	} else if (sme_match) {
		u64 pfr1;

		if (target) {
			if (late_cpu_hwcap_register(target, SYS_ID_AA64PFR1_EL1,
						    &pfr1))
				return false;
		} else {
			pfr1 = read_sanitised_ftr_reg(SYS_ID_AA64PFR1_EL1);
		}
		if (!cpuid_feature_extract_unsigned_field(pfr1,
						      ID_AA64PFR1_EL1_SME_SHIFT))
			return false;
	}

	return feature_matches(value, cap);
}

static bool __init
late_cpu_hwcap_matches(const struct arm64_cpu_capabilities *cap,
		       const struct arm64_late_cpu_register_image *target)
{
	const struct arm64_cpu_capabilities *match;
	int i;

	if (!cap->match_list)
		return late_cpu_hwcap_match_one(cap, target);
	if (cap->matches != cpucap_multi_entry_cap_matches)
		return false;

	match = cap->match_list;
	for (i = 0; i < ARM64_NCAPS; i++, match++) {
		if (!match->matches)
			return false;
		if (late_cpu_hwcap_match_one(match, target))
			return true;
	}

	return false;
}

static bool __init
late_cpu_hwcap_all_cpus(const struct arm64_cpu_capabilities *cap,
			const struct arm64_late_cpu_plan *plan)
{
	unsigned int target;

	if (!late_cpu_hwcap_matches(cap, NULL))
		return false;
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		if (!late_cpu_hwcap_matches(cap,
			    &plan->evidence.target_cap[target].registers))
			return false;

	return true;
}

static bool __init late_cpu_plan_all_cpus_support_32bit_el0(
	const struct arm64_late_cpu_plan *plan)
{
	unsigned int target;

	if (!system_supports_32bit_el0())
		return false;
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {
		u64 pfr0 = plan->evidence.target_cap[target].registers.id_aa64pfr0;

		if (!id_aa64pfr0_32bit_el0(pfr0))
			return false;
	}

	return true;
}

static bool __init
late_cpu_plan_any_cpu_has_cap(const struct arm64_late_cpu_plan *plan, int cap)
{
	return test_bit(cap, plan->early_local_caps) ||
	       test_bit(cap, plan->target_local_caps);
}

static int __init
late_cpu_plan_hwcap_array(const struct arm64_cpu_capabilities *caps,
			  struct arm64_late_cpu_plan *plan)
{
	for (; caps->matches; caps++) {
		if (!late_cpu_hwcap_all_cpus(caps, plan))
			continue;
		switch (caps->hwcap_type) {
		case CAP_HWCAP:
			if (caps->hwcap >= MAX_CPU_FEATURES)
				return -ERANGE;
			__set_bit(caps->hwcap,
				  (unsigned long *)plan->expected_elf_hwcap);
			break;
#ifdef CONFIG_COMPAT
		case CAP_COMPAT_HWCAP:
			plan->expected_compat_hwcap |= (u32)caps->hwcap;
			break;
		case CAP_COMPAT_HWCAP2:
			plan->expected_compat_hwcap2 |= (u32)caps->hwcap;
			break;
#endif
		default:
			return -EINVAL;
		}
	}

	return 0;
}

int __init arm64_plan_late_cpu_hwcaps(struct arm64_late_cpu_plan *plan)
{
	unsigned int target;
	int ret;

	if (!plan || !plan->local_caps_planned || !plan->effects_planned ||
	    plan->hwcaps_planned ||
	    memchr_inv(plan->expected_elf_hwcap, 0,
		       sizeof(plan->expected_elf_hwcap)) ||
	    plan->expected_compat_hwcap || plan->expected_compat_hwcap2)
		return -EINVAL;
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		if (!(plan->evidence.target_cap[target].valid &
		      ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID))
			return -EAGAIN;

	BUILD_BUG_ON(sizeof(unsigned long) != sizeof(u64));
	__set_bit(KERNEL_HWCAP_CPUID,
		  (unsigned long *)plan->expected_elf_hwcap);
	ret = late_cpu_plan_hwcap_array(arm64_elf_hwcaps, plan);
	if (ret)
		return ret;

#ifdef CONFIG_COMPAT
	if (late_cpu_plan_all_cpus_support_32bit_el0(plan)) {
		plan->expected_compat_hwcap = COMPAT_ELF_HWCAP_DEFAULT;
		ret = late_cpu_plan_hwcap_array(compat_elf_hwcaps, plan);
		if (ret)
			return ret;
		if (plan->effects.compat_aes_clear)
			plan->expected_compat_hwcap2 &= ~COMPAT_HWCAP2_AES;
	}
#endif
	if (late_cpu_plan_any_cpu_has_cap(plan, ARM64_WORKAROUND_2658417)) {
		__clear_bit(KERNEL_HWCAP_BF16,
			    (unsigned long *)plan->expected_elf_hwcap);
		__clear_bit(KERNEL_HWCAP_EBF16,
			    (unsigned long *)plan->expected_elf_hwcap);
	}
	if (late_cpu_plan_any_cpu_has_cap(plan,
				       ARM64_WORKAROUND_SPECULATIVE_SSBS))
		__clear_bit(KERNEL_HWCAP_SSBS,
			    (unsigned long *)plan->expected_elf_hwcap);

	plan->hwcaps_planned = 1;
	return 0;
}
#endif

'''


IDENTITY_FINALIZER = r'''static const u8 late_evidence_identity_domain[] __initconst =
	"gemini-late-cpu-evidence-v1";
static const u8 late_plan_identity_domain[] __initconst =
	"gemini-late-cpu-plan-v1";

static void __init
late_canonical_update_u8(struct sha256_ctx *ctx, u8 value)
{
	sha256_update(ctx, &value, sizeof(value));
}

static void __init
late_canonical_update_u32(struct sha256_ctx *ctx, u32 value)
{
	__be32 encoded = cpu_to_be32(value);

	sha256_update(ctx, (const u8 *)&encoded, sizeof(encoded));
}

static void __init
late_canonical_update_u64(struct sha256_ctx *ctx, u64 value)
{
	__be64 encoded = cpu_to_be64(value);

	sha256_update(ctx, (const u8 *)&encoded, sizeof(encoded));
}

static void __init
late_canonical_update_identity(struct sha256_ctx *ctx,
	const u64 identity[ARM64_LATE_CPU_ID_WORDS])
{
	unsigned int i;

	for (i = 0; i < ARM64_LATE_CPU_ID_WORDS; i++)
		late_canonical_update_u64(ctx, identity[i]);
}

static void __init
late_canonical_digest_identity(struct sha256_ctx *ctx,
			       u64 identity[ARM64_LATE_CPU_ID_WORDS])
{
	u8 digest[SHA256_DIGEST_SIZE];
	unsigned int i;

	sha256_final(ctx, digest);
	for (i = 0; i < ARM64_LATE_CPU_ID_WORDS; i++)
		identity[i] = get_unaligned_be64(digest + i * sizeof(u64));
}

static void __init
late_canonical_update_registers(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_register_image *registers)
{
	const struct arm64_late_cpu_aarch32_register_image *aarch32 =
		&registers->aarch32;

	late_canonical_update_u64(ctx, registers->ctr);
	late_canonical_update_u64(ctx, registers->cntfrq);
	late_canonical_update_u64(ctx, registers->dczid);
	late_canonical_update_u64(ctx, registers->midr);
	late_canonical_update_u64(ctx, registers->revidr);
	late_canonical_update_u64(ctx, registers->aidr);
	late_canonical_update_u64(ctx, registers->gmid);
	late_canonical_update_u64(ctx, registers->smidr);
	late_canonical_update_u64(ctx, registers->mpamidr);
	late_canonical_update_u64(ctx, registers->id_aa64dfr0);
	late_canonical_update_u64(ctx, registers->id_aa64dfr1);
	late_canonical_update_u64(ctx, registers->id_aa64isar0);
	late_canonical_update_u64(ctx, registers->id_aa64isar1);
	late_canonical_update_u64(ctx, registers->id_aa64isar2);
	late_canonical_update_u64(ctx, registers->id_aa64isar3);
	late_canonical_update_u64(ctx, registers->id_aa64mmfr0);
	late_canonical_update_u64(ctx, registers->id_aa64mmfr1);
	late_canonical_update_u64(ctx, registers->id_aa64mmfr2);
	late_canonical_update_u64(ctx, registers->id_aa64mmfr3);
	late_canonical_update_u64(ctx, registers->id_aa64mmfr4);
	late_canonical_update_u64(ctx, registers->id_aa64pfr0);
	late_canonical_update_u64(ctx, registers->id_aa64pfr1);
	late_canonical_update_u64(ctx, registers->id_aa64pfr2);
	late_canonical_update_u64(ctx, registers->id_aa64zfr0);
	late_canonical_update_u64(ctx, registers->id_aa64smfr0);
	late_canonical_update_u64(ctx, registers->id_aa64fpfr0);
	late_canonical_update_u32(ctx, aarch32->id_dfr0);
	late_canonical_update_u32(ctx, aarch32->id_dfr1);
	late_canonical_update_u32(ctx, aarch32->id_isar0);
	late_canonical_update_u32(ctx, aarch32->id_isar1);
	late_canonical_update_u32(ctx, aarch32->id_isar2);
	late_canonical_update_u32(ctx, aarch32->id_isar3);
	late_canonical_update_u32(ctx, aarch32->id_isar4);
	late_canonical_update_u32(ctx, aarch32->id_isar5);
	late_canonical_update_u32(ctx, aarch32->id_isar6);
	late_canonical_update_u32(ctx, aarch32->id_mmfr0);
	late_canonical_update_u32(ctx, aarch32->id_mmfr1);
	late_canonical_update_u32(ctx, aarch32->id_mmfr2);
	late_canonical_update_u32(ctx, aarch32->id_mmfr3);
	late_canonical_update_u32(ctx, aarch32->id_mmfr4);
	late_canonical_update_u32(ctx, aarch32->id_mmfr5);
	late_canonical_update_u32(ctx, aarch32->id_pfr0);
	late_canonical_update_u32(ctx, aarch32->id_pfr1);
	late_canonical_update_u32(ctx, aarch32->id_pfr2);
	late_canonical_update_u32(ctx, aarch32->mvfr0);
	late_canonical_update_u32(ctx, aarch32->mvfr1);
	late_canonical_update_u32(ctx, aarch32->mvfr2);
}

static void __init
late_canonical_update_expected_pair(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_expected_pair *expected)
{
	unsigned int target;

	late_canonical_update_u32(ctx, expected->abi);
	late_canonical_update_u32(ctx, expected->target_count);
	late_canonical_update_u64(ctx, expected->valid);
	late_canonical_update_identity(ctx, expected->source_identity);
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		late_canonical_update_u64(ctx,
					  expected->capsule_identity[target]);
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		late_canonical_update_u64(ctx, expected->mpidr[target]);
	late_canonical_update_u64(ctx, expected->midr);
	late_canonical_update_u64(ctx, expected->revidr);
	late_canonical_update_u64(ctx, expected->cntfrq);
	late_canonical_update_u64(ctx, expected->ctr);
	late_canonical_update_u64(ctx, expected->dczid);
	late_canonical_update_u64(ctx, expected->clidr_el1);
	late_canonical_update_u64(ctx, expected->id_aa64dfr0);
	late_canonical_update_u64(ctx, expected->id_aa64isar0);
	late_canonical_update_u64(ctx, expected->id_aa64isar1);
	late_canonical_update_u64(ctx, expected->id_aa64mmfr0);
	late_canonical_update_u64(ctx, expected->id_aa64mmfr1);
	late_canonical_update_u64(ctx, expected->id_aa64pfr0);
	late_canonical_update_u64(ctx, expected->id_aa64pfr1);
	late_canonical_update_u32(ctx, expected->id_isar0);
	late_canonical_update_u32(ctx, expected->id_isar1);
	late_canonical_update_u32(ctx, expected->id_isar2);
	late_canonical_update_u32(ctx, expected->id_isar3);
	late_canonical_update_u32(ctx, expected->id_isar4);
	late_canonical_update_u32(ctx, expected->id_isar5);
	late_canonical_update_u32(ctx, expected->id_mmfr0);
	late_canonical_update_u32(ctx, expected->id_mmfr1);
	late_canonical_update_u32(ctx, expected->id_mmfr2);
	late_canonical_update_u32(ctx, expected->id_mmfr3);
	late_canonical_update_u32(ctx, expected->id_pfr0);
	late_canonical_update_u32(ctx, expected->id_pfr1);
}

static void __init
late_canonical_update_binding(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_runtime_binding *binding)
{
	late_canonical_update_u32(ctx, binding->valid);
	late_canonical_update_u32(ctx, binding->origin);
	late_canonical_update_identity(ctx,
				       binding->expected_config_identity);
	late_canonical_update_identity(ctx,
				       binding->running_config_identity);
	late_canonical_update_identity(ctx,
				       binding->expected_build_id_identity);
	late_canonical_update_identity(ctx,
				       binding->running_build_id_identity);
	late_canonical_update_identity(ctx,
				       binding->expected_cmdline_identity);
	late_canonical_update_identity(ctx,
				       binding->running_cmdline_identity);
}

static void __init
late_canonical_update_target_cap(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_target_cap_evidence *target)
{
	late_canonical_update_u32(ctx, target->valid);
	late_canonical_update_registers(ctx, &target->registers);
	late_canonical_update_u64(ctx, target->clidr_el1);
	late_canonical_update_u64(ctx, target->ctr_effective);
	late_canonical_update_u64(ctx, target->icc_sre_el1);
	late_canonical_update_u64(ctx, target->icc_idr0_el1);
	late_canonical_update_u64(ctx, target->ich_vtr_el2);
	late_canonical_update_u32(ctx, (u32)target->ich_vtr_status);
	late_canonical_update_u32(ctx, (u32)target->smccc_wa1);
	late_canonical_update_u32(ctx, (u32)target->smccc_wa2);
	late_canonical_update_u32(ctx, (u32)target->smccc_wa3);
	late_canonical_update_u32(ctx, target->asid_bits);
	late_canonical_update_u8(ctx, target->page_shift);
	late_canonical_update_u8(ctx, target->va_bits);
	late_canonical_update_u8(ctx, target->hyp_available);
	late_canonical_update_u8(ctx, target->kernel_in_hyp_mode);
	late_canonical_update_u8(ctx, target->gic_sre_usable);
	late_canonical_update_u8(ctx, target->ich_vtr_source);
}

static void __init
late_canonical_update_target_policy(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_target_policy_evidence *policy)
{
	late_canonical_update_u32(ctx, policy->valid);
	late_canonical_update_u8(ctx, policy->smccc_conduit);
	late_canonical_update_u8(ctx, policy->mitigations_off);
	late_canonical_update_u8(ctx, policy->nospectre_v2);
	late_canonical_update_u8(ctx, policy->spectre_v4_policy);
}

static void __init
late_canonical_update_system_cap(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_system_cap_evidence *system)
{
	late_canonical_update_u32(ctx, system->valid);
	late_canonical_update_u64(ctx, system->ctr_sys_val);
	late_canonical_update_u64(ctx, system->ctr_strict_mask);
	late_canonical_update_u8(ctx, system->ssbs);
	late_canonical_update_u8(ctx, system->spectre_v2_state);
	late_canonical_update_u8(ctx, system->spectre_v4_state);
	late_canonical_update_u8(ctx, system->bhb_state);
	late_canonical_update_u8(ctx, system->bhb_matcher_loop_count);
	late_canonical_update_u8(ctx, system->bhb_system_method);
}

static void __init
late_canonical_hash_evidence(const struct arm64_late_cpu_evidence *evidence,
	u64 identity[ARM64_LATE_CPU_ID_WORDS])
{
	struct sha256_ctx ctx;
	unsigned int target;

	sha256_init(&ctx);
	sha256_update(&ctx, late_evidence_identity_domain,
		      sizeof(late_evidence_identity_domain));
	late_canonical_update_u32(&ctx, evidence->abi);
	late_canonical_update_identity(&ctx,
				       evidence->source_parent_identity);
	late_canonical_update_identity(&ctx,
				       evidence->config_input_identity);
	late_canonical_update_expected_pair(&ctx, &evidence->expected_pair);
	late_canonical_update_binding(&ctx, &evidence->binding);
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {
		late_canonical_update_u32(&ctx, evidence->target_cpu[target]);
		late_canonical_update_u64(&ctx,
			 evidence->expected_target_mpidr[target]);
		late_canonical_update_u64(&ctx,
			 evidence->observed_target_mpidr[target]);
		late_canonical_update_u32(&ctx,
			 evidence->expected_target_midr[target]);
		late_canonical_update_u32(&ctx,
			 evidence->observed_target_midr[target]);
		late_canonical_update_u32(&ctx,
			 evidence->observed_target_revidr[target]);
		late_canonical_update_target_cap(&ctx,
			 &evidence->target_cap[target]);
		late_canonical_update_target_policy(&ctx,
			    &evidence->target_policy[target]);
	}
	late_canonical_update_system_cap(&ctx, &evidence->system_cap);
	/* blocker_mask is a derived admission result, not input evidence. */
	late_canonical_digest_identity(&ctx, identity);
}

static void __init
late_canonical_update_bitmap(struct sha256_ctx *ctx,
			     const unsigned long *bitmap)
{
	unsigned int cap;

	late_canonical_update_u32(ctx, ARM64_NCAPS);
	for (cap = 0; cap < ARM64_NCAPS; cap++)
		late_canonical_update_u8(ctx, test_bit(cap, bitmap));
}

static void __init
late_canonical_update_target_effect(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_target_effect_plan *effect)
{
	late_canonical_update_u32(ctx, effect->valid);
	late_canonical_update_u8(ctx, effect->spectre_v2_state);
	late_canonical_update_u8(ctx, effect->spectre_v2_conduit);
	late_canonical_update_u8(ctx, effect->spectre_v2_callback);
	late_canonical_update_u8(ctx, effect->spectre_v2_hyp_vector);
	late_canonical_update_u8(ctx, effect->spectre_v4_state);
	late_canonical_update_u8(ctx, effect->spectre_v4_method);
	late_canonical_update_u8(ctx, effect->spectre_v4_conduit);
	late_canonical_update_u8(ctx, effect->spectre_v4_policy);
	late_canonical_update_u8(ctx,
				 effect->spectre_v4_callback_required);
	late_canonical_update_u8(ctx, effect->bhb_method);
	late_canonical_update_u8(ctx, effect->bhb_loop_count);
	late_canonical_update_u8(ctx, effect->bhb_matcher_loop_count);
	late_canonical_update_u8(ctx, effect->bhb_conduit);
	late_canonical_update_u8(ctx, effect->bhb_mitigation_state);
	late_canonical_update_u8(ctx, effect->bhb_vector_template);
	late_canonical_update_u8(ctx, effect->bhb_hyp_vector);
	late_canonical_update_u8(ctx, effect->bhb_v2_non_vulnerable);
}

static void __init
late_canonical_update_effects(struct sha256_ctx *ctx,
	const struct arm64_late_cpu_effect_plan *effects)
{
	unsigned int target;

	late_canonical_update_u8(ctx, effects->ctr_mismatch.required);
	late_canonical_update_u8(ctx, effects->ctr_mismatch.target_mask);
	late_canonical_update_u8(ctx, effects->ctr_mismatch.trap_ctr_el0);
	late_canonical_update_u8(ctx, effects->ctr_mismatch.alternative);
	late_canonical_update_u8(ctx, effects->spectre_v2.required);
	late_canonical_update_u8(ctx, effects->spectre_v2.target_mask);
	late_canonical_update_u8(ctx, effects->spectre_v2.mitigation_state);
	late_canonical_update_u8(ctx, effects->spectre_v2.conduit);
	late_canonical_update_u8(ctx, effects->spectre_v2.callback);
	late_canonical_update_u8(ctx, effects->spectre_v2.hyp_vector);
	late_canonical_update_u8(ctx, effects->spectre_v2.alternative);
	late_canonical_update_u8(ctx, effects->spectre_v4.required);
	late_canonical_update_u8(ctx, effects->spectre_v4.target_mask);
	late_canonical_update_u8(ctx, effects->spectre_v4.mitigation_state);
	late_canonical_update_u8(ctx, effects->spectre_v4.method);
	late_canonical_update_u8(ctx, effects->spectre_v4.conduit);
	late_canonical_update_u8(ctx, effects->spectre_v4.policy);
	late_canonical_update_u8(ctx,
				 effects->spectre_v4.callback_required_mask);
	late_canonical_update_u8(ctx,
				 effects->spectre_v4.firmware_alternative);
	late_canonical_update_u8(ctx, effects->bhb.required);
	late_canonical_update_u8(ctx, effects->bhb.target_mask);
	late_canonical_update_u8(ctx, effects->bhb.method);
	late_canonical_update_u8(ctx, effects->bhb.loop_count);
	late_canonical_update_u8(ctx, effects->bhb.matcher_loop_count);
	late_canonical_update_u8(ctx, effects->bhb.conduit);
	late_canonical_update_u8(ctx, effects->bhb.system_method);
	late_canonical_update_u8(ctx, effects->bhb.mitigation_state);
	late_canonical_update_u8(ctx, effects->bhb.vector_template);
	late_canonical_update_u8(ctx, effects->bhb.hyp_vector);
	late_canonical_update_u8(ctx, effects->bhb.alternative);
	late_canonical_update_u8(ctx, effects->bhb.v2_non_vulnerable);
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		late_canonical_update_target_effect(ctx,
					    &effects->target[target]);
	late_canonical_update_u8(ctx, effects->compat_aes_clear);
	late_canonical_update_u8(ctx, effects->speculative_at_finalization);
}

static void __init
late_canonical_hash_plan(const struct arm64_late_cpu_plan *plan,
			 u64 identity[ARM64_LATE_CPU_ID_WORDS])
{
	struct sha256_ctx ctx;
	unsigned int target;
	unsigned int cpu;
	unsigned int i;

	sha256_init(&ctx);
	sha256_update(&ctx, late_plan_identity_domain,
		      sizeof(late_plan_identity_domain));
	late_canonical_update_u32(&ctx, plan->abi);
	late_canonical_update_u32(&ctx, strlen(plan->profile_id));
	sha256_update(&ctx, (const u8 *)plan->profile_id,
		      strlen(plan->profile_id));
	late_canonical_update_u32(&ctx, cpumask_weight(&plan->target_cpus));
	for_each_cpu(cpu, &plan->target_cpus)
		late_canonical_update_u32(&ctx, cpu);
	late_canonical_update_identity(&ctx,
				       plan->evidence.evidence_identity);
	late_canonical_update_bitmap(&ctx, plan->canonical_caps);
	late_canonical_update_bitmap(&ctx, plan->compiled_local_caps);
	late_canonical_update_bitmap(&ctx, plan->classified_local_caps);
	late_canonical_update_bitmap(&ctx, plan->early_local_caps);
	late_canonical_update_bitmap(&ctx, plan->target_local_caps);
	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {
		late_canonical_update_bitmap(&ctx,
			plan->target[target].classified_local_caps);
		late_canonical_update_bitmap(&ctx,
			plan->target[target].local_caps);
	}
	late_canonical_update_bitmap(&ctx, plan->required_local_caps);
	late_canonical_update_bitmap(&ctx, plan->conflicting_local_caps);
	late_canonical_update_effects(&ctx, &plan->effects);
	for (i = 0; i < ARRAY_SIZE(plan->expected_elf_hwcap); i++)
		late_canonical_update_u64(&ctx, plan->expected_elf_hwcap[i]);
	late_canonical_update_u32(&ctx, plan->expected_compat_hwcap);
	late_canonical_update_u32(&ctx, plan->expected_compat_hwcap2);
	late_canonical_update_u8(&ctx, plan->local_caps_planned);
	late_canonical_update_u8(&ctx, plan->effects_planned);
	late_canonical_update_u8(&ctx, plan->hwcaps_planned);
	late_canonical_digest_identity(&ctx, identity);
}

static int __init
late_profile_finalize_plan_identity(struct arm64_late_cpu_plan *plan)
{
	if (!plan || !plan->local_caps_planned || !plan->effects_planned ||
	    !plan->hwcaps_planned ||
	    strnlen(plan->profile_id, sizeof(plan->profile_id)) >=
		    sizeof(plan->profile_id) ||
	    !late_profile_identity_empty(plan->evidence.evidence_identity) ||
	    !late_profile_identity_empty(plan->identity))
		return -EINVAL;

	late_canonical_hash_evidence(&plan->evidence,
				     plan->evidence.evidence_identity);
	if (late_profile_identity_empty(plan->evidence.evidence_identity))
		return -EKEYREJECTED;
	late_canonical_hash_plan(plan, plan->identity);
	if (late_profile_identity_empty(plan->identity)) {
		memset(plan->evidence.evidence_identity, 0,
		       sizeof(plan->evidence.evidence_identity));
		return -EKEYREJECTED;
	}

	return 0;
}

'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"replacement anchor count changed in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")


def apply(root: Path) -> None:
    validate_parent(root)

    header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    replace_once(
        header,
        "\tu8 local_caps_planned;\n\tu8 effects_planned;\n"
        "\t/* Future complete planner supplies a canonical field-wise identity. */\n",
        "\tu8 local_caps_planned;\n\tu8 effects_planned;\n"
        "\tu8 hwcaps_planned;\n"
        "\t/* Core-owned SHA-256 over named fields, never structure padding. */\n",
    )
    replace_once(
        header,
        "int __init arm64_plan_late_cpu_effects(struct arm64_late_cpu_plan *draft,\n"
        "\t\t\t\t       const struct arm64_late_cpu_profile *profile);\n",
        "int __init arm64_plan_late_cpu_effects(struct arm64_late_cpu_plan *draft,\n"
        "\t\t\t\t       const struct arm64_late_cpu_profile *profile);\n"
        "int __init arm64_plan_late_cpu_hwcaps(struct arm64_late_cpu_plan *draft);\n",
    )

    cpufeature = root / "arch/arm64/kernel/cpufeature.c"
    replace_once(
        cpufeature,
        "static void cap_set_elf_hwcap(const struct arm64_cpu_capabilities *cap)\n",
        HWCAP_PLANNER +
        "static void cap_set_elf_hwcap(const struct arm64_cpu_capabilities *cap)\n",
    )

    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    replace_once(
        core,
        "#ifdef CONFIG_ARM64_LATE_CPU_RUNTIME_IDENTITY\n"
        "#define LATE_RUNTIME_IKCONFIG_MAX\tSZ_4M\n",
        IDENTITY_FINALIZER +
        "#ifdef CONFIG_ARM64_LATE_CPU_RUNTIME_IDENTITY\n"
        "#define LATE_RUNTIME_IKCONFIG_MAX\tSZ_4M\n",
    )
    replace_once(
        core,
        "\tint validate_ret;\n\tint effect_ret;\n\tint plan_ret;\n\tint ret;\n",
        "\tint identity_ret;\n\tint validate_ret;\n\tint hwcap_ret;\n"
        "\tint effect_ret;\n\tint plan_ret;\n\tint ret;\n",
    )
    replace_once(
        core,
        "\tplan_ret = arm64_plan_late_cpu_capabilities(&draft, &late_profile);\n"
        "\teffect_ret = plan_ret ? -EAGAIN :\n"
        "\t\tarm64_plan_late_cpu_effects(&draft, &late_profile);\n"
        "\tvalidate_ret = late_profile.validate_plan(&draft);\n",
        "\tplan_ret = arm64_plan_late_cpu_capabilities(&draft, &late_profile);\n"
        "\teffect_ret = plan_ret ? -EAGAIN :\n"
        "\t\tarm64_plan_late_cpu_effects(&draft, &late_profile);\n"
        "\thwcap_ret = effect_ret ? -EAGAIN :\n"
        "\t\tarm64_plan_late_cpu_hwcaps(&draft);\n"
        "\tvalidate_ret = late_profile.validate_plan(&draft);\n"
        "\tidentity_ret = (plan_ret || effect_ret || hwcap_ret ||\n"
        "\t\t\tvalidate_ret) ? -EAGAIN :\n"
        "\t\tlate_profile_finalize_plan_identity(&draft);\n",
    )
    replace_once(
        core,
        "\tif (effect_ret)\n"
        "\t\tdraft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_EFFECT_PLAN;\n"
        "\tif (validate_ret)\n",
        "\tif (effect_ret)\n"
        "\t\tdraft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_EFFECT_PLAN;\n"
        "\tif (hwcap_ret)\n"
        "\t\tdraft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_HWCAP;\n"
        "\tif (identity_ret)\n"
        "\t\tdraft.evidence.blocker_mask |=\n"
        "\t\t\tARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY;\n"
        "\tif (validate_ret)\n",
    )
    replace_once(
        core,
        "\tif (ret || plan_ret || effect_ret || validate_ret ||\n",
        "\tif (ret || plan_ret || effect_ret || hwcap_ret || identity_ret ||\n"
        "\t    validate_ret ||\n",
    )
    replace_once(
        core,
        "\tif (!draft.local_caps_planned || !draft.effects_planned ||\n"
        "\t    !late_profile_plan_has_identity(&draft)) {\n",
        "\tif (!draft.local_caps_planned || !draft.effects_planned ||\n"
        "\t    !draft.hwcaps_planned ||\n"
        "\t    !late_profile_plan_has_identity(&draft)) {\n",
    )
    replace_once(
        core,
        "\t    !late_plan.local_caps_planned || !late_plan.effects_planned ||\n",
        "\t    !late_plan.local_caps_planned || !late_plan.effects_planned ||\n"
        "\t    !late_plan.hwcaps_planned ||\n",
    )

    profile = root / "arch/arm64/kernel/mt6797_psci.c"
    replace_once(
        profile,
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "static const u64 mt6797_a72_fixture_evidence_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {\n"
        "\t0x9e93afac8cddf877, 0x1fe76cd27c6818ce,\n"
        "\t0x3e165b1f47a43e8d, 0x1821b7769ce02fad,\n"
        "};\n"
        "#endif\n\n",
        "",
    )
    replace_once(
        profile,
        "\t    memcmp(evidence->evidence_identity,\n"
        "\t\t   mt6797_a72_fixture_evidence_identity,\n"
        "\t\t   sizeof(evidence->evidence_identity)) ||\n",
        "\t    !mt6797_a72_identity_empty(evidence->evidence_identity) ||\n",
    )
    replace_once(
        profile,
        "\tmemcpy(evidence->evidence_identity,\n"
        "\t       mt6797_a72_fixture_evidence_identity,\n"
        "\t       sizeof(evidence->evidence_identity));\n",
        "",
    )
    replace_once(
        profile,
        "\t    bitmap_weight(plan->classified_local_caps, ARM64_NCAPS) !=\n"
        "\t\tARRAY_SIZE(mt6797_a72_present_caps) +\n"
        "\t\tARRAY_SIZE(mt6797_a72_absent_caps) ||\n"
        "\t    plan->expected_compat_hwcap || plan->expected_compat_hwcap2)\n",
        "\t    bitmap_weight(plan->classified_local_caps, ARM64_NCAPS) !=\n"
        "\t\tARRAY_SIZE(mt6797_a72_present_caps) +\n"
        "\t\tARRAY_SIZE(mt6797_a72_absent_caps))\n",
    )
    replace_once(
        profile,
        "\tif (!plan->local_caps_planned || !plan->effects_planned ||\n"
        "\t    !mt6797_a72_evidence_is_fixture(&plan->evidence) ||\n",
        "\tif (!plan->local_caps_planned || !plan->effects_planned ||\n"
        "\t    !plan->hwcaps_planned ||\n"
        "\t    !mt6797_a72_evidence_is_fixture(&plan->evidence) ||\n",
    )
    replace_once(
        profile,
        "\tif (plan->local_caps_planned || plan->effects_planned ||\n"
        "\t    !mt6797_a72_evidence_is_expected_only(&plan->evidence) ||\n"
        "\t    !mt6797_a72_effects_empty(&plan->effects))\n",
        "\tif (plan->local_caps_planned || plan->effects_planned ||\n"
        "\t    plan->hwcaps_planned ||\n"
        "\t    !mt6797_a72_evidence_is_expected_only(&plan->evidence) ||\n"
        "\t    !mt6797_a72_effects_empty(&plan->effects) ||\n"
        "\t    memchr_inv(plan->expected_elf_hwcap, 0,\n"
        "\t\t       sizeof(plan->expected_elf_hwcap)) ||\n"
        "\t    plan->expected_compat_hwcap || plan->expected_compat_hwcap2)\n",
    )
    replace_once(
        profile,
        "\tfor (i = 0; i < ARRAY_SIZE(plan->expected_elf_hwcap); i++)\n"
        "\t\tif (plan->expected_elf_hwcap[i])\n"
        "\t\t\treturn -EINVAL;\n",
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\tif (!memchr_inv(plan->expected_elf_hwcap, 0, sizeof(plan->expected_elf_hwcap)))\n"
        "\t\treturn -EINVAL;\n"
        "#endif\n",
    )
    replace_once(
        profile,
        "\t/* Source-only fixture/expected evidence never publishes an identity. */\n"
        "\treturn -EAGAIN;\n",
        "\t/* The core owns canonical identities after this pure validation. */\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\treturn 0;\n"
        "#else\n"
        "\treturn -EAGAIN;\n"
        "#endif\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
