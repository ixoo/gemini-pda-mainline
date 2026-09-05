// SPDX-License-Identifier: GPL-2.0-only
#include "image-binding.h"
#include "binding-test-compat.h"
#include <stdio.h>
#include <zlib.h>

struct allocation {
	void *pointer;
	size_t bytes;
	struct allocation *next;
};
static pthread_mutex_t accounting = PTHREAD_MUTEX_INITIALIZER;
static struct allocation *allocations;
static struct mutex *live_mutexes[16];
static size_t live_allocations, allocation_calls, fail_call;
static unsigned int checks;

void *binding_test_alloc(size_t bytes, int zero)
{
	struct allocation *entry;
	void *pointer;

	assert(!pthread_mutex_lock(&accounting));
	allocation_calls++;
	if (fail_call && allocation_calls == fail_call) {
		assert(!pthread_mutex_unlock(&accounting));
		return NULL;
	}
	pointer = zero ? calloc(1, bytes) : malloc(bytes);
	assert(pointer);
	entry = malloc(sizeof(*entry));
	assert(entry);
	*entry = (struct allocation){pointer, bytes, allocations};
	allocations = entry;
	live_allocations++;
	assert(!pthread_mutex_unlock(&accounting));
	return pointer;
}

void binding_test_free(const void *pointer)
{
	struct allocation **cursor, *entry;

	if (!pointer)
		return;
	assert(!pthread_mutex_lock(&accounting));
	for (cursor = &allocations; *cursor; cursor = &(*cursor)->next)
		if ((*cursor)->pointer == pointer)
			break;
	assert(*cursor);
	entry = *cursor;
	*cursor = entry->next;
	memset(entry->pointer, 0xa5, entry->bytes);
	free(entry->pointer);
	free(entry);
	live_allocations--;
	assert(!pthread_mutex_unlock(&accounting));
}

void binding_test_mutex_init(struct mutex *lock)
{
	unsigned int i;

	assert(!pthread_mutex_init(&lock->native, NULL));
	assert(!pthread_mutex_lock(&accounting));
	for (i = 0; i < 16; i++)
		if (!live_mutexes[i])
			break;
	assert(i < 16);
	live_mutexes[i] = lock;
	assert(!pthread_mutex_unlock(&accounting));
}

void binding_test_mutex_destroy(struct mutex *lock)
{
	unsigned int i;

	assert(!pthread_mutex_destroy(&lock->native));
	assert(!pthread_mutex_lock(&accounting));
	for (i = 0; i < 16; i++)
		if (live_mutexes[i] == lock)
			break;
	assert(i < 16);
	live_mutexes[i] = NULL;
	assert(!pthread_mutex_unlock(&accounting));
}

static void allocation_failure(size_t nth)
{
	assert(!pthread_mutex_lock(&accounting));
	allocation_calls = 0;
	fail_call = nth;
	assert(!pthread_mutex_unlock(&accounting));
}

static void no_leaks(void)
{
	assert(!allocations && !live_allocations);
	for (unsigned int i = 0; i < 16; i++)
		assert(!live_mutexes[i]);
	checks++;
}

u32 mtke_crc32(const u8 *data, size_t bytes)
{
	assert(bytes <= MTKE_MAX_BYTES);
	return (u32)crc32(0, data, (uInt)bytes);
}

static void put32(u8 *data, u32 value)
{
	for (unsigned int i = 0; i < 4; i++)
		data[i] = (u8)(value >> (8 * i));
}

static void fix_crc(u8 *data, size_t bytes)
{
	put32(data + 4, mtke_crc32(data + 8, bytes - 8));
}

static u8 *image(unsigned int count, size_t *bytes)
{
	u8 *data;

	*bytes = 24 + (size_t)count * 20;
	data = calloc(1, *bytes);
	assert(data);
	memcpy(data, "MTKE", 4);
	put32(data + 8, count);
	for (unsigned int i = 0; i < count; i++) {
		put32(data + 24 + 16 * i, 24 + 16 * count + 4 * i);
		put32(data + 24 + 16 * i + 8, 4);
		put32(data + 24 + 16 * i + 12,
		      i < 2 ? 0x1000 + 4 * i : 0xf0000000U + 4 * i);
	}
	fix_crc(data, *bytes);
	return data;
}

static void snapshots_and_stale_tokens(void)
{
	const unsigned int counts[] = {1, 2, 3, 4, 256};
	struct mt6797_image_owner *owner;
	u64 previous = 0;

	assert(!mt6797_image_owner_alloc(&owner));
	for (unsigned int c = 0; c < sizeof(counts) / sizeof(counts[0]); c++) {
		struct mt6797_image_binding *binding;
		struct mt6797_image_binding_info info;
		struct mt6797_plan_section description;
		struct mt6797_image_plan caller_plan;
		u64 generation;
		size_t bytes;
		u8 *data = image(counts[c], &bytes);

		assert(!mt6797_image_plan_prepare(&caller_plan, data, bytes));
		assert(!mt6797_image_binding_create(owner, data, bytes,
						    &binding, &generation));
		assert(generation > previous);
		/* Destroy both caller context and bytes, then use the private plan. */
		mt6797_image_plan_invalidate(&caller_plan);
		memset(data, 0xa5, bytes);
		free(data);
		assert(!mt6797_image_binding_prevalidate(binding, generation));
		assert(mt6797_image_binding_begin(binding, generation) == -EOPNOTSUPP);
		assert(!mt6797_image_binding_info(binding, generation, &info));
		assert(info.sections == counts[c] && info.image_bytes == bytes);
		assert(info.state == MT6797_IMAGE_PASSIVE && !info.first_error);
		assert(info.ordinary_sections == (counts[c] < 2 ? counts[c] : 2));
		assert(info.emi_sections == (counts[c] > 2 ? counts[c] - 2 : 0));
		for (unsigned int i = 0; i < counts[c]; i++) {
			assert(!mt6797_image_binding_describe(binding, generation, i,
							      &description));
			assert(description.length == 4 && description.emi == (i >= 2));
		}
		memset(&description, 0xff, sizeof(description));
		assert(mt6797_image_binding_describe(binding, generation, counts[c],
						     &description) == -EINVAL);
		assert(!description.length && !description.offset);
		assert(mt6797_image_binding_begin(binding, previous) == -ESTALE);
		assert(mt6797_image_binding_release(binding, previous) == -ESTALE);
		assert(mt6797_image_binding_invalidate(binding, previous) == -ESTALE);
		assert(mt6797_image_binding_hold_fault(binding, previous, -EIO) == -ESTALE);
		memset(&info, 0xff, sizeof(info));
		assert(mt6797_image_binding_info(binding, previous, &info) == -ESTALE);
		assert(!info.generation && !info.sections);
		assert(!mt6797_image_binding_invalidate(binding, generation));
		assert(mt6797_image_binding_prevalidate(binding, generation) == -ESTALE);
		assert(mt6797_image_binding_begin(binding, generation) == -ESTALE);
		assert(!mt6797_image_binding_info(binding, generation, &info));
		assert(info.state == MT6797_IMAGE_INVALID && !info.sections);
		assert(!mt6797_image_binding_release(binding, generation));
		assert(live_allocations == 1);
		previous = generation;
		checks++;
	}
	assert(!mt6797_image_owner_free(owner));
	no_leaks();
}

static void failed_construction(void)
{
	struct mt6797_image_owner *owner = (void *)1;
	struct mt6797_image_binding *binding;
	u64 generation;
	size_t bytes;
	u8 *data = image(4, &bytes);

	allocation_failure(1);
	assert(mt6797_image_owner_alloc(&owner) == -ENOMEM && !owner);
	no_leaks();
	allocation_failure(0);
	assert(!mt6797_image_owner_alloc(&owner));
	for (size_t nth = 1; nth <= 2; nth++) {
		allocation_failure(nth);
		binding = (void *)1;
		generation = 99;
		assert(mt6797_image_binding_create(owner, data, bytes,
						   &binding, &generation) == -ENOMEM);
		assert(!binding && !generation && live_allocations == 1);
		checks++;
	}
	allocation_failure(0);
	assert(mt6797_image_binding_create(owner, data, MTKE_MAX_BYTES + 1,
					   &binding, &generation) == -EINVAL);
	assert(!allocation_calls && !binding && !generation);
	for (unsigned int defect = 0; defect < 4; defect++) {
		u8 *bad = malloc(bytes);

		assert(bad);
		memcpy(bad, data, bytes);
		if (defect == 0)
			put32(bad + 24 + 16 * 3 + 12, 0xf007ffffU);
		else if (defect == 1)
			put32(bad + 24 + 16 * 3 + 8, 0xffffffffU);
		else if (defect == 2)
			bad[24 + 16 * 3 + 6] = 1;
		else
			bad[4] ^= 1;
		if (defect != 3)
			fix_crc(bad, bytes);
		assert(mt6797_image_binding_create(owner, bad, bytes, &binding,
						   &generation) ==
		       (defect == 2 ? -EOPNOTSUPP : -EINVAL));
		assert(!binding && !generation && live_allocations == 1);
		free(bad);
		checks++;
	}
	assert(!mt6797_image_binding_create(owner, data, bytes, &binding, &generation));
	assert(generation == 1); /* No failed allocation/plan consumed a generation. */
	assert(!mt6797_image_binding_release(binding, generation));
	assert(!mt6797_image_owner_free(owner));
	free(data);
	no_leaks();
}

static void claims_and_exhaustion(void)
{
	struct mt6797_image_owner *owner;
	struct mt6797_image_binding *binding;
	u64 claims[MT6797_IMAGE_CLIENTS], generation, old;
	size_t bytes;
	u8 *data = image(4, &bytes);

	assert(!mt6797_image_owner_alloc(&owner));
	for (unsigned int i = 0; i < MT6797_IMAGE_CLIENTS; i++) {
		assert(!mt6797_image_owner_claim(owner, (enum mt6797_image_client)i,
						&claims[i]));
		assert(mt6797_image_binding_create(owner, data, bytes, &binding,
						   &generation) == -EBUSY);
		assert(!binding && !generation);
		assert(mt6797_image_owner_free(owner) == -EBUSY);
		assert(mt6797_image_owner_claim(owner, (enum mt6797_image_client)i,
						&generation) == -EBUSY && !generation);
	}
	for (unsigned int i = 0; i < MT6797_IMAGE_CLIENTS; i++)
		assert(!mt6797_image_owner_unclaim(owner, (enum mt6797_image_client)i,
						  claims[i]));
	old = claims[MT6797_IMAGE_BT];
	assert(!mt6797_image_owner_claim(owner, MT6797_IMAGE_BT, &generation));
	assert(generation > old);
	assert(mt6797_image_owner_unclaim(owner, MT6797_IMAGE_BT, old) == -ESTALE);
	assert(!mt6797_image_owner_unclaim(owner, MT6797_IMAGE_BT, generation));
	assert(!mt6797_image_binding_create(owner, data, bytes, &binding, &generation));
	assert(mt6797_image_owner_claim(owner, MT6797_IMAGE_GNSS, &old) == -EBUSY);
	assert(!old && mt6797_image_owner_free(owner) == -EBUSY);
	assert(!mt6797_image_binding_release(binding, generation));
	assert(!mt6797_binding_test_generation(owner, UINT64_MAX - 1));
	assert(!mt6797_image_binding_create(owner, data, bytes, &binding, &generation));
	assert(generation == UINT64_MAX);
	assert(!mt6797_image_binding_release(binding, generation));
	allocation_failure(0);
	assert(mt6797_image_binding_create(owner, data, bytes, &binding,
					   &generation) == -EOVERFLOW);
	assert(!allocation_calls && !binding && !generation);
	assert(mt6797_image_owner_claim(owner, MT6797_IMAGE_WLAN, &generation) == -EOVERFLOW);
	assert(!generation);
	assert(mt6797_binding_test_generation(owner, 1) == -EBUSY);
	assert(!mt6797_image_owner_free(owner));
	free(data);
	checks++;
	no_leaks();
}

struct race {
	struct mt6797_image_owner *owner;
	const u8 *data;
	size_t bytes;
	struct mt6797_image_binding *binding;
	u64 generation;
	int result;
};
static pthread_mutex_t start_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t start_condition = PTHREAD_COND_INITIALIZER;
static unsigned int waiting;
static int start;

static void *race_create(void *argument)
{
	struct race *race = argument;

	assert(!pthread_mutex_lock(&start_mutex));
	waiting++;
	assert(!pthread_cond_broadcast(&start_condition));
	while (!start)
		assert(!pthread_cond_wait(&start_condition, &start_mutex));
	assert(!pthread_mutex_unlock(&start_mutex));
	race->result = mt6797_image_binding_create(race->owner, race->data,
						  race->bytes, &race->binding,
						  &race->generation);
	return NULL;
}

static void competing_threads(void)
{
	struct mt6797_image_owner *owner;
	u64 previous = 0;
	size_t bytes;
	u8 *data = image(4, &bytes);

	assert(!mt6797_image_owner_alloc(&owner));
	for (unsigned int round = 0; round < 32; round++) {
		struct race races[8] = {0};
		pthread_t threads[8];
		unsigned int winners = 0, winner = 0;

		waiting = 0;
		start = 0;
		for (unsigned int i = 0; i < 8; i++) {
			races[i].owner = owner;
			races[i].data = data;
			races[i].bytes = bytes;
			assert(!pthread_create(&threads[i], NULL, race_create, &races[i]));
		}
		assert(!pthread_mutex_lock(&start_mutex));
		while (waiting != 8)
			assert(!pthread_cond_wait(&start_condition, &start_mutex));
		start = 1;
		assert(!pthread_cond_broadcast(&start_condition));
		assert(!pthread_mutex_unlock(&start_mutex));
		for (unsigned int i = 0; i < 8; i++) {
			assert(!pthread_join(threads[i], NULL));
			if (!races[i].result) {
				winner = i;
				winners++;
			} else {
				assert(races[i].result == -EBUSY);
				assert(!races[i].binding && !races[i].generation);
			}
		}
		assert(winners == 1 && races[winner].generation > previous);
		previous = races[winner].generation;
		assert(!mt6797_image_binding_release(races[winner].binding,
						     races[winner].generation));
		assert(live_allocations == 1);
		checks++;
	}
	assert(!mt6797_image_owner_free(owner));
	free(data);
	no_leaks();
}

static void held_fault(void)
{
	struct mt6797_image_owner *owner;
	struct mt6797_image_binding *binding, *other;
	struct mt6797_image_binding_info info;
	struct mt6797_plan_section description;
	u64 generation, other_generation;
	size_t bytes;
	u8 *data = image(4, &bytes);

	assert(!mt6797_image_owner_alloc(&owner));
	assert(!mt6797_image_binding_create(owner, data, bytes, &binding, &generation));
	free(data);
	assert(live_allocations == 3);
	assert(mt6797_image_binding_hold_fault(binding, generation, 0) == -EINVAL);
	assert(mt6797_image_binding_hold_fault(binding, generation, -ETIMEDOUT) == -ETIMEDOUT);
	assert(mt6797_image_binding_hold_fault(binding, generation, -EIO) == -ETIMEDOUT);
	assert(!mt6797_image_binding_info(binding, generation, &info));
	assert(info.state == MT6797_IMAGE_FAULT_HELD && info.first_error == -ETIMEDOUT);
	assert(info.image_bytes == bytes && info.sections == 4);
	assert(mt6797_image_binding_prevalidate(binding, generation) == -ETIMEDOUT);
	assert(mt6797_image_binding_begin(binding, generation) == -ETIMEDOUT);
	assert(mt6797_image_binding_invalidate(binding, generation) == -ETIMEDOUT);
	memset(&description, 0xff, sizeof(description));
	assert(mt6797_image_binding_describe(binding, generation, 0, &description) == -ETIMEDOUT);
	assert(!description.length && !description.offset);
	assert(mt6797_image_binding_release(binding, generation) == -EBUSY);
	assert(mt6797_image_owner_free(owner) == -EBUSY);
	data = image(1, &bytes);
	assert(mt6797_image_binding_create(owner, data, bytes, &other, &other_generation) == -EBUSY);
	assert(!other && !other_generation && live_allocations == 3);
	free(data);
	assert(mt6797_image_owner_claim(owner, MT6797_IMAGE_BT, &other_generation) == -EBUSY);
	assert(!other_generation && live_allocations == 3);
	checks++;
	/* End this hardware-free fixture, not a production recovery operation.
	 * The public API above could not free or reactivate anything. Dispose the
	 * test allocator's complete environment only after every user has joined;
	 * never return the held object to another test or manufacture quiescence.
	 */
	for (unsigned int i = 0; i < 16; i++)
		if (live_mutexes[i])
			binding_test_mutex_destroy(live_mutexes[i]);
	while (allocations)
		binding_test_free(allocations->pointer);
	no_leaks();
}

static void null_and_invalid_arguments(void)
{
	struct mt6797_image_owner *owner;
	struct mt6797_image_binding *binding = (void *)1;
	struct mt6797_image_binding_info info;
	struct mt6797_plan_section section;
	u64 generation = 4;

	assert(mt6797_image_owner_alloc(NULL) == -EINVAL);
	assert(mt6797_image_owner_free(NULL) == -EINVAL);
	assert(!mt6797_image_owner_alloc(&owner));
	assert(mt6797_image_owner_claim(owner, (enum mt6797_image_client)-1,
					&generation) == -EINVAL && !generation);
	assert(mt6797_image_owner_claim(owner, MT6797_IMAGE_WLAN, NULL) == -EINVAL);
	assert(mt6797_image_owner_unclaim(owner, MT6797_IMAGE_WLAN, 0) == -ESTALE);
	assert(mt6797_image_binding_create(owner, NULL, 24, &binding, &generation) == -EINVAL);
	assert(!binding && !generation);
	assert(mt6797_image_binding_info(NULL, 0, &info) == -EINVAL && !info.sections);
	assert(mt6797_image_binding_describe(NULL, 0, 0, &section) == -EINVAL && !section.length);
	assert(mt6797_image_binding_begin(NULL, 0) == -EINVAL);
	assert(mt6797_image_binding_release(NULL, 0) == -EINVAL);
	assert(mt6797_image_binding_hold_fault(NULL, 0, -EIO) == -EINVAL);
	assert(!mt6797_image_owner_free(owner));
	no_leaks();
}

int main(void)
{
	null_and_invalid_arguments();
	snapshots_and_stale_tokens();
	failed_construction();
	claims_and_exhaustion();
	competing_threads();
	held_fault();
	printf("binding_checks=%u\nconcurrent_claim_rounds=32\nactive_entry=refused\n", checks);
	return 0;
}
