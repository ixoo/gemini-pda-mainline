// SPDX-License-Identifier: GPL-2.0-only
/* Re-run the pinned original lifetime/allocator/concurrency fixtures unchanged. */
#define main previous_binding_tests
#include "test-binding.c"
#undef main

static struct device_node *root_node;
static int region_error;
static unsigned long region_flags = IORESOURCE_MEM;
static unsigned int device_gets, device_puts, node_gets, node_puts;
static unsigned int resource_checks;

struct device *get_device(struct device *dev)
{
	if (dev) {
		assert(dev->refs > 0);
		dev->refs++;
		device_gets++;
	}
	return dev;
}

void put_device(struct device *dev)
{
	if (dev) {
		assert(dev->refs > 1);
		dev->refs--;
		device_puts++;
	}
}

struct device_node *of_node_get(struct device_node *node)
{
	if (node) {
		assert(node->refs > 0);
		node->refs++;
		node_gets++;
	}
	return node;
}

void of_node_put(struct device_node *node)
{
	if (node) {
		assert(node->refs > 1);
		node->refs--;
		node_puts++;
	}
}

struct device_node *of_get_parent(const struct device_node *node)
{
	return of_node_get(node->parent);
}

struct device_node *of_find_node_by_path(const char *path)
{
	assert(!strcmp(path, "/reserved-memory"));
	return of_node_get(root_node);
}

struct device_node *of_parse_phandle(const struct device_node *node,
				    const char *name, int index)
{
	assert(!strcmp(name, "memory-region"));
	if (index < 0 || (unsigned int)index != node->selected_index)
		return NULL;
	return of_node_get(node->phandle);
}

int of_device_is_available(const struct device_node *node)
{
	return node && node->available;
}

int of_node_check_flag(const struct device_node *node, unsigned long flag)
{
	assert(flag == OF_DYNAMIC || flag == OF_DETACHED);
	return flag == OF_DYNAMIC ? node->dynamic : node->detached;
}

int of_property_read_bool(const struct device_node *node, const char *name)
{
	if (!strcmp(name, "no-map"))
		return node->no_map;
	if (!strcmp(name, "reusable"))
		return node->reusable;
	assert(!strcmp(name, "no-map-fixup"));
	return node->fixup;
}

int of_device_is_compatible(const struct device_node *node, const char *name)
{
	if (!strcmp(name, "shared-dma-pool"))
		return node->pool == 1;
	assert(!strcmp(name, "restricted-dma-pool"));
	return node->pool == 2;
}

int of_n_addr_cells(struct device_node *node)
{
	return node->address_cells;
}

int of_n_size_cells(struct device_node *node)
{
	return node->size_cells;
}

int of_property_count_u32_elems(const struct device_node *node, const char *name)
{
	assert(!strcmp(name, "reg"));
	return node->reg_cells;
}

struct reserved_mem *of_reserved_mem_lookup(struct device_node *node)
{
	/* Deliberately borrowed, even for a wrongly parented node. The C caller
	 * must reject that identity rather than trusting the lookup as authority.
	 */
	return node->rmem;
}

int of_reserved_mem_region_to_resource(const struct device_node *node,
				       unsigned int index, struct resource *resource)
{
	struct device_node *target;
	struct reserved_mem *rmem;
	int error = -EINVAL;

	if (region_error)
		return region_error;
	target = of_parse_phandle(node, "memory-region", (int)index);
	if (!target || !of_device_is_available(target)) {
		error = -ENODEV;
		goto out;
	}
	rmem = of_reserved_mem_lookup(target);
	if (!rmem)
		goto out;
	*resource = (struct resource){rmem->base, rmem->base + rmem->size - 1,
				     region_flags};
	error = 0;
out:
	of_node_put(target);
	return error;
}

int of_address_to_resource(struct device_node *node, int index,
			   struct resource *resource)
{
	assert(!index);
	if (node->address_error)
		return node->address_error;
	*resource = node->reg;
	return 0;
}

struct fixture {
	struct device_node root, target, consumer, foreign;
	struct reserved_mem rmem;
	struct device dev;
};

static void fixture_init(struct fixture *fixture, u64 base, u64 bytes)
{
	*fixture = (struct fixture){0};
	fixture->root.refs = fixture->foreign.refs = 1;
	fixture->target.refs = fixture->consumer.refs = 1;
	fixture->dev.refs = 1;
	fixture->root.available = fixture->target.available = 1;
	fixture->consumer.available = 1;
	fixture->target.no_map = 1;
	fixture->target.address_cells = fixture->target.size_cells = 2;
	fixture->target.reg_cells = 4;
	fixture->rmem.base = base;
	fixture->rmem.size = bytes;
	fixture->target.rmem = &fixture->rmem;
	fixture->target.parent = &fixture->root;
	fixture->target.reg = (struct resource){base, base + bytes - 1, IORESOURCE_MEM};
	fixture->consumer.phandle = &fixture->target;
	fixture->dev.of_node = &fixture->consumer;
	root_node = &fixture->root;
	region_error = 0;
	region_flags = IORESOURCE_MEM;
}

static void fixture_balanced(struct fixture *fixture)
{
	assert(fixture->root.refs == 1 && fixture->target.refs == 1);
	assert(fixture->consumer.refs == 1 && fixture->foreign.refs == 1);
	assert(fixture->dev.refs == 1);
	assert(device_gets == device_puts && node_gets == node_puts);
	resource_checks++;
}

static void valid_intervals(void)
{
	const u64 bases[] = {0x40000000ULL, 0xfff00000ULL, 0xfff00000ULL, 0};
	const u64 sizes[] = {0x200000ULL, 0x100000ULL, 0x200000ULL, 0x100000ULL};

	for (unsigned int i = 0; i < 4; i++) {
		struct fixture fixture;
		struct mt6797_image_owner *owner;
		struct mt6797_image_binding *binding;
		struct mt6797_image_reserved_info info;
		u64 generation, image_generation;
		size_t bytes;
		u8 *data;

		fixture_init(&fixture, bases[i], sizes[i]);
		fixture.consumer.selected_index = 3; /* Never silently choose index 0. */
		assert(!mt6797_image_owner_alloc(&owner));
		assert(!mt6797_image_owner_bind_reserved(owner, &fixture.dev, 3, &generation));
		assert(fixture.dev.refs == 2 && fixture.consumer.refs == 2 && fixture.target.refs == 2);
		assert(!mt6797_image_owner_reserved_info(owner, generation, &info));
		assert(info.start == bases[i] && info.end == bases[i] + sizes[i] - 1);
		assert(info.wlan_start == bases[i] && info.wlan_end == bases[i] + 0x7ffff);
		assert(info.wmt_start == bases[i] + 0x80000 && info.wmt_end == bases[i] + 0xfffff);
		assert(info.wmt_start == info.wlan_end + 1 && info.wmt_end <= info.end);
		data = image(4, &bytes);
		assert(!mt6797_image_binding_create(owner, data, bytes, &binding, &image_generation));
		free(data);
		assert(image_generation > generation);
		assert(mt6797_image_binding_begin(binding, image_generation) == -EOPNOTSUPP);
		assert(mt6797_image_owner_unbind_reserved(owner, generation) == -EBUSY);
		assert(!mt6797_image_binding_release(binding, image_generation));
		/* Owner destruction drops descriptor references without callbacks. */
		assert(!mt6797_image_owner_free(owner));
		fixture_balanced(&fixture);
		no_leaks();
	}
}

static void invalid_boundaries(void)
{
	const u64 bases[] = {0x40010000ULL, 0x100000000ULL, 0x40000000ULL,
			     0x40000000ULL, 0x40000000ULL};
	const u64 sizes[] = {0x100000ULL, 0x100000ULL, 0,
			     0xfffffULL, UINT64_MAX};

	for (unsigned int i = 0; i < 5; i++) {
		struct fixture fixture;
		struct mt6797_image_owner *owner;
		u64 generation = 99;

		fixture_init(&fixture, bases[i], sizes[i]);
		assert(!mt6797_image_owner_alloc(&owner));
		assert(mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation) == -ERANGE);
		assert(!generation && live_allocations == 1);
		fixture_balanced(&fixture);
		assert(!mt6797_image_owner_free(owner));
		no_leaks();
	}
}

static void refusal_matrix(void)
{
	for (unsigned int defect = 0; defect < 23; defect++) {
		struct fixture fixture;
		struct mt6797_image_owner *owner;
		u64 generation = 99;
		int expected = -EINVAL;

		fixture_init(&fixture, 0x40000000, 0x200000);
		switch (defect) {
		case 0: fixture.target.no_map = 0; expected = -EOPNOTSUPP; break;
		case 1: fixture.target.reusable = 1; expected = -EOPNOTSUPP; break;
		case 2: fixture.target.fixup = 1; expected = -EOPNOTSUPP; break;
		case 3: fixture.target.pool = 1; expected = -EOPNOTSUPP; break;
		case 4: fixture.target.pool = 2; expected = -EOPNOTSUPP; break;
		case 5: fixture.target.parent = &fixture.foreign; break;
		case 6: root_node = NULL; break;
		case 7: fixture.target.available = 0; break;
		case 8: fixture.target.dynamic = 1; break;
		case 9: fixture.target.detached = 1; break;
		case 10: fixture.consumer.available = 0; expected = -ESTALE; break;
		case 11: fixture.consumer.dynamic = 1; expected = -ESTALE; break;
		case 12: fixture.consumer.phandle = NULL; expected = -ENODEV; break;
		case 13: fixture.target.reg_cells = 8; break;
		case 14: fixture.target.address_cells = 0; break;
		case 15: fixture.target.size_cells = 3; break;
		case 16: fixture.target.rmem = NULL; expected = -ENODEV; break;
		case 17: fixture.rmem.ops = (void *)1; expected = -EOPNOTSUPP; break;
		case 18: fixture.rmem.priv = (void *)1; expected = -EOPNOTSUPP; break;
		case 19: fixture.target.reg.end--; expected = -ESTALE; break;
		case 20: fixture.target.reg.flags = IORESOURCE_IO; expected = -ESTALE; break;
		case 21: region_error = -ENOSYS; expected = -ENOSYS; break;
		case 22: fixture.target.address_error = -EIO; expected = -EIO; break;
		}
		assert(!mt6797_image_owner_alloc(&owner));
		assert(mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation) == expected);
		assert(!generation && live_allocations == 1);
		fixture_balanced(&fixture);
		assert(!mt6797_image_owner_free(owner));
		no_leaks();
	}
}

static void stale_and_lifetime(void)
{
	struct fixture fixture;
	struct mt6797_image_owner *owner;
	struct mt6797_image_binding *binding;
	struct mt6797_image_reserved_info info;
	struct device_node replacement;
	struct reserved_mem other_rmem;
	u64 generation, stale, image_generation, client;
	size_t bytes;
	u8 *data;

	fixture_init(&fixture, 0x40000000, 0x200000);
	assert(!mt6797_image_owner_alloc(&owner));
	assert(!mt6797_image_owner_claim(owner, MT6797_IMAGE_BT, &client));
	assert(mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation) == -EBUSY);
	assert(!generation);
	assert(!mt6797_image_owner_unclaim(owner, MT6797_IMAGE_BT, client));
	assert(!mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation));
	assert(mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &stale) == -EBUSY);
	assert(!stale && live_allocations == 2);
	stale = generation;
	assert(!mt6797_image_owner_unbind_reserved(owner, generation));
	assert(!mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation));
	assert(generation > stale);
	assert(mt6797_image_owner_unbind_reserved(owner, stale) == -ESTALE);
	memset(&info, 0xff, sizeof(info));
	assert(mt6797_image_owner_reserved_info(owner, stale, &info) == -ESTALE);
	assert(!info.generation && !info.end);
	data = image(4, &bytes);
	assert(!mt6797_image_binding_create(owner, data, bytes, &binding, &image_generation));
	free(data);
	fixture.target.no_map = 0;
	assert(mt6797_image_binding_prevalidate(binding, image_generation) == -EOPNOTSUPP);
	assert(mt6797_image_binding_begin(binding, image_generation) == -EOPNOTSUPP);
	assert(mt6797_image_owner_reserved_info(owner, generation, &info) == -EOPNOTSUPP);
	assert(!info.end);
	fixture.target.no_map = 1;
	assert(!mt6797_image_binding_prevalidate(binding, image_generation));
	replacement = fixture.target;
	replacement.refs = 1;
	fixture.consumer.phandle = &replacement;
	assert(mt6797_image_binding_prevalidate(binding, image_generation) == -ESTALE);
	assert(replacement.refs == 1);
	fixture.consumer.phandle = &fixture.target;
	other_rmem = fixture.rmem;
	fixture.target.rmem = &other_rmem;
	assert(mt6797_image_owner_reserved_info(owner, generation, &info) == -ESTALE);
	fixture.target.rmem = &fixture.rmem;
	fixture.rmem.size += 0x100000;
	fixture.target.reg.end += 0x100000;
	assert(mt6797_image_binding_prevalidate(binding, image_generation) == -ESTALE);
	fixture.rmem.size -= 0x100000;
	fixture.target.reg.end -= 0x100000;
	fixture.dev.of_node = &fixture.foreign;
	assert(mt6797_image_owner_reserved_info(owner, generation, &info) == -ESTALE);
	fixture.dev.of_node = &fixture.consumer;
	assert(!mt6797_image_binding_release(binding, image_generation));
	assert(!mt6797_image_owner_unbind_reserved(owner, generation));
	fixture_balanced(&fixture);
	assert(!mt6797_image_owner_free(owner));
	no_leaks();
}

static void allocation_and_exhaustion(void)
{
	struct fixture fixture;
	struct mt6797_image_owner *owner;
	u64 generation;

	fixture_init(&fixture, 0x40000000, 0x100000);
	assert(!mt6797_image_owner_alloc(&owner));
	allocation_failure(1);
	assert(mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation) == -ENOMEM);
	assert(!generation && live_allocations == 1);
	fixture_balanced(&fixture);
	allocation_failure(0);
	assert(mt6797_image_owner_bind_reserved(owner, &fixture.dev, UINT_MAX, &generation) == -EINVAL);
	assert(!generation && !allocation_calls);
	assert(!mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation));
	assert(generation == 1);
	assert(mt6797_binding_test_generation(owner, UINT64_MAX) == -EBUSY);
	assert(!mt6797_image_owner_unbind_reserved(owner, generation));
	assert(!mt6797_binding_test_generation(owner, UINT64_MAX - 1));
	assert(!mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation));
	assert(generation == UINT64_MAX);
	assert(!mt6797_image_owner_unbind_reserved(owner, generation));
	allocation_failure(0);
	assert(mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation) == -EOVERFLOW);
	assert(!generation && !allocation_calls);
	fixture_balanced(&fixture);
	assert(!mt6797_image_owner_free(owner));
	no_leaks();
}

static void reserved_fault_retention(void)
{
	struct fixture fixture;
	struct mt6797_image_owner *owner;
	struct mt6797_image_binding *binding;
	u64 generation, image_generation;
	size_t bytes;
	u8 *data;

	fixture_init(&fixture, 0x40000000, 0x200000);
	assert(!mt6797_image_owner_alloc(&owner));
	assert(!mt6797_image_owner_bind_reserved(owner, &fixture.dev, 0, &generation));
	data = image(4, &bytes);
	assert(!mt6797_image_binding_create(owner, data, bytes, &binding, &image_generation));
	free(data);
	assert(mt6797_image_binding_hold_fault(binding, image_generation, -EIO) == -EIO);
	assert(mt6797_image_binding_release(binding, image_generation) == -EBUSY);
	assert(mt6797_image_owner_unbind_reserved(owner, generation) == -EBUSY);
	assert(mt6797_image_owner_free(owner) == -EBUSY);
	assert(live_allocations == 4);
	assert(fixture.dev.refs == 2 && fixture.consumer.refs == 2 && fixture.target.refs == 2);
	resource_checks++;
	/* Dispose the complete hardware-free test environment, not a successful
	 * production release/recovery. Retention above remains the tested result.
	 */
	for (unsigned int i = 0; i < 16; i++)
		if (live_mutexes[i])
			binding_test_mutex_destroy(live_mutexes[i]);
	while (allocations)
		binding_test_free(allocations->pointer);
	put_device(&fixture.dev);
	of_node_put(&fixture.consumer);
	of_node_put(&fixture.target);
	fixture_balanced(&fixture);
	no_leaks();
}

int main(void)
{
	assert(!previous_binding_tests());
	valid_intervals();
	invalid_boundaries();
	refusal_matrix();
	stale_and_lifetime();
	allocation_and_exhaustion();
	reserved_fault_retention();
	printf("reserved_checks=%u\nnode_refs=balanced\ndevice_refs=balanced\nactive_entry=refused\n", resource_checks);
	return 0;
}
