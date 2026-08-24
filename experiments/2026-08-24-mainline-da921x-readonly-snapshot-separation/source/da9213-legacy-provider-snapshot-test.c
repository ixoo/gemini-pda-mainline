// SPDX-License-Identifier: GPL-2.0-only
/* Hardware-free coverage for the read-only DA921x provider snapshot. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/i2c.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/string.h>

#include "da9213-legacy-provider-contract.h"

#define DA9213_SNAPSHOT_TEST_ADDRESS	0x2a
#define DA9213_SNAPSHOT_TEST_RETRIES	3
#define DA9213_SNAPSHOT_READS		10
#define DA9213_SNAPSHOT_BYTES		5

struct da9213_snapshot_fake {
	struct i2c_adapter adapter;
	u8 registers[256];
	unsigned int lock_calls;
	unsigned int unlock_calls;
	unsigned int transfer_calls;
	unsigned int fail_ordinal;
	unsigned int short_ordinal;
	unsigned int mismatch_byte;
	bool locked;
	bool transfer_unlocked;
	bool retry_nonzero;
};

struct da9213_snapshot_test_state {
	struct da9213_legacy_provider_endpoint endpoint;
	struct da9213_legacy_provider_endpoint duplicate;
	struct da9213_snapshot_fake fake;
	struct da9213_snapshot_fake duplicate_fake;
};

static struct da9213_legacy_provider_endpoint *registered_endpoint;

static struct da9213_snapshot_fake *
da9213_snapshot_adapter_fake(struct i2c_adapter *adapter)
{
	return container_of(adapter, struct da9213_snapshot_fake, adapter);
}

static void da9213_snapshot_lock(struct i2c_adapter *adapter, unsigned int flags)
{
	struct da9213_snapshot_fake *fake = da9213_snapshot_adapter_fake(adapter);

	(void)flags;
	fake->lock_calls++;
	fake->locked = true;
}

static int da9213_snapshot_trylock(struct i2c_adapter *adapter,
				   unsigned int flags)
{
	(void)adapter;
	(void)flags;
	return 0;
}

static void da9213_snapshot_unlock(struct i2c_adapter *adapter, unsigned int flags)
{
	struct da9213_snapshot_fake *fake = da9213_snapshot_adapter_fake(adapter);

	(void)flags;
	fake->unlock_calls++;
	fake->locked = false;
}

static const struct i2c_lock_operations da9213_snapshot_lock_ops = {
	.lock_bus = da9213_snapshot_lock,
	.trylock_bus = da9213_snapshot_trylock,
	.unlock_bus = da9213_snapshot_unlock,
};

static int da9213_snapshot_transfer(struct i2c_adapter *adapter,
				    struct i2c_msg *messages, int count)
{
	struct da9213_snapshot_fake *fake = da9213_snapshot_adapter_fake(adapter);
	u8 value;
	u8 reg;

	fake->transfer_calls++;
	if (!fake->locked)
		fake->transfer_unlocked = true;
	if (adapter->retries)
		fake->retry_nonzero = true;
	if (fake->fail_ordinal == fake->transfer_calls)
		return -EIO;
	if (fake->short_ordinal == fake->transfer_calls)
		return 1;
	if (count != 2 || messages[0].addr != DA9213_SNAPSHOT_TEST_ADDRESS ||
	    messages[1].addr != DA9213_SNAPSHOT_TEST_ADDRESS ||
	    messages[0].flags || messages[1].flags != I2C_M_RD ||
	    messages[0].len != 1 || messages[1].len != 1 ||
	    !messages[0].buf || !messages[1].buf)
		return -EPROTO;

	reg = messages[0].buf[0];
	value = fake->registers[reg];
	if (fake->mismatch_byte &&
	    fake->transfer_calls == 5 + fake->mismatch_byte)
		value ^= 1;
	messages[1].buf[0] = value;
	return 2;
}

static void da9213_snapshot_fake_init(struct da9213_snapshot_fake *fake)
{
	memset(fake, 0, sizeof(*fake));
	fake->adapter.lock_ops = &da9213_snapshot_lock_ops;
	fake->adapter.retries = DA9213_SNAPSHOT_TEST_RETRIES;
	fake->registers[0x56] = 0x7b;
	fake->registers[0x51] = 0xc1;
	fake->registers[0x5e] = 0x00;
	fake->registers[0xd9] = 0x46;
	fake->registers[0xda] = 0x46;
}

static int
da9213_snapshot_register(struct da9213_legacy_provider_endpoint *endpoint,
			 struct da9213_snapshot_fake *fake)
{
	int ret;

	ret = da9213_provider_snapshot_test_register(endpoint, &fake->adapter,
						     DA9213_SNAPSHOT_TEST_ADDRESS,
						     da9213_snapshot_transfer);
	if (!ret)
		registered_endpoint = endpoint;
	return ret;
}

static void
da9213_snapshot_unregister(struct da9213_legacy_provider_endpoint *endpoint)
{
	da9213_provider_snapshot_test_unregister(endpoint);
	if (registered_endpoint == endpoint)
		registered_endpoint = NULL;
}

static void
da9213_snapshot_expect_zero(struct kunit *test,
			    const struct mt6797_a72_provider_snapshot *snapshot)
{
	const struct mt6797_a72_provider_snapshot zero = { };

	KUNIT_EXPECT_MEMEQ(test, snapshot, &zero, sizeof(*snapshot));
}

static void
da9213_snapshot_expect_transport_closed(struct kunit *test,
					const struct da9213_snapshot_fake *fake)
{
	KUNIT_EXPECT_EQ(test, fake->lock_calls, 1U);
	KUNIT_EXPECT_EQ(test, fake->unlock_calls, 1U);
	KUNIT_EXPECT_FALSE(test, fake->locked);
	KUNIT_EXPECT_FALSE(test, fake->transfer_unlocked);
	KUNIT_EXPECT_FALSE(test, fake->retry_nonzero);
	KUNIT_EXPECT_EQ(test, fake->adapter.retries,
			DA9213_SNAPSHOT_TEST_RETRIES);
}

static void da9213_snapshot_success_test(struct kunit *test)
{
	struct da9213_snapshot_test_state *state;
	struct mt6797_a72_provider_snapshot snapshot;
	int ret;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	da9213_snapshot_fake_init(&state->fake);
	ret = da9213_snapshot_register(&state->endpoint, &state->fake);
	KUNIT_ASSERT_EQ(test, ret, 0);
	memset(&snapshot, 0xa5, sizeof(snapshot));
	ret = mt6797_a72_provider_snapshot(&snapshot);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, snapshot.abi,
			MT6797_A72_PROVIDER_STATE_ABI);
	KUNIT_EXPECT_EQ(test, snapshot.valid, 1U);
	KUNIT_EXPECT_EQ(test, snapshot.control_a, 0x7bU);
	KUNIT_EXPECT_EQ(test, snapshot.status_b, 0xc1U);
	KUNIT_EXPECT_EQ(test, snapshot.buckb_cont, 0U);
	KUNIT_EXPECT_EQ(test, snapshot.vbuckb_a, 0x46U);
	KUNIT_EXPECT_EQ(test, snapshot.vbuckb_b, 0x46U);
	KUNIT_EXPECT_EQ(test, snapshot.reserved, 0U);
	KUNIT_EXPECT_EQ(test, state->fake.transfer_calls,
			DA9213_SNAPSHOT_READS);
	da9213_snapshot_expect_transport_closed(test, &state->fake);
	da9213_snapshot_unregister(&state->endpoint);
}

static void da9213_snapshot_transfer_faults_test(struct kunit *test)
{
	struct da9213_snapshot_test_state *state;
	unsigned int mode;
	unsigned int ordinal;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	for (mode = 0; mode < 2; mode++) {
		for (ordinal = 1; ordinal <= DA9213_SNAPSHOT_READS; ordinal++) {
			struct mt6797_a72_provider_snapshot snapshot;
			int ret;

			da9213_snapshot_fake_init(&state->fake);
			if (mode)
				state->fake.short_ordinal = ordinal;
			else
				state->fake.fail_ordinal = ordinal;
			ret = da9213_snapshot_register(&state->endpoint,
						       &state->fake);
			KUNIT_ASSERT_EQ(test, ret, 0);
			memset(&snapshot, 0xa5, sizeof(snapshot));
			ret = mt6797_a72_provider_snapshot(&snapshot);
			KUNIT_EXPECT_EQ_MSG(test, ret, -EIO,
					    "mode=%u ordinal=%u", mode, ordinal);
			da9213_snapshot_expect_zero(test, &snapshot);
			KUNIT_EXPECT_EQ(test, state->fake.transfer_calls, ordinal);
			da9213_snapshot_expect_transport_closed(test, &state->fake);
			da9213_snapshot_unregister(&state->endpoint);
		}
	}
}

static void da9213_snapshot_mismatches_test(struct kunit *test)
{
	struct da9213_snapshot_test_state *state;
	unsigned int byte;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	for (byte = 1; byte <= DA9213_SNAPSHOT_BYTES; byte++) {
		struct mt6797_a72_provider_snapshot snapshot;
		int ret;

		da9213_snapshot_fake_init(&state->fake);
		state->fake.mismatch_byte = byte;
		ret = da9213_snapshot_register(&state->endpoint, &state->fake);
		KUNIT_ASSERT_EQ(test, ret, 0);
		memset(&snapshot, 0xa5, sizeof(snapshot));
		ret = mt6797_a72_provider_snapshot(&snapshot);
		KUNIT_EXPECT_EQ_MSG(test, ret, -EAGAIN, "byte=%u", byte);
		da9213_snapshot_expect_zero(test, &snapshot);
		KUNIT_EXPECT_EQ(test, state->fake.transfer_calls,
				DA9213_SNAPSHOT_READS);
		da9213_snapshot_expect_transport_closed(test, &state->fake);
		da9213_snapshot_unregister(&state->endpoint);
	}
}

static void da9213_snapshot_registry_lifetime_test(struct kunit *test)
{
	struct da9213_snapshot_test_state *state;
	struct mt6797_a72_provider_snapshot snapshot;
	int ret;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	memset(&snapshot, 0xa5, sizeof(snapshot));
	ret = mt6797_a72_provider_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENODEV);
	da9213_snapshot_expect_zero(test, &snapshot);

	da9213_snapshot_fake_init(&state->fake);
	ret = da9213_snapshot_register(&state->endpoint, &state->fake);
	KUNIT_ASSERT_EQ(test, ret, 0);
	da9213_snapshot_fake_init(&state->duplicate_fake);
	ret = da9213_provider_snapshot_test_register(&state->duplicate,
						     &state->duplicate_fake.adapter,
						     DA9213_SNAPSHOT_TEST_ADDRESS,
						     da9213_snapshot_transfer);
	KUNIT_EXPECT_EQ(test, ret, -EBUSY);
	da9213_snapshot_unregister(&state->duplicate);
	memset(&snapshot, 0xa5, sizeof(snapshot));
	ret = mt6797_a72_provider_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->fake.transfer_calls,
			DA9213_SNAPSHOT_READS);
	da9213_snapshot_unregister(&state->endpoint);
	memset(&snapshot, 0xa5, sizeof(snapshot));
	ret = mt6797_a72_provider_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENODEV);
	da9213_snapshot_expect_zero(test, &snapshot);
}

static void da9213_snapshot_readonly_lifecycle_test(struct kunit *test)
{
	struct da9213_snapshot_test_state *state;
	struct mt6797_a72_provider_request request = {
		.abi = MT6797_A72_PROVIDER_CALL_ABI,
		.operation = MT6797_A72_PROVIDER_OPERATION_CPU8_UP,
		.settle_us = MT6797_A72_PROVIDER_CALL_SETTLE_US,
		.da921x_page = MT6797_A72_PROVIDER_CALL_DA921X_PAGE,
		.buckb_vsel = MT6797_A72_PROVIDER_CALL_BUCKB_VSEL,
		.transaction_generation = 1,
		.transaction_cookie = 2,
	};
	struct mt6797_a72_provider_handle handle = {
		.generation = 1,
		.cookie = 2,
	};
	struct mt6797_a72_provider_response response;
	int ret;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	da9213_snapshot_fake_init(&state->fake);
	ret = da9213_snapshot_register(&state->endpoint, &state->fake);
	KUNIT_ASSERT_EQ(test, ret, 0);
	memset(&response, 0xa5, sizeof(response));
	ret = mt6797_a72_provider_acquire(&request, &response);
	KUNIT_EXPECT_EQ(test, ret, -EOPNOTSUPP);
	KUNIT_EXPECT_EQ(test, response.abi, MT6797_A72_PROVIDER_CALL_ABI);
	KUNIT_EXPECT_EQ(test, response.returned, 1U);
	KUNIT_EXPECT_EQ(test, response.vote_requested, 0U);
	KUNIT_EXPECT_EQ(test, response.provider_mutated, 0U);
	KUNIT_EXPECT_EQ(test, response.rail_mutated, 0U);
	KUNIT_EXPECT_EQ(test, state->fake.transfer_calls, 0U);

	memset(&response, 0xa5, sizeof(response));
	ret = mt6797_a72_provider_release(&handle, &response);
	KUNIT_EXPECT_EQ(test, ret, -EOPNOTSUPP);
	KUNIT_EXPECT_EQ(test, response.abi, MT6797_A72_PROVIDER_CALL_ABI);
	KUNIT_EXPECT_EQ(test, response.returned, 1U);
	KUNIT_EXPECT_EQ(test, response.origin, 1U);
	KUNIT_EXPECT_EQ(test, response.provider_mutated, 0U);
	KUNIT_EXPECT_EQ(test, response.rail_mutated, 0U);
	KUNIT_EXPECT_EQ(test, state->fake.transfer_calls, 0U);
	da9213_snapshot_unregister(&state->endpoint);
}

static int da9213_snapshot_test_init(struct kunit *test)
{
	(void)test;
	if (registered_endpoint)
		da9213_snapshot_unregister(registered_endpoint);
	return 0;
}

static void da9213_snapshot_test_exit(struct kunit *test)
{
	(void)test;
	if (registered_endpoint)
		da9213_snapshot_unregister(registered_endpoint);
}

static struct kunit_case da9213_snapshot_test_cases[] = {
	KUNIT_CASE(da9213_snapshot_success_test),
	KUNIT_CASE(da9213_snapshot_transfer_faults_test),
	KUNIT_CASE(da9213_snapshot_mismatches_test),
	KUNIT_CASE(da9213_snapshot_registry_lifetime_test),
	KUNIT_CASE(da9213_snapshot_readonly_lifecycle_test),
	{ }
};

static struct kunit_suite da9213_snapshot_test_suite = {
	.name = "da9213-legacy-provider-snapshot",
	.init = da9213_snapshot_test_init,
	.exit = da9213_snapshot_test_exit,
	.test_cases = da9213_snapshot_test_cases,
};

kunit_test_suite(da9213_snapshot_test_suite);

MODULE_LICENSE("GPL");
