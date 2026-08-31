#!/usr/bin/env python3
"""Apply the exact P30E post-MMU publication repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


P30E_C = Path("arch/arm64/kernel/mt6797_a72_p30e.c")
P30E_ASM = Path("arch/arm64/kernel/mt6797_a72_p30e_asm.S")
SOURCE_FILES = (P30E_C, P30E_ASM)
PARENT_SHA256 = {
    P30E_C: "35e4049b9ee32ac8324cda4c7c1c4b2d79f394080f4a763c460c77d7769dad6c",
    P30E_ASM: "39828a36e0864b75b4337567d41a9055d4ac17cdc7f995e25631e2a50a348c6f",
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
    c_path = root / P30E_C
    asm_path = root / P30E_ASM
    c_text = c_path.read_text(encoding="utf-8")
    asm_text = asm_path.read_text(encoding="utf-8")

    c_text = replace_once(
        c_text,
        """#include <asm/barrier.h>
#include <asm/cacheflush.h>
#include <asm/memory.h>""",
        """#include <asm/barrier.h>
#include <asm/cacheflush.h>
#include <asm/cputype.h>
#include <asm/memory.h>""",
        "post-MMU MPIDR include",
    )
    c_text = replace_once(
        c_text,
        """static u64 p30e_mpidr(unsigned int cpu)
{
	return cpu == ARM64_MT6797_A72_P30E_CPU8 ?
		ARM64_MT6797_A72_P30E_MPIDR_CPU8 :
		ARM64_MT6797_A72_P30E_MPIDR_CPU9;
}
""",
        """static u64 p30e_mpidr(unsigned int cpu)
{
	return cpu == ARM64_MT6797_A72_P30E_CPU8 ?
		ARM64_MT6797_A72_P30E_MPIDR_CPU8 :
		ARM64_MT6797_A72_P30E_MPIDR_CPU9;
}

static int p30e_current_cpu(void)
{
	u64 mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK;

	switch (mpidr) {
	case ARM64_MT6797_A72_P30E_MPIDR_CPU8:
		return ARM64_MT6797_A72_P30E_CPU8;
	case ARM64_MT6797_A72_P30E_MPIDR_CPU9:
		return ARM64_MT6797_A72_P30E_CPU9;
	default:
		return -ENODEV;
	}
}
""",
        "post-MMU target selection",
    )
    if not c_text.endswith("\n\treturn ret;\n}\n"):
        raise ValueError("P30E controller source tail changed")
    c_text += """
int arm64_mt6797_a72_p30e_target_publish(u64 state, u64 reason,
					 u64 effects, u64 entry_pc,
					 u64 entry_sp)
{
	struct arm64_mt6797_a72_p30e_slot *slot;
	struct arm64_mt6797_a72_p30e_wire *wire;
	unsigned long flags;
	u64 sequence;
	int cpu, ret = 0;

	if (state < ARM64_MT6797_A72_P30E_TARGET_PUBLISHED ||
	    state > ARM64_MT6797_A72_P30E_PANICKED)
		return -EINVAL;

	cpu = p30e_current_cpu();
	if (cpu < 0)
		return cpu;
	slot = p30e_slot(cpu);
	wire = &slot->wire;

	raw_spin_lock_irqsave(&p30e_lock, flags);
	dsb(sy);
	p30e_invalidate_slot(slot);
	if (p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD) !=
	    ARM64_MT6797_A72_P30E_TARGET_CLAIMED) {
		ret = -EALREADY;
		goto out_unlock;
	}

	sequence = p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD);
	p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD, sequence + 1);
	p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, reason);
	p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD, effects);
	p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD, entry_pc);
	p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD, entry_sp);
	p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD, state);
	p30e_clean_slot(slot);

out_unlock:
	raw_spin_unlock_irqrestore(&p30e_lock, flags);
	return ret;
}
"""

    asm_text = replace_once(
        asm_text,
        """/* x1 = selected slot; the cache routine corrupts x0-x3 only. */
SYM_FUNC_START_LOCAL(p30e_clean_slot)
	mov	x0, x1
	add	x1, x1, #ARM64_MT6797_A72_P30E_SLOT_BYTES
	adr_l	x2, dcache_clean_inval_poc
	blr	x2
	dsb	sy
	ret
SYM_FUNC_END(p30e_clean_slot)""",
        """/* x1 = selected slot; the cache routine corrupts x0-x3 only. */
SYM_FUNC_START_LOCAL(p30e_clean_slot)
	mov	x14, x30
	mov	x0, x1
	add	x1, x1, #ARM64_MT6797_A72_P30E_SLOT_BYTES
	adr_l	x2, dcache_clean_inval_poc
	blr	x2
	dsb	sy
	mov	x30, x14
	ret
SYM_FUNC_END(p30e_clean_slot)""",
        "MMU-off cache-helper link preservation",
    )
    asm_text = replace_once(
        asm_text,
        """SYM_FUNC_START(arm64_mt6797_a72_p30e_target_publish)
	/* Preserve the terminal tuple across slot selection/cache maintenance. */
	mov	x15, x30
	mov	x5, x0
	mov	x6, x1
	mov	x7, x2
	mov	x8, x3
	mov	x9, x4
	cmp	x5, #ARM64_MT6797_A72_P30E_TARGET_PUBLISHED
	b.lo	.Lp30e_publish_bad_state
	cmp	x5, #ARM64_MT6797_A72_P30E_PANICKED
	b.hi	.Lp30e_publish_bad_state
	bl	p30e_select_slot
	cmp	x0, #0
	b.lt	.Lp30e_publish_no_target
	add	x3, x1, #ARM64_MT6797_A72_P30E_TARGET_STATE_OFF
	ldar	x4, [x3]
	cmp	x4, #ARM64_MT6797_A72_P30E_TARGET_CLAIMED
	b.ne	.Lp30e_publish_not_claimed
	ldr	x10, [x1, #ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_OFF]
	add	x10, x10, #1
	str	x10, [x1, #ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_OFF]
	str	x6, [x1, #ARM64_MT6797_A72_P30E_TARGET_REASON_OFF]
	str	x7, [x1, #ARM64_MT6797_A72_P30E_TARGET_EFFECTS_OFF]
	str	x8, [x1, #ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_OFF]
	str	x9, [x1, #ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_OFF]
	bl	p30e_clean_slot
	bl	p30e_select_slot
	add	x3, x1, #ARM64_MT6797_A72_P30E_TARGET_STATE_OFF
	stlr	x5, [x3]
	mov	x0, #0
	mov	x30, x15
	ret
.Lp30e_publish_bad_state:
	mov	x0, #-EINVAL
	mov	x30, x15
	ret
.Lp30e_publish_no_target:
	mov	x0, #-ENODEV
	mov	x30, x15
	ret
.Lp30e_publish_not_claimed:
	mov	x0, #-EALREADY
	mov	x30, x15
	ret
SYM_FUNC_END(arm64_mt6797_a72_p30e_target_publish)

""",
        "",
        "remove post-MMU publisher from idmap text",
    )

    c_path.write_text(c_text, encoding="utf-8")
    asm_path.write_text(asm_text, encoding="utf-8")
