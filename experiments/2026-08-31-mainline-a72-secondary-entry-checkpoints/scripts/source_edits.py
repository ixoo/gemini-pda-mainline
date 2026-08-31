#!/usr/bin/env python3
"""Apply the exact monotonic P30E secondary-entry checkpoints."""

from __future__ import annotations

import hashlib
from pathlib import Path


HEAD = Path("arch/arm64/kernel/head.S")
SMP = Path("arch/arm64/kernel/smp.c")
P30E_C = Path("arch/arm64/kernel/mt6797_a72_p30e.c")
P30E_ASM = Path("arch/arm64/kernel/mt6797_a72_p30e_asm.S")
P30E_H = Path("arch/arm64/include/asm/mt6797_a72_p30e.h")
BINDER_PUBLIC = Path("include/linux/soc/mediatek/mt6797-a72-binder.h")
BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
ADMISSION = Path("drivers/soc/mediatek/mt6797-a72-admission-controller.c")
SOURCE_FILES = (
    HEAD, SMP, P30E_C, P30E_ASM, P30E_H,
    BINDER_PUBLIC, BINDER, BINDER_TEST, ADMISSION,
)
PARENT_SHA256 = {
    HEAD: "17dac1b2a499bb21f8a0e160aff9fd9fd24343c0f6d0dc12a4f4cbafb99d0749",
    SMP: "b8d0f94cb2c2c90b3fe5af178ae7c0a068720ba1e574495eeee8be4297c94f7c",
    P30E_C: "4322d389da74f966f74cea3247a4f1ff139c5ec315d972a9034b094bea09b34a",
    P30E_ASM: "5a23c459560bb51cb4803f10a91262633be6f24e2ed02bb54dd3c31630a33702",
    P30E_H: "eeaeab87dc5d7cc7d0f05df64c1396060f9c7578c41f0a3038c61ad25178228c",
    BINDER_PUBLIC: "ea393bf9f3dd1fd69b5e42ef717906cdf79027fb5a70d726e4ad980de549ed03",
    BINDER: "c59032f544d6528e933fd2c75635b1fe0e8e2dd4424bce45b8864fa6b6dcc2ce",
    BINDER_TEST: "d8d1221458ce1452de155bbdc867650faa9249b9e7179ed4df76be452cffdd70",
    ADMISSION: "fa97ee583a2fd50db3c4649131e25f22cf4565eeb469dd7b3fe288e1ef4f6b09",
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

    header_path = root / P30E_H
    header = header_path.read_text(encoding="utf-8")
    header = replace_once(
        header,
        """#define ARM64_MT6797_A72_P30E_PANICKED\t6

#define ARM64_MT6797_A72_P30E_MAGIC_WORD\t0""",
        """#define ARM64_MT6797_A72_P30E_PANICKED\t6

#define ARM64_MT6797_A72_P30E_CHECKPOINT_NONE\t\t0
#define ARM64_MT6797_A72_P30E_CHECKPOINT_CPU_SETUP\t1
#define ARM64_MT6797_A72_P30E_CHECKPOINT_TASK_READY\t2
#define ARM64_MT6797_A72_P30E_CHECKPOINT_C_ENTRY\t\t3
#define ARM64_MT6797_A72_P30E_CHECKPOINT_IDMAP_OFF\t4
#define ARM64_MT6797_A72_P30E_CHECKPOINT_CAPABILITIES\t5
#define ARM64_MT6797_A72_P30E_CHECKPOINT_TARGET_VALID\t6
#define ARM64_MT6797_A72_P30E_CHECKPOINT_IRQ_READY\t7

#define ARM64_MT6797_A72_P30E_MAGIC_WORD\t0""",
        "P30E checkpoint constants",
    )
    header = replace_once(
        header,
        """/* MMU-off primitives; no current caller or CPU_ON path is installed. */
int arm64_mt6797_a72_p30e_target_claim(void);
int arm64_mt6797_a72_p30e_target_publish(u64 state, u64 reason,""",
        """/* Target-side entry primitives; checkpoints never issue a CPU request. */
int arm64_mt6797_a72_p30e_target_claim(void);
int arm64_mt6797_a72_p30e_target_checkpoint_mmuoff(u64 checkpoint);
int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint);
int arm64_mt6797_a72_p30e_target_publish(u64 state, u64 reason,""",
        "P30E checkpoint prototypes",
    )
    header_path.write_text(header, encoding="utf-8")

    asm_path = root / P30E_ASM
    assembly = asm_path.read_text(encoding="utf-8")
    assembly = replace_once(
        assembly,
        """SYM_FUNC_END(arm64_mt6797_a72_p30e_target_claim)

\t.text""",
        """SYM_FUNC_END(arm64_mt6797_a72_p30e_target_claim)

SYM_FUNC_START(arm64_mt6797_a72_p30e_target_checkpoint_mmuoff)
\tmov\tx17, x30
\tmov\tx16, x0
\tcmp\tx16, #ARM64_MT6797_A72_P30E_CHECKPOINT_CPU_SETUP
\tb.ne\t.Lp30e_checkpoint_bad_stage
\tbl\tp30e_select_slot
\tcmp\tx0, #0
\tb.lt\t.Lp30e_checkpoint_return
\tldr\tx4, [x1, #ARM64_MT6797_A72_P30E_CONTROLLER_STATE_OFF]
\tcmp\tx4, #ARM64_MT6797_A72_P30E_ARMED
\tb.ne\t.Lp30e_checkpoint_unavailable
\tadd\tx3, x1, #ARM64_MT6797_A72_P30E_TARGET_STATE_OFF
\tldar\tx4, [x3]
\tcmp\tx4, #ARM64_MT6797_A72_P30E_TARGET_CLAIMED
\tb.ne\t.Lp30e_checkpoint_unavailable
\tldr\tx4, [x1, #ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_OFF]
\tcbnz\tx4, .Lp30e_checkpoint_unavailable
\tldr\tx4, [x1, #ARM64_MT6797_A72_P30E_TARGET_REASON_OFF]
\tcbnz\tx4, .Lp30e_checkpoint_unavailable
\tstr\tx16, [x1, #ARM64_MT6797_A72_P30E_TARGET_REASON_OFF]
\tbl\tp30e_clean_slot
\tmov\tx0, #0
\tb\t.Lp30e_checkpoint_return
.Lp30e_checkpoint_bad_stage:
\tmov\tx0, #-EINVAL
\tb\t.Lp30e_checkpoint_return
.Lp30e_checkpoint_unavailable:
\tmov\tx0, #-EAGAIN
.Lp30e_checkpoint_return:
\tmov\tx30, x17
\tret
SYM_FUNC_END(arm64_mt6797_a72_p30e_target_checkpoint_mmuoff)

\t.text""",
        "MMU-off P30E checkpoint writer",
    )
    asm_path.write_text(assembly, encoding="utf-8")

    head_path = root / HEAD
    head = head_path.read_text(encoding="utf-8")
    head = replace_once(
        head,
        """\tbl\t__cpu_setup\t\t\t// initialise processor
\tadrp\tx1, swapper_pg_dir""",
        """\tbl\t__cpu_setup\t\t\t// initialise processor
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tmov\tx15, x0\t\t\t// preserve the SCTLR value
\tmov\tx0, #ARM64_MT6797_A72_P30E_CHECKPOINT_CPU_SETUP
\tbl\tarm64_mt6797_a72_p30e_target_checkpoint_mmuoff
\tmov\tx0, x15
#endif
\tadrp\tx1, swapper_pg_dir""",
        "post-CPU-setup checkpoint call",
    )
    head = replace_once(
        head,
        """#ifdef CONFIG_ARM64_PTR_AUTH
\tptrauth_keys_init_cpu x2, x3, x4, x5
#endif

\tbl\tsecondary_start_kernel""",
        """#ifdef CONFIG_ARM64_PTR_AUTH
\tptrauth_keys_init_cpu x2, x3, x4, x5
#endif

#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tmov\tx0, #ARM64_MT6797_A72_P30E_CHECKPOINT_TASK_READY
\tbl\tarm64_mt6797_a72_p30e_target_checkpoint
#endif
\tbl\tsecondary_start_kernel""",
        "secondary-task checkpoint call",
    )
    head_path.write_text(head, encoding="utf-8")

    p30e_path = root / P30E_C
    p30e = p30e_path.read_text(encoding="utf-8")
    p30e = replace_once(
        p30e,
        """int arm64_mt6797_a72_p30e_target_publish(u64 state, u64 reason,
\t\t\t\t\t u64 effects, u64 entry_pc,
\t\t\t\t\t u64 entry_sp)
{""",
        """int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint)
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

int arm64_mt6797_a72_p30e_target_publish(u64 state, u64 reason,
\t\t\t\t\t u64 effects, u64 entry_pc,
\t\t\t\t\t u64 entry_sp)
{""",
        "normal-text P30E checkpoint writer",
    )
    p30e_path.write_text(p30e, encoding="utf-8")

    smp_path = root / SMP
    smp = smp_path.read_text(encoding="utf-8")
    smp = replace_once(
        smp,
        """asmlinkage notrace void secondary_start_kernel(void)
{
\tu64 mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK;
\tstruct mm_struct *mm = &init_mm;
\tconst struct cpu_operations *ops;
\tunsigned int cpu = smp_processor_id();
\tint expectation_ret;

\t/*""",
        """asmlinkage notrace void secondary_start_kernel(void)
{
\tu64 mpidr;
\tstruct mm_struct *mm = &init_mm;
\tconst struct cpu_operations *ops;
\tunsigned int cpu;
\tint expectation_ret;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tu64 p30e_checkpoint;
#endif

#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_C_ENTRY;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif
\tmpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK;
\tcpu = smp_processor_id();

\t/*""",
        "secondary C-entry checkpoint",
    )
    smp = replace_once(
        smp,
        """\tcpu_uninstall_idmap();

\tif (system_uses_irq_prio_masking())""",
        """\tcpu_uninstall_idmap();
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_IDMAP_OFF;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif

\tif (system_uses_irq_prio_masking())""",
        "post-idmap checkpoint",
    )
    smp = replace_once(
        smp,
        """\tcheck_local_cpu_capabilities();

\tops = get_cpu_ops(cpu);""",
        """\tcheck_local_cpu_capabilities();
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_CAPABILITIES;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif

\tops = get_cpu_ops(cpu);""",
        "post-capabilities checkpoint",
    )
    smp = replace_once(
        smp,
        """\tstore_cpu_topology(cpu);

\t/*
\t * Enable GIC and timers.""",
        """\tstore_cpu_topology(cpu);
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_TARGET_VALID;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif

\t/*
\t * Enable GIC and timers.""",
        "post-target-validation checkpoint",
    )
    smp = replace_once(
        smp,
        """\tnuma_add_cpu(cpu);

\t/*
\t * OK, now it's safe to let the boot CPU continue.""",
        """\tnuma_add_cpu(cpu);
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tp30e_checkpoint = ARM64_MT6797_A72_P30E_CHECKPOINT_IRQ_READY;
\t(void)arm64_mt6797_a72_p30e_target_checkpoint(p30e_checkpoint);
#endif

\t/*
\t * OK, now it's safe to let the boot CPU continue.""",
        "post-IRQ-setup checkpoint",
    )
    smp_path.write_text(smp, encoding="utf-8")

    public_path = root / BINDER_PUBLIC
    public = public_path.read_text(encoding="utf-8")
    public = replace_once(
        public,
        "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 3U",
        "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 4U",
        "binder diagnostic ABI",
    )
    public = replace_once(
        public,
        """\tu32 p30e_controller_state;
\tu32 p30e_target_state;
\tu32 p30e_target_sequence;""",
        """\tu32 p30e_controller_state;
\tu32 p30e_target_state;
\tu32 p30e_target_reason;
\tu32 p30e_target_sequence;""",
        "binder checkpoint field",
    )
    public_path.write_text(public, encoding="utf-8")

    binder_path = root / BINDER
    binder = binder_path.read_text(encoding="utf-8")
    binder = replace_once(
        binder,
        """\tconst struct mt6797_a72_platform_effect_result *release =
\t\t&binder->p27_release;

\tmemset(snapshot, 0, sizeof(*snapshot));""",
        """\tconst struct mt6797_a72_platform_effect_result *release =
\t\t&binder->p27_release;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tconst __le64 *p30e = binder->p30e_snapshot.word;
#endif

\tmemset(snapshot, 0, sizeof(*snapshot));""",
        "binder checkpoint word view",
    )
    binder = replace_once(
        binder,
        """\tsnapshot->p30e_target_state = le64_to_cpu(binder->p30e_snapshot.word[
\t\tARM64_MT6797_A72_P30E_TARGET_STATE_WORD]);
\tsnapshot->p30e_target_sequence = le64_to_cpu(binder->p30e_snapshot.word[""",
        """\tsnapshot->p30e_target_state = le64_to_cpu(binder->p30e_snapshot.word[
\t\tARM64_MT6797_A72_P30E_TARGET_STATE_WORD]);
\tsnapshot->p30e_target_reason =
\t\tle64_to_cpu(p30e[ARM64_MT6797_A72_P30E_TARGET_REASON_WORD]);
\tsnapshot->p30e_target_sequence = le64_to_cpu(binder->p30e_snapshot.word[""",
        "binder checkpoint diagnostic copy",
    )
    binder_path.write_text(binder, encoding="utf-8")

    test_path = root / BINDER_TEST
    test = test_path.read_text(encoding="utf-8")
    test = replace_once(
        test,
        """#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tu32 p30e_target_state;
\tu32 p30e_prepares;""",
        """#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tu32 p30e_target_state;
\tu32 p30e_target_reason;
\tu32 p30e_prepares;""",
        "focused checkpoint state",
    )
    test = replace_once(
        test,
        """\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_STATE_WORD] =
\t\tcpu_to_le64(target);
\tcopy->word[ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD] =""",
        """\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_STATE_WORD] =
\t\tcpu_to_le64(target);
\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_REASON_WORD] =
\t\tcpu_to_le64(state->p30e_target_reason);
\tcopy->word[ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD] =""",
        "focused checkpoint readback",
    )
    test = replace_once(
        test,
        """\t\tstate->p30e_target_state = target_states[i];
\t\tret = mt6797_a72_binder_test_failure""",
        """\t\tstate->p30e_target_state = target_states[i];
\t\tstate->p30e_target_reason = target_states[i] ==
\t\t\tARM64_MT6797_A72_P30E_TARGET_CLAIMED ?
\t\t\tARM64_MT6797_A72_P30E_CHECKPOINT_C_ENTRY : 0;
\t\tret = mt6797_a72_binder_test_failure""",
        "focused checkpoint fixture",
    )
    test = replace_once(
        test,
        """\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_state,
\t\t\t\ttarget_states[i]);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_sequence,""",
        """\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_state,
\t\t\t\ttarget_states[i]);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_reason,
\t\t\t\tstate->p30e_target_reason);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_sequence,""",
        "focused checkpoint expectation",
    )
    test_path.write_text(test, encoding="utf-8")

    admission_path = root / ADMISSION
    admission = admission_path.read_text(encoding="utf-8")
    admission = replace_once(
        admission,
        """\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   "p30e_controller_state=%u p30e_target_state=%u p30e_target_sequence=%u p30e_controller_sequence=%u\\n",
\t\t\t\t   diagnostic.p30e_controller_state,
\t\t\t\t   diagnostic.p30e_target_state,
\t\t\t\t   diagnostic.p30e_target_sequence,
\t\t\t\t   diagnostic.p30e_controller_sequence);""",
        """\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   "p30e_controller_state=%u p30e_target_state=%u p30e_target_reason=%u p30e_target_sequence=%u p30e_controller_sequence=%u\\n",
\t\t\t\t   diagnostic.p30e_controller_state,
\t\t\t\t   diagnostic.p30e_target_state,
\t\t\t\t   diagnostic.p30e_target_reason,
\t\t\t\t   diagnostic.p30e_target_sequence,
\t\t\t\t   diagnostic.p30e_controller_sequence);""",
        "admission checkpoint status",
    )
    admission_path.write_text(admission, encoding="utf-8")
