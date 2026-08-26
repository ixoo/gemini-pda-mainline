// SPDX-License-Identifier: GPL-2.0-only
/* One-shot retained last-stage ledger for the Gemini CPU8 transition. */

#include <linux/crc32.h>
#include <linux/errno.h>
#include <linux/export.h>
#include <linux/gemini_transition_ledger.h>
#include <linux/io.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/string.h>

#include "gemini_transition_ledger_internal.h"

#define GEMINI_TRANSITION_LEDGER_BASE 0x44410000ULL
#define GEMINI_TRANSITION_LEDGER_RESERVE_SIZE 0x000e0000ULL

static unsigned int gemini_transition_ledger_copy_word(unsigned int copy,
						       unsigned int word)
{
	return GEMINI_TRANSITION_LEDGER_HEADER_WORDS +
		copy * GEMINI_TRANSITION_LEDGER_COPY_WORDS + word;
}

static u32 gemini_transition_ledger_integrity(const __le32 *wire)
{
	return crc32_le(~0U, (const u8 *)wire,
			GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD *
			sizeof(*wire)) ^ ~0U;
}

static void
gemini_transition_ledger_read_wire(const struct gemini_transition_ledger_ops *ops,
				   void *context, unsigned int copy,
				   __le32 *wire)
{
	unsigned int word;

	for (word = 0; word < GEMINI_TRANSITION_LEDGER_COPY_WORDS; word++)
		wire[word] = cpu_to_le32(ops->read(context,
						   gemini_transition_ledger_copy_word(copy, word)));
}

static bool
gemini_transition_ledger_wire_valid(const __le32 *wire,
				    struct gemini_transition_ledger_record *record)
{
	u64 attempt_id;
	u32 phase;
	u32 stage;
	u32 terminal;

	if (le32_to_cpu(wire[0]) != GEMINI_TRANSITION_LEDGER_MAGIC ||
	    le32_to_cpu(wire[1]) != GEMINI_TRANSITION_LEDGER_VERSION_WORD ||
	    le32_to_cpu(wire[GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD]) !=
		    gemini_transition_ledger_integrity(wire))
		return false;
	attempt_id = le32_to_cpu(wire[2]);
	attempt_id |= (u64)le32_to_cpu(wire[3]) << 32;
	phase = le32_to_cpu(wire[5]);
	stage = le32_to_cpu(wire[6]);
	terminal = le32_to_cpu(wire[7]);
	if (!attempt_id || !le32_to_cpu(wire[4]) ||
	    phase < GEMINI_TRANSITION_LEDGER_BEFORE ||
	    phase > GEMINI_TRANSITION_LEDGER_TERMINAL || !stage ||
	    stage > GEMINI_TRANSITION_LEDGER_MAX_STAGE ||
	    terminal > GEMINI_TRANSITION_LEDGER_MAX_TERMINAL ||
	    (phase == GEMINI_TRANSITION_LEDGER_TERMINAL && !terminal) ||
	    (phase != GEMINI_TRANSITION_LEDGER_TERMINAL && terminal))
		return false;

	record->attempt_id = attempt_id;
	record->generation = le32_to_cpu(wire[4]);
	record->phase = phase;
	record->stage = stage;
	record->terminal = terminal;
	return true;
}

bool
gemini_transition_ledger_read_latest(const struct gemini_transition_ledger_ops *ops,
				     void *context,
	struct gemini_transition_ledger_record *record, u32 *copy_index)
{
	struct gemini_transition_ledger_record candidate;
	__le32 wire[GEMINI_TRANSITION_LEDGER_COPY_WORDS];
	bool found = false;
	unsigned int copy;

	if (!ops || !ops->read || !record || !copy_index)
		return false;
	for (copy = 0; copy < GEMINI_TRANSITION_LEDGER_COPIES; copy++) {
		gemini_transition_ledger_read_wire(ops, context, copy, wire);
		if (!gemini_transition_ledger_wire_valid(wire, &candidate))
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

static bool
gemini_transition_ledger_ops_valid(const struct gemini_transition_ledger_ops *ops)
{
	return ops && ops->read && ops->write && ops->barrier;
}

int
gemini_transition_ledger_owner_begin(struct gemini_transition_ledger_owner *owner,
				     const struct gemini_transition_ledger_ops *ops,
				     void *context,
	u64 attempt_id)
{
	struct gemini_transition_ledger_record latest;
	u32 signature;
	u32 copy = 0;
	u32 size;
	u32 start;
	bool committed;
	bool empty;
	bool raw;
	bool valid = false;

	if (!owner || !gemini_transition_ledger_ops_valid(ops) || !attempt_id)
		return -EINVAL;
	if (owner->active || owner->sealed)
		return -EALREADY;
	signature = ops->read(context, 0);
	start = ops->read(context, 1);
	size = ops->read(context, 2);
	raw = signature == ~0U && start == ~0U && size == ~0U;
	empty = signature == GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
		!start && !size;
	committed = signature == GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
		start == GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES && start == size;
	if (!raw && !empty && !committed)
		return -EBADMSG;
	if (committed) {
		valid = gemini_transition_ledger_read_latest(ops, context,
							     &latest, &copy);
		if (!valid)
			return -EBADMSG;
		if (latest.generation == U32_MAX)
			return -EOVERFLOW;
	}

	owner->attempt_id = attempt_id;
	owner->next_generation = valid ? latest.generation + 1 : 1;
	owner->newest_copy = copy;
	owner->active = true;
	owner->have_valid = valid;
	owner->header_committed = committed;
	owner->needs_signature = raw;
	return 0;
}

static bool
gemini_transition_ledger_sequence_valid(const struct gemini_transition_ledger_owner *owner,
					u32 phase,
	u32 stage, u32 terminal)
{
	if (phase < GEMINI_TRANSITION_LEDGER_BEFORE ||
	    phase > GEMINI_TRANSITION_LEDGER_TERMINAL || !stage ||
	    stage > GEMINI_TRANSITION_LEDGER_MAX_STAGE ||
	    terminal > GEMINI_TRANSITION_LEDGER_MAX_TERMINAL)
		return false;
	if (phase == GEMINI_TRANSITION_LEDGER_TERMINAL && !terminal)
		return false;
	if (phase != GEMINI_TRANSITION_LEDGER_TERMINAL && terminal)
		return false;
	if (!owner->have_checkpoint)
		return phase == GEMINI_TRANSITION_LEDGER_BEFORE && stage == 1;
	if (phase == GEMINI_TRANSITION_LEDGER_AFTER)
		return owner->last_phase == GEMINI_TRANSITION_LEDGER_BEFORE &&
			owner->last_stage == stage;
	if (phase == GEMINI_TRANSITION_LEDGER_BEFORE)
		return owner->last_phase == GEMINI_TRANSITION_LEDGER_AFTER &&
			owner->last_stage < GEMINI_TRANSITION_LEDGER_MAX_STAGE &&
			owner->last_stage + 1 == stage;
	return owner->last_stage == stage;
}

static int
gemini_transition_ledger_fault(struct gemini_transition_ledger_owner *owner)
{
	owner->active = false;
	owner->failed = true;
	owner->sealed = true;
	return -EIO;
}

int
gemini_transition_ledger_owner_checkpoint(struct gemini_transition_ledger_owner *owner,
					  const struct gemini_transition_ledger_ops *ops,
					  void *context,
	u64 attempt_id, u32 phase, u32 stage, u32 terminal)
{
	__le32 readback[GEMINI_TRANSITION_LEDGER_COPY_WORDS];
	__le32 wire[GEMINI_TRANSITION_LEDGER_COPY_WORDS] = {};
	unsigned int target;
	unsigned int word;

	if (!owner || !gemini_transition_ledger_ops_valid(ops))
		return -EINVAL;
	if (!owner->active)
		return owner->sealed ? -EALREADY : -EPERM;
	if (attempt_id != owner->attempt_id)
		return -EACCES;
	if (!gemini_transition_ledger_sequence_valid(owner, phase, stage,
						     terminal))
		return -EINVAL;
	if (!owner->next_generation)
		return gemini_transition_ledger_fault(owner);

	wire[0] = cpu_to_le32(GEMINI_TRANSITION_LEDGER_MAGIC);
	wire[1] = cpu_to_le32(GEMINI_TRANSITION_LEDGER_VERSION_WORD);
	wire[2] = cpu_to_le32(lower_32_bits(attempt_id));
	wire[3] = cpu_to_le32(upper_32_bits(attempt_id));
	wire[4] = cpu_to_le32(owner->next_generation);
	wire[5] = cpu_to_le32(phase);
	wire[6] = cpu_to_le32(stage);
	wire[7] = cpu_to_le32(terminal);
	wire[8] = cpu_to_le32(gemini_transition_ledger_integrity(wire));
	target = owner->have_valid ? owner->newest_copy ^ 1U : 0;

	ops->write(context, gemini_transition_ledger_copy_word(target,
			 GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD), 0);
	ops->barrier(context);
	for (word = 0; word < GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD; word++)
		ops->write(context, gemini_transition_ledger_copy_word(target,
								 word),
			   le32_to_cpu(wire[word]));
	ops->barrier(context);
	ops->write(context, gemini_transition_ledger_copy_word(target,
			 GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD),
		   le32_to_cpu(wire[GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD]));
	ops->barrier(context);
	gemini_transition_ledger_read_wire(ops, context, target, readback);
	if (memcmp(wire, readback, sizeof(wire)))
		return gemini_transition_ledger_fault(owner);

	if (!owner->header_committed) {
		ops->write(context, 1, GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES);
		ops->barrier(context);
		ops->write(context, 2, GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES);
		ops->barrier(context);
		if (owner->needs_signature) {
			ops->write(context, 0,
				   GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE);
			ops->barrier(context);
		}
		if (ops->read(context, 0) !=
			    GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE ||
		    ops->read(context, 1) !=
			    GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES ||
		    ops->read(context, 2) !=
			    GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES)
			return gemini_transition_ledger_fault(owner);
		owner->header_committed = true;
	}

	owner->newest_copy = target;
	owner->have_valid = true;
	owner->have_checkpoint = true;
	owner->last_phase = phase;
	owner->last_stage = stage;
	if (owner->next_generation == U32_MAX)
		owner->next_generation = 0;
	else
		owner->next_generation++;
	if (phase == GEMINI_TRANSITION_LEDGER_TERMINAL) {
		owner->active = false;
		owner->sealed = true;
	}
	return 0;
}

static bool gemini_transition_ledger_exact_dt(void)
{
	struct device_node *node;
	struct resource resource;
	const char *model;
	u32 value;
	bool exact = false;

	if (!of_machine_is_compatible("planet,gemini-pda") ||
	    of_property_read_string(of_root, "model", &model) ||
	    strcmp(model, "MT6797X"))
		return false;
	node = of_find_node_by_path("/reserved-memory/ramoops@44410000");
	if (!node)
		return false;
	if (!of_device_is_compatible(node, "ramoops") ||
	    of_address_to_resource(node, 0, &resource) ||
	    resource.start != GEMINI_TRANSITION_LEDGER_BASE ||
	    resource_size(&resource) != GEMINI_TRANSITION_LEDGER_RESERVE_SIZE ||
	    !of_property_read_bool(node, "no-map"))
		goto out;
	if (of_property_read_u32(node, "record-size", &value) ||
	    value != GEMINI_TRANSITION_LEDGER_SLOT_SIZE)
		goto out;
	if (of_property_read_u32(node, "console-size", &value) ||
	    value != 0x10000 ||
	    of_property_read_u32(node, "ftrace-size", &value) || value != 0x1000 ||
	    of_property_read_u32(node, "pmsg-size", &value) || value != 0x20000 ||
	    of_property_read_u32(node, "mem-type", &value) || value)
		goto out;
	exact = true;
out:
	of_node_put(node);
	return exact;
}

static u32 gemini_transition_ledger_mmio_read(void *context,
					      unsigned int word)
{
	void __iomem *slot = context;

	return readl((u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_transition_ledger_mmio_write(void *context,
						unsigned int word, u32 value)
{
	void __iomem *slot = context;

	writel(value, (u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_transition_ledger_mmio_barrier(void *context)
{
	(void)context;
	wmb(); /* Commit each record phase before the next one. */
}

static const struct gemini_transition_ledger_ops
gemini_transition_ledger_mmio_ops = {
	.read = gemini_transition_ledger_mmio_read,
	.write = gemini_transition_ledger_mmio_write,
	.barrier = gemini_transition_ledger_mmio_barrier,
};

static DEFINE_MUTEX(gemini_transition_ledger_lock);
static struct gemini_transition_ledger_owner gemini_transition_ledger_owner;
static void __iomem *gemini_transition_ledger_slot;

int gemini_transition_ledger_begin(u64 attempt_id)
{
	void __iomem *slot;
	int ret;

	mutex_lock(&gemini_transition_ledger_lock);
	if (gemini_transition_ledger_slot ||
	    gemini_transition_ledger_owner.sealed) {
		ret = -EALREADY;
		goto out_unlock;
	}
	if (!gemini_transition_ledger_exact_dt()) {
		ret = -ENODEV;
		goto out_unlock;
	}
	slot = ioremap_wc(GEMINI_TRANSITION_LEDGER_BASE,
			  GEMINI_TRANSITION_LEDGER_SLOT_SIZE);
	if (!slot) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	ret = gemini_transition_ledger_owner_begin(&gemini_transition_ledger_owner,
						   &gemini_transition_ledger_mmio_ops,
						   slot, attempt_id);
	if (ret)
		iounmap(slot);
	else
		gemini_transition_ledger_slot = slot;
out_unlock:
	mutex_unlock(&gemini_transition_ledger_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_transition_ledger_begin);

int gemini_transition_ledger_checkpoint(u64 attempt_id, u32 phase,
					u32 stage, u32 terminal)
{
	struct gemini_transition_ledger_owner *owner;
	int ret;

	mutex_lock(&gemini_transition_ledger_lock);
	owner = &gemini_transition_ledger_owner;
	if (!gemini_transition_ledger_slot) {
		ret = owner->sealed ?
			-EALREADY : -ENODEV;
		goto out_unlock;
	}
	ret = gemini_transition_ledger_owner_checkpoint(owner,
							&gemini_transition_ledger_mmio_ops,
						gemini_transition_ledger_slot,
						attempt_id, phase, stage, terminal);
	if (ret || phase == GEMINI_TRANSITION_LEDGER_TERMINAL) {
		iounmap(gemini_transition_ledger_slot);
		gemini_transition_ledger_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_transition_ledger_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_transition_ledger_checkpoint);
