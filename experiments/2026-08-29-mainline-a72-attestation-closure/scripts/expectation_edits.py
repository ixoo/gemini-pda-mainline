#!/usr/bin/env python3
"""Deterministic source edits for slice 6's expected planning input."""

from __future__ import annotations

import hashlib
from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "6bf7283eab859a1758aa450bf1ff0933a15a02c5274a0cd3a397d61b7b9975b0",
    "arch/arm64/kernel/cpufeature.c":
        "3f7eb6aa186d4f4d98944febd4342f16072764f9f57d51f632a44fa3594f1394",
    "arch/arm64/kernel/cpu_errata.c":
        "007a3523ba15d1d9783fdde0868b8688daab8d974cc244f8ed7fead5acb86fc5",
    "arch/arm64/kernel/late_cpu_profile.c":
        "0b1f59af63003f3357d7496a2456adea15285d9247a6c0ea542b4a217dc64129",
    "arch/arm64/kernel/mt6797_psci.c":
        "6c2b140c5c4e62d65c56a644946c6468be91aba4a6fc86852648a8aab408be4a",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"edit anchor count changed for {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


def replace_region(path: Path, start: str, end: str, replacement: str) -> None:
    text = path.read_text()
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError(f"edit region changed for {path}")
    begin = text.index(start)
    finish = text.index(end, begin)
    path.write_text(text[:begin] + replacement + text[finish:])


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"parent source absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"parent source changed: {relative}: {actual} != {expected}")


EXPECTED_HWCAP_BLOCK = r'''static bool __init
late_cpu_expected_field_valid(const struct arm64_late_cpu_expected_pair *expected,
	enum arm64_late_cpu_expected_pair_field field)
{
	return expected && expected->abi == ARM64_LATE_CPU_EXPECTED_PAIR_ABI &&
	       expected->target_count == ARM64_LATE_CPU_MAX_TARGETS &&
	       field < ARM64_LATE_CPU_EXPECT_FIELD_COUNT &&
	       !(expected->valid & ~ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK) &&
	       expected->valid & BIT_ULL(field);
}

static int __init
late_cpu_expected_hwcap_register(const struct arm64_late_cpu_expected_pair *expected,
	u32 sys_reg, u64 *value)
{
	enum arm64_late_cpu_expected_pair_field field;
	u64 register_value;

	if (!value)
		return -EINVAL;

	switch (sys_reg) {
	case SYS_ID_AA64DFR0_EL1:
		field = ARM64_LATE_CPU_EXPECT_AA64DFR0;
		register_value = expected ? expected->id_aa64dfr0 : 0;
		break;
	case SYS_ID_AA64ISAR0_EL1:
		field = ARM64_LATE_CPU_EXPECT_AA64ISAR0;
		register_value = expected ? expected->id_aa64isar0 : 0;
		break;
	case SYS_ID_AA64ISAR1_EL1:
		field = ARM64_LATE_CPU_EXPECT_AA64ISAR1;
		register_value = expected ? expected->id_aa64isar1 : 0;
		break;
	case SYS_ID_AA64MMFR0_EL1:
		field = ARM64_LATE_CPU_EXPECT_AA64MMFR0;
		register_value = expected ? expected->id_aa64mmfr0 : 0;
		break;
	case SYS_ID_AA64MMFR1_EL1:
		field = ARM64_LATE_CPU_EXPECT_AA64MMFR1;
		register_value = expected ? expected->id_aa64mmfr1 : 0;
		break;
	case SYS_ID_AA64PFR0_EL1:
		field = ARM64_LATE_CPU_EXPECT_AA64PFR0;
		register_value = expected ? expected->id_aa64pfr0 : 0;
		break;
	case SYS_ID_AA64PFR1_EL1:
		field = ARM64_LATE_CPU_EXPECT_AA64PFR1;
		register_value = expected ? expected->id_aa64pfr1 : 0;
		break;
	case SYS_ID_ISAR5_EL1:
		field = ARM64_LATE_CPU_EXPECT_A32ISAR5;
		register_value = expected ? expected->id_isar5 : 0;
		break;
	default:
		return -ENOENT;
	}

	if (!late_cpu_expected_field_valid(expected, field))
		return -ENOENT;
	*value = register_value;
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
	const struct arm64_late_cpu_expected_pair *expected)
{
	bool sve_match = false;
	bool sme_match = false;
	u64 value;

#ifdef CONFIG_COMPAT
	if (cap->matches == compat_has_neon) {
		if (expected) {
			if (late_cpu_expected_hwcap_register(expected,
							 SYS_MVFR1_EL1, &value))
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
	if (expected) {
		if (late_cpu_expected_hwcap_register(expected, cap->sys_reg,
						       &value))
			return false;
	} else {
		value = read_sanitised_ftr_reg(cap->sys_reg);
	}

	if (sve_match) {
		u64 pfr0;

		if (expected) {
			if (late_cpu_expected_hwcap_register(expected,
							 SYS_ID_AA64PFR0_EL1,
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

		if (expected) {
			if (late_cpu_expected_hwcap_register(expected,
							 SYS_ID_AA64PFR1_EL1,
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
	const struct arm64_late_cpu_expected_pair *expected)
{
	const struct arm64_cpu_capabilities *match;
	int i;

	if (!cap->match_list)
		return late_cpu_hwcap_match_one(cap, expected);
	if (cap->matches != cpucap_multi_entry_cap_matches)
		return false;

	match = cap->match_list;
	for (i = 0; i < ARM64_NCAPS; i++, match++) {
		if (!match->matches)
			return false;
		if (late_cpu_hwcap_match_one(match, expected))
			return true;
	}

	return false;
}

static bool __init
late_cpu_hwcap_all_cpus(const struct arm64_cpu_capabilities *cap,
			const struct arm64_late_cpu_plan *plan)
{
	if (!arm64_late_cpu_expected_pair_complete(plan) ||
	    !late_cpu_hwcap_matches(cap, NULL))
		return false;

	return late_cpu_hwcap_matches(cap, &plan->evidence.expected_pair);
}

static bool __init
late_cpu_all_support_32bit_el0(const struct arm64_late_cpu_plan *plan)
{
	const struct arm64_late_cpu_expected_pair *expected;
	u64 pfr0;

	if (!system_supports_32bit_el0() ||
	    !arm64_late_cpu_expected_pair_complete(plan))
		return false;
	expected = &plan->evidence.expected_pair;
	if (late_cpu_expected_hwcap_register(expected, SYS_ID_AA64PFR0_EL1,
					       &pfr0))
		return false;

	return id_aa64pfr0_32bit_el0(pfr0);
}

'''


EXPECTED_CACHE_STATE = r'''

enum arm64_late_cpu_cap_state __init
arm64_late_cpu_expected_cache_type_state(const struct arm64_cpu_capabilities *cap,
	const struct arm64_cpu_capabilities *match,
	const struct arm64_late_cpu_expected_pair *expected,
	const struct arm64_late_cpu_system_cap_evidence *system)
{
	const u64 required = BIT_ULL(ARM64_LATE_CPU_EXPECT_CTR) |
		BIT_ULL(ARM64_LATE_CPU_EXPECT_CLIDR);
	u64 effective;
	u64 mask;
	u64 raw;
	u64 sys;

	if (!cap || cap != match || cap->match_list ||
	    cap->capability != ARM64_MISMATCHED_CACHE_TYPE ||
	    cap->type != ARM64_CPUCAP_LOCAL_CPU_ERRATUM ||
	    cap->matches != has_mismatched_cache_type ||
	    cap->cpu_enable != cpu_enable_trap_ctr_access || cap->cpus ||
	    !expected || !system ||
	    expected->abi != ARM64_LATE_CPU_EXPECTED_PAIR_ABI ||
	    expected->target_count != ARM64_LATE_CPU_MAX_TARGETS ||
	    expected->valid & ~ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK ||
	    (expected->valid & required) != required ||
	    !(system->valid & ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID) ||
	    system->valid & ~ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK)
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	raw = expected->ctr;
	mask = system->ctr_strict_mask;
	if (mask != ~GENMASK_ULL(15, 14) ||
	    (raw | system->ctr_sys_val) & ~GENMASK_ULL(31, 0) ||
	    !(raw & BIT(31)) || !(system->ctr_sys_val & BIT(31)))
		return ARM64_LATE_CPU_CAP_UNRESOLVED;

	effective = raw;
	if (!(raw & BIT(CTR_EL0_IDC_SHIFT)) &&
	    (!CLIDR_LOC(expected->clidr_el1) ||
	     (!CLIDR_LOUIS(expected->clidr_el1) &&
	      !CLIDR_LOUU(expected->clidr_el1))))
		effective |= BIT(CTR_EL0_IDC_SHIFT);

	raw &= mask;
	effective &= mask;
	sys = system->ctr_sys_val & mask;

	return effective != sys && raw != sys ?
		ARM64_LATE_CPU_CAP_PRESENT : ARM64_LATE_CPU_CAP_ABSENT;
}
'''


def apply(root: Path) -> None:
    validate_parent(root)
    header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    cpufeature = root / "arch/arm64/kernel/cpufeature.c"
    errata = root / "arch/arm64/kernel/cpu_errata.c"
    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    profile = root / "arch/arm64/kernel/mt6797_psci.c"

    replace_once(
        header,
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);\n",
        "bool arm64_late_cpu_expected_pair_complete("
        "const struct arm64_late_cpu_plan *plan);\n"
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);\n",
    )
    replace_once(
        header,
        "arm64_late_cpu_cache_type_state(\n"
        "\tconst struct arm64_cpu_capabilities *cap,\n"
        "\tconst struct arm64_cpu_capabilities *match,\n"
        "\tconst struct arm64_late_cpu_target_cap_evidence *target,\n"
        "\tconst struct arm64_late_cpu_system_cap_evidence *system);\n",
        "arm64_late_cpu_cache_type_state(\n"
        "\tconst struct arm64_cpu_capabilities *cap,\n"
        "\tconst struct arm64_cpu_capabilities *match,\n"
        "\tconst struct arm64_late_cpu_target_cap_evidence *target,\n"
        "\tconst struct arm64_late_cpu_system_cap_evidence *system);\n"
        "enum arm64_late_cpu_cap_state __init\n"
        "arm64_late_cpu_expected_cache_type_state("
        "const struct arm64_cpu_capabilities *cap,\n"
        "\tconst struct arm64_cpu_capabilities *match,\n"
        "\tconst struct arm64_late_cpu_expected_pair *expected,\n"
        "\tconst struct arm64_late_cpu_system_cap_evidence *system);\n",
    )

    replace_once(
        core,
        "static bool\nlate_expected_pair_complete",
        "bool\narm64_late_cpu_expected_pair_complete",
    )
    replace_once(
        core,
        "!late_expected_pair_complete(&late_plan)",
        "!arm64_late_cpu_expected_pair_complete(&late_plan)",
    )

    replace_region(
        cpufeature,
        "static int __init\nlate_cpu_hwcap_register(",
        "static bool __init\nlate_cpu_plan_any_cpu_has_cap(",
        EXPECTED_HWCAP_BLOCK,
    )
    replace_once(
        cpufeature,
        "int __init arm64_plan_late_cpu_hwcaps(struct arm64_late_cpu_plan *plan)\n"
        "{\n\tunsigned int target;\n\tint ret;\n",
        "int __init arm64_plan_late_cpu_hwcaps(struct arm64_late_cpu_plan *plan)\n"
        "{\n\tint ret;\n",
    )
    replace_once(
        cpufeature,
        "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)\n"
        "\t\tif (!(plan->evidence.target_cap[target].valid &\n"
        "\t\t      ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID))\n"
        "\t\t\treturn -EAGAIN;\n",
        "\tif (!arm64_late_cpu_expected_pair_complete(plan))\n"
        "\t\treturn -EAGAIN;\n",
    )

    replace_once(
        errata,
        "\treturn effective != sys && raw != sys ?\n"
        "\t\tARM64_LATE_CPU_CAP_PRESENT : ARM64_LATE_CPU_CAP_ABSENT;\n"
        "}\n#endif\n\n#ifdef CONFIG_ARM64_ERRATUM_4311569",
        "\treturn effective != sys && raw != sys ?\n"
        "\t\tARM64_LATE_CPU_CAP_PRESENT : ARM64_LATE_CPU_CAP_ABSENT;\n"
        "}\n" + EXPECTED_CACHE_STATE +
        "#endif\n\n#ifdef CONFIG_ARM64_ERRATUM_4311569",
    )

    replace_once(
        profile,
        "\t\treturn arm64_late_cpu_cache_type_state(\n"
        "\t\t\tcap, match,\n"
        "\t\t\t&evidence->target_cap[target], &evidence->system_cap);\n",
        "#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
        "\t\treturn arm64_late_cpu_cache_type_state(\n"
        "\t\t\tcap, match,\n"
        "\t\t\t&evidence->target_cap[target], &evidence->system_cap);\n"
        "#else\n"
        "\t\treturn arm64_late_cpu_expected_cache_type_state("
        "cap, match,\n"
        "\t\t\t&evidence->expected_pair,\n"
        "\t\t\t&evidence->system_cap);\n"
        "#endif\n",
    )


if __name__ == "__main__":
    raise SystemExit("expectation_edits.py is imported by the generator")
