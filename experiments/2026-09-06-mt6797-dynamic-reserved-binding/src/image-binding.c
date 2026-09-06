// SPDX-License-Identifier: GPL-2.0-only
#include "image-binding.h"
#ifdef MT6797_BINDING_HOST_TEST
#include "binding-test-compat.h"
#else
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/ioport.h>
#include <linux/limits.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/of_reserved_mem.h>
#include <linux/sizes.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/vmalloc.h>
#endif

struct mt6797_reserved_declaration {
	const u8 *reg;
	int reg_length;
	int reg_present;
	const u8 *size;
	int size_length;
	int size_present;
	const u8 *alignment_raw;
	int alignment_length;
	int alignment_present;
	const u8 *alloc_ranges;
	int alloc_ranges_length;
	int alloc_ranges_present;
	unsigned int address_cells;
	unsigned int size_cells;
	u64 declared_size;
	u64 alignment;
	int dynamic;
	int owned;
};

static int mt6797_reserved_declaration_capture(struct device_node *node,
					       int address_cells, int size_cells,
					       struct mt6797_reserved_declaration *declaration);

struct mt6797_reserved_snapshot {
	struct device *dev;
	struct device_node *consumer;
	struct device_node *target;
	const struct reserved_mem *rmem;
	unsigned int index;
	struct mt6797_reserved_declaration declaration;
	struct mt6797_image_reserved_info info;
};

struct mt6797_image_owner {
	/* Protects registry, generations and every binding's plan/state. */
	struct mutex mutex;
	u64 last_generation;
	u64 clients[MT6797_IMAGE_CLIENTS];
	struct mt6797_image_binding *image;
	struct mt6797_reserved_snapshot *reserved;
};

struct mt6797_image_binding {
	struct mt6797_image_owner *owner;
	struct mt6797_image_plan plan;
	u8 *data;
	size_t bytes;
	u64 generation;
	enum mt6797_image_binding_state state;
	int first_error;
};

static u32 mt6797_be32(const u8 *bytes)
{
	return ((u32)bytes[0] << 24) | ((u32)bytes[1] << 16) |
	       ((u32)bytes[2] << 8) | bytes[3];
}

static int mt6797_read_cells(const u8 *bytes, int length,
			     unsigned int cells, u64 *value)
{
	unsigned int i;

	if (!bytes || !value || cells < 1 || cells > 2 ||
	    length != (int)(cells * sizeof(u32)))
		return -EINVAL;
	*value = 0;
	for (i = 0; i < cells; i++)
		*value = (*value << 32) | mt6797_be32(bytes + i * sizeof(u32));
	return 0;
}

struct mt6797_property_view {
	const u8 *bytes;
	int length;
	int present;
};

static int mt6797_property_view_get(const struct device_node *node,
				    const char *name,
				    struct mt6797_property_view *view)
{
	const struct property *property;
	int length = -1;

	property = of_find_property(node, name, &length);
	if (property &&
	    (length < 0 || property->length < 0 || length != property->length ||
	     (property->length > 0 && !property->value)))
		return -EINVAL;
	*view = (struct mt6797_property_view){
		.bytes = property ? property->value : NULL,
		.length = property ? property->length : 0,
		.present = !!property,
	};
	return 0;
}

static int mt6797_property_equal(const struct mt6797_property_view *observed,
				 const u8 *saved, int saved_length,
				 int saved_present)
{
	if (observed->present != saved_present || observed->length != saved_length)
		return -ESTALE;
	if (observed->present && observed->length &&
	    memcmp(observed->bytes, saved, (size_t)observed->length))
		return -ESTALE;
	return 0;
}

static void mt6797_declaration_destroy(struct mt6797_reserved_declaration *declaration)
{
	if (!declaration->owned)
		return;
	kvfree(declaration->reg);
	kvfree(declaration->size);
	kvfree(declaration->alignment_raw);
	kvfree(declaration->alloc_ranges);
	*declaration = (struct mt6797_reserved_declaration){0};
}

static int mt6797_declaration_copy(struct mt6797_reserved_declaration *destination,
				   const struct mt6797_reserved_declaration *source)
{
	*destination = *source;
	destination->reg = NULL;
	destination->size = NULL;
	destination->alignment_raw = NULL;
	destination->alloc_ranges = NULL;
	destination->owned = 1;
	if (source->reg_present && source->reg_length) {
		destination->reg = kvmalloc((size_t)source->reg_length, GFP_KERNEL);
		if (!destination->reg)
			goto fail;
		memcpy((void *)destination->reg, source->reg,
		       (size_t)source->reg_length);
	}
	if (source->size_present && source->size_length) {
		destination->size = kvmalloc((size_t)source->size_length,
					     GFP_KERNEL);
		if (!destination->size)
			goto fail;
		memcpy((void *)destination->size, source->size,
		       (size_t)source->size_length);
	}
	if (source->alignment_present && source->alignment_length) {
		destination->alignment_raw =
			kvmalloc((size_t)source->alignment_length, GFP_KERNEL);
		if (!destination->alignment_raw)
			goto fail;
		memcpy((void *)destination->alignment_raw, source->alignment_raw,
		       (size_t)source->alignment_length);
	}
	if (source->alloc_ranges_present && source->alloc_ranges_length) {
		destination->alloc_ranges =
			kvmalloc((size_t)source->alloc_ranges_length, GFP_KERNEL);
		if (!destination->alloc_ranges)
			goto fail;
		memcpy((void *)destination->alloc_ranges, source->alloc_ranges,
		       (size_t)source->alloc_ranges_length);
	}
	return 0;
fail:
	mt6797_declaration_destroy(destination);
	return -ENOMEM;
}

static int mt6797_declaration_equal(const struct device_node *node,
				    const struct mt6797_reserved_declaration *saved)
{
	struct mt6797_reserved_declaration observed = {0};
	struct mt6797_property_view view;
	int address_cells = of_n_addr_cells((struct device_node *)node);
	int size_cells = of_n_size_cells((struct device_node *)node);
	int error;

	error = mt6797_reserved_declaration_capture((struct device_node *)node,
						    address_cells, size_cells,
						    &observed);
	if (error)
		return error;
	if (observed.dynamic != saved->dynamic ||
	    observed.address_cells != saved->address_cells ||
	    observed.size_cells != saved->size_cells ||
	    observed.declared_size != saved->declared_size ||
	    observed.alignment_present != saved->alignment_present ||
	    observed.alignment != saved->alignment ||
	    observed.reg_present != saved->reg_present ||
	    observed.alloc_ranges_present != saved->alloc_ranges_present)
		return -ESTALE;
	view = (struct mt6797_property_view){
		.bytes = observed.reg,
		.length = observed.reg_length,
		.present = observed.reg_present,
	};
	error = mt6797_property_equal(&view, saved->reg, saved->reg_length,
				      saved->reg_present);
	if (error)
		return error;
	view = (struct mt6797_property_view){
		.bytes = observed.size,
		.length = observed.size_length,
		.present = observed.size_present,
	};
	error = mt6797_property_equal(&view, saved->size, saved->size_length,
				      saved->size_present);
	if (error)
		return error;
	view = (struct mt6797_property_view){
		.bytes = observed.alignment_raw,
		.length = observed.alignment_length,
		.present = observed.alignment_present,
	};
	error = mt6797_property_equal(&view, saved->alignment_raw,
				      saved->alignment_length,
				      saved->alignment_present);
	if (error)
		return error;
	view = (struct mt6797_property_view){
		.bytes = observed.alloc_ranges,
		.length = observed.alloc_ranges_length,
		.present = observed.alloc_ranges_present,
	};
	return mt6797_property_equal(&view, saved->alloc_ranges,
				     saved->alloc_ranges_length,
				     saved->alloc_ranges_present);
}

/* Capture only the DT declaration. Property values are boot-lifetime borrowed
 * views; the initial validated declaration is copied before publication and
 * every revalidation compares current bytes and widths without allocation.
 * This records initialized Linux state, never proof that memblock reserved it.
 */
static int mt6797_reserved_declaration_capture(struct device_node *node,
					       int address_cells, int size_cells,
					       struct mt6797_reserved_declaration *declaration)
{
	struct mt6797_property_view reg, size, alignment, ranges;
	int count;
	int error;
	u64 value;

	*declaration = (struct mt6797_reserved_declaration){
		.address_cells = (unsigned int)address_cells,
		.size_cells = (unsigned int)size_cells,
	};
	if (address_cells < 1 || address_cells > 2 || size_cells < 1 ||
	    size_cells > 2)
		return -EINVAL;
	error = mt6797_property_view_get(node, "reg", &reg);
	if (error)
		return error;
	error = mt6797_property_view_get(node, "size", &size);
	if (error)
		return error;
	error = mt6797_property_view_get(node, "alignment", &alignment);
	if (error)
		return error;
	error = mt6797_property_view_get(node, "alloc-ranges", &ranges);
	if (error)
		return error;
	declaration->reg = reg.bytes;
	declaration->reg_length = reg.length;
	declaration->reg_present = reg.present;
	declaration->size = size.bytes;
	declaration->size_length = size.length;
	declaration->size_present = size.present;
	declaration->alignment_raw = alignment.bytes;
	declaration->alignment_length = alignment.length;
	declaration->alignment_present = alignment.present;
	declaration->alloc_ranges = ranges.bytes;
	declaration->alloc_ranges_length = ranges.length;
	declaration->alloc_ranges_present = ranges.present;
	if (declaration->reg_present) {
		count = of_property_count_u32_elems(node, "reg");
		if (count != address_cells + size_cells ||
		    reg.length != count * (int)sizeof(u32) ||
		    mt6797_read_cells(reg.bytes, address_cells * (int)sizeof(u32),
				      (unsigned int)address_cells, &value) ||
		    mt6797_read_cells(reg.bytes +
				      (size_t)address_cells * sizeof(u32),
				      size_cells * (int)sizeof(u32),
				      (unsigned int)size_cells,
				      &declaration->declared_size))
			return -EINVAL;
	} else {
		count = of_property_count_u32_elems(node, "reg");
		if (count >= 0 || address_cells != size_cells)
			return -EINVAL;
		declaration->dynamic = 1;
		if (!size.present ||
		    mt6797_read_cells(size.bytes, size.length,
				      (unsigned int)size_cells,
				      &declaration->declared_size) ||
		    !declaration->declared_size)
			return -EINVAL;
	}
	if (declaration->dynamic && declaration->alignment_present &&
	    (mt6797_read_cells(alignment.bytes, alignment.length,
				(unsigned int)size_cells, &declaration->alignment) ||
	     !declaration->alignment))
		return -EINVAL;
	if (declaration->dynamic && declaration->alloc_ranges_present) {
		unsigned int cells = (unsigned int)(address_cells + size_cells);
		unsigned int offset;
		u64 range_base, range_size;

		if (!ranges.length || ranges.length % (int)(cells * sizeof(u32)))
			return -EINVAL;
		for (offset = 0; offset < (unsigned int)ranges.length;
		     offset += cells * sizeof(u32)) {
			if (mt6797_read_cells(ranges.bytes + offset,
					      address_cells * (int)sizeof(u32),
					      (unsigned int)address_cells, &range_base) ||
			    mt6797_read_cells(ranges.bytes + offset +
					      (size_t)address_cells * sizeof(u32),
					      size_cells * (int)sizeof(u32),
					      (unsigned int)size_cells, &range_size) ||
			    !range_size || range_size - 1 > ~(u64)0 - range_base)
				return -ERANGE;
		}
	}
	return 0;
}

/* Caller holds stable OF configuration during this descriptive resolution.
 * The lookup is borrowed/name-matched, not an exclusive ownership operation.
 */
static int mt6797_reserved_resolve(struct mt6797_reserved_snapshot *snapshot,
				   struct mt6797_image_reserved_info *info)
{
	struct device_node *target, *parent = NULL, *root = NULL;
	struct resource boot = {0}, live = {0};
	struct mt6797_reserved_declaration declaration;
	struct reserved_mem *rmem;
	u64 base, bytes, end;
	int address_cells, size_cells, error = -EINVAL;

	*info = (struct mt6797_image_reserved_info){0};
	if (snapshot->dev->of_node != snapshot->consumer ||
	    !of_device_is_available(snapshot->consumer) ||
	    of_node_check_flag(snapshot->consumer, OF_DYNAMIC) ||
	    of_node_check_flag(snapshot->consumer, OF_DETACHED))
		return -ESTALE;
	target = of_parse_phandle(snapshot->consumer, "memory-region",
				  (int)snapshot->index);
	if (!target)
		return -ENODEV;
	if (snapshot->target && snapshot->target != target) {
		error = -ESTALE;
		goto out;
	}
	parent = of_get_parent(target);
	root = of_find_node_by_path("/reserved-memory");
	if (!root || parent != root || !of_device_is_available(root) ||
	    !of_device_is_available(target) ||
	    of_node_check_flag(root, OF_DYNAMIC) ||
	    of_node_check_flag(root, OF_DETACHED) ||
	    of_node_check_flag(target, OF_DYNAMIC) ||
	    of_node_check_flag(target, OF_DETACHED))
		goto out;
	if (!of_property_read_bool(target, "no-map") ||
	    of_property_read_bool(target, "reusable") ||
	    of_property_read_bool(target, "no-map-fixup") ||
	    of_device_is_compatible(target, "shared-dma-pool") ||
	    of_device_is_compatible(target, "restricted-dma-pool")) {
		error = -EOPNOTSUPP;
		goto out;
	}
	address_cells = of_n_addr_cells(target);
	size_cells = of_n_size_cells(target);
	error = mt6797_reserved_declaration_capture(target, address_cells,
						    size_cells, &declaration);
	if (error)
		goto out;
	if (snapshot->target) {
		error = mt6797_declaration_equal(target, &snapshot->declaration);
		if (error)
			goto out;
	}
	rmem = of_reserved_mem_lookup(target);
	if (!rmem) {
		error = -ENODEV;
		goto out;
	}
	/* Unknown region-specific operations need their actual owner adapter.
	 * Never call device_init merely to obtain a descriptor: it can change DMA.
	 */
	if (rmem->ops || rmem->priv) {
		error = -EOPNOTSUPP;
		goto out;
	}
	if (snapshot->rmem && snapshot->rmem != rmem) {
		error = -ESTALE;
		goto out;
	}
	base = rmem->base;
	bytes = rmem->size;
	if (declaration.dynamic && bytes != declaration.declared_size) {
		error = -ESTALE;
		goto out;
	}
	if (declaration.dynamic && !base) {
		error = -ERANGE;
		goto out;
	}
	if (declaration.dynamic && declaration.alignment_present &&
	    base % declaration.alignment) {
		error = -ERANGE;
		goto out;
	}
	if (bytes < SZ_1M || (base & (SZ_1M - 1)) ||
	    base > 0xffffffffULL || SZ_1M - 1 > 0xffffffffULL - base ||
	    bytes - 1 > ~(u64)0 - base) {
		error = -ERANGE;
		goto out;
	}
	end = base + bytes - 1;
	error = of_reserved_mem_region_to_resource(snapshot->consumer,
						   snapshot->index, &boot);
	if (error)
		goto out;
	if (resource_type(&boot) != IORESOURCE_MEM ||
	    boot.start != base || boot.end != end) {
		error = -ESTALE;
		goto out;
	}
	if (!declaration.dynamic) {
		error = of_address_to_resource(target, 0, &live);
		if (error)
			goto out;
		if (resource_type(&live) != IORESOURCE_MEM ||
		    live.start != base || live.end != end) {
			error = -ESTALE;
			goto out;
		}
	}
	if (declaration.dynamic && declaration.alloc_ranges_present) {
		unsigned int cells = declaration.address_cells + declaration.size_cells;
		unsigned int offset;
		int contained = 0;

		for (offset = 0; offset < (unsigned int)declaration.alloc_ranges_length;
		     offset += cells * sizeof(u32)) {
			u64 range_base, range_size, range_end;

			if (mt6797_read_cells(declaration.alloc_ranges + offset,
					      (int)(declaration.address_cells * sizeof(u32)),
					      declaration.address_cells, &range_base) ||
			    mt6797_read_cells(declaration.alloc_ranges + offset +
					      (size_t)declaration.address_cells * sizeof(u32),
					      (int)(declaration.size_cells * sizeof(u32)),
					      declaration.size_cells, &range_size))
				continue;
			range_end = range_base + range_size - 1;
			if (base >= range_base && end <= range_end)
				contained = 1;
		}
		if (!contained) {
			error = -ERANGE;
			goto out;
		}
	}
	*info = (struct mt6797_image_reserved_info){
		.start = base,
		.end = end,
		.wlan_start = base,
		.wlan_end = base + SZ_512K - 1,
		.wmt_start = base + SZ_512K,
		.wmt_end = base + SZ_1M - 1,
	};
	if (!snapshot->target) {
		error = mt6797_declaration_copy(&snapshot->declaration,
						&declaration);
		if (error)
			goto out;
		snapshot->target = of_node_get(target);
		snapshot->rmem = rmem;
	}
	error = 0;
out:
	of_node_put(root);
	of_node_put(parent);
	of_node_put(target);
	return error;
}

static void mt6797_reserved_put(struct mt6797_reserved_snapshot *snapshot)
{
	if (!snapshot)
		return;
	mt6797_declaration_destroy(&snapshot->declaration);
	of_node_put(snapshot->target);
	of_node_put(snapshot->consumer);
	put_device(snapshot->dev);
	kfree(snapshot);
}

static int mt6797_reserved_revalidate(struct mt6797_reserved_snapshot *snapshot,
				      struct mt6797_image_reserved_info *info)
{
	int error;

	error = mt6797_reserved_resolve(snapshot, info);
	if (error)
		return error;
	if (info->start != snapshot->info.start || info->end != snapshot->info.end)
		return -ESTALE;
	info->generation = snapshot->info.generation;
	return 0;
}

static int mt6797_owner_has_clients(struct mt6797_image_owner *owner)
{
	unsigned int i;

	for (i = 0; i < MT6797_IMAGE_CLIENTS; i++)
		if (owner->clients[i])
			return 1;
	return 0;
}

static int mt6797_binding_match(struct mt6797_image_binding *binding,
				u64 generation)
{
	if (!generation || binding->generation != generation ||
	    binding->owner->image != binding)
		return -ESTALE;
	return 0;
}

static int mt6797_binding_validate(struct mt6797_image_binding *binding)
{
	struct mt6797_plan_section section;
	struct mt6797_image_reserved_info reserved;
	unsigned int i;
	int error;

	if (binding->state == MT6797_IMAGE_FAULT_HELD)
		return binding->first_error;
	if (binding->state != MT6797_IMAGE_PASSIVE || !binding->plan.valid ||
	    binding->plan.image.data != binding->data ||
	    binding->plan.image.size != binding->bytes ||
	    binding->plan.sections != binding->plan.image.count)
		return -ESTALE;
	if (binding->owner->reserved) {
		error = mt6797_reserved_revalidate(binding->owner->reserved, &reserved);
		if (error)
			return error;
	}
	/* Use the complete immutable plan, not get_ordinary() as an escape
	 * hatch. These are format bounds, not a claim about an actual
	 * reservation.
	 */
	for (i = 0; i < binding->plan.sections; i++) {
		if (mt6797_image_plan_describe(&binding->plan, i, &section))
			return -EINVAL;
		if (section.emi &&
		    (section.emi_offset >= 0x80000U ||
		     section.length > 0x80000U - section.emi_offset))
			return -ERANGE;
	}
	return 0;
}

int mt6797_image_owner_alloc(struct mt6797_image_owner **out)
{
	struct mt6797_image_owner *owner;

	if (!out)
		return -EINVAL;
	*out = NULL;
	owner = kzalloc_obj(*owner, GFP_KERNEL);
	if (!owner)
		return -ENOMEM;
	mutex_init(&owner->mutex);
	*out = owner;
	return 0;
}

int mt6797_image_owner_free(struct mt6797_image_owner *owner)
{
	struct mt6797_reserved_snapshot *reserved;

	if (!owner)
		return -EINVAL;
	mutex_lock(&owner->mutex);
	if (owner->image || mt6797_owner_has_clients(owner)) {
		mutex_unlock(&owner->mutex);
		return -EBUSY;
	}
	reserved = owner->reserved;
	owner->reserved = NULL;
	mutex_unlock(&owner->mutex);
	mt6797_reserved_put(reserved);
	mutex_destroy(&owner->mutex);
	kfree(owner);
	return 0;
}

int mt6797_image_owner_bind_reserved(struct mt6797_image_owner *owner,
				     struct device *dev, unsigned int index,
				     u64 *generation)
{
	struct mt6797_reserved_snapshot *snapshot = NULL;
	int error;

	if (!generation)
		return -EINVAL;
	*generation = 0;
	if (!owner || !dev || !dev->of_node || index > INT_MAX)
		return -EINVAL;
	mutex_lock(&owner->mutex);
	if (owner->image || owner->reserved || mt6797_owner_has_clients(owner)) {
		error = -EBUSY;
		goto out;
	}
	if (owner->last_generation == ~(u64)0) {
		error = -EOVERFLOW;
		goto out;
	}
	snapshot = kzalloc_obj(*snapshot, GFP_KERNEL);
	if (!snapshot) {
		error = -ENOMEM;
		goto out;
	}
	snapshot->dev = get_device(dev);
	snapshot->consumer = of_node_get(dev->of_node);
	snapshot->index = index;
	if (!snapshot->dev || !snapshot->consumer) {
		error = -ENODEV;
		goto out;
	}
	error = mt6797_reserved_resolve(snapshot, &snapshot->info);
	if (error)
		goto out;
	snapshot->info.generation = ++owner->last_generation;
	*generation = snapshot->info.generation;
	owner->reserved = snapshot;
	snapshot = NULL;
out:
	mutex_unlock(&owner->mutex);
	mt6797_reserved_put(snapshot);
	return error;
}

int mt6797_image_owner_reserved_info(struct mt6797_image_owner *owner,
				     u64 generation,
				     struct mt6797_image_reserved_info *info)
{
	struct mt6797_image_reserved_info pending;
	int error;

	if (!info)
		return -EINVAL;
	*info = (struct mt6797_image_reserved_info){0};
	if (!owner)
		return -EINVAL;
	mutex_lock(&owner->mutex);
	if (!owner->reserved || !generation ||
	    owner->reserved->info.generation != generation) {
		error = -ESTALE;
		goto out;
	}
	error = mt6797_reserved_revalidate(owner->reserved, &pending);
	if (!error)
		*info = pending;
out:
	mutex_unlock(&owner->mutex);
	return error;
}

int mt6797_image_owner_unbind_reserved(struct mt6797_image_owner *owner,
				       u64 generation)
{
	struct mt6797_reserved_snapshot *snapshot = NULL;
	int error = 0;

	if (!owner)
		return -EINVAL;
	mutex_lock(&owner->mutex);
	if (!owner->reserved || !generation ||
	    owner->reserved->info.generation != generation) {
		error = -ESTALE;
	} else if (owner->image || mt6797_owner_has_clients(owner)) {
		error = -EBUSY;
	} else {
		snapshot = owner->reserved;
		owner->reserved = NULL;
	}
	mutex_unlock(&owner->mutex);
	mt6797_reserved_put(snapshot);
	return error;
}

int mt6797_image_owner_claim(struct mt6797_image_owner *owner,
			     enum mt6797_image_client client, u64 *generation)
{
	int error = 0;

	if (!generation)
		return -EINVAL;
	*generation = 0;
	if (!owner || (unsigned int)client >= MT6797_IMAGE_CLIENTS)
		return -EINVAL;
	mutex_lock(&owner->mutex);
	if (owner->image || owner->clients[client]) {
		error = -EBUSY;
	} else if (owner->last_generation == ~(u64)0) {
		error = -EOVERFLOW;
	} else {
		owner->clients[client] = ++owner->last_generation;
		*generation = owner->clients[client];
	}
	mutex_unlock(&owner->mutex);
	return error;
}

int mt6797_image_owner_unclaim(struct mt6797_image_owner *owner,
			       enum mt6797_image_client client, u64 generation)
{
	int error = 0;

	if (!owner || (unsigned int)client >= MT6797_IMAGE_CLIENTS)
		return -EINVAL;
	mutex_lock(&owner->mutex);
	if (!generation || owner->clients[client] != generation)
		error = -ESTALE;
	else
		owner->clients[client] = 0;
	mutex_unlock(&owner->mutex);
	return error;
}

int mt6797_image_binding_create(struct mt6797_image_owner *owner,
				const u8 *data, size_t bytes,
				struct mt6797_image_binding **out,
				u64 *generation)
{
	struct mt6797_image_binding *binding;
	int error;

	if (out)
		*out = NULL;
	if (generation)
		*generation = 0;
	if (!owner || !out || !generation || !data || bytes < 24 ||
	    bytes > MTKE_MAX_BYTES)
		return -EINVAL;
	mutex_lock(&owner->mutex);
	if (owner->image || mt6797_owner_has_clients(owner)) {
		error = -EBUSY;
		goto out_unlock;
	}
	if (owner->last_generation == ~(u64)0) {
		error = -EOVERFLOW;
		goto out_unlock;
	}
	binding = kzalloc_obj(*binding, GFP_KERNEL);
	if (!binding) {
		error = -ENOMEM;
		goto out_unlock;
	}
	binding->data = kvmalloc(bytes, GFP_KERNEL);
	if (!binding->data) {
		error = -ENOMEM;
		goto out_binding;
	}
	memcpy(binding->data, data, bytes);
	binding->bytes = bytes;
	binding->owner = owner;
	binding->state = MT6797_IMAGE_PASSIVE;
	error = mt6797_image_plan_prepare(&binding->plan, binding->data, bytes);
	if (error) {
		error = error == -2 ? -EOPNOTSUPP : -EINVAL;
		goto out_data;
	}
	error = mt6797_binding_validate(binding);
	if (error)
		goto out_data;
	/* Publication and generation allocation happen only after all sections.
	 * Generation history belongs to the owner, not this allocation.
	 */
	binding->generation = ++owner->last_generation;
	owner->image = binding;
	*generation = binding->generation;
	*out = binding;
	mutex_unlock(&owner->mutex);
	return 0;

out_data:
	mt6797_image_plan_invalidate(&binding->plan);
	kvfree(binding->data);
out_binding:
	kfree(binding);
out_unlock:
	mutex_unlock(&owner->mutex);
	return error;
}

int mt6797_image_binding_info(struct mt6797_image_binding *binding,
			      u64 generation,
			      struct mt6797_image_binding_info *info)
{
	int error;

	if (!info)
		return -EINVAL;
	*info = (struct mt6797_image_binding_info){0};
	if (!binding)
		return -EINVAL;
	mutex_lock(&binding->owner->mutex);
	error = mt6797_binding_match(binding, generation);
	if (!error)
		*info = (struct mt6797_image_binding_info){
		    .generation = binding->generation,
		    .state = binding->state,
		    .first_error = binding->first_error,
		    .sections = binding->plan.sections,
		    .ordinary_sections = binding->plan.ordinary_sections,
		    .emi_sections = binding->plan.emi_sections,
		    .image_bytes = binding->bytes,
		};
	mutex_unlock(&binding->owner->mutex);
	return error;
}

int mt6797_image_binding_describe(struct mt6797_image_binding *binding,
				  u64 generation, unsigned int index,
				  struct mt6797_plan_section *section)
{
	int error;

	if (!section)
		return -EINVAL;
	*section = (struct mt6797_plan_section){0};
	if (!binding)
		return -EINVAL;
	mutex_lock(&binding->owner->mutex);
	error = mt6797_binding_match(binding, generation);
	if (!error)
		error = mt6797_binding_validate(binding);
	if (!error &&
	    mt6797_image_plan_describe(&binding->plan, index, section))
		error = -EINVAL;
	mutex_unlock(&binding->owner->mutex);
	return error;
}

int mt6797_image_binding_prevalidate(struct mt6797_image_binding *binding,
				     u64 generation)
{
	int error;

	if (!binding)
		return -EINVAL;
	mutex_lock(&binding->owner->mutex);
	error = mt6797_binding_match(binding, generation);
	if (!error)
		error = mt6797_binding_validate(binding);
	mutex_unlock(&binding->owner->mutex);
	return error;
}

int mt6797_image_binding_begin(struct mt6797_image_binding *binding,
			       u64 generation)
{
	int error = mt6797_image_binding_prevalidate(binding, generation);

	/* No powered lifetime, reservation, MPU/remap or IRQ/reset owner
	 * exists. Ordinary-only images must not bypass this real-provider
	 * requirement.
	 */
	return error ? error : -EOPNOTSUPP;
}

int mt6797_image_binding_invalidate(struct mt6797_image_binding *binding,
				    u64 generation)
{
	int error;

	if (!binding)
		return -EINVAL;
	mutex_lock(&binding->owner->mutex);
	error = mt6797_binding_match(binding, generation);
	if (!error && binding->state == MT6797_IMAGE_FAULT_HELD)
		error = binding->first_error;
	if (!error) {
		binding->state = MT6797_IMAGE_INVALID;
		mt6797_image_plan_invalidate(&binding->plan);
	}
	mutex_unlock(&binding->owner->mutex);
	return error;
}

int mt6797_image_binding_hold_fault(struct mt6797_image_binding *binding,
				    u64 generation, int error)
{
	int result;

	if (!binding || error >= 0)
		return -EINVAL;
	mutex_lock(&binding->owner->mutex);
	result = mt6797_binding_match(binding, generation);
	if (!result) {
		if (!binding->first_error)
			binding->first_error = error;
		binding->state = MT6797_IMAGE_FAULT_HELD;
		result = binding->first_error;
	}
	mutex_unlock(&binding->owner->mutex);
	return result;
}

int mt6797_image_binding_release(struct mt6797_image_binding *binding,
				 u64 generation)
{
	struct mt6797_image_owner *owner;
	int error;

	if (!binding)
		return -EINVAL;
	owner = binding->owner;
	mutex_lock(&owner->mutex);
	error = mt6797_binding_match(binding, generation);
	if (!error && binding->state == MT6797_IMAGE_FAULT_HELD)
		error = -EBUSY;
	if (!error) {
		mt6797_image_plan_invalidate(&binding->plan);
		owner->image = NULL;
		kvfree(binding->data);
		kfree(binding);
	}
	mutex_unlock(&owner->mutex);
	return error;
}

#ifdef MT6797_BINDING_HOST_TEST
/* Test-only boundary setup, never part of the emitted kernel API. */
int mt6797_binding_test_generation(struct mt6797_image_owner *owner, u64 value)
{
	int error = 0;

	mutex_lock(&owner->mutex);
	if (owner->image || owner->reserved || mt6797_owner_has_clients(owner) ||
	    value < owner->last_generation)
		error = -EBUSY;
	else
		owner->last_generation = value;
	mutex_unlock(&owner->mutex);
	return error;
}
#endif
