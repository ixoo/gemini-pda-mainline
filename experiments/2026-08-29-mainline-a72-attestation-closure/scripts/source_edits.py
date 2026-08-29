#!/usr/bin/env python3
"""Apply deterministic dormant expected-target and entry-validator edits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "e6bde598f415d8da0ba4073c37d2c8c341a70afb1d0237fc130ad113e494cd36",
    "arch/arm64/kernel/late_cpu_profile.c":
        "22ecfb06e8d00972ffdecad6019c11f2b4d695a38c90aa3bbd6977c4c22bc29b",
    "arch/arm64/kernel/smp.c":
        "2af27545feff3adf6e3514f6a42ffb50b4edac714c7e7d719bd7a4448f13ba7e",
}

RUNTIME_PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "b84c227709927bef35f3c8114484e6fab6e92550097dd605ab92fb28cedd878e",
    "arch/arm64/kernel/late_cpu_profile.c":
        "cb1b778d2ee92314b0d62539dfa27b0dd268a34808198e7ff9e39e521703368e",
    "arch/arm64/kernel/smp.c":
        "cb5d400e31be67561216a6020bcfdb0808eadd6991cf6b675d5c55bb15433869",
}

STACK_PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "b84c227709927bef35f3c8114484e6fab6e92550097dd605ab92fb28cedd878e",
    "arch/arm64/kernel/late_cpu_profile.c":
        "681c1cbaa74e86ce9aa78e5621a3295a9fd52d28aa2d886229113c08d8624577",
    "arch/arm64/kernel/smp.c":
        "cb5d400e31be67561216a6020bcfdb0808eadd6991cf6b675d5c55bb15433869",
}

SYSTEM_POLICY_PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "b84c227709927bef35f3c8114484e6fab6e92550097dd605ab92fb28cedd878e",
    "arch/arm64/kernel/late_cpu_profile.c":
        "0831c263ae521d0f22c2632066892287a49470717c8e180651ad1a2e7a85921a",
    "arch/arm64/kernel/cpufeature.c":
        "4d4f8f3c5e2f20ea54ccc68649b4418b6931f0285b52028627950815981dd244",
    "arch/arm64/kernel/proton-pack.c":
        "d74b82a614ddcb2797c894301daabdf04b0130a96090889b562feff1688a7917",
    "arch/arm64/kernel/smp.c":
        "cb5d400e31be67561216a6020bcfdb0808eadd6991cf6b675d5c55bb15433869",
}


SYSTEM_CAP_PRODUCER = '''#ifdef CONFIG_ARM64_LATE_CPU_PROFILE
int __init
arm64_late_cpu_collect_system(struct arm64_late_cpu_system_cap_evidence *system)
{
	u64 pfr1;
	u64 ssbs;

	if (!system || system_capabilities_finalized() ||
	    memchr_inv(system, 0, sizeof(*system)))
		return -EINVAL;

	pfr1 = read_sanitised_ftr_reg(SYS_ID_AA64PFR1_EL1);
	ssbs = cpuid_feature_extract_unsigned_field(pfr1,
						    ID_AA64PFR1_EL1_SSBS_SHIFT);
	if (ssbs > 2)
		return -ERANGE;

	/* Preserve the exact CTR owner state; SSBS consumers need availability. */
	system->ctr_sys_val = arm64_ftr_reg_ctrel0.sys_val;
	system->ctr_strict_mask = arm64_ftr_reg_ctrel0.strict_mask;
	system->ssbs = !!ssbs;
	system->valid = ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |
			ARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID;

	return 0;
}
#endif

'''


MITIGATION_PRODUCER = '''#ifdef CONFIG_ARM64_LATE_CPU_PROFILE
static int __init
late_cpu_current_mitigation_state(enum mitigation_state state, u8 *value)
{
	switch (state) {
	case SPECTRE_UNAFFECTED:
		*value = ARM64_LATE_CPU_MITIGATION_UNAFFECTED;
		return 0;
	case SPECTRE_MITIGATED:
		*value = ARM64_LATE_CPU_MITIGATION_MITIGATED;
		return 0;
	case SPECTRE_VULNERABLE:
		*value = ARM64_LATE_CPU_MITIGATION_VULNERABLE;
		return 0;
	default:
		return -ERANGE;
	}
}

static int __init late_cpu_current_smccc_conduit(u8 *value)
{
	switch (arm_smccc_1_1_get_conduit()) {
	case SMCCC_CONDUIT_NONE:
		*value = ARM64_LATE_CPU_SMCCC_NONE;
		return 0;
	case SMCCC_CONDUIT_SMC:
		*value = ARM64_LATE_CPU_SMCCC_SMC;
		return 0;
	case SMCCC_CONDUIT_HVC:
		*value = ARM64_LATE_CPU_SMCCC_HVC;
		return 0;
	default:
		return -ERANGE;
	}
}

static int __init late_cpu_current_v4_policy(u8 *value)
{
	switch (READ_ONCE(__spectre_v4_policy)) {
	case SPECTRE_V4_POLICY_MITIGATION_DYNAMIC:
		*value = ARM64_LATE_CPU_V4_POLICY_DYNAMIC;
		return 0;
	case SPECTRE_V4_POLICY_MITIGATION_ENABLED:
		*value = ARM64_LATE_CPU_V4_POLICY_FORCE_ON;
		return 0;
	case SPECTRE_V4_POLICY_MITIGATION_DISABLED:
		*value = ARM64_LATE_CPU_V4_POLICY_FORCE_OFF;
		return 0;
	default:
		return -ERANGE;
	}
}

int __init
arm64_late_cpu_collect_policy(struct arm64_late_cpu_target_policy_evidence *policy,
			      struct arm64_late_cpu_system_cap_evidence *system)
{
	unsigned long bhb_methods = READ_ONCE(system_bhb_mitigations);
	int ret;

	if (!policy || !system || system_capabilities_finalized() ||
	    memchr_inv(policy, 0, sizeof(*policy)) ||
	    system->valid != (ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID |
			      ARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID) ||
	    bhb_methods & ~GENMASK(BHB_INSN, BHB_LOOP))
		return -EINVAL;

	ret = late_cpu_current_smccc_conduit(&policy->smccc_conduit);
	if (ret)
		return ret;
	ret = late_cpu_current_v4_policy(&policy->spectre_v4_policy);
	if (ret)
		return ret;
	ret = late_cpu_current_mitigation_state(arm64_get_spectre_v2_state(),
						&system->spectre_v2_state);
	if (ret)
		return ret;
	ret = late_cpu_current_mitigation_state(arm64_get_spectre_v4_state(),
						&system->spectre_v4_state);
	if (ret)
		return ret;
	ret = late_cpu_current_mitigation_state(arm64_get_spectre_bhb_state(),
						&system->bhb_state);
	if (ret)
		return ret;

	policy->mitigations_off = cpu_mitigations_off();
	policy->nospectre_v2 = READ_ONCE(__nospectre_v2);
	policy->valid = ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK;
	system->bhb_matcher_loop_count = get_spectre_bhb_loop_value();
	system->bhb_system_method = bhb_methods;
	system->valid |= ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID;

	return 0;
}
#endif

'''


SCHEMA_BLOCK = '''#define ARM64_LATE_CPU_EXPECTED_PAIR_ABI	1

enum arm64_late_cpu_expected_pair_field {
	ARM64_LATE_CPU_EXPECT_SOURCE_IDENTITY,
	ARM64_LATE_CPU_EXPECT_CAPSULE_IDENTITY,
	ARM64_LATE_CPU_EXPECT_MPIDR,
	ARM64_LATE_CPU_EXPECT_MIDR,
	ARM64_LATE_CPU_EXPECT_REVIDR,
	ARM64_LATE_CPU_EXPECT_CNTFRQ,
	ARM64_LATE_CPU_EXPECT_CTR,
	ARM64_LATE_CPU_EXPECT_DCZID,
	ARM64_LATE_CPU_EXPECT_CLIDR,
	ARM64_LATE_CPU_EXPECT_AA64DFR0,
	ARM64_LATE_CPU_EXPECT_AA64ISAR0,
	ARM64_LATE_CPU_EXPECT_AA64ISAR1,
	ARM64_LATE_CPU_EXPECT_AA64MMFR0,
	ARM64_LATE_CPU_EXPECT_AA64MMFR1,
	ARM64_LATE_CPU_EXPECT_AA64PFR0,
	ARM64_LATE_CPU_EXPECT_AA64PFR1,
	ARM64_LATE_CPU_EXPECT_A32ISAR0,
	ARM64_LATE_CPU_EXPECT_A32ISAR1,
	ARM64_LATE_CPU_EXPECT_A32ISAR2,
	ARM64_LATE_CPU_EXPECT_A32ISAR3,
	ARM64_LATE_CPU_EXPECT_A32ISAR4,
	ARM64_LATE_CPU_EXPECT_A32ISAR5,
	ARM64_LATE_CPU_EXPECT_A32MMFR0,
	ARM64_LATE_CPU_EXPECT_A32MMFR1,
	ARM64_LATE_CPU_EXPECT_A32MMFR2,
	ARM64_LATE_CPU_EXPECT_A32MMFR3,
	ARM64_LATE_CPU_EXPECT_A32PFR0,
	ARM64_LATE_CPU_EXPECT_A32PFR1,
	ARM64_LATE_CPU_EXPECT_FIELD_COUNT,
};

#define ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK				\\
	GENMASK_ULL(ARM64_LATE_CPU_EXPECT_FIELD_COUNT - 1, 0)

/* Prior-cycle expectation; no field is a current-boot observation. */
struct arm64_late_cpu_expected_pair {
	u32 abi;
	u32 target_count;
	u64 valid;
	u64 source_identity[ARM64_LATE_CPU_ID_WORDS];
	u64 capsule_identity[ARM64_LATE_CPU_MAX_TARGETS];
	u64 mpidr[ARM64_LATE_CPU_MAX_TARGETS];
	u64 midr;
	u64 revidr;
	u64 cntfrq;
	u64 ctr;
	u64 dczid;
	u64 clidr_el1;
	u64 id_aa64dfr0;
	u64 id_aa64isar0;
	u64 id_aa64isar1;
	u64 id_aa64mmfr0;
	u64 id_aa64mmfr1;
	u64 id_aa64pfr0;
	u64 id_aa64pfr1;
	u32 id_isar0;
	u32 id_isar1;
	u32 id_isar2;
	u32 id_isar3;
	u32 id_isar4;
	u32 id_isar5;
	u32 id_mmfr0;
	u32 id_mmfr1;
	u32 id_mmfr2;
	u32 id_mmfr3;
	u32 id_pfr0;
	u32 id_pfr1;
};

'''


VALIDATOR_BLOCK = '''static bool
late_expected_pair_complete(const struct arm64_late_cpu_plan *plan)
{
	const struct arm64_late_cpu_expected_pair *expected =
		&plan->evidence.expected_pair;
	unsigned int target;

	if (expected->abi != ARM64_LATE_CPU_EXPECTED_PAIR_ABI ||
	    expected->target_count != ARM64_LATE_CPU_MAX_TARGETS ||
	    expected->valid != ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK ||
	    late_profile_identity_empty(expected->source_identity) ||
	    cpumask_weight(&plan->target_cpus) != expected->target_count)
		return false;

	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		if (!expected->capsule_identity[target] ||
		    expected->mpidr[target] !=
			    plan->evidence.expected_target_mpidr[target] ||
		    expected->midr !=
			    plan->evidence.expected_target_midr[target])
			return false;

	return true;
}

static bool
late_expected_target_matches(const struct arm64_late_cpu_expected_pair *expected,
			     unsigned int target,
			     const struct cpuinfo_arm64 *info)
{
	const struct cpuinfo_32bit *aarch32 = &info->aarch32;
	u64 mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK;

	return expected->mpidr[target] == mpidr &&
	       expected->midr == info->reg_midr &&
	       expected->revidr == info->reg_revidr &&
	       expected->cntfrq == info->reg_cntfrq &&
	       expected->ctr == read_cpuid_cachetype() &&
	       expected->dczid == info->reg_dczid &&
	       expected->clidr_el1 == read_sysreg(clidr_el1) &&
	       expected->id_aa64dfr0 == info->reg_id_aa64dfr0 &&
	       expected->id_aa64isar0 == info->reg_id_aa64isar0 &&
	       expected->id_aa64isar1 == info->reg_id_aa64isar1 &&
	       expected->id_aa64mmfr0 == info->reg_id_aa64mmfr0 &&
	       expected->id_aa64mmfr1 == info->reg_id_aa64mmfr1 &&
	       expected->id_aa64pfr0 == info->reg_id_aa64pfr0 &&
	       expected->id_aa64pfr1 == info->reg_id_aa64pfr1 &&
	       expected->id_isar0 == aarch32->reg_id_isar0 &&
	       expected->id_isar1 == aarch32->reg_id_isar1 &&
	       expected->id_isar2 == aarch32->reg_id_isar2 &&
	       expected->id_isar3 == aarch32->reg_id_isar3 &&
	       expected->id_isar4 == aarch32->reg_id_isar4 &&
	       expected->id_isar5 == aarch32->reg_id_isar5 &&
	       expected->id_mmfr0 == aarch32->reg_id_mmfr0 &&
	       expected->id_mmfr1 == aarch32->reg_id_mmfr1 &&
	       expected->id_mmfr2 == aarch32->reg_id_mmfr2 &&
	       expected->id_mmfr3 == aarch32->reg_id_mmfr3 &&
	       expected->id_pfr0 == aarch32->reg_id_pfr0 &&
	       expected->id_pfr1 == aarch32->reg_id_pfr1;
}

int arm64_validate_late_cpu_expected_target(unsigned int cpu)
{
	const struct arm64_late_cpu_expected_pair *expected;
	const struct cpuinfo_arm64 *info;
	unsigned int target;

	/* Pairs with READY publication of late_plan and late_receipt. */
	if (smp_load_acquire(&late_receipt.state) !=
	    ARM64_LATE_CPU_PROFILE_READY)
		return 0;
	if (!cpumask_test_cpu(cpu, &late_plan.target_cpus))
		return 0;
	if (cpu != smp_processor_id() || !late_expected_pair_complete(&late_plan))
		return -EINVAL;

	for (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
		if (late_plan.evidence.target_cpu[target] == cpu)
			break;
	if (target == ARM64_LATE_CPU_MAX_TARGETS)
		return -EINVAL;

	expected = &late_plan.evidence.expected_pair;
	info = this_cpu_ptr(&cpu_data);
	return late_expected_target_matches(expected, target, info) ? 0 : -ERANGE;
}

'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_file(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"source path is not an exact file: {relative}")
    return path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"source anchor count changed in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate_parent(root: Path, stage: str) -> None:
    if stage == "system-policy":
        for relative, expected in SYSTEM_POLICY_PARENT_HASHES.items():
            if sha256(require_file(root, relative)) != expected:
                raise SystemExit(f"system-policy source hash changed: {relative}")
        return

    if stage == "stack-fix":
        for relative, expected in STACK_PARENT_HASHES.items():
            if sha256(require_file(root, relative)) != expected:
                raise SystemExit(f"stack-fix source hash changed: {relative}")
        return

    if stage == "runtime-fix":
        for relative, expected in RUNTIME_PARENT_HASHES.items():
            if sha256(require_file(root, relative)) != expected:
                raise SystemExit(f"runtime source hash changed: {relative}")
        return

    relatives = tuple(PARENT_HASHES)
    if stage == "schema":
        for relative in relatives:
            if sha256(require_file(root, relative)) != PARENT_HASHES[relative]:
                raise SystemExit(f"source hash changed: {relative}")
        return

    for relative in (relatives[2],):
        if sha256(require_file(root, relative)) != PARENT_HASHES[relative]:
            raise SystemExit(f"source hash changed before validator: {relative}")
    header = require_file(root, relatives[0]).read_text(encoding="utf-8")
    core = require_file(root, relatives[1]).read_text(encoding="utf-8")
    if header.count("struct arm64_late_cpu_expected_pair {") != 1:
        raise SystemExit("schema stage is absent before validator")
    if header.count("struct arm64_late_cpu_expected_pair expected_pair;") != 1:
        raise SystemExit("expected pair is absent from evidence")
    if core.count("&late_runtime_evidence.expected_pair") != 1:
        raise SystemExit("runtime evidence empty-storage gate is absent")


def apply_schema(root: Path) -> None:
    header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    replace_once(
        header,
        "struct arm64_late_cpu_target_cap_evidence {\n",
        SCHEMA_BLOCK + "struct arm64_late_cpu_target_cap_evidence {\n",
    )
    replace_once(
        header,
        "struct arm64_late_cpu_evidence {\n"
        "\tu32 abi;\n"
        "\t/* Non-circular inputs; neither field proves the running image/config. */\n"
        "\tu64 source_parent_identity[ARM64_LATE_CPU_ID_WORDS];\n"
        "\tu64 config_input_identity[ARM64_LATE_CPU_ID_WORDS];\n"
        "\tstruct arm64_late_cpu_runtime_binding binding;\n",
        "struct arm64_late_cpu_evidence {\n"
        "\tu32 abi;\n"
        "\t/* Non-circular inputs; neither field proves the running image/config. */\n"
        "\tu64 source_parent_identity[ARM64_LATE_CPU_ID_WORDS];\n"
        "\tu64 config_input_identity[ARM64_LATE_CPU_ID_WORDS];\n"
        "\tstruct arm64_late_cpu_expected_pair expected_pair;\n"
        "\tstruct arm64_late_cpu_runtime_binding binding;\n",
    )
    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    replace_once(
        core,
        "\t    !late_profile_identity_empty(late_runtime_evidence.config_input_identity) ||\n"
        "\t    !late_profile_binding_empty(&late_runtime_evidence.binding) ||\n",
        "\t    !late_profile_identity_empty(late_runtime_evidence.config_input_identity) ||\n"
        "\t    memchr_inv(&late_runtime_evidence.expected_pair, 0,\n"
        "\t\t       sizeof(late_runtime_evidence.expected_pair)) ||\n"
        "\t    !late_profile_binding_empty(&late_runtime_evidence.binding) ||\n",
    )


def apply_validator(root: Path) -> None:
    header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    replace_once(
        header,
        "void __init arm64_collect_late_cpu_runtime_identity(void);\n",
        "void __init arm64_collect_late_cpu_runtime_identity(void);\n"
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);\n",
    )
    replace_once(
        header,
        "static inline void __init arm64_collect_late_cpu_runtime_identity(void)\n"
        "{\n}\n",
        "static inline void __init arm64_collect_late_cpu_runtime_identity(void)\n"
        "{\n}\n\n"
        "static inline int\n"
        "arm64_validate_late_cpu_expected_target(unsigned int cpu)\n"
        "{\n\treturn 0;\n}\n",
    )

    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    replace_once(
        core,
        "#include <asm/cpufeature.h>\n#include <asm/late_cpu_profile.h>\n",
        "#include <asm/cpu.h>\n#include <asm/cpufeature.h>\n"
        "#include <asm/cputype.h>\n#include <asm/late_cpu_profile.h>\n"
        "#include <asm/sysreg.h>\n",
    )
    replace_once(
        core,
        "const struct arm64_late_cpu_ready_token *\n"
        "arm64_get_late_cpu_ready_token(void)\n",
        VALIDATOR_BLOCK
        + "const struct arm64_late_cpu_ready_token *\n"
        + "arm64_get_late_cpu_ready_token(void)\n",
    )

    smp = root / "arch/arm64/kernel/smp.c"
    replace_once(
        smp,
        "\tconst struct cpu_operations *ops;\n\tunsigned int cpu = smp_processor_id();\n",
        "\tconst struct cpu_operations *ops;\n"
        "\tunsigned int cpu = smp_processor_id();\n"
        "\tint expectation_ret;\n",
    )
    replace_once(
        smp,
        "\tcpuinfo_store_cpu();\n\tstore_cpu_topology(cpu);\n",
        "\tcpuinfo_store_cpu();\n"
        "\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu);\n"
        "\tif (expectation_ret) {\n"
        "\t\tpr_crit(\"CPU%u: late target expectation mismatch: %d\\n\",\n"
        "\t\t\tcpu, expectation_ret);\n"
        "\t\tupdate_cpu_boot_status(CPU_STUCK_IN_KERNEL);\n"
        "\t\tcpu_park_loop();\n"
        "\t}\n"
        "\tstore_cpu_topology(cpu);\n",
    )


def apply_runtime_fix(root: Path) -> None:
    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    replace_once(
        core,
        "\t    late_profile_identity_empty(expected->source_identity) ||\n",
        "\t    !memchr_inv(expected->source_identity, 0,\n"
        "\t\t\t   sizeof(expected->source_identity)) ||\n",
    )


def apply_stack_fix(root: Path) -> None:
    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    replace_once(
        core,
        "static struct arm64_late_cpu_plan late_plan __ro_after_init;\n",
        "static struct arm64_late_cpu_evidence profile_evidence __initdata;\n"
        "static struct arm64_late_cpu_plan draft __initdata;\n"
        "static struct arm64_late_cpu_plan late_plan __ro_after_init;\n",
    )
    replace_once(
        core,
        "\tstruct arm64_late_cpu_evidence profile_evidence = {\n"
        "\t\t.abi = ARM64_LATE_CPU_PLAN_ABI,\n"
        "\t};\n"
        "\tstruct arm64_late_cpu_plan draft = {\n"
        "\t\t.abi = ARM64_LATE_CPU_PLAN_ABI,\n"
        "\t};\n",
        "",
    )
    replace_once(
        core,
        "\tint ret;\n\n"
        "\tif (!late_profile_active && !late_profile_registration_fault)\n",
        "\tint ret;\n\n"
        "\tmemset(&profile_evidence, 0, sizeof(profile_evidence));\n"
        "\tprofile_evidence.abi = ARM64_LATE_CPU_PLAN_ABI;\n"
        "\tmemset(&draft, 0, sizeof(draft));\n"
        "\tdraft.abi = ARM64_LATE_CPU_PLAN_ABI;\n\n"
        "\tif (!late_profile_active && !late_profile_registration_fault)\n",
    )


def apply_system_policy(root: Path) -> None:
    header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    replace_once(
        header,
        "void __init arm64_collect_late_cpu_runtime_identity(void);\n"
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);\n",
        "void __init arm64_collect_late_cpu_runtime_identity(void);\n"
        "void __init arm64_collect_late_cpu_runtime_system_policy(void);\n"
        "int __init arm64_late_cpu_collect_system("
        "struct arm64_late_cpu_system_cap_evidence *system);\n"
        "int __init\n"
        "arm64_late_cpu_collect_policy("
        "struct arm64_late_cpu_target_policy_evidence *policy,\n"
        "\t\t\t      struct arm64_late_cpu_system_cap_evidence *system);\n"
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);\n",
    )
    replace_once(
        header,
        "static inline void __init arm64_collect_late_cpu_runtime_identity(void)\n"
        "{\n}\n\n"
        "static inline int\n",
        "static inline void __init arm64_collect_late_cpu_runtime_identity(void)\n"
        "{\n}\n\n"
        "static inline void __init\n"
        "arm64_collect_late_cpu_runtime_system_policy(void)\n"
        "{\n}\n\n"
        "static inline int\n",
    )

    cpufeature = root / "arch/arm64/kernel/cpufeature.c"
    replace_once(
        cpufeature,
        "#include <linux/stop_machine.h>\n",
        "#include <linux/stop_machine.h>\n#include <linux/string.h>\n",
    )
    replace_once(
        cpufeature,
        "static void user_feature_fixup(void)\n",
        SYSTEM_CAP_PRODUCER + "static void user_feature_fixup(void)\n",
    )

    proton = root / "arch/arm64/kernel/proton-pack.c"
    replace_once(
        proton,
        "#include <linux/sched/task_stack.h>\n",
        "#include <linux/sched/task_stack.h>\n#include <linux/string.h>\n",
    )
    replace_once(
        proton,
        "u8 get_spectre_bhb_loop_value(void)\n"
        "{\n"
        "\treturn max_bhb_k;\n"
        "}\n\n"
        "static void this_cpu_set_vectors("
        "enum arm64_bp_harden_el1_vectors slot)\n",
        "u8 get_spectre_bhb_loop_value(void)\n"
        "{\n"
        "\treturn max_bhb_k;\n"
        "}\n\n"
        + MITIGATION_PRODUCER
        + "static void this_cpu_set_vectors("
        "enum arm64_bp_harden_el1_vectors slot)\n",
    )

    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    replace_once(
        core,
        "\tLATE_RUNTIME_EVIDENCE_SEALED_EMPTY,\n"
        "\tLATE_RUNTIME_EVIDENCE_SEALED_IDENTITY,\n",
        "\tLATE_RUNTIME_EVIDENCE_SEALED_SYSTEM_POLICY,\n"
        "\tLATE_RUNTIME_EVIDENCE_SEALED_IDENTITY_SYSTEM_POLICY,\n",
    )
    replace_once(
        core,
        "static bool __init\n"
        "late_profile_binding_empty",
        "static bool __init late_runtime_evidence_storage_empty(void);\n\n"
        "void __init arm64_collect_late_cpu_runtime_system_policy(void)\n"
        "{\n"
        "\tstruct arm64_late_cpu_target_policy_evidence policy = {};\n"
        "\tstruct arm64_late_cpu_system_cap_evidence system = {};\n"
        "\tunsigned int target;\n"
        "\tint ret;\n\n"
        "\tif (READ_ONCE(late_runtime_evidence_state) !=\n"
        "\t\t    LATE_RUNTIME_EVIDENCE_OPEN ||\n"
        "\t    READ_ONCE(late_runtime_identity_state) ==\n"
        "\t\t    LATE_RUNTIME_IDENTITY_UNCOLLECTED ||\n"
        "\t    system_capabilities_finalized() ||\n"
        "\t    cpus_have_cap(ARM64_ALWAYS_SYSTEM) ||\n"
        "\t    !late_runtime_evidence_storage_empty()) {\n"
        "\t\tWRITE_ONCE(late_runtime_evidence_state,\n"
        "\t\t\t   LATE_RUNTIME_EVIDENCE_FAULT);\n"
        "\t\treturn;\n"
        "\t}\n\n"
        "\tret = arm64_late_cpu_collect_system(&system);\n"
        "\tif (!ret)\n"
        "\t\tret = arm64_late_cpu_collect_policy(&policy, &system);\n"
        "\tif (ret ||\n"
        "\t    system.valid != ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK ||\n"
        "\t    policy.valid != ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK) {\n"
        "\t\tWRITE_ONCE(late_runtime_evidence_state,\n"
        "\t\t\t   LATE_RUNTIME_EVIDENCE_FAULT);\n"
        "\t\treturn;\n"
        "\t}\n\n"
        "\tlate_runtime_evidence.system_cap = system;\n"
        "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)\n"
        "\t\tlate_runtime_evidence.target_policy[target] = policy;\n"
        "}\n\n"
        "static bool __init\n"
        "late_profile_binding_empty",
    )
    replace_once(
        core,
        "static bool __init\n"
        "late_profile_identity_cross_bound",
        "static bool __init\n"
        "late_runtime_system_policy_complete(void)\n"
        "{\n"
        "\tconst struct arm64_late_cpu_system_cap_evidence *system =\n"
        "\t\t&late_runtime_evidence.system_cap;\n"
        "\tconst struct arm64_late_cpu_target_policy_evidence *first =\n"
        "\t\t&late_runtime_evidence.target_policy[0];\n"
        "\tunsigned int target;\n\n"
        "\tif (system->valid != ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK ||\n"
        "\t    !system->ctr_strict_mask || system->ssbs > 1 ||\n"
        "\t    system->spectre_v2_state <\n"
        "\t\t    ARM64_LATE_CPU_MITIGATION_UNAFFECTED ||\n"
        "\t    system->spectre_v2_state >\n"
        "\t\t    ARM64_LATE_CPU_MITIGATION_VULNERABLE ||\n"
        "\t    system->spectre_v4_state <\n"
        "\t\t    ARM64_LATE_CPU_MITIGATION_UNAFFECTED ||\n"
        "\t    system->spectre_v4_state >\n"
        "\t\t    ARM64_LATE_CPU_MITIGATION_VULNERABLE ||\n"
        "\t    system->bhb_state < ARM64_LATE_CPU_BHB_STATE_UNAFFECTED ||\n"
        "\t    system->bhb_state > ARM64_LATE_CPU_BHB_STATE_VULNERABLE ||\n"
        "\t    system->bhb_system_method & ~GENMASK(3, 0) ||\n"
        "\t    first->valid != ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK ||\n"
        "\t    first->smccc_conduit < ARM64_LATE_CPU_SMCCC_NONE ||\n"
        "\t    first->smccc_conduit > ARM64_LATE_CPU_SMCCC_HVC ||\n"
        "\t    first->mitigations_off > 1 || first->nospectre_v2 > 1 ||\n"
        "\t    first->spectre_v4_policy <\n"
        "\t\t    ARM64_LATE_CPU_V4_POLICY_DYNAMIC ||\n"
        "\t    first->spectre_v4_policy >\n"
        "\t\t    ARM64_LATE_CPU_V4_POLICY_FORCE_OFF)\n"
        "\t\treturn false;\n\n"
        "\tfor (target = 1; target < ARM64_LATE_CPU_MAX_TARGETS; target++)\n"
        "\t\tif (memcmp(first, &late_runtime_evidence.target_policy[target],\n"
        "\t\t\t   sizeof(*first)))\n"
        "\t\t\treturn false;\n\n"
        "\treturn true;\n"
        "}\n\n"
        "static bool __init\n"
        "late_runtime_evidence_storage_complete(void)\n"
        "{\n"
        "\tunsigned int target;\n\n"
        "\tif (late_runtime_evidence.abi != ARM64_LATE_CPU_PLAN_ABI ||\n"
        "\t    !late_profile_identity_empty("
        "late_runtime_evidence.source_parent_identity) ||\n"
        "\t    !late_profile_identity_empty("
        "late_runtime_evidence.config_input_identity) ||\n"
        "\t    memchr_inv(&late_runtime_evidence.expected_pair, 0,\n"
        "\t\t       sizeof(late_runtime_evidence.expected_pair)) ||\n"
        "\t    !late_profile_binding_empty(&late_runtime_evidence.binding) ||\n"
        "\t    !late_profile_identity_empty("
        "late_runtime_evidence.evidence_identity) ||\n"
        "\t    late_runtime_evidence.blocker_mask ||\n"
        "\t    !late_runtime_system_policy_complete())\n"
        "\t\treturn false;\n\n"
        "\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)\n"
        "\t\tif (late_runtime_evidence.target_cpu[target] ||\n"
        "\t\t    late_runtime_evidence.expected_target_mpidr[target] ||\n"
        "\t\t    late_runtime_evidence.observed_target_mpidr[target] ||\n"
        "\t\t    late_runtime_evidence.expected_target_midr[target] ||\n"
        "\t\t    late_runtime_evidence.observed_target_midr[target] ||\n"
        "\t\t    late_runtime_evidence.observed_target_revidr[target] ||\n"
        "\t\t    memchr_inv(&late_runtime_evidence.target_cap[target], 0,\n"
        "\t\t\t       sizeof(late_runtime_evidence.target_cap[target])))\n"
        "\t\t\treturn false;\n\n"
        "\treturn true;\n"
        "}\n\n"
        "static bool __init\n"
        "late_profile_identity_cross_bound",
    )
    replace_once(
        core,
        "\tif (!late_runtime_evidence_storage_empty() ||\n"
        "\t    identity_state == LATE_RUNTIME_IDENTITY_UNCOLLECTED) {\n",
        "\tif (!late_runtime_evidence_storage_complete() ||\n"
        "\t    identity_state == LATE_RUNTIME_IDENTITY_UNCOLLECTED) {\n",
    )
    replace_once(
        core,
        "\t\tstate = LATE_RUNTIME_EVIDENCE_SEALED_EMPTY;\n",
        "\t\tstate = LATE_RUNTIME_EVIDENCE_SEALED_SYSTEM_POLICY;\n",
    )
    replace_once(
        core,
        "\t\tstate = LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY;\n",
        "\t\tstate =\n"
        "\t\t\tLATE_RUNTIME_EVIDENCE_SEALED_IDENTITY_SYSTEM_POLICY;\n",
    )
    replace_once(
        core,
        "\tif (runtime_state != LATE_RUNTIME_EVIDENCE_SEALED_EMPTY &&\n"
        "\t    runtime_state != LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY) {\n",
        "\tif (runtime_state !=\n"
        "\t\t    LATE_RUNTIME_EVIDENCE_SEALED_SYSTEM_POLICY &&\n"
        "\t    runtime_state !=\n"
        "\t\t    LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY_SYSTEM_POLICY) {\n",
    )
    replace_once(
        core,
        "\t\tif (runtime_state == LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY) {\n",
        "\t\tif (runtime_state ==\n"
        "\t\t    LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY_SYSTEM_POLICY) {\n",
    )
    replace_once(
        core,
        "\t\t\tdraft.evidence.binding = late_runtime_evidence.binding;\n"
        "\t\t\tdraft.evidence.blocker_mask &=\n",
        "\t\t\tdraft.evidence.binding = late_runtime_evidence.binding;\n"
        "\t\t\tdraft.evidence.system_cap =\n"
        "\t\t\t\tlate_runtime_evidence.system_cap;\n"
        "\t\t\tfor (target = 0;\n"
        "\t\t\t     target < ARM64_LATE_CPU_MAX_TARGETS; target++)\n"
        "\t\t\t\tdraft.evidence.target_policy[target] =\n"
        "\t\t\t\t\tlate_runtime_evidence.target_policy[target];\n"
        "\t\t\tdraft.evidence.blocker_mask &=\n",
    )
    replace_once(
        core,
        "\tu32 runtime_state;\n\tint validate_ret;\n",
        "\tu32 runtime_state;\n\tunsigned int target;\n\tint validate_ret;\n",
    )

    smp = root / "arch/arm64/kernel/smp.c"
    replace_once(
        smp,
        "\tarm64_collect_late_cpu_runtime_identity();\n"
        "\tarm64_seal_late_cpu_runtime_evidence();\n",
        "\tarm64_collect_late_cpu_runtime_identity();\n"
        "\tarm64_collect_late_cpu_runtime_system_policy();\n"
        "\tarm64_seal_late_cpu_runtime_evidence();\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=("schema", "validator", "runtime-fix", "stack-fix",
                 "system-policy"),
        required=True,
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_parent(root, args.stage)
    if args.stage == "schema":
        apply_schema(root)
    elif args.stage == "validator":
        apply_validator(root)
    elif args.stage == "runtime-fix":
        apply_runtime_fix(root)
    elif args.stage == "stack-fix":
        apply_stack_fix(root)
    else:
        apply_system_policy(root)


if __name__ == "__main__":
    main()
