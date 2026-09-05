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
#endif
