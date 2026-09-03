#!/usr/bin/env python3
"""Apply the exact CPU9 P30E rearm primitive and restore integration."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"edit anchor changed: {path}: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def primitive(root: Path) -> None:
    kconfig = root / "arch/arm64/Kconfig"
    replace_once(kconfig,
        '\nsource "arch/arm64/kvm/Kconfig"\n',
        '''
config ARM64_MT6797_A72_P30E_REARM_KUNIT_TEST
	bool "KUnit tests for the MT6797 A72 P30E CPU9 rearm"
	depends on KUNIT=y
	depends on ARM64_MT6797_A72_P30E_WIRE
	default n
	help
	  Exercise the pure validation and reconstruction step used by the
	  exact CPU9-only P30E rearm. The suite covers the intact published
	  request, one-shot rejection, and every identity, state, result,
	  entry, reserved-byte, and CRC mismatch without issuing a CPU request.

source "arch/arm64/kvm/Kconfig"
''')

    makefile = root / "arch/arm64/kernel/Makefile"
    replace_once(makefile,
        "obj-$(CONFIG_ARM64_MT6797_A72_P30E_WIRE)\t+= mt6797_a72_p30e_asm.o\n",
        "obj-$(CONFIG_ARM64_MT6797_A72_P30E_WIRE)\t+= mt6797_a72_p30e_asm.o\n"
        "obj-$(CONFIG_ARM64_MT6797_A72_P30E_REARM_KUNIT_TEST) += mt6797_a72_p30e_test.o\n")

    header = root / "arch/arm64/include/asm/mt6797_a72_p30e.h"
    replace_once(header,
        "int arm64_mt6797_a72_p30e_readback(unsigned int cpu,\n"
        "\t\t\t\t\t const struct arm64_mt6797_a72_p30e_request *request,\n"
        "\t\t\t\t\t struct arm64_mt6797_a72_p30e_wire *copy);\n",
        "int arm64_mt6797_a72_p30e_readback(unsigned int cpu,\n"
        "\t\t\t\t\t const struct arm64_mt6797_a72_p30e_request *request,\n"
        "\t\t\t\t\t struct arm64_mt6797_a72_p30e_wire *copy);\n"
        "int arm64_mt6797_a72_p30e_rearm_cpu9(void);\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_P30E_REARM_KUNIT_TEST\n"
        "int arm64_mt6797_a72_p30e_prepare_cpu9_rearm(\n"
        "\tconst struct arm64_mt6797_a72_p30e_slot *slot, u64 entry_pa,\n"
        "\tstruct arm64_mt6797_a72_p30e_wire *next);\n"
        "#endif\n")

    source = root / "arch/arm64/kernel/mt6797_a72_p30e.c"
    anchor = "int arm64_mt6797_a72_p30e_readback(\n"
    addition = r'''static void p30e_initial_wire(
	const struct arm64_mt6797_a72_p30e_wire *published,
	struct arm64_mt6797_a72_p30e_wire *initial)
{
	*initial = *published;
	p30e_put(initial, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD,
		 ARM64_MT6797_A72_P30E_EMPTY);
	p30e_put(initial, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD, 0);
	p30e_put(initial, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, 0);
	p30e_put(initial, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD, 0);
	p30e_put(initial, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD, 0);
	p30e_put(initial, ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD, 0);
}

int arm64_mt6797_a72_p30e_prepare_cpu9_rearm(
	const struct arm64_mt6797_a72_p30e_slot *slot, u64 entry_pa,
	struct arm64_mt6797_a72_p30e_wire *next)
{
	const struct arm64_mt6797_a72_p30e_wire *wire;
	struct arm64_mt6797_a72_p30e_wire initial;
	u64 generation, cookie;
	unsigned int i;

	if (!slot || !entry_pa || !next)
		return -EINVAL;
	wire = &slot->wire;
	generation = p30e_word(wire, ARM64_MT6797_A72_P30E_GENERATION_WORD);
	cookie = p30e_word(wire, ARM64_MT6797_A72_P30E_COOKIE_WORD);
	if (p30e_word(wire, ARM64_MT6797_A72_P30E_MAGIC_WORD) !=
		    ARM64_MT6797_A72_P30E_MAGIC ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_ABI_WORD) !=
		    ARM64_MT6797_A72_P30E_ABI_AND_SIZE ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_OPERATION_WORD) !=
		    ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_CPU_WORD) !=
		    ARM64_MT6797_A72_P30E_CPU9 ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_MPIDR_WORD) !=
		    ARM64_MT6797_A72_P30E_MPIDR_CPU9 ||
	    !generation || generation == ~0ULL || !cookie || cookie == ~0ULL ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_CONTROLLER_STATE_WORD) !=
		    ARM64_MT6797_A72_P30E_ARMED ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD) != 1 ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD) !=
		    ARM64_MT6797_A72_P30E_TARGET_PUBLISHED ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD) != 1 ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD) ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD) ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD) !=
		    entry_pa ||
	    p30e_word(wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD))
		return -EPROTO;

	for (i = 0; i < ARM64_MT6797_A72_P30E_TARGET_BOOT_ID_WORDS; i++) {
		u64 identity = p30e_word(wire,
			ARM64_MT6797_A72_P30E_BOOT_ID0_WORD + i);

		if (!identity || identity == ~0ULL ||
		    identity != le64_to_cpu(READ_ONCE(
			    slot->target_boot_identity[i])))
			return -EPROTO;
	}
	if (memchr_inv(slot->reserved, 0, sizeof(slot->reserved)))
		return -EPROTO;

	p30e_initial_wire(wire, &initial);
	if (p30e_crc64(&initial) !=
	    p30e_word(wire, ARM64_MT6797_A72_P30E_CRC64_WORD))
		return -EBADMSG;

	*next = initial;
	p30e_put(next, ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD, 2);
	p30e_put(next, ARM64_MT6797_A72_P30E_CRC64_WORD, p30e_crc64(next));
	return 0;
}

int arm64_mt6797_a72_p30e_rearm_cpu9(void)
{
	struct arm64_mt6797_a72_p30e_slot *slot =
		&arm64_mt6797_a72_p30e_cpu9_slot;
	struct arm64_mt6797_a72_p30e_wire next;
	unsigned long flags;
	unsigned int i;
	int ret;

	raw_spin_lock_irqsave(&p30e_lock, flags);
	dsb(sy);
	p30e_invalidate_slot(slot);
	ret = arm64_mt6797_a72_p30e_prepare_cpu9_rearm(
		slot, __pa_symbol(secondary_entry), &next);
	if (ret)
		goto out_unlock;
	for (i = 0; i < ARM64_MT6797_A72_P30E_WIRE_WORDS; i++) {
		if (i == ARM64_MT6797_A72_P30E_TARGET_STATE_WORD)
			continue;
		p30e_put(&slot->wire, i, p30e_word(&next, i));
	}
	p30e_clean_slot(slot);
	smp_store_release((u64 *)&slot->wire.word[
		ARM64_MT6797_A72_P30E_TARGET_STATE_WORD],
		cpu_to_le64(ARM64_MT6797_A72_P30E_EMPTY));
	p30e_clean_slot(slot);

out_unlock:
	raw_spin_unlock_irqrestore(&p30e_lock, flags);
	return ret;
}

'''
    replace_once(source, anchor, addition + anchor)

    test = root / "arch/arm64/kernel/mt6797_a72_p30e_test.c"
    if test.exists():
        raise SystemExit(f"new test path already exists: {test}")
    test.write_text(r'''// SPDX-License-Identifier: GPL-2.0-only
/* KUnit tests for the exact CPU9 P30E rearm reconstruction. */

#include <kunit/test.h>

#include <linux/bitops.h>
#include <linux/byteorder/little_endian.h>
#include <linux/errno.h>
#include <linux/string.h>

#include <asm/mt6797_a72_p30e.h>

#define P30E_TEST_ENTRY_PA 0x80000ULL

static u64 p30e_test_crc64(const struct arm64_mt6797_a72_p30e_wire *wire)
{
	const u8 *bytes = (const u8 *)wire;
	u64 crc = 0;
	unsigned int bit, i;

	for (i = 0; i < ARM64_MT6797_A72_P30E_CRC64_OFF; i++) {
		crc ^= (u64)bytes[i] << 56;
		for (bit = 0; bit < 8; bit++)
			crc = (crc << 1) ^
				((crc & BIT_ULL(63)) ?
				 ARM64_MT6797_A72_P30E_CRC64_POLY : 0);
	}
	return crc;
}

static void p30e_test_put(struct arm64_mt6797_a72_p30e_wire *wire,
			   unsigned int word, u64 value)
{
	wire->word[word] = cpu_to_le64(value);
}

static u64 p30e_test_word(const struct arm64_mt6797_a72_p30e_wire *wire,
			  unsigned int word)
{
	return le64_to_cpu(wire->word[word]);
}

static void p30e_test_refresh_crc(
	struct arm64_mt6797_a72_p30e_slot *slot)
{
	struct arm64_mt6797_a72_p30e_wire initial = slot->wire;

	p30e_test_put(&initial, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD, 0);
	p30e_test_put(&initial, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD, 0);
	p30e_test_put(&initial, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, 0);
	p30e_test_put(&initial, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD, 0);
	p30e_test_put(&initial, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD, 0);
	p30e_test_put(&initial, ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD, 0);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_CRC64_WORD,
		       p30e_test_crc64(&initial));
}

static void p30e_test_published(
	struct arm64_mt6797_a72_p30e_slot *slot)
{
	unsigned int i;

	memset(slot, 0, sizeof(*slot));
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_MAGIC_WORD,
		       ARM64_MT6797_A72_P30E_MAGIC);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_ABI_WORD,
		       ARM64_MT6797_A72_P30E_ABI_AND_SIZE);
	for (i = 0; i < ARM64_MT6797_A72_P30E_TARGET_BOOT_ID_WORDS; i++) {
		p30e_test_put(&slot->wire,
			       ARM64_MT6797_A72_P30E_BOOT_ID0_WORD + i,
			       0x1000ULL + i);
		slot->target_boot_identity[i] = cpu_to_le64(0x1000ULL + i);
	}
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_OPERATION_WORD,
		       ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_CPU_WORD,
		       ARM64_MT6797_A72_P30E_CPU9);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_MPIDR_WORD,
		       ARM64_MT6797_A72_P30E_MPIDR_CPU9);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_GENERATION_WORD, 2);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_COOKIE_WORD, 0xa7200002);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_CONTROLLER_STATE_WORD,
		       ARM64_MT6797_A72_P30E_ARMED);
	p30e_test_put(&slot->wire,
		       ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD, 1);
	p30e_test_refresh_crc(slot);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD,
		       ARM64_MT6797_A72_P30E_TARGET_PUBLISHED);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD, 1);
	p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD,
		       P30E_TEST_ENTRY_PA);
}

static void p30e_rearm_success_test(struct kunit *test)
{
	struct arm64_mt6797_a72_p30e_slot slot;
	struct arm64_mt6797_a72_p30e_wire next;

	p30e_test_published(&slot);
	KUNIT_ASSERT_EQ(test, arm64_mt6797_a72_p30e_prepare_cpu9_rearm(
		&slot, P30E_TEST_ENTRY_PA, &next), 0);
	KUNIT_EXPECT_EQ(test, p30e_test_word(&next,
		ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD), 2ULL);
	KUNIT_EXPECT_EQ(test, p30e_test_word(&next,
		ARM64_MT6797_A72_P30E_TARGET_STATE_WORD), 0ULL);
	KUNIT_EXPECT_EQ(test, p30e_test_word(&next,
		ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD), 0ULL);
	KUNIT_EXPECT_EQ(test, p30e_test_word(&next,
		ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD), 0ULL);
	KUNIT_EXPECT_EQ(test, p30e_test_word(&next,
		ARM64_MT6797_A72_P30E_CRC64_WORD), p30e_test_crc64(&next));

	slot.wire = next;
	KUNIT_EXPECT_LT(test, arm64_mt6797_a72_p30e_prepare_cpu9_rearm(
		&slot, P30E_TEST_ENTRY_PA, &next), 0);
}

enum p30e_test_mutation {
	P30E_MUT_MAGIC,
	P30E_MUT_ABI,
	P30E_MUT_BOOT_ID,
	P30E_MUT_TARGET_BOOT_ID,
	P30E_MUT_OPERATION,
	P30E_MUT_CPU,
	P30E_MUT_MPIDR,
	P30E_MUT_GENERATION_ZERO,
	P30E_MUT_GENERATION_ONES,
	P30E_MUT_COOKIE_ZERO,
	P30E_MUT_COOKIE_ONES,
	P30E_MUT_CONTROLLER_STATE,
	P30E_MUT_CONTROLLER_SEQUENCE,
	P30E_MUT_TARGET_STATE,
	P30E_MUT_TARGET_SEQUENCE,
	P30E_MUT_REASON,
	P30E_MUT_EFFECTS,
	P30E_MUT_ENTRY_PC,
	P30E_MUT_ENTRY_SP,
	P30E_MUT_RESERVED,
	P30E_MUT_CRC,
	P30E_MUT_COUNT,
};

static void p30e_test_mutate(struct arm64_mt6797_a72_p30e_slot *slot,
			      enum p30e_test_mutation mutation)
{
	switch (mutation) {
	case P30E_MUT_MAGIC:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_MAGIC_WORD, 1);
		break;
	case P30E_MUT_ABI:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_ABI_WORD, 1);
		break;
	case P30E_MUT_BOOT_ID:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_BOOT_ID0_WORD,
			       0x2000);
		break;
	case P30E_MUT_TARGET_BOOT_ID:
		slot->target_boot_identity[0] = cpu_to_le64(0x2000);
		break;
	case P30E_MUT_OPERATION:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_OPERATION_WORD,
			       ARM64_MT6797_A72_P30E_OPERATION_CPU8_UP);
		break;
	case P30E_MUT_CPU:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_CPU_WORD, 8);
		break;
	case P30E_MUT_MPIDR:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_MPIDR_WORD,
			       ARM64_MT6797_A72_P30E_MPIDR_CPU8);
		break;
	case P30E_MUT_GENERATION_ZERO:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_GENERATION_WORD, 0);
		break;
	case P30E_MUT_GENERATION_ONES:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_GENERATION_WORD,
			       ~0ULL);
		break;
	case P30E_MUT_COOKIE_ZERO:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_COOKIE_WORD, 0);
		break;
	case P30E_MUT_COOKIE_ONES:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_COOKIE_WORD, ~0ULL);
		break;
	case P30E_MUT_CONTROLLER_STATE:
		p30e_test_put(&slot->wire,
			       ARM64_MT6797_A72_P30E_CONTROLLER_STATE_WORD, 0);
		break;
	case P30E_MUT_CONTROLLER_SEQUENCE:
		p30e_test_put(&slot->wire,
			       ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD, 2);
		break;
	case P30E_MUT_TARGET_STATE:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD,
			       ARM64_MT6797_A72_P30E_FAILED);
		break;
	case P30E_MUT_TARGET_SEQUENCE:
		p30e_test_put(&slot->wire,
			       ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD, 2);
		break;
	case P30E_MUT_REASON:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, 1);
		break;
	case P30E_MUT_EFFECTS:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD, 1);
		break;
	case P30E_MUT_ENTRY_PC:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD,
			       P30E_TEST_ENTRY_PA + 4);
		break;
	case P30E_MUT_ENTRY_SP:
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD, 1);
		break;
	case P30E_MUT_RESERVED:
		slot->reserved[0] = 1;
		break;
	case P30E_MUT_CRC:
		break;
	case P30E_MUT_COUNT:
		return;
	}
	if (mutation != P30E_MUT_CRC)
		p30e_test_refresh_crc(slot);
	else
		p30e_test_put(&slot->wire, ARM64_MT6797_A72_P30E_CRC64_WORD,
			       p30e_test_word(&slot->wire,
				       ARM64_MT6797_A72_P30E_CRC64_WORD) ^ 1);
}

static void p30e_rearm_mutations_test(struct kunit *test)
{
	struct arm64_mt6797_a72_p30e_slot slot;
	struct arm64_mt6797_a72_p30e_wire next;
	enum p30e_test_mutation mutation;

	for (mutation = 0; mutation < P30E_MUT_COUNT; mutation++) {
		p30e_test_published(&slot);
		p30e_test_mutate(&slot, mutation);
		memset(&next, 0xa5, sizeof(next));
		KUNIT_EXPECT_LT_MSG(test,
			arm64_mt6797_a72_p30e_prepare_cpu9_rearm(
				&slot, P30E_TEST_ENTRY_PA, &next), 0,
			"mutation %u accepted", mutation);
	}
}

static struct kunit_case p30e_rearm_cases[] = {
	KUNIT_CASE(p30e_rearm_success_test),
	KUNIT_CASE(p30e_rearm_mutations_test),
	{ }
};

static struct kunit_suite p30e_rearm_suite = {
	.name = "mt6797-a72-p30e-rearm",
	.test_cases = p30e_rearm_cases,
};

kunit_test_suite(p30e_rearm_suite);
''', encoding="utf-8")


def integration(root: Path) -> None:
    executor_header = (
        root / "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h"
    )
    replace_once(executor_header,
        "\tMT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED = 15,\n"
        "\tMT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE = 16,\n"
        "\tMT6797_A72_RESTORE_STAGE_FULL_COMPLETE = 17,\n",
        "\tMT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED = 15,\n"
        "\tMT6797_A72_RESTORE_STAGE_P30E_REARMED = 16,\n"
        "\tMT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE = 17,\n"
        "\tMT6797_A72_RESTORE_STAGE_FULL_COMPLETE = 18,\n")
    replace_once(executor_header,
        "\tMT6797_A72_RESTORE_ON_COMMITTED,\n"
        "\tMT6797_A72_RESTORE_BOOTING,\n",
        "\tMT6797_A72_RESTORE_ON_COMMITTED,\n"
        "\tMT6797_A72_RESTORE_REARMING,\n"
        "\tMT6797_A72_RESTORE_REARMED,\n"
        "\tMT6797_A72_RESTORE_BOOTING,\n")
    replace_once(executor_header,
        "\tu32 begin_calls;\n\tu32 cpu_boot_calls;\n",
        "\tu32 begin_calls;\n\tu32 p30e_rearm_calls;\n\tu32 cpu_boot_calls;\n")
    replace_once(executor_header,
        "\tbool cpu_on_committed;\n\tbool cpu_boot_issued;\n",
        "\tbool cpu_on_committed;\n\tbool p30e_rearmed;\n\tbool cpu_boot_issued;\n")
    replace_once(executor_header,
        "\tint (*cpu_boot)(void *context, unsigned int cpu);\n",
        "\tint (*p30e_rearm)(void *context, unsigned int cpu);\n"
        "\tint (*cpu_boot)(void *context, unsigned int cpu);\n")

    executor = root / "drivers/soc/mediatek/mt6797-a72-restore-executor.c"
    replace_once(executor,
        "\t\tops->validate_restore && ops->begin_restore && ops->cpu_boot &&\n",
        "\t\tops->validate_restore && ops->begin_restore &&\n"
        "\t\tops->p30e_rearm && ops->cpu_boot &&\n")
    replace_once(executor,
        "\tatomic_set_release(&controller->lifecycle,\n"
        "\t\t\t   MT6797_A72_RESTORE_BOOTING);\n"
        "\tresult->last_stage = MT6797_A72_RESTORE_STAGE_CPU_BOOT;\n",
        "\tatomic_set_release(&controller->lifecycle,\n"
        "\t\t\t   MT6797_A72_RESTORE_REARMING);\n"
        "\tresult->last_stage = MT6797_A72_RESTORE_STAGE_P30E_REARMED;\n"
        "\tresult->p30e_rearm_calls++;\n"
        "\tret = ops->p30e_rearm(context, cpu);\n"
        "\tif (ret)\n"
        "\t\treturn mt6797_a72_restore_fault(controller, ops, context,\n"
        "\t\t\t\t\t\tresult, ret, true);\n"
        "\tresult->p30e_rearmed = true;\n"
        "\tatomic_set_release(&controller->lifecycle,\n"
        "\t\t\t   MT6797_A72_RESTORE_REARMED);\n"
        "\tret = mt6797_a72_restore_checkpoint(controller, ops, context, result,\n"
        "\t\t\tMT6797_A72_RESTORE_STAGE_P30E_REARMED, true);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\tatomic_set_release(&controller->lifecycle,\n"
        "\t\t\t   MT6797_A72_RESTORE_BOOTING);\n"
        "\tresult->last_stage = MT6797_A72_RESTORE_STAGE_CPU_BOOT;\n")

    executor_test = (
        root / "drivers/soc/mediatek/mt6797-a72-restore-executor-test.c"
    )
    replace_once(executor_test,
        "\tRESTORE_TEST_BEGIN,\n\tRESTORE_TEST_BOOT,\n",
        "\tRESTORE_TEST_BEGIN,\n\tRESTORE_TEST_REARM,\n\tRESTORE_TEST_BOOT,\n")
    replace_once(executor_test,
        "\tRESTORE_TEST_CHECKPOINT_COMMITTED,\n"
        "\tRESTORE_TEST_CHECKPOINT_SECONDARY,\n",
        "\tRESTORE_TEST_CHECKPOINT_COMMITTED,\n"
        "\tRESTORE_TEST_CHECKPOINT_REARMED,\n"
        "\tRESTORE_TEST_CHECKPOINT_SECONDARY,\n")
    replace_once(executor_test,
        "\tenum mt6797_a72_restore_executor_stage checkpoints[3];\n",
        "\tenum mt6797_a72_restore_executor_stage checkpoints[4];\n")
    replace_once(executor_test,
        "\tu32 begin_calls;\n\tu32 boot_calls;\n",
        "\tu32 begin_calls;\n\tu32 rearm_calls;\n\tu32 boot_calls;\n")
    replace_once(executor_test,
        "\t    (stage == MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE &&\n",
        "\t    (stage == MT6797_A72_RESTORE_STAGE_P30E_REARMED &&\n"
        "\t     restore_executor_test_fails(\n"
        "\t\t     state, RESTORE_TEST_CHECKPOINT_REARMED)) ||\n"
        "\t    (stage == MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE &&\n")
    boot_anchor = "static int restore_executor_test_boot(void *context, unsigned int cpu)\n"
    rearm_fn = r'''static int restore_executor_test_rearm(void *context, unsigned int cpu)
{
	struct restore_executor_test_state *state = context;

	state->rearm_calls++;
	if (cpu != MT6797_A72_RESTORE_CPU9 || state->boot_calls)
		return -EPROTO;
	return restore_executor_test_fails(state, RESTORE_TEST_REARM) ?
		-EIO : 0;
}

'''
    replace_once(executor_test, boot_anchor, rearm_fn + boot_anchor)
    replace_once(executor_test,
        "\t.begin_restore = restore_executor_test_begin,\n"
        "\t.cpu_boot = restore_executor_test_boot,\n",
        "\t.begin_restore = restore_executor_test_begin,\n"
        "\t.p30e_rearm = restore_executor_test_rearm,\n"
        "\t.cpu_boot = restore_executor_test_boot,\n")
    replace_once(executor_test,
        "\tKUNIT_EXPECT_EQ(test, state->result.validate_calls, (u32)1);\n"
        "\tKUNIT_EXPECT_EQ(test, state->result.begin_calls, (u32)1);\n"
        "\tKUNIT_EXPECT_EQ(test, state->result.cpu_boot_calls, (u32)1);\n",
        "\tKUNIT_EXPECT_EQ(test, state->result.validate_calls, (u32)1);\n"
        "\tKUNIT_EXPECT_EQ(test, state->result.begin_calls, (u32)1);\n"
        "\tKUNIT_EXPECT_EQ(test, state->result.p30e_rearm_calls, (u32)1);\n"
        "\tKUNIT_EXPECT_TRUE(test, state->result.p30e_rearmed);\n"
        "\tKUNIT_EXPECT_EQ(test, state->result.cpu_boot_calls, (u32)1);\n")
    replace_once(executor_test,
        "\tKUNIT_EXPECT_EQ(test, state->result.checkpoint_calls, (u32)3);\n"
        "\tKUNIT_EXPECT_EQ(test, state->result.terminal_calls, (u32)1);\n"
        "\tKUNIT_EXPECT_EQ(test, state->checkpoint_calls, (u32)3);\n",
        "\tKUNIT_EXPECT_EQ(test, state->result.checkpoint_calls, (u32)4);\n"
        "\tKUNIT_EXPECT_EQ(test, state->result.terminal_calls, (u32)1);\n"
        "\tKUNIT_EXPECT_EQ(test, state->checkpoint_calls, (u32)4);\n")
    replace_once(executor_test,
        "\tKUNIT_EXPECT_EQ(test, state->checkpoints[2],\n"
        "\t\t\tMT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE);\n",
        "\tKUNIT_EXPECT_EQ(test, state->checkpoints[2],\n"
        "\t\t\tMT6797_A72_RESTORE_STAGE_P30E_REARMED);\n"
        "\tKUNIT_EXPECT_EQ(test, state->checkpoints[3],\n"
        "\t\t\tMT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE);\n")
    replace_once(executor_test,
        "\tops.cpu_boot = NULL;\n",
        "\tops.p30e_rearm = NULL;\n"
        "\tret = mt6797_a72_restore_executor_preflight(\n"
        "\t\t&state->controller, &ops, state, &state->request,\n"
        "\t\t&state->result);\n"
        "\tKUNIT_EXPECT_EQ(test, ret, -EINVAL);\n"
        "\tops.p30e_rearm = restore_executor_test_rearm;\n"
        "\tops.cpu_boot = NULL;\n")
    boot_failure_anchor = "static void restore_executor_boot_failure_test(struct kunit *test)\n"
    rearm_test = r'''static void restore_executor_rearm_failure_test(struct kunit *test)
{
	struct restore_executor_test_state *state = test->priv;
	int ret;

	KUNIT_ASSERT_EQ(test, restore_executor_test_to_validated(state), 0);
	state->failure = RESTORE_TEST_REARM;
	ret = mt6797_a72_restore_executor_boot(
		&state->controller, &restore_executor_test_ops, state,
		MT6797_A72_RESTORE_CPU9, true, false, &state->result);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state->result.p30e_rearm_calls, 1U);
	KUNIT_EXPECT_FALSE(test, state->result.p30e_rearmed);
	KUNIT_EXPECT_EQ(test, state->result.cpu_boot_calls, 0U);
	KUNIT_EXPECT_EQ(test, state->boot_calls, 0U);
	KUNIT_EXPECT_EQ(test, state->result.fail_calls, 1U);
}

'''
    replace_once(executor_test, boot_failure_anchor, rearm_test + boot_failure_anchor)
    replace_once(executor_test,
        "\tstruct restore_executor_test_state *secondary;\n",
        "\tstruct restore_executor_test_state *rearmed;\n"
        "\tstruct restore_executor_test_state *secondary;\n")
    replace_once(executor_test,
        "\tsecondary = restore_executor_test_new(test);\n",
        "\trearmed = restore_executor_test_new(test);\n"
        "\tKUNIT_ASSERT_NOT_NULL(test, rearmed);\n"
        "\tret = restore_executor_test_to_validated(rearmed);\n"
        "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
        "\trearmed->failure = RESTORE_TEST_CHECKPOINT_REARMED;\n"
        "\tret = mt6797_a72_restore_executor_boot(\n"
        "\t\t&rearmed->controller, &restore_executor_test_ops, rearmed,\n"
        "\t\tMT6797_A72_RESTORE_CPU9, true, false, &rearmed->result);\n"
        "\tKUNIT_EXPECT_EQ(test, ret, -EIO);\n"
        "\tKUNIT_EXPECT_EQ(test, rearmed->rearm_calls, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, rearmed->boot_calls, 0U);\n"
        "\tKUNIT_EXPECT_EQ(test, rearmed->fail_calls, 1U);\n\n"
        "\tsecondary = restore_executor_test_new(test);\n",  # type: ignore[arg-type]
    )
    replace_once(executor_test,
        "\tKUNIT_CASE(restore_executor_boot_failure_test),\n",
        "\tKUNIT_CASE(restore_executor_rearm_failure_test),\n"
        "\tKUNIT_CASE(restore_executor_boot_failure_test),\n")

    binding_header = (
        root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
    )
    replace_once(binding_header,
        "#define MT6797_A72_RESTORE_READY_CPU9_STATUS BIT(6)\n",
        "#define MT6797_A72_RESTORE_READY_CPU9_STATUS BIT(6)\n"
        "#define MT6797_A72_RESTORE_READY_CPU9_PWR_CON 0x00010332U\n")

    binding = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
    replace_once(binding,
        "#include <asm/mt6797_a72_membership.h>\n",
        "#include <asm/mt6797_a72_membership.h>\n"
        "#include <asm/mt6797_a72_p30e.h>\n")
    replace_once(binding,
        "\t\tif (!((result->last.spm_cpu_pwr_status |\n"
        "\t\t       result->last.spm_cpu_pwr_status_2nd) &\n"
        "\t\t      MT6797_A72_RESTORE_READY_CPU9_STATUS)) {\n",
        "\t\tif (!(result->last.spm_cpu_pwr_status &\n"
        "\t\t      MT6797_A72_RESTORE_READY_CPU9_STATUS) &&\n"
        "\t\t    result->last.spm_mp2_cpu1_pwr_con ==\n"
        "\t\t      MT6797_A72_RESTORE_READY_CPU9_PWR_CON) {\n")
    boot_fn_anchor = "static int mt6797_a72_hotplug_restore_cpu_boot(void *context,\n"
    rearm_binding = r'''static int mt6797_a72_hotplug_restore_p30e_rearm(void *context,
						 unsigned int cpu)
{
	(void)context;
	return cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 ?
		arm64_mt6797_a72_p30e_rearm_cpu9() : -EPERM;
}

'''
    replace_once(binding, boot_fn_anchor, rearm_binding + boot_fn_anchor)
    replace_once(binding,
        "\t    stage != MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED &&\n"
        "\t    stage != MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE)\n",
        "\t    stage != MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED &&\n"
        "\t    stage != MT6797_A72_RESTORE_STAGE_P30E_REARMED &&\n"
        "\t    stage != MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE)\n")
    replace_once(binding,
        "\t.begin_restore = mt6797_a72_hotplug_begin_restore_op,\n"
        "\t.cpu_boot = mt6797_a72_hotplug_restore_cpu_boot,\n",
        "\t.begin_restore = mt6797_a72_hotplug_begin_restore_op,\n"
        "\t.p30e_rearm = mt6797_a72_hotplug_restore_p30e_rearm,\n"
        "\t.cpu_boot = mt6797_a72_hotplug_restore_cpu_boot,\n")

    binding_test = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c"
    replace_once(binding_test,
        "\t\t\t.spm_mp2_cpu1_pwr_con = 0x10,\n",
        "\t\t\t.spm_mp2_cpu1_pwr_con =\n"
        "\t\t\t\tMT6797_A72_RESTORE_READY_CPU9_PWR_CON,\n")
    replace_once(binding_test,
        "\tKUNIT_EXPECT_EQ(test, result.last.spm_mp2_cpu1_pwr_con, 0x10U);\n",
        "\tKUNIT_EXPECT_EQ(test, result.last.spm_mp2_cpu1_pwr_con,\n"
        "\t\t\tMT6797_A72_RESTORE_READY_CPU9_PWR_CON);\n")
    old_settles = r'''static void hotplug_binding_readiness_settles_test(struct kunit *test)
{
	struct mt6797_a72_restore_readiness_result result;
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->readiness_count = 3;
	state->readiness[1] = state->readiness[0];
	state->readiness[2] = state->readiness[0];
	state->readiness[0].spm_cpu_pwr_status_2nd |= BIT(6);
	state->readiness[1].spm_cpu_pwr_status_2nd |= BIT(6);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_restore_readiness_with_ops(
		&hotplug_binding_test_readiness_ops, state, &result), 0);
	KUNIT_EXPECT_TRUE(test, result.ready);
	KUNIT_EXPECT_EQ(test, result.sample_calls, 3U);
	KUNIT_EXPECT_EQ(test, result.sleep_calls, 2U);
	KUNIT_EXPECT_EQ(test, state->readiness_sleep_calls, 2U);
	KUNIT_EXPECT_TRUE(test, result.first.spm_cpu_pwr_status_2nd & BIT(6));
	KUNIT_EXPECT_FALSE(test, result.last.spm_cpu_pwr_status_2nd & BIT(6));
}
'''
    new_settles = r'''static void hotplug_binding_readiness_persistent_secondary_test(
	struct kunit *test)
{
	struct mt6797_a72_restore_readiness_result result;
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->readiness[0].spm_cpu_pwr_status_2nd |= BIT(6);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_restore_readiness_with_ops(
		&hotplug_binding_test_readiness_ops, state, &result), 0);
	KUNIT_EXPECT_TRUE(test, result.ready);
	KUNIT_EXPECT_EQ(test, result.sample_calls, 1U);
	KUNIT_EXPECT_EQ(test, result.sleep_calls, 0U);
	KUNIT_EXPECT_TRUE(test, result.last.spm_cpu_pwr_status_2nd & BIT(6));
}
'''
    replace_once(binding_test, old_settles, new_settles)
    replace_once(binding_test,
        "static void hotplug_binding_readiness_timeout_test(struct kunit *test)\n"
        "{\n"
        "\tstruct mt6797_a72_restore_readiness_result result;\n"
        "\tstruct hotplug_binding_test_state *state;\n\n"
        "\tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);\n"
        "\tKUNIT_ASSERT_NOT_NULL(test, state);\n"
        "\thotplug_binding_test_init(state);\n"
        "\tstate->readiness[0].spm_cpu_pwr_status_2nd |= BIT(6);\n",
        "static void hotplug_binding_readiness_timeout_test(struct kunit *test)\n"
        "{\n"
        "\tstruct mt6797_a72_restore_readiness_result result;\n"
        "\tstruct hotplug_binding_test_state *state;\n\n"
        "\tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);\n"
        "\tKUNIT_ASSERT_NOT_NULL(test, state);\n"
        "\thotplug_binding_test_init(state);\n"
        "\tstate->readiness[0].spm_cpu_pwr_status |= BIT(6);\n")
    power_test_anchor = "static void hotplug_binding_readiness_cpu8_guard_test(struct kunit *test)\n"
    power_test = r'''static void hotplug_binding_readiness_power_guard_test(struct kunit *test)
{
	struct mt6797_a72_restore_readiness_result result;
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->readiness[0].spm_mp2_cpu1_pwr_con = 0x0001033f;
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_restore_readiness_with_ops(
		&hotplug_binding_test_readiness_ops, state, &result), -ETIMEDOUT);
	KUNIT_EXPECT_FALSE(test, result.ready);
	KUNIT_EXPECT_EQ(test, result.sample_calls,
			MT6797_A72_RESTORE_READY_SAMPLES_MAX);
}

'''
    replace_once(binding_test, power_test_anchor, power_test + power_test_anchor)
    replace_once(binding_test,
        "\tKUNIT_CASE(hotplug_binding_readiness_settles_test),\n"
        "\tKUNIT_CASE(hotplug_binding_readiness_timeout_test),\n",
        "\tKUNIT_CASE(hotplug_binding_readiness_persistent_secondary_test),\n"
        "\tKUNIT_CASE(hotplug_binding_readiness_timeout_test),\n"
        "\tKUNIT_CASE(hotplug_binding_readiness_power_guard_test),\n")

    ledger_public = root / "include/linux/gemini_a72_hotplug_ledger.h"
    replace_once(ledger_public,
        "\tGEMINI_A72_HOTPLUG_CPU_ON_COMMITTED,\n"
        "\tGEMINI_A72_HOTPLUG_SECONDARY_COMPLETE,\n"
        "\tGEMINI_A72_HOTPLUG_RESTORE_COMPLETE,\n",
        "\tGEMINI_A72_HOTPLUG_CPU_ON_COMMITTED,\n"
        "\tGEMINI_A72_HOTPLUG_P30E_REARMED,\n"
        "\tGEMINI_A72_HOTPLUG_SECONDARY_COMPLETE,\n"
        "\tGEMINI_A72_HOTPLUG_RESTORE_COMPLETE,\n")
    ledger_internal = root / "fs/pstore/gemini_a72_hotplug_ledger_internal.h"
    replace_once(ledger_internal,
        "#define GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 16U\n",
        "#define GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 17U\n")

    ledger_test = root / "fs/pstore/gemini_a72_hotplug_ledger_test.c"
    replace_once(ledger_test,
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS, 16U);\n",
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS, 17U);\n")
    replace_once(ledger_test,
        "\tKUNIT_EXPECT_EQ(test, state.writes, 611U);\n",
        "\tKUNIT_EXPECT_EQ(test, state.writes, 649U);\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("primitive", "integration"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "primitive":
        primitive(root)
    else:
        integration(root)


if __name__ == "__main__":
    main()
