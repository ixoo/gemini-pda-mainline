// SPDX-License-Identifier: GPL-2.0-only
/* One-shot retained record-5 ledger for the Gemini MT6797 thermal probe. */

#include <linux/crc32.h>
#include <linux/errno.h>
#include <linux/export.h>
#include <linux/gemini_mt6797_thermal_ledger.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/string.h>

#include "gemini_mt6797_thermal_ledger_internal.h"

#define GEMINI_MT6797_THERMAL_LEDGER_RESERVE_BASE 0x44410000ULL
#define GEMINI_MT6797_THERMAL_LEDGER_BASE 0x44415000ULL
#define GEMINI_MT6797_THERMAL_LEDGER_RESERVE_SIZE 0x000e0000ULL

static unsigned int thermal_copy_word(unsigned int copy, unsigned int word)
{
	return GEMINI_MT6797_THERMAL_LEDGER_HEADER_WORDS +
		copy * GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS + word;
}

static u32 thermal_integrity(const __le32 *wire)
{
	return crc32_le(~0U, (const u8 *)wire,
			GEMINI_MT6797_THERMAL_LEDGER_INTEGRITY_WORD *
			sizeof(*wire)) ^ ~0U;
}

static void thermal_read_wire(
	const struct gemini_mt6797_thermal_ledger_ops *ops, void *context,
	unsigned int copy, __le32 *wire)
{
	unsigned int word;

	for (word = 0; word < GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS;
	     word++)
		wire[word] = cpu_to_le32(ops->read(context,
						   thermal_copy_word(copy, word)));
}

static bool thermal_index_valid(u32 operation, u32 index)
{
	switch (operation) {
	case GEMINI_MT6797_THERMAL_PREPARE_BANK:
	case GEMINI_MT6797_THERMAL_ENABLE_BANK:
	case GEMINI_MT6797_THERMAL_RELEASE_BANK:
	case GEMINI_MT6797_THERMAL_FIRST_SAMPLE:
		return index <= GEMINI_MT6797_THERMAL_LEDGER_MAX_BANK;
	default:
		return index == GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE;
	}
}

static bool thermal_record_shape_valid(
	const struct gemini_mt6797_thermal_ledger_record *record)
{
	if (record->attempt_id != GEMINI_MT6797_THERMAL_LEDGER_ATTEMPT_ID ||
	    !record->generation ||
	    record->generation > GEMINI_MT6797_THERMAL_LEDGER_MAX_RECORDS ||
	    !record->operation ||
	    record->operation > GEMINI_MT6797_THERMAL_PROBE_COMPLETE ||
	    record->phase < GEMINI_MT6797_THERMAL_LEDGER_BEFORE ||
	    record->phase > GEMINI_MT6797_THERMAL_LEDGER_TERMINAL ||
	    !thermal_index_valid(record->operation, record->index))
		return false;

	if (record->phase == GEMINI_MT6797_THERMAL_LEDGER_BEFORE)
		return !record->result && !record->terminal;
	if (record->phase == GEMINI_MT6797_THERMAL_LEDGER_AFTER)
		return record->result <= 0 && !record->terminal;
	if (record->terminal == GEMINI_MT6797_THERMAL_LEDGER_SUCCESS)
		return record->operation ==
			GEMINI_MT6797_THERMAL_PROBE_COMPLETE && !record->result;
	return record->terminal == GEMINI_MT6797_THERMAL_LEDGER_FAILURE &&
		record->result < 0;
}

static bool thermal_wire_valid(
	const __le32 *wire,
	struct gemini_mt6797_thermal_ledger_record *record)
{
	if (le32_to_cpu(wire[0]) != GEMINI_MT6797_THERMAL_LEDGER_MAGIC ||
	    le32_to_cpu(wire[1]) !=
		    GEMINI_MT6797_THERMAL_LEDGER_VERSION_WORD ||
	    le32_to_cpu(
		    wire[GEMINI_MT6797_THERMAL_LEDGER_INTEGRITY_WORD]) !=
		    thermal_integrity(wire))
		return false;

	record->generation = le32_to_cpu(wire[2]);
	record->operation = le32_to_cpu(wire[3]);
	record->phase = le32_to_cpu(wire[4]);
	record->index = le32_to_cpu(wire[5]);
	record->result = (s32)le32_to_cpu(wire[6]);
	record->terminal = le32_to_cpu(wire[7]);
	record->attempt_id = le32_to_cpu(wire[8]);
	record->attempt_id |= (u64)le32_to_cpu(wire[9]) << 32;
	if (le32_to_cpu(wire[10]))
		return false;

	return thermal_record_shape_valid(record);
}

bool gemini_mt6797_thermal_ledger_read_latest(
	const struct gemini_mt6797_thermal_ledger_ops *ops, void *context,
	struct gemini_mt6797_thermal_ledger_record *record, u32 *copy_index)
{
	struct gemini_mt6797_thermal_ledger_record candidate;
	__le32 wire[GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS];
	bool found = false;
	unsigned int copy;

	if (!ops || !ops->read || !record || !copy_index)
		return false;
	for (copy = 0; copy < GEMINI_MT6797_THERMAL_LEDGER_COPIES; copy++) {
		thermal_read_wire(ops, context, copy, wire);
		if (!thermal_wire_valid(wire, &candidate))
			continue;
		if (found && candidate.generation == record->generation)
			return false;
		if (!found || candidate.generation > record->generation) {
			*record = candidate;
			*copy_index = copy;
			found = true;
		}
	}

	return found;
}

static bool thermal_ops_valid(
	const struct gemini_mt6797_thermal_ledger_ops *ops)
{
	return ops && ops->read && ops->write && ops->sync;
}

int gemini_mt6797_thermal_ledger_owner_begin(
	struct gemini_mt6797_thermal_ledger_owner *owner,
	const struct gemini_mt6797_thermal_ledger_ops *ops, void *context)
{
	struct gemini_mt6797_thermal_ledger_record record;
	u32 copy;
	u32 signature;
	u32 size;
	u32 start;
	bool empty;
	bool raw;

	if (!owner || !thermal_ops_valid(ops))
		return -EINVAL;
	if (owner->active || owner->sealed)
		return -EALREADY;
	signature = ops->read(context, 0);
	start = ops->read(context, 1);
	size = ops->read(context, 2);
	raw = signature == ~0U && start == ~0U && size == ~0U;
	empty = signature == GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE &&
		!start && !size;
	if (!raw && !empty) {
		if (signature ==
			    GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE &&
		    start == GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES &&
		    size == start &&
		    gemini_mt6797_thermal_ledger_read_latest(
			    ops, context, &record, &copy))
			return -EALREADY;
		return -EBADMSG;
	}

	owner->next_generation = 1;
	owner->active = true;
	owner->needs_signature = raw;

	return 0;
}

static int thermal_fault(struct gemini_mt6797_thermal_ledger_owner *owner)
{
	owner->active = false;
	owner->failed = true;
	owner->sealed = true;

	return -EIO;
}

int gemini_mt6797_thermal_ledger_owner_checkpoint(
	struct gemini_mt6797_thermal_ledger_owner *owner,
	const struct gemini_mt6797_thermal_ledger_ops *ops, void *context,
	u32 operation, u32 phase, u32 index, int result, u32 terminal)
{
	struct gemini_mt6797_thermal_ledger_record committed = {
		.attempt_id = GEMINI_MT6797_THERMAL_LEDGER_ATTEMPT_ID,
		.operation = operation,
		.phase = phase,
		.index = index,
		.result = result,
		.terminal = terminal,
	};
	__le32 readback[GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS];
	__le32 wire[GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS] = {};
	unsigned int target;
	unsigned int word;

	if (!owner || !thermal_ops_valid(ops))
		return -EINVAL;
	if (!owner->active)
		return owner->sealed ? -EALREADY : -EPERM;
	if (!owner->records &&
	    (operation != GEMINI_MT6797_THERMAL_PROBE ||
	     phase != GEMINI_MT6797_THERMAL_LEDGER_BEFORE))
		return -EINVAL;
	if (owner->records >= GEMINI_MT6797_THERMAL_LEDGER_MAX_RECORDS)
		return -EOVERFLOW;
	committed.generation = owner->next_generation;
	if (!thermal_record_shape_valid(&committed))
		return -EINVAL;

	wire[0] = cpu_to_le32(GEMINI_MT6797_THERMAL_LEDGER_MAGIC);
	wire[1] = cpu_to_le32(GEMINI_MT6797_THERMAL_LEDGER_VERSION_WORD);
	wire[2] = cpu_to_le32(committed.generation);
	wire[3] = cpu_to_le32(committed.operation);
	wire[4] = cpu_to_le32(committed.phase);
	wire[5] = cpu_to_le32(committed.index);
	wire[6] = cpu_to_le32((u32)committed.result);
	wire[7] = cpu_to_le32(committed.terminal);
	wire[8] = cpu_to_le32(lower_32_bits(committed.attempt_id));
	wire[9] = cpu_to_le32(upper_32_bits(committed.attempt_id));
	wire[10] = 0;
	wire[11] = cpu_to_le32(thermal_integrity(wire));
	target = owner->have_valid ? owner->newest_copy ^ 1U : 0;

	ops->write(context, thermal_copy_word(target,
			GEMINI_MT6797_THERMAL_LEDGER_INTEGRITY_WORD), 0);
	ops->sync(context);
	for (word = 0; word < GEMINI_MT6797_THERMAL_LEDGER_INTEGRITY_WORD;
	     word++)
		ops->write(context, thermal_copy_word(target, word),
			   le32_to_cpu(wire[word]));
	ops->sync(context);
	ops->write(context, thermal_copy_word(target,
			GEMINI_MT6797_THERMAL_LEDGER_INTEGRITY_WORD),
		   le32_to_cpu(
			   wire[GEMINI_MT6797_THERMAL_LEDGER_INTEGRITY_WORD]));
	ops->sync(context);
	thermal_read_wire(ops, context, target, readback);
	if (memcmp(wire, readback, sizeof(wire)))
		return thermal_fault(owner);

	if (!owner->header_committed) {
		ops->write(context, 1,
			   GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES);
		ops->sync(context);
		ops->write(context, 2,
			   GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES);
		ops->sync(context);
		if (owner->needs_signature) {
			ops->write(context, 0,
				   GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE);
			ops->sync(context);
		}
		if (ops->read(context, 0) !=
			    GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE ||
		    ops->read(context, 1) !=
			    GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES ||
		    ops->read(context, 2) !=
			    GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES)
			return thermal_fault(owner);
		owner->header_committed = true;
	}

	owner->newest_copy = target;
	owner->have_valid = true;
	owner->records++;
	owner->next_generation++;
	if (phase == GEMINI_MT6797_THERMAL_LEDGER_TERMINAL) {
		owner->active = false;
		owner->sealed = true;
	}

	return 0;
}

static bool gemini_mt6797_thermal_ledger_exact_dt(void)
{
	struct device_node *node;
	struct device_node *thermal;
	struct resource resource;
	const char *model;
	u32 value;
	bool exact = false;

	if (!of_machine_is_compatible("planet,gemini-pda") ||
	    of_property_read_string(of_root, "model", &model) ||
	    strcmp(model,
		   "Planet Computers Gemini PDA (thermal serviceability)"))
		return false;
	node = of_find_node_by_path("/reserved-memory/ramoops@44410000");
	if (!node)
		return false;
	if (!of_device_is_compatible(node, "ramoops") ||
	    of_address_to_resource(node, 0, &resource) ||
	    resource.start != GEMINI_MT6797_THERMAL_LEDGER_RESERVE_BASE ||
	    resource_size(&resource) !=
		    GEMINI_MT6797_THERMAL_LEDGER_RESERVE_SIZE ||
	    !of_property_read_bool(node, "no-map"))
		goto out_node;
	if (of_property_read_u32(node, "record-size", &value) ||
	    value != GEMINI_MT6797_THERMAL_LEDGER_SLOT_SIZE ||
	    of_property_read_u32(node, "console-size", &value) ||
	    value != 0x10000 ||
	    of_property_read_u32(node, "ftrace-size", &value) ||
	    value != 0x1000 ||
	    of_property_read_u32(node, "pmsg-size", &value) ||
	    value != 0x20000 ||
	    of_property_read_u32(node, "mem-type", &value) || value)
		goto out_node;

	thermal = of_find_node_by_path("/thermal@1100b000");
	if (!thermal)
		goto out_node;
	if (of_device_is_compatible(thermal, "mediatek,mt6797-thermal") &&
	    of_device_is_available(thermal))
		exact = true;
	of_node_put(thermal);
out_node:
	of_node_put(node);

	return exact;
}

static u32 gemini_mt6797_thermal_ledger_mmio_read(void *context,
						   unsigned int word)
{
	void __iomem *slot = context;

	return readl((u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_mt6797_thermal_ledger_mmio_write(void *context,
						     unsigned int word,
						     u32 value)
{
	void __iomem *slot = context;

	writel(value, (u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_mt6797_thermal_ledger_mmio_sync(void *context)
{
	(void)context;
	wmb(); /* Publish each complete record before its commit marker. */
}

static const struct gemini_mt6797_thermal_ledger_ops thermal_mmio_ops = {
	.read = gemini_mt6797_thermal_ledger_mmio_read,
	.write = gemini_mt6797_thermal_ledger_mmio_write,
	.sync = gemini_mt6797_thermal_ledger_mmio_sync,
};

static DEFINE_MUTEX(gemini_mt6797_thermal_ledger_lock);
static struct gemini_mt6797_thermal_ledger_owner thermal_owner;
static void __iomem *thermal_slot;

int gemini_mt6797_thermal_ledger_begin(void)
{
	int ret;

	mutex_lock(&gemini_mt6797_thermal_ledger_lock);
	if (thermal_slot || thermal_owner.sealed) {
		ret = -EALREADY;
		goto out_unlock;
	}
	if (!gemini_mt6797_thermal_ledger_exact_dt()) {
		ret = -ENODEV;
		goto out_unlock;
	}
	thermal_slot = ioremap_wc(GEMINI_MT6797_THERMAL_LEDGER_BASE,
				  GEMINI_MT6797_THERMAL_LEDGER_SLOT_SIZE);
	if (!thermal_slot) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	ret = gemini_mt6797_thermal_ledger_owner_begin(
		&thermal_owner, &thermal_mmio_ops, thermal_slot);
	if (!ret)
		ret = gemini_mt6797_thermal_ledger_owner_checkpoint(
			&thermal_owner, &thermal_mmio_ops, thermal_slot,
			GEMINI_MT6797_THERMAL_PROBE,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
			GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0);
	if (ret) {
		iounmap(thermal_slot);
		thermal_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_mt6797_thermal_ledger_lock);

	return ret;
}
EXPORT_SYMBOL_GPL(gemini_mt6797_thermal_ledger_begin);

int gemini_mt6797_thermal_ledger_checkpoint(u32 operation, u32 phase,
					     u32 index, int result,
					     u32 terminal)
{
	int ret;

	mutex_lock(&gemini_mt6797_thermal_ledger_lock);
	if (!thermal_slot) {
		ret = thermal_owner.sealed ? -EALREADY : -ENODEV;
		goto out_unlock;
	}
	ret = gemini_mt6797_thermal_ledger_owner_checkpoint(
		&thermal_owner, &thermal_mmio_ops, thermal_slot, operation, phase,
		index, result, terminal);
	if (ret || phase == GEMINI_MT6797_THERMAL_LEDGER_TERMINAL) {
		iounmap(thermal_slot);
		thermal_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_mt6797_thermal_ledger_lock);

	return ret;
}
EXPORT_SYMBOL_GPL(gemini_mt6797_thermal_ledger_checkpoint);

MODULE_DESCRIPTION("Gemini MT6797 retained thermal-stage ledger");
MODULE_LICENSE("GPL");
