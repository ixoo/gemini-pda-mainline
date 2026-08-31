// SPDX-License-Identifier: GPL-2.0-only
/* One-shot retained ledger for the Gemini same-boot CPU9 successor. */

#include <linux/errno.h>
#include <linux/export.h>
#include <linux/gemini_cpu9_transition_ledger.h>
#include <linux/io.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/string.h>

#include "gemini_cpu9_transition_ledger_internal.h"

#define GEMINI_CPU9_LEDGER_CPU8_BASE 0x44410000ULL
#define GEMINI_CPU9_LEDGER_BASE \
	(GEMINI_CPU9_LEDGER_CPU8_BASE + GEMINI_TRANSITION_LEDGER_SLOT_SIZE)
#define GEMINI_CPU9_LEDGER_RESERVE_SIZE 0x000e0000ULL
#define GEMINI_CPU9_LEDGER_CPU8_STAGE 10U
#define GEMINI_CPU9_LEDGER_CPU8_TERMINAL 5U

static bool
cpu9_ledger_header_committed(const struct gemini_transition_ledger_ops *ops,
			     void *context)
{
	return ops->read(context, 0) ==
			GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
		ops->read(context, 1) ==
			GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES &&
		ops->read(context, 2) ==
			GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES;
}

int cpu9_ledger_validate_cpu8(const struct gemini_transition_ledger_ops *ops,
			      void *context, u64 cpu8_attempt_id)
{
	struct gemini_transition_ledger_record latest;
	u32 copy;

	if (!ops || !ops->read || !cpu8_attempt_id)
		return -EINVAL;
	if (!cpu9_ledger_header_committed(ops, context))
		return -ENODATA;
	if (!gemini_transition_ledger_read_latest(ops, context, &latest, &copy))
		return -EBADMSG;
	if (latest.attempt_id != cpu8_attempt_id)
		return -EACCES;
	if (latest.phase != GEMINI_TRANSITION_LEDGER_TERMINAL ||
	    latest.stage != GEMINI_CPU9_LEDGER_CPU8_STAGE ||
	    latest.terminal != GEMINI_CPU9_LEDGER_CPU8_TERMINAL)
		return -EPERM;
	return 0;
}

static int
cpu9_ledger_lane_empty(const struct gemini_transition_ledger_ops *ops,
		       void *context)
{
	u32 signature;
	u32 size;
	u32 start;
	bool empty;
	bool raw;

	if (!ops || !ops->read)
		return -EINVAL;
	signature = ops->read(context, 0);
	start = ops->read(context, 1);
	size = ops->read(context, 2);
	raw = signature == ~0U && start == ~0U && size == ~0U;
	empty = signature == GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
		!start && !size;
	if (raw || empty)
		return 0;
	if (signature == GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
	    start == GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES && start == size)
		return -EALREADY;
	return -EBADMSG;
}

int cpu9_ledger_open(struct gemini_cpu9_transition_ledger_owner *owner,
		     const struct gemini_transition_ledger_ops *ops,
		     void *context, u64 cpu9_attempt_id)
{
	int ret;

	if (!owner)
		return -EINVAL;
	ret = cpu9_ledger_lane_empty(ops, context);
	if (ret)
		return ret;
	return gemini_transition_ledger_owner_begin(&owner->ledger, ops, context,
						    cpu9_attempt_id);
}

int cpu9_ledger_owner_begin(struct gemini_cpu9_transition_ledger_owner *owner,
			    const struct gemini_transition_ledger_ops *cpu8_ops,
			    void *cpu8_context,
			    const struct gemini_transition_ledger_ops *cpu9_ops,
			    void *cpu9_context, u64 cpu8_attempt_id,
			    u64 cpu9_attempt_id)
{
	int ret;

	if (!owner)
		return -EINVAL;
	if (owner->attempted)
		return -EALREADY;
	owner->attempted = true;
	ret = cpu9_ledger_validate_cpu8(cpu8_ops, cpu8_context,
					cpu8_attempt_id);
	if (ret)
		return ret;
	return cpu9_ledger_open(owner, cpu9_ops, cpu9_context, cpu9_attempt_id);
}

int
cpu9_ledger_owner_checkpoint(struct gemini_cpu9_transition_ledger_owner *owner,
			     const struct gemini_transition_ledger_ops *ops, void *context,
	u64 cpu9_attempt_id, u32 phase, u32 stage, u32 terminal)
{
	if (!owner || !stage || stage > GEMINI_CPU9_LEDGER_MEMBERSHIP ||
	    terminal > GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF)
		return -EINVAL;
	return gemini_transition_ledger_owner_checkpoint(&owner->ledger, ops,
			context, cpu9_attempt_id, phase, stage, terminal);
}

static bool gemini_cpu9_transition_ledger_exact_dt(void)
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
	    resource.start != GEMINI_CPU9_LEDGER_CPU8_BASE ||
	    resource_size(&resource) != GEMINI_CPU9_LEDGER_RESERVE_SIZE ||
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

static u32 gemini_cpu9_transition_ledger_mmio_read(void *context,
						   unsigned int word)
{
	void __iomem *slot = context;

	return readl((u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_cpu9_transition_ledger_mmio_write(void *context,
						     unsigned int word,
						     u32 value)
{
	void __iomem *slot = context;

	writel(value, (u8 __iomem *)slot + word * sizeof(u32));
}

static void gemini_cpu9_transition_ledger_mmio_sync(void *context)
{
	(void)context;
	wmb(); /* Commit each record phase before the next one. */
}

static const struct gemini_transition_ledger_ops
gemini_cpu9_transition_ledger_mmio_ops = {
	.read = gemini_cpu9_transition_ledger_mmio_read,
	.write = gemini_cpu9_transition_ledger_mmio_write,
	.sync = gemini_cpu9_transition_ledger_mmio_sync,
};

static DEFINE_MUTEX(gemini_cpu9_transition_ledger_lock);
static struct gemini_cpu9_transition_ledger_owner
gemini_cpu9_transition_ledger_owner;
static void __iomem *gemini_cpu9_transition_ledger_slot;

int gemini_cpu9_ledger_begin(u64 cpu8_attempt_id, u64 cpu9_attempt_id)
{
	struct gemini_cpu9_transition_ledger_owner *owner;
	void __iomem *cpu8_slot;
	void __iomem *cpu9_slot;
	int ret;

	mutex_lock(&gemini_cpu9_transition_ledger_lock);
	owner = &gemini_cpu9_transition_ledger_owner;
	if (owner->attempted) {
		ret = -EALREADY;
		goto out_unlock;
	}
	owner->attempted = true;
	if (!cpu8_attempt_id || !cpu9_attempt_id) {
		ret = -EINVAL;
		goto out_unlock;
	}
	if (!gemini_cpu9_transition_ledger_exact_dt()) {
		ret = -ENODEV;
		goto out_unlock;
	}
	cpu8_slot = ioremap(GEMINI_CPU9_LEDGER_CPU8_BASE,
			    GEMINI_TRANSITION_LEDGER_SLOT_SIZE);
	if (!cpu8_slot) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	ret = cpu9_ledger_validate_cpu8(&gemini_cpu9_transition_ledger_mmio_ops,
					cpu8_slot, cpu8_attempt_id);
	iounmap(cpu8_slot);
	if (ret)
		goto out_unlock;

	cpu9_slot = ioremap_wc(GEMINI_CPU9_LEDGER_BASE,
			       GEMINI_TRANSITION_LEDGER_SLOT_SIZE);
	if (!cpu9_slot) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	ret = cpu9_ledger_open(owner, &gemini_cpu9_transition_ledger_mmio_ops,
			       cpu9_slot, cpu9_attempt_id);
	if (ret)
		iounmap(cpu9_slot);
	else
		gemini_cpu9_transition_ledger_slot = cpu9_slot;
out_unlock:
	mutex_unlock(&gemini_cpu9_transition_ledger_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_cpu9_ledger_begin);

int gemini_cpu9_ledger_checkpoint(u64 cpu9_attempt_id, u32 phase, u32 stage,
				  u32 terminal)
{
	struct gemini_cpu9_transition_ledger_owner *owner;
	int ret;

	mutex_lock(&gemini_cpu9_transition_ledger_lock);
	owner = &gemini_cpu9_transition_ledger_owner;
	if (!gemini_cpu9_transition_ledger_slot) {
		ret = owner->attempted ? -EALREADY : -ENODEV;
		goto out_unlock;
	}
	ret = cpu9_ledger_owner_checkpoint(owner,
					   &gemini_cpu9_transition_ledger_mmio_ops,
		gemini_cpu9_transition_ledger_slot, cpu9_attempt_id, phase, stage,
		terminal);
	if (ret || phase == GEMINI_TRANSITION_LEDGER_TERMINAL) {
		iounmap(gemini_cpu9_transition_ledger_slot);
		gemini_cpu9_transition_ledger_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_cpu9_transition_ledger_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_cpu9_ledger_checkpoint);
