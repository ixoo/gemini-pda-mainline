/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_TEST_COMPAT_H
#define MT6797_TEST_COMPAT_H
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define __iomem
#define GFP_KERNEL 0
#define kzalloc_obj(object, flags) kzalloc(sizeof(object), flags)
#define IS_ALIGNED(value, align) (!((value) & ((align) - 1)))
#define ERR_PTR(error) ((void *)(intptr_t)(error))
#define IS_ERR(pointer) ((uintptr_t)(pointer) >= (uintptr_t)-4095)
struct mutex { bool held; };
static inline void mutex_init(struct mutex *lock) { lock->held = false; }
static inline bool mutex_trylock(struct mutex *lock)
{
	if (lock->held)
		return false;
	lock->held = true;
	return true;
}
static inline void mutex_unlock(struct mutex *lock)
{
	assert(lock->held);
	lock->held = false;
}
static inline void *kzalloc(size_t length, int flags)
{
	(void)flags;
	return calloc(1, length);
}
static inline void kfree(void *pointer) { free(pointer); }
u64 ktime_get_ns(void);
void usleep_range(unsigned long minimum, unsigned long maximum);
int mt6797_test_write(unsigned int value, void *address);
int mt6797_test_read(void *address, unsigned int *value);
#endif
