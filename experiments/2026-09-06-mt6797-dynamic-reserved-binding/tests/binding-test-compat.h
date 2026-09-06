/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_BINDING_TEST_COMPAT_H
#define MT6797_BINDING_TEST_COMPAT_H
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define GFP_KERNEL 0
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint8_t u8;
struct mutex { pthread_mutex_t native; };
void binding_test_mutex_init(struct mutex *lock);
void binding_test_mutex_destroy(struct mutex *lock);
void *binding_test_alloc(size_t bytes, int zero);
void binding_test_free(const void *pointer);
#define mutex_init(lock) binding_test_mutex_init(lock)
#define mutex_destroy(lock) binding_test_mutex_destroy(lock)
static inline void mutex_lock(struct mutex *lock)
{
	assert(!pthread_mutex_lock(&lock->native));
}
static inline void mutex_unlock(struct mutex *lock)
{
	assert(!pthread_mutex_unlock(&lock->native));
}
#define kzalloc_obj(object, flags) binding_test_alloc(sizeof(object), 1)
#define kvmalloc(bytes, flags) binding_test_alloc(bytes, 0)
#define kfree(pointer) binding_test_free(pointer)
#define kvfree(pointer) binding_test_free(pointer)

struct mt6797_image_owner;
int mt6797_binding_test_generation(struct mt6797_image_owner *owner,
					 uint64_t value);
#include <limits.h>

#define SZ_512K 0x80000U
#define SZ_1M 0x100000U
#define IORESOURCE_MEM 0x00000200UL
#define IORESOURCE_IO 0x00000100UL
#define IORESOURCE_TYPE_BITS 0x00001f00UL
#define OF_DYNAMIC 1
#define OF_DETACHED 2

struct resource {
	u64 start;
	u64 end;
	unsigned long flags;
};
struct property {
	const void *value;
	int length;
};
static inline unsigned long resource_type(const struct resource *resource)
{
	return resource->flags & IORESOURCE_TYPE_BITS;
}

struct reserved_mem {
	const void *ops;
	u64 base;
	u64 size;
	void *priv;
};

/* API-boundary observations, not an OF parser or a hardware emulator. */
struct device_node {
	int refs;
	int available;
	int dynamic;
	int detached;
	int no_map;
	int reusable;
	int fixup;
	int pool;
	int address_cells;
	int size_cells;
	int reg_cells;
	const u8 *reg_data;
	int reg_present;
	int reg_length;
	const u8 *size_data;
	int size_present;
	int size_length;
	const u8 *alignment_data;
	int alignment_present;
	int alignment_length;
	const u8 *alloc_ranges_data;
	int alloc_ranges_present;
	int alloc_ranges_length;
	int address_error;
	unsigned int selected_index;
	struct device_node *parent;
	struct device_node *phandle;
	struct reserved_mem *rmem;
	struct resource reg;
	struct property reg_property;
	struct property size_property;
	struct property alignment_property;
	struct property alloc_ranges_property;
};
struct device {
	int refs;
	struct device_node *of_node;
};

struct device *get_device(struct device *dev);
void put_device(struct device *dev);
struct device_node *of_node_get(struct device_node *node);
void of_node_put(struct device_node *node);
struct device_node *of_get_parent(const struct device_node *node);
struct device_node *of_find_node_by_path(const char *path);
struct device_node *of_parse_phandle(const struct device_node *node,
				    const char *name, int index);
int of_device_is_available(const struct device_node *node);
int of_node_check_flag(const struct device_node *node, unsigned long flag);
int of_property_read_bool(const struct device_node *node, const char *name);
int of_device_is_compatible(const struct device_node *node, const char *name);
int of_n_addr_cells(struct device_node *node);
int of_n_size_cells(struct device_node *node);
int of_property_count_u32_elems(const struct device_node *node, const char *name);
struct property *of_find_property(const struct device_node *node,
					  const char *name, int *length);
struct reserved_mem *of_reserved_mem_lookup(struct device_node *node);
int of_reserved_mem_region_to_resource(const struct device_node *node,
				       unsigned int index, struct resource *resource);
int of_address_to_resource(struct device_node *node, int index,
			   struct resource *resource);
#endif
