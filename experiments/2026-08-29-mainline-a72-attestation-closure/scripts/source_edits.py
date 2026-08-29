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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("schema", "validator"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_parent(root, args.stage)
    if args.stage == "schema":
        apply_schema(root)
    else:
        apply_validator(root)


if __name__ == "__main__":
    main()
