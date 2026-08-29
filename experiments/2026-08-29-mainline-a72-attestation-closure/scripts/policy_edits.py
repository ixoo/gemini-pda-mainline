#!/usr/bin/env python3
"""Deterministic source edits for the conservative-policy slice."""

from __future__ import annotations

import hashlib
from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "f1de7967f7bfba16642212bc8e32d25fda9b56ce1434c1687106b5dd6c3055b0",
    "arch/arm64/kernel/cpufeature.c":
        "f18b1331797469f38f4864ca52a17550d2099aed7d8d47d8869b589ec263e22d",
    "arch/arm64/kernel/late_cpu_profile.c":
        "271e4a3d489c9eb5053764a6b4b5d48296d67687df5644c3fbbcffc05f65dcd6",
    "arch/arm64/kernel/mt6797_psci.c":
        "ff8e4ce803d0ad4a5fc35989a3d38169a3e7260bd737e861317b22f1ca8f5471",
    "arch/arm64/kernel/proton-pack.c":
        "09de56a67c4e5e42847c11ee2d4da0d675aa6309815ffae221a4987b66e4e427",
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


EARLY_SYSTEM_STATE = r'''enum arm64_late_cpu_cap_state __init
arm64_late_cpu_early_system_cap_state(const struct arm64_cpu_capabilities *cap,
				      const struct arm64_cpu_capabilities *match,
				      const struct arm64_late_cpu_system_cap_evidence *system)
{
	bool present;

	if (!system ||
	    !(system->valid & ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID) ||
	    system->valid & ~ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK ||
	    system->gicv5_legacy > 1 || system->ich_hcr_tdir > 1 ||
	    !cpucap_late_cpu_permitted(cap))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	switch (cap->capability) {
	case ARM64_HAS_GICV5_LEGACY:
		if (!late_cpu_gic_descriptor_valid(cap, match))
			return ARM64_LATE_CPU_CAP_UNRESOLVED;
		present = system->gicv5_legacy;
		break;
	case ARM64_HAS_ICH_HCR_EL2_TDIR:
		if (!late_cpu_ich_descriptor_valid(cap, match))
			return ARM64_LATE_CPU_CAP_UNRESOLVED;
		present = system->ich_hcr_tdir;
		break;
	default:
		return ARM64_LATE_CPU_CAP_UNRESOLVED;
	}

	/* A present system capability still needs target controller evidence. */
	return present ? ARM64_LATE_CPU_CAP_UNRESOLVED :
			 ARM64_LATE_CPU_CAP_ABSENT;
}

'''


EXPECTED_SPECTRE = r'''static bool __init
late_cpu_expected_field_valid(const struct arm64_late_cpu_expected_pair *expected,
			      enum arm64_late_cpu_expected_pair_field field)
{
	return expected && expected->abi == ARM64_LATE_CPU_EXPECTED_PAIR_ABI &&
	       expected->target_count == ARM64_LATE_CPU_MAX_TARGETS &&
	       field < ARM64_LATE_CPU_EXPECT_FIELD_COUNT &&
	       !(expected->valid & ~ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK) &&
	       expected->valid & BIT_ULL(field) &&
	       expected->midr == MIDR_CORTEX_A72;
}

static enum arm64_late_cpu_cap_state __init
late_cpu_expected_v2_evidence_state(const struct arm64_late_cpu_expected_pair *expected)
{
	u64 csv2;

	if (!late_cpu_expected_field_valid(expected,
					   ARM64_LATE_CPU_EXPECT_AA64PFR0) ||
	    !late_cpu_expected_field_valid(expected,
					   ARM64_LATE_CPU_EXPECT_MIDR))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;
	csv2 = cpuid_feature_extract_unsigned_field(expected->id_aa64pfr0,
						   ID_AA64PFR0_EL1_CSV2_SHIFT);
	if (csv2 > 3)
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	return csv2 ? ARM64_LATE_CPU_CAP_ABSENT :
		      ARM64_LATE_CPU_CAP_PRESENT;
}

enum arm64_late_cpu_cap_state __init
arm64_late_cpu_expected_v2_state(const struct arm64_cpu_capabilities *cap,
				 const struct arm64_cpu_capabilities *match,
				 const struct arm64_late_cpu_expected_pair *expected)
{
	if (!late_cpu_spectre_descriptor_valid(cap, match, ARM64_SPECTRE_V2))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	return late_cpu_expected_v2_evidence_state(expected);
}

static enum arm64_late_cpu_cap_state __init
late_cpu_expected_v4_evidence_state(const struct arm64_late_cpu_expected_pair *expected)
{
	u64 ssbs;

	if (!late_cpu_expected_field_valid(expected,
					   ARM64_LATE_CPU_EXPECT_AA64PFR1) ||
	    !late_cpu_expected_field_valid(expected,
					   ARM64_LATE_CPU_EXPECT_MIDR))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;
	ssbs = cpuid_feature_extract_unsigned_field(expected->id_aa64pfr1,
						   ID_AA64PFR1_EL1_SSBS_SHIFT);
	if (ssbs > 2)
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	/* Without a current WA2 result, even SSBS==0 remains affected. */
	return ARM64_LATE_CPU_CAP_PRESENT;
}

enum arm64_late_cpu_cap_state __init
arm64_late_cpu_expected_v4_state(const struct arm64_cpu_capabilities *cap,
				 const struct arm64_cpu_capabilities *match,
				 const struct arm64_late_cpu_expected_pair *expected)
{
	if (!late_cpu_spectre_descriptor_valid(cap, match, ARM64_SPECTRE_V4))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	return late_cpu_expected_v4_evidence_state(expected);
}

static enum arm64_late_cpu_cap_state __init
late_cpu_expected_bhb_evidence_state(const struct arm64_late_cpu_expected_pair *expected)
{
	u64 csv2;

	if (!late_cpu_expected_field_valid(expected,
					   ARM64_LATE_CPU_EXPECT_AA64PFR0) ||
	    !late_cpu_expected_field_valid(expected,
					   ARM64_LATE_CPU_EXPECT_MIDR))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;
	csv2 = cpuid_feature_extract_unsigned_field(expected->id_aa64pfr0,
						   ID_AA64PFR0_EL1_CSV2_SHIFT);
	if (csv2 > 3)
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	return csv2 == 3 ? ARM64_LATE_CPU_CAP_ABSENT :
			 ARM64_LATE_CPU_CAP_PRESENT;
}

enum arm64_late_cpu_cap_state __init
arm64_late_cpu_expected_bhb_state(const struct arm64_cpu_capabilities *cap,
				  const struct arm64_cpu_capabilities *match,
				  const struct arm64_late_cpu_expected_pair *expected)
{
	if (!late_cpu_spectre_descriptor_valid(cap, match, ARM64_SPECTRE_BHB))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	return late_cpu_expected_bhb_evidence_state(expected);
}

'''


EXPECTED_EFFECTS = r'''int __init
arm64_late_cpu_expected_effects(const struct arm64_late_cpu_expected_pair *expected,
				const struct arm64_late_cpu_target_policy_evidence *policy,
				struct arm64_late_cpu_target_effect_plan *effects)
{
	enum arm64_late_cpu_cap_state bhb_state;
	enum arm64_late_cpu_cap_state v2_state;
	enum arm64_late_cpu_cap_state v4_state;
	u64 ssbs;

	if (!effects || effects->valid || !late_cpu_policy_valid(policy) ||
	    arm64_late_cpu_target_impl_override_active())
		return -EINVAL;
	v2_state = late_cpu_expected_v2_evidence_state(expected);
	v4_state = late_cpu_expected_v4_evidence_state(expected);
	bhb_state = late_cpu_expected_bhb_evidence_state(expected);
	if (v2_state == ARM64_LATE_CPU_CAP_UNRESOLVED ||
	    v4_state == ARM64_LATE_CPU_CAP_UNRESOLVED ||
	    bhb_state == ARM64_LATE_CPU_CAP_UNRESOLVED)
		return -EAGAIN;

	effects->valid = ARM64_LATE_CPU_TARGET_EFFECT_VALID_MASK;
	effects->spectre_v2_hyp_vector = ARM64_LATE_CPU_HYP_VECTOR_DIRECT;
	effects->spectre_v2_conduit = ARM64_LATE_CPU_SMCCC_NONE;
	effects->spectre_v2_callback = ARM64_LATE_CPU_V2_CALLBACK_NONE;
	effects->spectre_v2_state =
		v2_state == ARM64_LATE_CPU_CAP_ABSENT ?
			ARM64_LATE_CPU_MITIGATION_UNAFFECTED :
			ARM64_LATE_CPU_MITIGATION_VULNERABLE;

	effects->spectre_v4_policy = policy->spectre_v4_policy;
	effects->spectre_v4_conduit = ARM64_LATE_CPU_SMCCC_NONE;
	ssbs = cpuid_feature_extract_unsigned_field(expected->id_aa64pfr1,
						   ID_AA64PFR1_EL1_SSBS_SHIFT);
	if (ssbs && !policy->mitigations_off &&
	    policy->spectre_v4_policy != ARM64_LATE_CPU_V4_POLICY_FORCE_OFF) {
		effects->spectre_v4_state = ARM64_LATE_CPU_MITIGATION_MITIGATED;
		effects->spectre_v4_method = ARM64_LATE_CPU_V4_SSBS;
	} else {
		effects->spectre_v4_state = ARM64_LATE_CPU_MITIGATION_VULNERABLE;
		effects->spectre_v4_method = ARM64_LATE_CPU_V4_NONE;
	}

	effects->bhb_conduit = ARM64_LATE_CPU_SMCCC_NONE;
	effects->bhb_vector_template = ARM64_LATE_CPU_BHB_VECTOR_NONE;
	effects->bhb_hyp_vector = effects->spectre_v2_hyp_vector;
	effects->bhb_v2_non_vulnerable =
		effects->spectre_v2_state != ARM64_LATE_CPU_MITIGATION_VULNERABLE;
	if (bhb_state == ARM64_LATE_CPU_CAP_ABSENT) {
		effects->bhb_method = ARM64_LATE_CPU_BHB_NONE;
		effects->bhb_mitigation_state =
			ARM64_LATE_CPU_BHB_STATE_UNAFFECTED;
	} else if (!effects->bhb_v2_non_vulnerable) {
		effects->bhb_method = ARM64_LATE_CPU_BHB_NONE;
		effects->bhb_mitigation_state =
			ARM64_LATE_CPU_BHB_STATE_VULNERABLE;
	} else {
		/* A non-vulnerable v2 path would need the missing BHB IDs. */
		return -EAGAIN;
	}

	return 0;
}

'''


def apply(root: Path) -> None:
    validate_parent(root)
    header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    cpufeature = root / "arch/arm64/kernel/cpufeature.c"
    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    profile = root / "arch/arm64/kernel/mt6797_psci.c"
    proton = root / "arch/arm64/kernel/proton-pack.c"

    replace_once(
        header,
        "#define ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID\tBIT(2)\n"
        "#define ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK\t\t\t\t\\\n"
        "\t(ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |\t\t\t\t\\\n"
        "\t ARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID |\t\t\t\t\\\n"
        "\t ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID)\n",
        "#define ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID\tBIT(2)\n"
        "#define ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID\tBIT(3)\n"
        "#define ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK\t\t\t\t\\\n"
        "\t(ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |\t\t\t\t\\\n"
        "\t ARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID |\t\t\t\t\\\n"
        "\t ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID |\t\t\t\\\n"
        "\t ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID)\n",
    )
    replace_once(
        header,
        "\tu8 bhb_matcher_loop_count;\n\tu8 bhb_system_method;\n};\n",
        "\tu8 bhb_matcher_loop_count;\n\tu8 bhb_system_method;\n"
        "\tu8 gicv5_legacy;\n\tu8 ich_hcr_tdir;\n};\n",
    )
    replace_once(
        header,
        "bool __init arm64_late_cpu_target_impl_override_active(void);\n"
        "enum arm64_late_cpu_cap_state __init\n"
        "arm64_late_cpu_gicv5_legacy_state(\n",
        "bool __init arm64_late_cpu_target_impl_override_active(void);\n"
        "enum arm64_late_cpu_cap_state __init\n"
        "arm64_late_cpu_early_system_cap_state("
        "const struct arm64_cpu_capabilities *cap,\n"
        "\t\t\t\t      const struct arm64_cpu_capabilities *match,\n"
        "\t\t\t\t      const struct arm64_late_cpu_system_cap_evidence *system);\n"
        "enum arm64_late_cpu_cap_state __init\n"
        "arm64_late_cpu_gicv5_legacy_state(\n",
    )
    replace_once(
        header,
        "int __init arm64_late_cpu_a72_bhb_effect(\n"
        "\tconst struct arm64_late_cpu_target_cap_evidence *target,\n"
        "\tconst struct arm64_late_cpu_target_policy_evidence *policy,\n"
        "\tu8 system_v2_state,\n"
        "\tstruct arm64_late_cpu_target_effect_plan *effects);\n",
        "int __init arm64_late_cpu_a72_bhb_effect(\n"
        "\tconst struct arm64_late_cpu_target_cap_evidence *target,\n"
        "\tconst struct arm64_late_cpu_target_policy_evidence *policy,\n"
        "\tu8 system_v2_state,\n"
        "\tstruct arm64_late_cpu_target_effect_plan *effects);\n"
        "enum arm64_late_cpu_cap_state __init\n"
        "arm64_late_cpu_expected_v2_state("
        "const struct arm64_cpu_capabilities *cap,\n"
        "\t\t\t\t const struct arm64_cpu_capabilities *match,\n"
        "\t\t\t\t const struct arm64_late_cpu_expected_pair *expected);\n"
        "enum arm64_late_cpu_cap_state __init\n"
        "arm64_late_cpu_expected_v4_state("
        "const struct arm64_cpu_capabilities *cap,\n"
        "\t\t\t\t const struct arm64_cpu_capabilities *match,\n"
        "\t\t\t\t const struct arm64_late_cpu_expected_pair *expected);\n"
        "enum arm64_late_cpu_cap_state __init\n"
        "arm64_late_cpu_expected_bhb_state("
        "const struct arm64_cpu_capabilities *cap,\n"
        "\t\t\t\t  const struct arm64_cpu_capabilities *match,\n"
        "\t\t\t\t  const struct arm64_late_cpu_expected_pair *expected);\n"
        "int __init\n"
        "arm64_late_cpu_expected_effects("
        "const struct arm64_late_cpu_expected_pair *expected,\n"
        "\t\t\t\tconst struct arm64_late_cpu_target_policy_evidence *policy,\n"
        "\t\t\t\tstruct arm64_late_cpu_target_effect_plan *effects);\n",
    )

    replace_once(
        cpufeature,
        "\tsystem->ssbs = !!ssbs;\n"
        "\tsystem->valid = ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |\n"
        "\t\t\tARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID;\n",
        "\tsystem->ssbs = !!ssbs;\n"
        "\tsystem->gicv5_legacy = cpus_have_cap(ARM64_HAS_GICV5_LEGACY);\n"
        "\tsystem->ich_hcr_tdir =\n"
        "\t\tcpus_have_cap(ARM64_HAS_ICH_HCR_EL2_TDIR);\n"
        "\tsystem->valid = ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |\n"
        "\t\t\tARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID |\n"
        "\t\t\tARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID;\n",
    )
    replace_once(
        cpufeature,
        "static enum arm64_late_cpu_cap_state __init\n"
        "late_cpu_gicv5_legacy_evidence_state(\n",
        EARLY_SYSTEM_STATE +
        "static enum arm64_late_cpu_cap_state __init\n"
        "late_cpu_gicv5_legacy_evidence_state(\n",
    )

    replace_once(
        core,
        "\tlate_canonical_update_u8(ctx, system->bhb_system_method);\n",
        "\tlate_canonical_update_u8(ctx, system->bhb_system_method);\n"
        "\tlate_canonical_update_u8(ctx, system->gicv5_legacy);\n"
        "\tlate_canonical_update_u8(ctx, system->ich_hcr_tdir);\n",
    )

    replace_once(
        proton,
        "\t    system->valid != (ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |\n"
        "\t\t\t      ARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID) ||\n",
        "\t    system->valid != (ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |\n"
        "\t\t\t      ARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID |\n"
        "\t\t\t      ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID) ||\n",
    )
    replace_once(
        proton,
        "static enum arm64_late_cpu_cap_state __init\n"
        "late_cpu_a72_spectre_v2_evidence_state(\n",
        EXPECTED_SPECTRE +
        "static enum arm64_late_cpu_cap_state __init\n"
        "late_cpu_a72_spectre_v2_evidence_state(\n",
    )
    replace_once(
        proton,
        "int __init arm64_late_cpu_a72_spectre_v2_v4_effects(\n",
        EXPECTED_EFFECTS +
        "int __init arm64_late_cpu_a72_spectre_v2_v4_effects(\n",
    )

    replace_once(
        profile,
        "\tcase ARM64_HAS_GICV5_LEGACY:\n"
        "\t\tif (cap->type != ARM64_CPUCAP_EARLY_LOCAL_CPU_FEATURE)\n"
        "\t\t\tbreak;\n"
        "\t\treturn arm64_late_cpu_gicv5_legacy_state(\n"
        "\t\t\tcap, match, &evidence->target_cap[target]);\n"
        "\tcase ARM64_HAS_ICH_HCR_EL2_TDIR:\n"
        "\t\tif (cap->type != ARM64_CPUCAP_EARLY_LOCAL_CPU_FEATURE)\n"
        "\t\t\tbreak;\n"
        "\t\treturn arm64_late_cpu_ich_hcr_tdir_state(\n"
        "\t\t\tcap, match, &evidence->target_cap[target]);\n",
        "\tcase ARM64_HAS_GICV5_LEGACY:\n"
        "\tcase ARM64_HAS_ICH_HCR_EL2_TDIR:\n"
        "\t\tif (cap->type != ARM64_CPUCAP_EARLY_LOCAL_CPU_FEATURE)\n"
        "\t\t\tbreak;\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\t\tif (cap->capability == ARM64_HAS_GICV5_LEGACY)\n"
        "\t\t\treturn arm64_late_cpu_gicv5_legacy_state(cap, match,\n"
        "\t\t\t\t&evidence->target_cap[target]);\n"
        "\t\treturn arm64_late_cpu_ich_hcr_tdir_state(cap, match,\n"
        "\t\t\t&evidence->target_cap[target]);\n"
        "#else\n"
        "\t\treturn arm64_late_cpu_early_system_cap_state(cap, match,\n"
        "\t\t\t&evidence->system_cap);\n"
        "#endif\n",
    )
    replace_once(
        profile,
        "\tcase ARM64_SPECTRE_V2:\n"
        "\t\tif (cap->type != ARM64_CPUCAP_LOCAL_CPU_ERRATUM)\n"
        "\t\t\tbreak;\n"
        "\t\treturn arm64_late_cpu_a72_spectre_v2_state(\n"
        "\t\t\tcap, match, &evidence->target_cap[target]);\n"
        "\tcase ARM64_SPECTRE_V4:\n"
        "\t\tif (cap->type != ARM64_CPUCAP_LOCAL_CPU_ERRATUM)\n"
        "\t\t\tbreak;\n"
        "\t\treturn arm64_late_cpu_a72_spectre_v4_state(\n"
        "\t\t\tcap, match, &evidence->target_cap[target]);\n"
        "\tcase ARM64_SPECTRE_BHB:\n"
        "\t\tif (cap->type != ARM64_CPUCAP_LOCAL_CPU_ERRATUM)\n"
        "\t\t\tbreak;\n"
        "\t\treturn arm64_late_cpu_a72_spectre_bhb_state(\n"
        "\t\t\tcap, match, &evidence->target_cap[target]);\n",
        "\tcase ARM64_SPECTRE_V2:\n"
        "\tcase ARM64_SPECTRE_V4:\n"
        "\tcase ARM64_SPECTRE_BHB:\n"
        "\t\tif (cap->type != ARM64_CPUCAP_LOCAL_CPU_ERRATUM)\n"
        "\t\t\tbreak;\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\t\tif (cap->capability == ARM64_SPECTRE_V2)\n"
        "\t\t\treturn arm64_late_cpu_a72_spectre_v2_state(cap, match,\n"
        "\t\t\t\t&evidence->target_cap[target]);\n"
        "\t\tif (cap->capability == ARM64_SPECTRE_V4)\n"
        "\t\t\treturn arm64_late_cpu_a72_spectre_v4_state(cap, match,\n"
        "\t\t\t\t&evidence->target_cap[target]);\n"
        "\t\treturn arm64_late_cpu_a72_spectre_bhb_state(cap, match,\n"
        "\t\t\t&evidence->target_cap[target]);\n"
        "#else\n"
        "\t\tif (cap->capability == ARM64_SPECTRE_V2)\n"
        "\t\t\treturn arm64_late_cpu_expected_v2_state(cap, match,\n"
        "\t\t\t\t&evidence->expected_pair);\n"
        "\t\tif (cap->capability == ARM64_SPECTRE_V4)\n"
        "\t\t\treturn arm64_late_cpu_expected_v4_state(cap, match,\n"
        "\t\t\t\t&evidence->expected_pair);\n"
        "\t\treturn arm64_late_cpu_expected_bhb_state(cap, match,\n"
        "\t\t\t&evidence->expected_pair);\n"
        "#endif\n",
    )
    replace_once(
        profile,
        "#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "static const u16 mt6797_a72_unresolved_caps[] __initconst = {\n"
        "\tARM64_HAS_GICV5_LEGACY,\n"
        "\tARM64_HAS_ICH_HCR_EL2_TDIR,\n"
        "\tARM64_MISMATCHED_CACHE_TYPE,\n",
        "#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "static const u16 mt6797_a72_unresolved_caps[] __initconst = {\n"
        "\tARM64_MISMATCHED_CACHE_TYPE,\n",
    )
    replace_once(
        profile,
        "static const u16 mt6797_a72_absent_caps[] __initconst = {\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\tARM64_HAS_GICV5_LEGACY,\n"
        "\tARM64_HAS_ICH_HCR_EL2_TDIR,\n"
        "#endif\n",
        "static const u16 mt6797_a72_absent_caps[] __initconst = {\n"
        "\tARM64_HAS_GICV5_LEGACY,\n"
        "\tARM64_HAS_ICH_HCR_EL2_TDIR,\n",
    )
    replace_once(
        profile,
        "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {\n"
        "\t\tret = arm64_late_cpu_a72_spectre_v2_v4_effects(\n"
        "\t\t\t&plan->evidence.target_cap[target],\n"
        "\t\t\t&plan->evidence.target_policy[target],\n"
        "\t\t\t&effects->target[target]);\n",
        "#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\tif (!arm64_late_cpu_expected_pair_complete(plan))\n"
        "\t\treturn -EAGAIN;\n"
        "#endif\n"
        "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\t\tret = arm64_late_cpu_a72_spectre_v2_v4_effects(\n"
        "\t\t\t&plan->evidence.target_cap[target],\n"
        "\t\t\t&plan->evidence.target_policy[target],\n"
        "\t\t\t&effects->target[target]);\n"
        "#else\n"
        "\t\tret = arm64_late_cpu_expected_effects("
        "&plan->evidence.expected_pair,\n"
        "\t\t\t&plan->evidence.target_policy[target],\n"
        "\t\t\t&effects->target[target]);\n"
        "#endif\n",
    )
    replace_once(
        profile,
        "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {\n"
        "\t\tret = arm64_late_cpu_a72_bhb_effect(\n"
        "\t\t\t&plan->evidence.target_cap[target],\n"
        "\t\t\t&plan->evidence.target_policy[target], system_v2_state,\n"
        "\t\t\t&effects->target[target]);\n"
        "\t\tif (ret)\n"
        "\t\t\treturn ret;\n",
        "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++) {\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\t\tret = arm64_late_cpu_a72_bhb_effect(\n"
        "\t\t\t&plan->evidence.target_cap[target],\n"
        "\t\t\t&plan->evidence.target_policy[target], system_v2_state,\n"
        "\t\t\t&effects->target[target]);\n"
        "\t\tif (ret)\n"
        "\t\t\treturn ret;\n"
        "#endif\n",
    )
    replace_once(
        profile,
        "\t    evidence->system_cap.bhb_matcher_loop_count ||\n"
        "\t    evidence->system_cap.bhb_system_method)\n",
        "\t    evidence->system_cap.bhb_matcher_loop_count ||\n"
        "\t    evidence->system_cap.bhb_system_method ||\n"
        "\t    evidence->system_cap.gicv5_legacy ||\n"
        "\t    evidence->system_cap.ich_hcr_tdir)\n",
    )


if __name__ == "__main__":
    raise SystemExit("policy_edits.py is imported by the generator")
