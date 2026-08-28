// SPDX-License-Identifier: GPL-2.0-only
/* Candidate-only immutable Gemini CPU8 admission trace records. */

#include <linux/gemini_admission_trace.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/string.h>

#include "gemini_admission_trace_internal.h"

#define GEMINI_ADMISSION_TRACE_RESERVE_BASE 0x44410000ULL
#define GEMINI_ADMISSION_TRACE_RESERVE_SIZE 0x000e0000ULL
#define GEMINI_ADMISSION_TRACE_BASE 0x44411000ULL
#define GEMINI_ADMISSION_TRACE_BYTES \
	(GEMINI_ADMISSION_TRACE_SLOT_COUNT * GEMINI_ADMISSION_TRACE_SLOT_SIZE)
#define GEMINI_ADMISSION_TRACE_ENTRY_SLOT 0U
#define GEMINI_ADMISSION_TRACE_TERMINAL_SLOT 1U

static const char gemini_admission_trace_entry_record[] =
	"====0.000000-D\n"
	"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
	"kind=entry slot=2\n";

static const char * const gemini_admission_trace_terminal_records[] = {
	[GEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER] =
		"====0.000000-D\n"
		"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
		"kind=zero-source-register slot=3\n",
	[GEMINI_ADMISSION_TRACE_ZERO_DERIVE] =
		"====0.000000-D\n"
		"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
		"kind=zero-derive slot=3\n",
	[GEMINI_ADMISSION_TRACE_ZERO_PUBLISH] =
		"====0.000000-D\n"
		"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
		"kind=zero-publish slot=3\n",
};

static bool
gemini_admission_trace_ops_valid(const struct gemini_admission_trace_ops *ops)
{
	return ops && ops->read_word && ops->write_word && ops->read_byte &&
		ops->write_byte && ops->sync;
}

static int
gemini_admission_trace_fault(struct gemini_admission_trace_owner *owner)
{
	owner->failed = true;
	return -EIO;
}

static bool
gemini_admission_trace_slot_empty(const struct gemini_admission_trace_ops *ops,
				  void *context, unsigned int slot)
{
	return ops->read_word(context, slot, 0) ==
			GEMINI_ADMISSION_TRACE_PSTORE_SIGNATURE &&
		ops->read_word(context, slot, 1) == 0 &&
		ops->read_word(context, slot, 2) == 0;
}

static bool
gemini_admission_trace_slot_exact(const struct gemini_admission_trace_ops *ops,
				  void *context, unsigned int slot,
				  const char *record)
{
	size_t length = strlen(record);
	size_t index;

	if (ops->read_word(context, slot, 0) !=
			GEMINI_ADMISSION_TRACE_PSTORE_SIGNATURE ||
	    ops->read_word(context, slot, 1) != length ||
	    ops->read_word(context, slot, 2) != length)
		return false;
	for (index = 0; index < length; index++)
		if (ops->read_byte(context, slot,
				   GEMINI_ADMISSION_TRACE_HEADER_SIZE + index) !=
		    record[index])
			return false;
	return true;
}

static int
gemini_admission_trace_write(struct gemini_admission_trace_owner *owner,
			     const struct gemini_admission_trace_ops *ops,
			     void *context, unsigned int slot,
			     const char *record)
{
	size_t length = strlen(record);
	size_t index;

	if (length > GEMINI_ADMISSION_TRACE_SLOT_SIZE -
			     GEMINI_ADMISSION_TRACE_HEADER_SIZE ||
	    !gemini_admission_trace_slot_empty(ops, context, slot))
		return gemini_admission_trace_fault(owner);
	for (index = 0; index < length; index++)
		ops->write_byte(context, slot,
				GEMINI_ADMISSION_TRACE_HEADER_SIZE + index,
				record[index]);
	ops->sync(context);
	ops->write_word(context, slot, 1, length);
	ops->sync(context);
	ops->write_word(context, slot, 2, length);
	ops->sync(context);
	if (!gemini_admission_trace_slot_exact(ops, context, slot, record))
		return gemini_admission_trace_fault(owner);
	owner->commits++;
	return 0;
}

int
gemini_admission_trace_owner_entry(struct gemini_admission_trace_owner *owner,
				   const struct gemini_admission_trace_ops *ops,
				   void *context)
{
	const char *entry = gemini_admission_trace_entry_record;
	const unsigned int entry_slot = GEMINI_ADMISSION_TRACE_ENTRY_SLOT;
	const unsigned int terminal_slot = GEMINI_ADMISSION_TRACE_TERMINAL_SLOT;
	int ret;

	if (!owner || !gemini_admission_trace_ops_valid(ops))
		return -EINVAL;
	if (owner->failed || owner->terminal_committed)
		return -EALREADY;
	if (!gemini_admission_trace_slot_empty(ops, context, terminal_slot))
		return gemini_admission_trace_fault(owner);
	if (gemini_admission_trace_slot_exact(ops, context, entry_slot, entry)) {
		owner->entry_committed = true;
		return 0;
	}
	if (owner->entry_committed)
		return gemini_admission_trace_fault(owner);
	ret = gemini_admission_trace_write(owner, ops, context, entry_slot,
					   entry);
	if (!ret)
		owner->entry_committed = true;
	return ret;
}

int
gemini_admission_trace_owner_zero_request(struct gemini_admission_trace_owner *owner,
					  const struct gemini_admission_trace_ops *ops,
					  void *context,
					  enum gemini_admission_trace_zero_result result)
{
	const char *entry = gemini_admission_trace_entry_record;
	const unsigned int entry_slot = GEMINI_ADMISSION_TRACE_ENTRY_SLOT;
	const unsigned int terminal_slot = GEMINI_ADMISSION_TRACE_TERMINAL_SLOT;
	const char *record;
	int ret;

	if (!owner || !gemini_admission_trace_ops_valid(ops) ||
	    result < GEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER ||
	    result > GEMINI_ADMISSION_TRACE_ZERO_PUBLISH)
		return -EINVAL;
	if (owner->failed || owner->terminal_committed ||
	    !owner->entry_committed)
		return -EALREADY;
	record = gemini_admission_trace_terminal_records[result];
	if (!record ||
	    !gemini_admission_trace_slot_exact(ops, context, entry_slot, entry) ||
	    !gemini_admission_trace_slot_empty(ops, context, terminal_slot))
		return gemini_admission_trace_fault(owner);
	ret = gemini_admission_trace_write(owner, ops, context, terminal_slot,
					   record);
	if (!ret)
		owner->terminal_committed = true;
	return ret;
}

static bool gemini_admission_trace_exact_dt(void)
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
	    resource.start != GEMINI_ADMISSION_TRACE_RESERVE_BASE ||
	    resource_size(&resource) != GEMINI_ADMISSION_TRACE_RESERVE_SIZE ||
	    !of_property_read_bool(node, "no-map"))
		goto out;
	if (of_property_read_u32(node, "record-size", &value) ||
	    value != GEMINI_ADMISSION_TRACE_SLOT_SIZE ||
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

static u32
gemini_admission_trace_mmio_read_word(void *context, unsigned int slot,
				      unsigned int word)
{
	void __iomem *base = context;

	return readl((u8 __iomem *)base + slot * GEMINI_ADMISSION_TRACE_SLOT_SIZE +
		     word * sizeof(u32));
}

static void
gemini_admission_trace_mmio_write_word(void *context, unsigned int slot,
				       unsigned int word, u32 value)
{
	void __iomem *base = context;

	writel(value, (u8 __iomem *)base + slot * GEMINI_ADMISSION_TRACE_SLOT_SIZE +
		       word * sizeof(u32));
}

static u8
gemini_admission_trace_mmio_read_byte(void *context, unsigned int slot,
				      unsigned int offset)
{
	void __iomem *base = context;

	return readb((u8 __iomem *)base + slot * GEMINI_ADMISSION_TRACE_SLOT_SIZE +
		     offset);
}

static void
gemini_admission_trace_mmio_write_byte(void *context, unsigned int slot,
				       unsigned int offset, u8 value)
{
	void __iomem *base = context;

	writeb(value, (u8 __iomem *)base + slot * GEMINI_ADMISSION_TRACE_SLOT_SIZE +
		       offset);
}

static void gemini_admission_trace_mmio_sync(void *context)
{
	(void)context;
	mb(); /* Commit each record phase before the next one. */
}

static const struct gemini_admission_trace_ops gemini_admission_trace_mmio_ops = {
	.read_word = gemini_admission_trace_mmio_read_word,
	.write_word = gemini_admission_trace_mmio_write_word,
	.read_byte = gemini_admission_trace_mmio_read_byte,
	.write_byte = gemini_admission_trace_mmio_write_byte,
	.sync = gemini_admission_trace_mmio_sync,
};

static DEFINE_MUTEX(gemini_admission_trace_lock);
static struct gemini_admission_trace_owner gemini_admission_trace_owner;

static int
gemini_admission_trace_commit(enum gemini_admission_trace_zero_result result,
			      bool entry)
{
	struct gemini_admission_trace_owner *owner = &gemini_admission_trace_owner;
	const struct gemini_admission_trace_ops *ops = &gemini_admission_trace_mmio_ops;
	void __iomem *slots;
	int ret;

	mutex_lock(&gemini_admission_trace_lock);
	if (!gemini_admission_trace_exact_dt()) {
		ret = -ENODEV;
		goto out_unlock;
	}
	slots = ioremap_wc(GEMINI_ADMISSION_TRACE_BASE,
			   GEMINI_ADMISSION_TRACE_BYTES);
	if (!slots) {
		ret = -ENOMEM;
		goto out_unlock;
	}
	if (entry)
		ret = gemini_admission_trace_owner_entry(owner, ops, slots);
	else
		ret = gemini_admission_trace_owner_zero_request(owner, ops, slots, result);
	iounmap(slots);
out_unlock:
	mutex_unlock(&gemini_admission_trace_lock);
	return ret;
}

int gemini_admission_trace_entry(void)
{
	return gemini_admission_trace_commit(0, true);
}
EXPORT_SYMBOL_GPL(gemini_admission_trace_entry);

int
gemini_admission_trace_zero_request(enum gemini_admission_trace_zero_result result)
{
	return gemini_admission_trace_commit(result, false);
}
EXPORT_SYMBOL_GPL(gemini_admission_trace_zero_request);

MODULE_DESCRIPTION("Gemini immutable CPU8 admission trace records");
MODULE_LICENSE("GPL");
