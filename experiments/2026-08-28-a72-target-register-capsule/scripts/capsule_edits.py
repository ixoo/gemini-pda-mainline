#!/usr/bin/env python3
"""Add bounded target-register capsules to the exact scheduler parent."""

from __future__ import annotations

import argparse
from pathlib import Path


class EditError(RuntimeError):
    pass


INCLUDE_PARENT = "#include <asm/compiler.h>\n#include <asm/cpu_ops.h>\n"
INCLUDE_CHILD = (
    "#include <asm/arch_timer.h>\n"
    "#include <asm/compiler.h>\n"
    "#include <asm/cpu.h>\n"
    "#include <asm/cpu_ops.h>\n"
    "#include <asm/cputype.h>\n"
)

CAPSULE_ANCHOR = "struct mt6797_a72_sc_result {\n"
CAPSULE_BLOCK = r'''#define MT6797_A72_REGCAP_ABI 1
#define MT6797_A72_REGCAP_FIELDS 32
#define MT6797_A72_REGCAP_VALID_IDENTITY BIT(0)
#define MT6797_A72_REGCAP_VALID_CACHE BIT(1)
#define MT6797_A72_REGCAP_VALID_AA64_ID BIT(2)
#define MT6797_A72_REGCAP_VALID_A32_ID BIT(3)
#define MT6797_A72_REGCAP_VALID_CPUINFO BIT(4)
#define MT6797_A72_REGCAP_VALID_MASK 0x1f

struct mt6797_a72_regcap_v1 {
	u32 abi;
	u32 fields;
	u32 valid;
	s32 error;
	u32 cpu;
	u32 midr;
	u32 revidr;
	u32 cntfrq;
	u32 ctr;
	u32 dczid;
	u32 cpuinfo_match;
	u64 mpidr;
	u64 clidr;
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
	u64 identity;
	u32 complete;
};

static u64 mt6797_a72_regcap_mix(u64 identity, u64 value)
{
	return (identity ^ value) * MT6797_A72_SC_HASH_PRIME;
}

static u64 mt6797_a72_regcap_identity(const struct mt6797_a72_regcap_v1 *capsule)
{
	u64 identity = MT6797_A72_SC_HASH_INIT;

	identity = mt6797_a72_regcap_mix(identity, capsule->abi);
	identity = mt6797_a72_regcap_mix(identity, capsule->fields);
	identity = mt6797_a72_regcap_mix(identity, capsule->valid);
	identity = mt6797_a72_regcap_mix(identity, (u32)capsule->error);
	identity = mt6797_a72_regcap_mix(identity, capsule->cpu);
	identity = mt6797_a72_regcap_mix(identity, capsule->midr);
	identity = mt6797_a72_regcap_mix(identity, capsule->revidr);
	identity = mt6797_a72_regcap_mix(identity, capsule->cntfrq);
	identity = mt6797_a72_regcap_mix(identity, capsule->ctr);
	identity = mt6797_a72_regcap_mix(identity, capsule->dczid);
	identity = mt6797_a72_regcap_mix(identity, capsule->cpuinfo_match);
	identity = mt6797_a72_regcap_mix(identity, capsule->mpidr);
	identity = mt6797_a72_regcap_mix(identity, capsule->clidr);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_aa64dfr0);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_aa64isar0);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_aa64isar1);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_aa64mmfr0);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_aa64mmfr1);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_aa64pfr0);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_aa64pfr1);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_isar0);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_isar1);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_isar2);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_isar3);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_isar4);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_isar5);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_mmfr0);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_mmfr1);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_mmfr2);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_mmfr3);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_pfr0);
	identity = mt6797_a72_regcap_mix(identity, capsule->id_pfr1);
	return identity;
}

static bool
mt6797_a72_regcap_cpuinfo_match(const struct mt6797_a72_regcap_v1 *capsule,
				const struct cpuinfo_arm64 *info)
{
	return capsule->cntfrq == info->reg_cntfrq &&
	       capsule->ctr == info->reg_ctr &&
	       capsule->dczid == info->reg_dczid &&
	       capsule->midr == info->reg_midr &&
	       capsule->id_aa64isar0 == info->reg_id_aa64isar0 &&
	       capsule->id_aa64isar1 == info->reg_id_aa64isar1 &&
	       capsule->id_aa64mmfr0 == info->reg_id_aa64mmfr0 &&
	       capsule->id_aa64mmfr1 == info->reg_id_aa64mmfr1 &&
	       capsule->id_aa64pfr0 == info->reg_id_aa64pfr0 &&
	       capsule->id_aa64pfr1 == info->reg_id_aa64pfr1 &&
	       capsule->id_isar0 == info->reg_id_isar0 &&
	       capsule->id_isar1 == info->reg_id_isar1 &&
	       capsule->id_isar2 == info->reg_id_isar2 &&
	       capsule->id_isar3 == info->reg_id_isar3 &&
	       capsule->id_isar4 == info->reg_id_isar4 &&
	       capsule->id_isar5 == info->reg_id_isar5 &&
	       capsule->id_mmfr0 == info->reg_id_mmfr0 &&
	       capsule->id_mmfr1 == info->reg_id_mmfr1 &&
	       capsule->id_mmfr2 == info->reg_id_mmfr2 &&
	       capsule->id_mmfr3 == info->reg_id_mmfr3 &&
	       capsule->id_pfr0 == info->reg_id_pfr0 &&
	       capsule->id_pfr1 == info->reg_id_pfr1;
}

static int
mt6797_a72_regcap_capture(struct mt6797_a72_regcap_v1 *capsule, int expected_cpu)
{
	const struct cpuinfo_arm64 *info;
	u64 expected_mpidr;
	int cpu;
	int error = 0;

	capsule->abi = MT6797_A72_REGCAP_ABI;
	capsule->fields = MT6797_A72_REGCAP_FIELDS;
	if (expected_cpu != 8 && expected_cpu != 9) {
		error = -EINVAL;
		goto publish;
	}
	expected_mpidr = expected_cpu == 8 ? 0x200ULL : 0x201ULL;
	cpu = get_cpu();
	capsule->cpu = cpu;
	if (cpu != expected_cpu) {
		error = -EXDEV;
		goto out_cpu;
	}
	info = this_cpu_ptr(&cpu_data);
	capsule->mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK;
	capsule->midr = read_cpuid_id();
	capsule->revidr = read_cpuid(REVIDR_EL1);
	capsule->cntfrq = arch_timer_get_cntfrq();
	capsule->ctr = read_cpuid_cachetype();
	capsule->dczid = read_cpuid(DCZID_EL0);
	capsule->clidr = read_cpuid(CLIDR_EL1);
	capsule->id_aa64dfr0 = read_cpuid(ID_AA64DFR0_EL1);
	capsule->id_aa64isar0 = read_cpuid(ID_AA64ISAR0_EL1);
	capsule->id_aa64isar1 = read_cpuid(ID_AA64ISAR1_EL1);
	capsule->id_aa64mmfr0 = read_cpuid(ID_AA64MMFR0_EL1);
	capsule->id_aa64mmfr1 = read_cpuid(ID_AA64MMFR1_EL1);
	capsule->id_aa64pfr0 = read_cpuid(ID_AA64PFR0_EL1);
	capsule->id_aa64pfr1 = read_cpuid(ID_AA64PFR1_EL1);
	capsule->id_isar0 = read_cpuid(ID_ISAR0_EL1);
	capsule->id_isar1 = read_cpuid(ID_ISAR1_EL1);
	capsule->id_isar2 = read_cpuid(ID_ISAR2_EL1);
	capsule->id_isar3 = read_cpuid(ID_ISAR3_EL1);
	capsule->id_isar4 = read_cpuid(ID_ISAR4_EL1);
	capsule->id_isar5 = read_cpuid(ID_ISAR5_EL1);
	capsule->id_mmfr0 = read_cpuid(ID_MMFR0_EL1);
	capsule->id_mmfr1 = read_cpuid(ID_MMFR1_EL1);
	capsule->id_mmfr2 = read_cpuid(ID_MMFR2_EL1);
	capsule->id_mmfr3 = read_cpuid(ID_MMFR3_EL1);
	capsule->id_pfr0 = read_cpuid(ID_PFR0_EL1);
	capsule->id_pfr1 = read_cpuid(ID_PFR1_EL1);
	capsule->valid = MT6797_A72_REGCAP_VALID_IDENTITY |
		MT6797_A72_REGCAP_VALID_CACHE |
		MT6797_A72_REGCAP_VALID_AA64_ID |
		MT6797_A72_REGCAP_VALID_A32_ID;
	if (mt6797_a72_regcap_cpuinfo_match(capsule, info)) {
		capsule->cpuinfo_match = 1;
		capsule->valid |= MT6797_A72_REGCAP_VALID_CPUINFO;
	} else {
		error = -EIO;
	}
	if (!error &&
	    (capsule->mpidr != expected_mpidr ||
	     MIDR_IMPLEMENTOR(capsule->midr) != ARM_CPU_IMP_ARM ||
	     MIDR_PARTNUM(capsule->midr) != ARM_CPU_PART_CORTEX_A72))
		error = -ENODEV;
out_cpu:
	put_cpu();
publish:
	capsule->error = error;
	capsule->identity = mt6797_a72_regcap_identity(capsule);
	/* Publish every field and the identity before exposing completion. */
	smp_wmb();
	WRITE_ONCE(capsule->complete, 1);
	return error;
}

static noinline void mt6797_a72_regcap_emit(const struct mt6797_a72_regcap_v1 *capsule)
{
	u64 expected_mpidr = capsule->cpu == 8 ? 0x200ULL : 0x201ULL;
	u32 complete = READ_ONCE(capsule->complete);
	bool passed;

	/* Pair with the capture-side barrier before consuming the capsule. */
	smp_rmb();
	passed = complete == 1 &&
		capsule->abi == MT6797_A72_REGCAP_ABI &&
		capsule->fields == MT6797_A72_REGCAP_FIELDS &&
		capsule->valid == MT6797_A72_REGCAP_VALID_MASK &&
		!capsule->error && capsule->cpuinfo_match == 1 &&
		(capsule->cpu == 8 || capsule->cpu == 9) &&
		capsule->mpidr == expected_mpidr &&
		MIDR_IMPLEMENTOR(capsule->midr) == ARM_CPU_IMP_ARM &&
		MIDR_PARTNUM(capsule->midr) == ARM_CPU_PART_CORTEX_A72 &&
		capsule->identity == mt6797_a72_regcap_identity(capsule);

	pr_emerg("gemini-a72-regcap-v1 part=core result=%s cpu=%u abi=%u fields=%u valid=%#x error=%d complete=%u identity=%016llx mpidr=%016llx midr=%08x revidr=%08x cntfrq=%08x ctr=%08x dczid=%08x clidr=%016llx\n",
		 passed ? "pass" : "fault", capsule->cpu, capsule->abi,
		 capsule->fields, capsule->valid, capsule->error,
		 complete, (unsigned long long)capsule->identity,
		 (unsigned long long)capsule->mpidr, capsule->midr,
		 capsule->revidr, capsule->cntfrq, capsule->ctr,
		 capsule->dczid, (unsigned long long)capsule->clidr);
	pr_emerg("gemini-a72-regcap-v1 part=aa64 result=%s cpu=%u identity=%016llx dfr0=%016llx isar0=%016llx isar1=%016llx mmfr0=%016llx mmfr1=%016llx pfr0=%016llx pfr1=%016llx\n",
		 passed ? "pass" : "fault", capsule->cpu,
		 (unsigned long long)capsule->identity,
		 (unsigned long long)capsule->id_aa64dfr0,
		 (unsigned long long)capsule->id_aa64isar0,
		 (unsigned long long)capsule->id_aa64isar1,
		 (unsigned long long)capsule->id_aa64mmfr0,
		 (unsigned long long)capsule->id_aa64mmfr1,
		 (unsigned long long)capsule->id_aa64pfr0,
		 (unsigned long long)capsule->id_aa64pfr1);
	pr_emerg("gemini-a72-regcap-v1 part=a32isar result=%s cpu=%u identity=%016llx isar0=%08x isar1=%08x isar2=%08x isar3=%08x isar4=%08x isar5=%08x\n",
		 passed ? "pass" : "fault", capsule->cpu,
		 (unsigned long long)capsule->identity, capsule->id_isar0,
		 capsule->id_isar1, capsule->id_isar2, capsule->id_isar3,
		 capsule->id_isar4, capsule->id_isar5);
	pr_emerg("gemini-a72-regcap-v1 part=a32mm result=%s cpu=%u identity=%016llx mmfr0=%08x mmfr1=%08x mmfr2=%08x mmfr3=%08x pfr0=%08x pfr1=%08x\n",
		 passed ? "pass" : "fault", capsule->cpu,
		 (unsigned long long)capsule->identity, capsule->id_mmfr0,
		 capsule->id_mmfr1, capsule->id_mmfr2, capsule->id_mmfr3,
		 capsule->id_pfr0, capsule->id_pfr1);
}

'''

RESULT_PARENT = "\tint rescheds;\n\tu64 hash;\n};\n"
RESULT_CHILD = (
    "\tint rescheds;\n"
    "\tu64 hash;\n"
    "\tstruct mt6797_a72_regcap_v1 regcap;\n"
    "};\n"
)

CAPTURE_CALL_PARENT = (
    "\telse if (cpu != result->expected_cpu)\n"
    "\t\terror = -EXDEV;\n\n"
    '\tpr_emerg("gemini-a72-sc-phase cpu=%d phase=task-ready-before\\n", result->expected_cpu);\n'
)
CAPTURE_CALL_CHILD = (
    "\telse if (cpu != result->expected_cpu)\n"
    "\t\terror = -EXDEV;\n"
    "\tif (!error) {\n"
    '\t\tpr_emerg("gemini-a72-sc-phase cpu=%d phase=task-capture-before\\n",\n'
    "\t\t\t result->expected_cpu);\n"
    "\t\terror = mt6797_a72_regcap_capture(&result->regcap, result->expected_cpu);\n"
    '\t\tpr_emerg("gemini-a72-sc-phase cpu=%d phase=task-capture-after\\n",\n'
    "\t\t\t result->expected_cpu);\n"
    "\t}\n\n"
    '\tpr_emerg("gemini-a72-sc-phase cpu=%d phase=task-ready-before\\n", result->expected_cpu);\n'
)

EMIT_PARENT = (
    "\t\t (unsigned long long)result8->hash,\n"
    "\t\t (unsigned long long)result9->hash);\n"
    "}\n#endif\n"
)
EMIT_CHILD = (
    "\t\t (unsigned long long)result8->hash,\n"
    "\t\t (unsigned long long)result9->hash);\n"
    "\tmt6797_a72_regcap_emit(&result8->regcap);\n"
    "\tmt6797_a72_regcap_emit(&result9->regcap);\n"
    "}\n#endif\n"
)

TRANSFORMATIONS = (
    ("includes", INCLUDE_PARENT, INCLUDE_CHILD),
    ("capsule-block", CAPSULE_ANCHOR, CAPSULE_BLOCK + CAPSULE_ANCHOR),
    ("result-field", RESULT_PARENT, RESULT_CHILD),
    ("capture-call", CAPTURE_CALL_PARENT, CAPTURE_CALL_CHILD),
    ("terminal-emission", EMIT_PARENT, EMIT_CHILD),
)


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise EditError(f"{name}: expected one anchor, found {count}")
    if new in text:
        raise EditError(f"{name}: child replacement already present")
    return text.replace(old, new, 1)


def transform_text(text: str) -> str:
    transformed = text
    for name, old, new in TRANSFORMATIONS:
        transformed = replace_once(transformed, old, new, name)
    return transformed


def reverse_text(text: str) -> str:
    restored = text
    for name, old, new in reversed(TRANSFORMATIONS):
        count = restored.count(new)
        if count != 1:
            raise EditError(f"{name}: expected one child anchor, found {count}")
        restored = restored.replace(new, old, 1)
    return restored


def edit(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"
    original = path.read_text(encoding="utf-8")
    path.write_text(transform_text(original), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    edit(args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
