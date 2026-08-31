#!/usr/bin/env python3
"""Apply exact post-capabilities P30E checkpoint and mismatch details."""

from __future__ import annotations

import hashlib
from pathlib import Path


P30E_H = Path("arch/arm64/include/asm/mt6797_a72_p30e.h")
P30E_C = Path("arch/arm64/kernel/mt6797_a72_p30e.c")
LATE_H = Path("arch/arm64/include/asm/late_cpu_profile.h")
LATE_C = Path("arch/arm64/kernel/late_cpu_profile.c")
SMP = Path("arch/arm64/kernel/smp.c")
BINDER_PUBLIC = Path("include/linux/soc/mediatek/mt6797-a72-binder.h")
BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
ADMISSION = Path("drivers/soc/mediatek/mt6797-a72-admission-controller.c")
SOURCE_FILES = (
    P30E_H,
    P30E_C,
    LATE_H,
    LATE_C,
    SMP,
    BINDER_PUBLIC,
    BINDER,
    BINDER_TEST,
    ADMISSION,
)
PARENT_SHA256 = {
    P30E_H: "e1b6fbe3a660e6455dd8f1de99e702a5f833bbab1ae5c51729464f694593fb8f",
    P30E_C: "c062a577e993266247533c1d0506afeba5e1f68a43b152af5630d21a342ed820",
    LATE_H: "ab130af5ea9bf879e851ee8266d13b96a72990f9187254044cfbb32bbf3c1f51",
    LATE_C: "96c22551262cca6533a13e0df5ad215a49861445b66232db47590e217d0803fc",
    SMP: "9405f0f13b26980faee35514c0fd26e7e5fa240ac08d3b9b4ead3a8005827776",
    BINDER_PUBLIC: "3c67c772d09382f70511b94c95c50d6e1d3ccae76a121977ea8fa7b487b67eb9",
    BINDER: "e149c5ee1a5b0d778ef9d6893fdd333a6f3371200c5a63084cdfde0b5f6539ee",
    BINDER_TEST: "6c7f8ffb6acdc03beb32e738034ec59f6f4f8a346ce531e85564fc301d8810b7",
    ADMISSION: "b91e4dfdb7202487bc1f99e6ecc9b4727b1f59a900b7c8775f359c92163cc3fe",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new)


def verify_parent(root: Path) -> None:
    for relative, expected in PARENT_SHA256.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"parent file is absent or unsafe: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(
                f"parent checksum changed for {relative}: {actual} != {expected}"
            )


def apply(root: Path) -> None:
    verify_parent(root)

    p30e_h_path = root / P30E_H
    p30e_h = p30e_h_path.read_text(encoding="utf-8")
    p30e_h = replace_once(
        p30e_h,
        """#define ARM64_MT6797_A72_P30E_CHECKPOINT_CAPABILITIES\t5
#define ARM64_MT6797_A72_P30E_CHECKPOINT_TARGET_VALID\t6
#define ARM64_MT6797_A72_P30E_CHECKPOINT_IRQ_READY\t7""",
        """#define ARM64_MT6797_A72_P30E_CHECKPOINT_CAPABILITIES\t5
#define ARM64_MT6797_A72_P30E_CHECKPOINT_CPU_OPS_READY\t6
#define ARM64_MT6797_A72_P30E_CHECKPOINT_CPUINFO_READY\t7
#define ARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_FAILED\t8
#define ARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_VALID\t9
#define ARM64_MT6797_A72_P30E_CHECKPOINT_TOPOLOGY_READY\t10
#define ARM64_MT6797_A72_P30E_CHECKPOINT_IRQ_READY\t11""",
        "extended checkpoint constants",
    )
    p30e_h = replace_once(
        p30e_h,
        """int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint);
int arm64_mt6797_a72_p30e_target_publish(u64 state, u64 reason,""",
        """int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint);
int arm64_mt6797_a72_p30e_target_detail(u64 checkpoint, u64 details,
\t\t\t\t\tu64 expected, u64 observed);
int arm64_mt6797_a72_p30e_target_publish(u64 state, u64 reason,""",
        "detailed checkpoint prototype",
    )
    p30e_h_path.write_text(p30e_h, encoding="utf-8")

    p30e_c_path = root / P30E_C
    p30e_c = p30e_c_path.read_text(encoding="utf-8")
    old_checkpoint = """int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint)
{
\tstruct arm64_mt6797_a72_p30e_slot *slot;
\tstruct arm64_mt6797_a72_p30e_wire *wire;
\tunsigned long flags;
\tu64 previous;
\tint cpu, ret = 0;

\tif (checkpoint < ARM64_MT6797_A72_P30E_CHECKPOINT_TASK_READY ||
\t    checkpoint > ARM64_MT6797_A72_P30E_CHECKPOINT_IRQ_READY)
\t\treturn -EINVAL;
\tcpu = p30e_current_cpu();
\tif (cpu < 0)
\t\treturn cpu;
\tslot = p30e_slot(cpu);
\twire = &slot->wire;

\traw_spin_lock_irqsave(&p30e_lock, flags);
\tdsb(sy);
\tp30e_invalidate_slot(slot);
\tif (p30e_word(wire, ARM64_MT6797_A72_P30E_CONTROLLER_STATE_WORD) !=
\t    ARM64_MT6797_A72_P30E_ARMED ||
\t    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD) !=
\t    ARM64_MT6797_A72_P30E_TARGET_CLAIMED ||
\t    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD) != 0) {
\t\tret = -EAGAIN;
\t\tgoto out_unlock;
\t}
\tprevious = p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD);
\tif (checkpoint <= previous) {
\t\tret = -EALREADY;
\t\tgoto out_unlock;
\t}
\tp30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, checkpoint);
\tp30e_clean_slot(slot);

out_unlock:
\traw_spin_unlock_irqrestore(&p30e_lock, flags);
\treturn ret;
}
"""
    new_checkpoint = """static int
p30e_target_checkpoint(u64 checkpoint, u64 details,
\t\t       u64 expected, u64 observed)
{
\tstruct arm64_mt6797_a72_p30e_slot *slot;
\tstruct arm64_mt6797_a72_p30e_wire *wire;
\tunsigned long flags;
\tu64 previous;
\tint cpu, ret = 0;

\tif (checkpoint < ARM64_MT6797_A72_P30E_CHECKPOINT_TASK_READY ||
\t    checkpoint > ARM64_MT6797_A72_P30E_CHECKPOINT_IRQ_READY ||
\t    (!!details != (checkpoint ==
\t\t\t    ARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_FAILED)) ||
\t    (!details && (expected || observed)))
\t\treturn -EINVAL;
\tcpu = p30e_current_cpu();
\tif (cpu < 0)
\t\treturn cpu;
\tslot = p30e_slot(cpu);
\twire = &slot->wire;

\traw_spin_lock_irqsave(&p30e_lock, flags);
\tdsb(sy);
\tp30e_invalidate_slot(slot);
\tif (p30e_word(wire, ARM64_MT6797_A72_P30E_CONTROLLER_STATE_WORD) !=
\t    ARM64_MT6797_A72_P30E_ARMED ||
\t    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD) !=
\t    ARM64_MT6797_A72_P30E_TARGET_CLAIMED ||
\t    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD) != 0 ||
\t    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD) != 0 ||
\t    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD) != 0 ||
\t    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD) != 0) {
\t\tret = -EAGAIN;
\t\tgoto out_unlock;
\t}
\tprevious = p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD);
\tif (checkpoint <= previous) {
\t\tret = -EALREADY;
\t\tgoto out_unlock;
\t}
\tif (details) {
\t\tp30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD,
\t\t\t details);
\t\tp30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD,
\t\t\t expected);
\t\tp30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD,
\t\t\t observed);
\t}
\tp30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, checkpoint);
\tp30e_clean_slot(slot);

out_unlock:
\traw_spin_unlock_irqrestore(&p30e_lock, flags);
\treturn ret;
}

int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint)
{
\treturn p30e_target_checkpoint(checkpoint, 0, 0, 0);
}

int
arm64_mt6797_a72_p30e_target_detail(u64 checkpoint, u64 details,
\t\t\t\t    u64 expected, u64 observed)
{
\treturn p30e_target_checkpoint(checkpoint, details, expected, observed);
}
"""
    p30e_c = replace_once(
        p30e_c, old_checkpoint, new_checkpoint, "detailed P30E checkpoint writer"
    )
    p30e_c_path.write_text(p30e_c, encoding="utf-8")

    late_h_path = root / LATE_H
    late_h = late_h_path.read_text(encoding="utf-8")
    late_h = replace_once(
        late_h,
        """int arm64_late_cpu_validate_boot_caps(void);

#ifdef CONFIG_ARM64_LATE_CPU_PROFILE""",
        """int arm64_late_cpu_validate_boot_caps(void);

#define ARM64_LATE_CPU_EXPECT_MISMATCH_MPIDR\t\tBIT_ULL(0)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_MIDR\t\tBIT_ULL(1)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_REVIDR\t\tBIT_ULL(2)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_CNTFRQ\t\tBIT_ULL(3)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_CTR\t\tBIT_ULL(4)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_DCZID\t\tBIT_ULL(5)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_CLIDR_EL1\tBIT_ULL(6)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_AA64DFR0\t\tBIT_ULL(7)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_AA64ISAR0\tBIT_ULL(8)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_AA64ISAR1\tBIT_ULL(9)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_AA64MMFR0\tBIT_ULL(10)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_AA64MMFR1\tBIT_ULL(11)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_AA64PFR0\t\tBIT_ULL(12)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_AA64PFR1\t\tBIT_ULL(13)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR0\t\tBIT_ULL(14)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR1\t\tBIT_ULL(15)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR2\t\tBIT_ULL(16)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR3\t\tBIT_ULL(17)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR4\t\tBIT_ULL(18)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR5\t\tBIT_ULL(19)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR0\t\tBIT_ULL(20)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR1\t\tBIT_ULL(21)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR2\t\tBIT_ULL(22)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR3\t\tBIT_ULL(23)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_PFR0\t\tBIT_ULL(24)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_PFR1\t\tBIT_ULL(25)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_CURRENT_CPU\tBIT_ULL(61)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_PAIR_CONTRACT\tBIT_ULL(62)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_TARGET_SLOT\tBIT_ULL(63)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_REGISTER_MASK\t(BIT_ULL(26) - 1)
#define ARM64_LATE_CPU_EXPECT_MISMATCH_ALLOWED_MASK\t\\
\t(ARM64_LATE_CPU_EXPECT_MISMATCH_REGISTER_MASK |\t\\
\t ARM64_LATE_CPU_EXPECT_MISMATCH_CURRENT_CPU |\t\\
\t ARM64_LATE_CPU_EXPECT_MISMATCH_PAIR_CONTRACT |\t\\
\t ARM64_LATE_CPU_EXPECT_MISMATCH_TARGET_SLOT)

#ifdef CONFIG_ARM64_LATE_CPU_PROFILE""",
        "late-target mismatch ABI",
    )
    late_h = replace_once(
        late_h,
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);",
        """int arm64_validate_late_cpu_expected_target(unsigned int cpu,
\t\t\t\t\t    u64 *mismatches,
\t\t\t\t\t    u64 *expected,
\t\t\t\t\t    u64 *observed);""",
        "late-target validator prototype",
    )
    late_h = replace_once(
        late_h,
        """static inline int
arm64_validate_late_cpu_expected_target(unsigned int cpu)
{
\treturn 0;
}""",
        """static inline int
arm64_validate_late_cpu_expected_target(unsigned int cpu, u64 *mismatches,
\t\t\t\t\tu64 *expected, u64 *observed)
{
\tif (mismatches)
\t\t*mismatches = 0;
\tif (expected)
\t\t*expected = 0;
\tif (observed)
\t\t*observed = 0;
\treturn 0;
}""",
        "late-target validator stub",
    )
    late_h_path.write_text(late_h, encoding="utf-8")

    late_c_path = root / LATE_C
    late_c = late_c_path.read_text(encoding="utf-8")
    old_validator = """static bool
late_expected_target_matches(const struct arm64_late_cpu_expected_pair *expected,
\t\t\t     unsigned int target,
\t\t\t     const struct cpuinfo_arm64 *info)
{
\tconst struct cpuinfo_32bit *aarch32 = &info->aarch32;
\tu64 mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK;

\treturn expected->mpidr[target] == mpidr &&
\t       expected->midr == info->reg_midr &&
\t       expected->revidr == info->reg_revidr &&
\t       expected->cntfrq == info->reg_cntfrq &&
\t       expected->ctr == read_cpuid_cachetype() &&
\t       expected->dczid == info->reg_dczid &&
\t       expected->clidr_el1 == read_sysreg(clidr_el1) &&
\t       expected->id_aa64dfr0 == info->reg_id_aa64dfr0 &&
\t       expected->id_aa64isar0 == info->reg_id_aa64isar0 &&
\t       expected->id_aa64isar1 == info->reg_id_aa64isar1 &&
\t       expected->id_aa64mmfr0 == info->reg_id_aa64mmfr0 &&
\t       expected->id_aa64mmfr1 == info->reg_id_aa64mmfr1 &&
\t       expected->id_aa64pfr0 == info->reg_id_aa64pfr0 &&
\t       expected->id_aa64pfr1 == info->reg_id_aa64pfr1 &&
\t       expected->id_isar0 == aarch32->reg_id_isar0 &&
\t       expected->id_isar1 == aarch32->reg_id_isar1 &&
\t       expected->id_isar2 == aarch32->reg_id_isar2 &&
\t       expected->id_isar3 == aarch32->reg_id_isar3 &&
\t       expected->id_isar4 == aarch32->reg_id_isar4 &&
\t       expected->id_isar5 == aarch32->reg_id_isar5 &&
\t       expected->id_mmfr0 == aarch32->reg_id_mmfr0 &&
\t       expected->id_mmfr1 == aarch32->reg_id_mmfr1 &&
\t       expected->id_mmfr2 == aarch32->reg_id_mmfr2 &&
\t       expected->id_mmfr3 == aarch32->reg_id_mmfr3 &&
\t       expected->id_pfr0 == aarch32->reg_id_pfr0 &&
\t       expected->id_pfr1 == aarch32->reg_id_pfr1;
}

int arm64_validate_late_cpu_expected_target(unsigned int cpu)
{
\tconst struct arm64_late_cpu_expected_pair *expected;
\tconst struct cpuinfo_arm64 *info;
\tunsigned int target;

\t/* Pairs with READY publication of late_plan and late_receipt. */
\tif (smp_load_acquire(&late_receipt.state) !=
\t    ARM64_LATE_CPU_PROFILE_READY)
\t\treturn 0;
\tif (!cpumask_test_cpu(cpu, &late_plan.target_cpus))
\t\treturn 0;
\tif (cpu != smp_processor_id() || !arm64_late_cpu_expected_pair_complete(&late_plan))
\t\treturn -EINVAL;

\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
\t\tif (late_plan.evidence.target_cpu[target] == cpu)
\t\t\tbreak;
\tif (target == ARM64_LATE_CPU_MAX_TARGETS)
\t\treturn -EINVAL;

\texpected = &late_plan.evidence.expected_pair;
\tinfo = this_cpu_ptr(&cpu_data);
\treturn late_expected_target_matches(expected, target, info) ? 0 : -ERANGE;
}
"""
    new_validator = """static void
late_expected_target_compare(u64 expected, u64 observed, u64 bit,
\t\t\t     u64 *mismatches, u64 *first_expected,
\t\t\t     u64 *first_observed)
{
\tif (expected == observed)
\t\treturn;
\tif (!*mismatches) {
\t\t*first_expected = expected;
\t\t*first_observed = observed;
\t}
\t*mismatches |= bit;
}

static u64
late_expected_target_mismatches(const struct arm64_late_cpu_expected_pair *pair,
\t\t\t\tunsigned int target,
\t\t\t\tconst struct cpuinfo_arm64 *info,
\t\t\t\tu64 *first_expected,
\t\t\t\tu64 *first_observed)
{
\tconst struct cpuinfo_32bit *aarch32 = &info->aarch32;
\tu64 mismatches = 0;
\tu64 mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK;

\tlate_expected_target_compare(pair->mpidr[target], mpidr,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_MPIDR, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->midr, info->reg_midr,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_MIDR, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->revidr, info->reg_revidr,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_REVIDR, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->cntfrq, info->reg_cntfrq,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_CNTFRQ, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->ctr, read_cpuid_cachetype(),
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_CTR, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->dczid, info->reg_dczid,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_DCZID, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->clidr_el1, read_sysreg(clidr_el1),
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_CLIDR_EL1, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_aa64dfr0, info->reg_id_aa64dfr0,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_AA64DFR0, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_aa64isar0, info->reg_id_aa64isar0,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_AA64ISAR0, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_aa64isar1, info->reg_id_aa64isar1,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_AA64ISAR1, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_aa64mmfr0, info->reg_id_aa64mmfr0,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_AA64MMFR0, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_aa64mmfr1, info->reg_id_aa64mmfr1,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_AA64MMFR1, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_aa64pfr0, info->reg_id_aa64pfr0,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_AA64PFR0, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_aa64pfr1, info->reg_id_aa64pfr1,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_AA64PFR1, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_isar0, aarch32->reg_id_isar0,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR0, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_isar1, aarch32->reg_id_isar1,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR1, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_isar2, aarch32->reg_id_isar2,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR2, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_isar3, aarch32->reg_id_isar3,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR3, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_isar4, aarch32->reg_id_isar4,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR4, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_isar5, aarch32->reg_id_isar5,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_ISAR5, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_mmfr0, aarch32->reg_id_mmfr0,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR0, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_mmfr1, aarch32->reg_id_mmfr1,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR1, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_mmfr2, aarch32->reg_id_mmfr2,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR2, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_mmfr3, aarch32->reg_id_mmfr3,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_MMFR3, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_pfr0, aarch32->reg_id_pfr0,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_PFR0, &mismatches,
\t\t\t\t     first_expected, first_observed);
\tlate_expected_target_compare(pair->id_pfr1, aarch32->reg_id_pfr1,
\t\t\t\t     ARM64_LATE_CPU_EXPECT_MISMATCH_PFR1, &mismatches,
\t\t\t\t     first_expected, first_observed);
\treturn mismatches;
}

int arm64_validate_late_cpu_expected_target(unsigned int cpu, u64 *mismatches,
\t\t\t\t\t    u64 *expected_value,
\t\t\t\t\t    u64 *observed_value)
{
\tconst struct arm64_late_cpu_expected_pair *expected;
\tconst struct cpuinfo_arm64 *info;
\tunsigned int target;

\tif (!mismatches || !expected_value || !observed_value)
\t\treturn -EINVAL;
\t*mismatches = 0;
\t*expected_value = 0;
\t*observed_value = 0;

\t/* Pairs with READY publication of late_plan and late_receipt. */
\tif (smp_load_acquire(&late_receipt.state) !=
\t    ARM64_LATE_CPU_PROFILE_READY)
\t\treturn 0;
\tif (!cpumask_test_cpu(cpu, &late_plan.target_cpus))
\t\treturn 0;
\tif (cpu != smp_processor_id()) {
\t\t*mismatches = ARM64_LATE_CPU_EXPECT_MISMATCH_CURRENT_CPU;
\t\t*expected_value = cpu;
\t\t*observed_value = smp_processor_id();
\t\treturn -EINVAL;
\t}
\tif (!arm64_late_cpu_expected_pair_complete(&late_plan)) {
\t\t*mismatches = ARM64_LATE_CPU_EXPECT_MISMATCH_PAIR_CONTRACT;
\t\t*expected_value = 1;
\t\treturn -EINVAL;
\t}

\tfor (target = 0; target < ARM64_LATE_CPU_MAX_TARGETS; target++)
\t\tif (late_plan.evidence.target_cpu[target] == cpu)
\t\t\tbreak;
\tif (target == ARM64_LATE_CPU_MAX_TARGETS) {
\t\t*mismatches = ARM64_LATE_CPU_EXPECT_MISMATCH_TARGET_SLOT;
\t\t*expected_value = cpu;
\t\t*observed_value = U64_MAX;
\t\treturn -EINVAL;
\t}

\texpected = &late_plan.evidence.expected_pair;
\tinfo = this_cpu_ptr(&cpu_data);
\t*mismatches = late_expected_target_mismatches(expected, target, info,
\t\t\t\t\t\t      expected_value,
\t\t\t\t\t\t      observed_value);
\treturn *mismatches ? -ERANGE : 0;
}
"""
    late_c = replace_once(
        late_c, old_validator, new_validator, "late-target mismatch classifier"
    )
    late_c_path.write_text(late_c, encoding="utf-8")

    smp_path = root / SMP
    smp = smp_path.read_text(encoding="utf-8")
    smp = replace_once(
        smp,
        """\tunsigned int cpu;
\tint expectation_ret;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE""",
        """\tunsigned int cpu;
\tint expectation_ret;
\tu64 expectation_mismatches = 0;
\tu64 expectation_expected = 0;
\tu64 expectation_observed = 0;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE""",
        "late-target detail locals",
    )
    smp = replace_once(
        smp,
        """\tops = get_cpu_ops(cpu);
\tif (ops->cpu_postboot)
\t\tops->cpu_postboot();

\t/*
\t * Log the CPU info before it is marked online and might get read.
\t */
\tcpuinfo_store_cpu();
\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu);
\tif (expectation_ret) {
\t\tpr_crit("CPU%u: late target expectation mismatch: %d\\n",
\t\t\tcpu, expectation_ret);
\t\tupdate_cpu_boot_status(CPU_STUCK_IN_KERNEL);
\t\tcpu_park_loop();
\t}
\tstore_cpu_topology(cpu);
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_TARGET_VALID;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif""",
        """\tops = get_cpu_ops(cpu);
\tif (ops->cpu_postboot)
\t\tops->cpu_postboot();
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_CPU_OPS_READY;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif

\t/*
\t * Log the CPU info before it is marked online and might get read.
\t */
\tcpuinfo_store_cpu();
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_CPUINFO_READY;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif
\texpectation_ret = arm64_validate_late_cpu_expected_target(cpu,
\t\t\t\t\t\t\t\t  &expectation_mismatches,
\t\t\t\t\t\t\t\t  &expectation_expected,
\t\t\t\t\t\t\t\t  &expectation_observed);
\tif (expectation_ret) {
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\t\tp30e_checkpoint =
\t\t\tARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_FAILED;
\t\t(void)arm64_mt6797_a72_p30e_target_detail(p30e_checkpoint,
\t\t\t\t\t\t\t  expectation_mismatches,
\t\t\t\t\t\t\t  expectation_expected,
\t\t\t\t\t\t\t  expectation_observed);
#endif
\t\tpr_crit("CPU%u: late target expectation mismatch: %d mask=%#llx\\n",
\t\t\tcpu, expectation_ret,
\t\t\t(unsigned long long)expectation_mismatches);
\t\tupdate_cpu_boot_status(CPU_STUCK_IN_KERNEL);
\t\tcpu_park_loop();
\t}
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_VALID;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif
\tstore_cpu_topology(cpu);
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_TOPOLOGY_READY;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif""",
        "post-capabilities checkpoints",
    )
    smp_path.write_text(smp, encoding="utf-8")

    public_path = root / BINDER_PUBLIC
    public = public_path.read_text(encoding="utf-8")
    public = replace_once(
        public,
        "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 4U",
        "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 5U",
        "binder diagnostic ABI",
    )
    public = replace_once(
        public,
        """\tu32 p30e_target_state;
\tu32 p30e_target_reason;
\tu32 p30e_target_sequence;""",
        """\tu32 p30e_target_state;
\tu32 p30e_target_reason;
\tu64 p30e_target_effects;
\tu64 p30e_target_entry_pc;
\tu64 p30e_target_entry_sp;
\tu32 p30e_target_sequence;""",
        "binder target detail fields",
    )
    public_path.write_text(public, encoding="utf-8")

    binder_path = root / BINDER
    binder = binder_path.read_text(encoding="utf-8")
    binder = replace_once(
        binder,
        """\tsnapshot->p30e_target_reason =
\t\tle64_to_cpu(p30e[ARM64_MT6797_A72_P30E_TARGET_REASON_WORD]);
\tsnapshot->p30e_target_sequence = le64_to_cpu(binder->p30e_snapshot.word[""",
        """\tsnapshot->p30e_target_reason =
\t\tle64_to_cpu(p30e[ARM64_MT6797_A72_P30E_TARGET_REASON_WORD]);
\tsnapshot->p30e_target_effects =
\t\tle64_to_cpu(p30e[ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD]);
\tsnapshot->p30e_target_entry_pc =
\t\tle64_to_cpu(p30e[ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD]);
\tsnapshot->p30e_target_entry_sp =
\t\tle64_to_cpu(p30e[ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD]);
\tsnapshot->p30e_target_sequence = le64_to_cpu(binder->p30e_snapshot.word[""",
        "binder target detail copy",
    )
    binder_path.write_text(binder, encoding="utf-8")

    test_path = root / BINDER_TEST
    test = test_path.read_text(encoding="utf-8")
    test = replace_once(
        test,
        """\tu32 p30e_target_state;
\tu32 p30e_target_reason;
\tu32 p30e_prepares;""",
        """\tu32 p30e_target_state;
\tu32 p30e_target_reason;
\tu64 p30e_target_effects;
\tu64 p30e_target_entry_pc;
\tu64 p30e_target_entry_sp;
\tu32 p30e_prepares;""",
        "focused target detail state",
    )
    test = replace_once(
        test,
        """\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_REASON_WORD] =
\t\tcpu_to_le64(state->p30e_target_reason);
\tcopy->word[ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD] =""",
        """\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_REASON_WORD] =
\t\tcpu_to_le64(state->p30e_target_reason);
\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD] =
\t\tcpu_to_le64(state->p30e_target_effects);
\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD] =
\t\tcpu_to_le64(state->p30e_target_entry_pc);
\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD] =
\t\tcpu_to_le64(state->p30e_target_entry_sp);
\tcopy->word[ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD] =""",
        "focused target detail readback",
    )
    test = replace_once(
        test,
        """\t\tstate->p30e_target_reason = target_states[i] ==
\t\t\tARM64_MT6797_A72_P30E_TARGET_CLAIMED ?
\t\t\tARM64_MT6797_A72_P30E_CHECKPOINT_C_ENTRY : 0;
\t\tret = mt6797_a72_binder_test_failure""",
        """\t\tstate->p30e_target_reason = target_states[i] ==
\t\t\tARM64_MT6797_A72_P30E_TARGET_CLAIMED ?
\t\t\tARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_FAILED : 0;
\t\tstate->p30e_target_effects = target_states[i] ==
\t\t\tARM64_MT6797_A72_P30E_TARGET_CLAIMED ?
\t\t\tARM64_LATE_CPU_EXPECT_MISMATCH_CTR : 0;
\t\tstate->p30e_target_entry_pc = target_states[i] ==
\t\t\tARM64_MT6797_A72_P30E_TARGET_CLAIMED ? 0x8444c004 : 0;
\t\tstate->p30e_target_entry_sp = target_states[i] ==
\t\t\tARM64_MT6797_A72_P30E_TARGET_CLAIMED ? 0x84448004 : 0;
\t\tret = mt6797_a72_binder_test_failure""",
        "focused target detail fixture",
    )
    test = replace_once(
        test,
        """\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_reason,
\t\t\t\tstate->p30e_target_reason);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_sequence,""",
        """\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_reason,
\t\t\t\tstate->p30e_target_reason);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_effects,
\t\t\t\tstate->p30e_target_effects);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_entry_pc,
\t\t\t\tstate->p30e_target_entry_pc);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_entry_sp,
\t\t\t\tstate->p30e_target_entry_sp);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_sequence,""",
        "focused target detail expectations",
    )
    test_path.write_text(test, encoding="utf-8")

    admission_path = root / ADMISSION
    admission = admission_path.read_text(encoding="utf-8")
    admission = replace_once(
        admission,
        """\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   "p30e_controller_state=%u p30e_target_state=%u p30e_target_reason=%u p30e_target_sequence=%u p30e_controller_sequence=%u\\n",
\t\t\t\t   diagnostic.p30e_controller_state,
\t\t\t\t   diagnostic.p30e_target_state,
\t\t\t\t   diagnostic.p30e_target_reason,
\t\t\t\t   diagnostic.p30e_target_sequence,
\t\t\t\t   diagnostic.p30e_controller_sequence);""",
        """\tlen += sysfs_emit_at(buf, len,
\t\t\t     "p30e_controller_state=%u p30e_target_state=%u p30e_target_reason=%u ",
\t\t\t     diagnostic.p30e_controller_state,
\t\t\t     diagnostic.p30e_target_state,
\t\t\t     diagnostic.p30e_target_reason);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "p30e_target_effects=0x%llx p30e_target_entry_pc=0x%llx ",
\t\t\t     (unsigned long long)diagnostic.p30e_target_effects,
\t\t\t     (unsigned long long)diagnostic.p30e_target_entry_pc);
\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   "p30e_target_entry_sp=0x%llx p30e_target_sequence=%u p30e_controller_sequence=%u\\n",
\t\t\t\t   (unsigned long long)diagnostic.p30e_target_entry_sp,
\t\t\t\t   diagnostic.p30e_target_sequence,
\t\t\t\t   diagnostic.p30e_controller_sequence);""",
        "admission target detail status",
    )
    admission_path.write_text(admission, encoding="utf-8")
