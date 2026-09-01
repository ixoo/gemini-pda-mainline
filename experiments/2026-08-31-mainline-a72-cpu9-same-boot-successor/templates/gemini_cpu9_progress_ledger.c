// SPDX-License-Identifier: GPL-2.0-only
/* Retained progress ledger for the Gemini CPU9 pre-ledger boundary. */

#include <linux/errno.h>
#include <linux/export.h>
#include <linux/gemini_cpu9_progress_ledger.h>
#include <linux/io.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/string.h>

#include "gemini_cpu9_progress_ledger_internal.h"
#include "gemini_cpu9_transition_ledger_internal.h"

#define GEMINI_CPU9_PROGRESS_CPU8_BASE 0x44410000ULL
#define GEMINI_CPU9_PROGRESS_BASE \
	(GEMINI_CPU9_PROGRESS_CPU8_BASE + 2 * GEMINI_TRANSITION_LEDGER_SLOT_SIZE)
#define GEMINI_CPU9_PROGRESS_RESERVE_SIZE 0x000e0000ULL

static bool cpu9_progress_lane_empty(
	const struct gemini_transition_ledger_ops *ops, void *context)
{
	return ops->read(context, 0) ==
			GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
		ops->read(context, 1) == 0 && ops->read(context, 2) == 0;
}

static int cpu9_progress_commit_stage(
	struct gemini_cpu9_progress_owner *owner,
	const struct gemini_transition_ledger_ops *ops, void *context,
	u64 cpu8_attempt_id, u32 stage)
{
	int ret;

	ret = gemini_transition_ledger_owner_checkpoint(
		&owner->ledger, ops, context, cpu8_attempt_id,
		GEMINI_TRANSITION_LEDGER_BEFORE, stage, 0);
	if (ret)
		return ret;
	return gemini_transition_ledger_owner_checkpoint(
		&owner->ledger, ops, context, cpu8_attempt_id,
		GEMINI_TRANSITION_LEDGER_AFTER, stage, 0);
}

int cpu9_progress_owner_begin(
	struct gemini_cpu9_progress_owner *owner,
	const struct gemini_transition_ledger_ops *cpu8_ops,
	void *cpu8_context,
	const struct gemini_transition_ledger_ops *progress_ops,
	void *progress_context, u64 cpu8_attempt_id)
{
	int ret;

	if (!owner || !cpu8_ops || !cpu8_ops->read || !progress_ops ||
	    !progress_ops->read || !cpu8_attempt_id)
		return -EINVAL;
	if (owner->attempted)
		return -EALREADY;
	owner->attempted = true;
	ret = cpu9_ledger_validate_cpu8(cpu8_ops, cpu8_context,
					cpu8_attempt_id);
	if (ret)
		return ret;
	if (!cpu9_progress_lane_empty(progress_ops, progress_context))
		return progress_ops->read(progress_context, 0) ==
				GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
		       progress_ops->read(progress_context, 1) ==
				GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES &&
		       progress_ops->read(progress_context, 2) ==
				GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES ?
			-EALREADY : -EBADMSG;
	ret = gemini_transition_ledger_owner_begin(
		&owner->ledger, progress_ops, progress_context, cpu8_attempt_id);
	if (ret)
		return ret;
	return cpu9_progress_commit_stage(owner, progress_ops, progress_context,
					 cpu8_attempt_id,
					 GEMINI_CPU9_PROGRESS_CPU8_PROOF);
}

int cpu9_progress_owner_checkpoint(
	struct gemini_cpu9_progress_owner *owner,
	const struct gemini_transition_ledger_ops *ops, void *context,
	u64 cpu8_attempt_id, u32 stage)
{
	int ret;

	if (!owner || stage <= GEMINI_CPU9_PROGRESS_CPU8_PROOF ||
	    stage > GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN)
		return -EINVAL;
	ret = cpu9_progress_commit_stage(owner, ops, context, cpu8_attempt_id,
					 stage);
	if (!ret && stage == GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN) {
		owner->ledger.active = false;
		owner->ledger.sealed = true;
	}
	return ret;
}

static bool gemini_cpu9_progress_exact_dt(void)
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
	    resource.start != GEMINI_CPU9_PROGRESS_CPU8_BASE ||
	    resource_size(&resource) != GEMINI_CPU9_PROGRESS_RESERVE_SIZE ||
	    !of_property_read_bool(node, "no-map"))
		goto out;
	if (of_property_read_u32(node, "record-size", &value) ||
	    value != GEMINI_TRANSITION_LEDGER_SLOT_SIZE ||
	    of_property_read_u32(node, "console-size", &value) ||
	    value != 0x10000 ||
	    of_property_read_u32(node, "ftrace-size", &value) ||
	    value != 0x1000 ||
	    of_property_read_u32(node, "pmsg-size", &value) ||
	    value != 0x20000 ||
	    of_property_read_u32(node, "mem-type", &value) || value)
		goto out;
	exact = true;
out:
	of_node_put(node);
	return exact;
}

static u32 gemini_cpu9_progress_mmio_read(void *context, unsigned int word)
{
	void __iomem *slot = context;

	return readl((u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_cpu9_progress_mmio_write(void *context,
					    unsigned int word, u32 value)
{
	void __iomem *slot = context;

	writel(value, (u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_cpu9_progress_mmio_sync(void *context)
{
	(void)context;
	/* Order record payload writes before commit publication. */
	wmb();
}

static const struct gemini_transition_ledger_ops
gemini_cpu9_progress_mmio_ops = {
	.read = gemini_cpu9_progress_mmio_read,
	.write = gemini_cpu9_progress_mmio_write,
	.sync = gemini_cpu9_progress_mmio_sync,
};

static DEFINE_MUTEX(gemini_cpu9_progress_lock);
static struct gemini_cpu9_progress_owner gemini_cpu9_progress_owner;
static void __iomem *gemini_cpu9_progress_slot;

int gemini_cpu9_progress_begin(u64 cpu8_attempt_id)
{
	void __iomem *cpu8_slot;
	void __iomem *progress_slot;
	int ret;

	mutex_lock(&gemini_cpu9_progress_lock);
	if (gemini_cpu9_progress_owner.attempted) {
		ret = -EALREADY;
		goto out_unlock;
	}
	if (!gemini_cpu9_progress_exact_dt()) {
		ret = -ENODEV;
		goto out_unlock;
	}
	cpu8_slot = ioremap(GEMINI_CPU9_PROGRESS_CPU8_BASE,
			    GEMINI_TRANSITION_LEDGER_SLOT_SIZE);
	if (!cpu8_slot) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	progress_slot = ioremap_wc(GEMINI_CPU9_PROGRESS_BASE,
				   GEMINI_TRANSITION_LEDGER_SLOT_SIZE);
	if (!progress_slot) {
		ret = -ENOMEM;
		goto out_unmap_cpu8;
	}
	ret = cpu9_progress_owner_begin(
		&gemini_cpu9_progress_owner, &gemini_cpu9_progress_mmio_ops,
		cpu8_slot, &gemini_cpu9_progress_mmio_ops, progress_slot,
		cpu8_attempt_id);
	if (ret)
		iounmap(progress_slot);
	else
		gemini_cpu9_progress_slot = progress_slot;
out_unmap_cpu8:
	iounmap(cpu8_slot);
out_unlock:
	mutex_unlock(&gemini_cpu9_progress_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_cpu9_progress_begin);

int gemini_cpu9_progress_checkpoint(u64 cpu8_attempt_id, u32 stage)
{
	int ret;

	mutex_lock(&gemini_cpu9_progress_lock);
	if (!gemini_cpu9_progress_slot) {
		ret = gemini_cpu9_progress_owner.attempted ? -EALREADY : -ENODEV;
		goto out_unlock;
	}
	ret = cpu9_progress_owner_checkpoint(
		&gemini_cpu9_progress_owner, &gemini_cpu9_progress_mmio_ops,
		gemini_cpu9_progress_slot, cpu8_attempt_id, stage);
	if (ret || stage == GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN) {
		iounmap(gemini_cpu9_progress_slot);
		gemini_cpu9_progress_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_cpu9_progress_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_cpu9_progress_checkpoint);

MODULE_DESCRIPTION("Gemini CPU9 pre-ledger retained progress ledger");
MODULE_LICENSE("GPL");
