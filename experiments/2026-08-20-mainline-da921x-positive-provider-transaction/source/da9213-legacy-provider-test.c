// SPDX-License-Identifier: GPL-2.0-only
/* Hardware-free coverage for the positive DA921x provider transaction. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/i2c.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/string.h>

#include "da9213-legacy-provider-contract.h"

#define DA9213_PROVIDER_TEST_ADDRESS	0x2a
#define DA9213_PROVIDER_TEST_RETRIES	3

struct da9213_provider_test_fake {
	struct i2c_adapter adapter;
	u8 registers[256];
	unsigned int lock_calls;
	unsigned int unlock_calls;
	unsigned int operation_calls;
	unsigned int total_calls;
	unsigned int delay_calls;
	unsigned int fail_ordinal;
	unsigned int short_ordinal;
	unsigned int mismatch_ordinal;
	unsigned int write_count;
	unsigned long delay_minimum;
	unsigned long delay_maximum;
	u8 write_registers[2];
	u8 write_values[2];
	bool locked;
	bool transfer_unlocked;
	bool delay_locked;
	bool retry_nonzero;
};

static struct da9213_provider_test_fake *active_fake;

static void
da9213_provider_test_lock(struct i2c_adapter *adapter, unsigned int flags)
{
	struct da9213_provider_test_fake *fake = active_fake;

	(void)adapter;
	(void)flags;
	fake->lock_calls++;
	fake->locked = true;
}

static int
da9213_provider_test_trylock(struct i2c_adapter *adapter, unsigned int flags)
{
	(void)adapter;
	(void)flags;
	return 0;
}

static void
da9213_provider_test_unlock(struct i2c_adapter *adapter, unsigned int flags)
{
	struct da9213_provider_test_fake *fake = active_fake;

	(void)adapter;
	(void)flags;
	fake->unlock_calls++;
	fake->locked = false;
}

static const struct i2c_lock_operations da9213_provider_test_lock_ops = {
	.lock_bus = da9213_provider_test_lock,
	.trylock_bus = da9213_provider_test_trylock,
	.unlock_bus = da9213_provider_test_unlock,
};

static int
da9213_provider_test_transfer(struct i2c_adapter *adapter,
	struct i2c_msg *messages, int count)
{
	struct da9213_provider_test_fake *fake = active_fake;
	u8 reg;

	if (!fake || adapter != &fake->adapter)
		return -EINVAL;
	fake->operation_calls++;
	fake->total_calls++;
	if (!fake->locked)
		fake->transfer_unlocked = true;
	if (adapter->retries)
		fake->retry_nonzero = true;
	if (fake->fail_ordinal == fake->operation_calls)
		return -EIO;
	if (fake->short_ordinal == fake->operation_calls)
		return count == 2 ? 1 : 0;

	if (count == 2 && messages[0].addr == DA9213_PROVIDER_TEST_ADDRESS &&
	    messages[1].addr == DA9213_PROVIDER_TEST_ADDRESS &&
	    !messages[0].flags && messages[1].flags == I2C_M_RD &&
	    messages[0].len == 1 && messages[1].len == 1 &&
	    messages[0].buf && messages[1].buf) {
		reg = messages[0].buf[0];
		messages[1].buf[0] = fake->registers[reg];
		if (fake->mismatch_ordinal == fake->operation_calls)
			messages[1].buf[0] ^= 0x01;
		return 2;
	}

	if (count == 1 && messages[0].addr == DA9213_PROVIDER_TEST_ADDRESS &&
	    !messages[0].flags && messages[0].len == 2 && messages[0].buf) {
		reg = messages[0].buf[0];
		if (fake->write_count < ARRAY_SIZE(fake->write_registers)) {
			fake->write_registers[fake->write_count] = reg;
			fake->write_values[fake->write_count] = messages[0].buf[1];
		}
		fake->write_count++;
		fake->registers[reg] = messages[0].buf[1];
		return 1;
	}

	return -EPROTO;
}

static void
da9213_provider_test_delay(unsigned long minimum, unsigned long maximum)
{
	struct da9213_provider_test_fake *fake = active_fake;

	fake->delay_calls++;
	fake->delay_minimum = minimum;
	fake->delay_maximum = maximum;
	if (fake->locked)
		fake->delay_locked = true;
}

static const struct da9213_legacy_provider_transport_ops
da9213_provider_test_ops = {
	.transfer = da9213_provider_test_transfer,
	.delay = da9213_provider_test_delay,
};

static void
da9213_provider_test_init(struct da9213_provider_test_fake *fake,
	struct da9213_legacy_provider_result *result)
{
	memset(fake, 0, sizeof(*fake));
	memset(result, 0, sizeof(*result));
	fake->adapter.lock_ops = &da9213_provider_test_lock_ops;
	fake->adapter.retries = DA9213_PROVIDER_TEST_RETRIES;
	fake->registers[0x56] = 0x7b;
	fake->registers[0x51] = 0xc1;
	fake->registers[0x5e] = 0x00;
	fake->registers[0xd9] = 0x46;
	fake->registers[0xda] = 0x46;
	active_fake = fake;
}

static struct mt6797_a72_provider_request da9213_provider_test_request(void)
{
	return (struct mt6797_a72_provider_request) {
		.abi = MT6797_A72_PROVIDER_CALL_ABI,
		.operation = MT6797_A72_PROVIDER_OPERATION_CPU8_UP,
		.settle_us = MT6797_A72_PROVIDER_CALL_SETTLE_US,
		.da921x_page = MT6797_A72_PROVIDER_CALL_DA921X_PAGE,
		.buckb_vsel = MT6797_A72_PROVIDER_CALL_BUCKB_VSEL,
		.transaction_generation = 17,
		.transaction_cookie = 29,
	};
}

static int
da9213_provider_test_acquire(struct da9213_provider_test_fake *fake,
	struct da9213_legacy_provider_result *result,
	struct mt6797_a72_provider_response *response)
{
	struct mt6797_a72_provider_request request =
		da9213_provider_test_request();

	return da9213_legacy_provider_transaction_acquire(&fake->adapter,
		DA9213_PROVIDER_TEST_ADDRESS,
		&da9213_provider_test_ops, &request, result, response);
}

static void da9213_provider_lifecycle_success(struct kunit *test)
{
	struct da9213_provider_test_fake fake;
	struct da9213_legacy_provider_result result;
	struct mt6797_a72_provider_response acquire_response;
	struct mt6797_a72_provider_response release_response;
	int ret;

	da9213_provider_test_init(&fake, &result);
	ret = da9213_provider_test_acquire(&fake, &result, &acquire_response);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_PROVIDER_HELD);
	KUNIT_EXPECT_EQ(test, result.operation_transfers, 11U);
	KUNIT_EXPECT_EQ(test, result.total_transfers, 11U);
	KUNIT_EXPECT_EQ(test, result.write_attempts, 1U);
	KUNIT_EXPECT_EQ(test, result.inverse_write_attempts, 0U);
	KUNIT_EXPECT_EQ(test, fake.registers[0x5e], (u8)0x01);
	KUNIT_EXPECT_EQ(test, acquire_response.held_handle.generation, 17ULL);
	KUNIT_EXPECT_EQ(test, acquire_response.held_handle.cookie, 29ULL);
	KUNIT_EXPECT_EQ(test, acquire_response.buckb_enabled, 1U);

	fake.operation_calls = 0;
	ret = da9213_legacy_provider_transaction_release(&fake.adapter,
		DA9213_PROVIDER_TEST_ADDRESS,
		&da9213_provider_test_ops, &acquire_response.held_handle,
		&result, &release_response);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_PROVIDER_RELEASED);
	KUNIT_EXPECT_EQ(test, result.operation_transfers, 11U);
	KUNIT_EXPECT_EQ(test, result.total_transfers, 22U);
	KUNIT_EXPECT_EQ(test, result.inverse_write_attempts, 1U);
	KUNIT_EXPECT_EQ(test, fake.registers[0x5e], (u8)0x00);
	KUNIT_EXPECT_EQ(test, release_response.buckb_enabled, 0U);
	KUNIT_EXPECT_EQ(test, fake.write_count, 2U);
	KUNIT_EXPECT_EQ(test, fake.write_registers[0], (u8)0x5e);
	KUNIT_EXPECT_EQ(test, fake.write_values[0], (u8)0x01);
	KUNIT_EXPECT_EQ(test, fake.write_registers[1], (u8)0x5e);
	KUNIT_EXPECT_EQ(test, fake.write_values[1], (u8)0x00);
	KUNIT_EXPECT_EQ(test, fake.lock_calls, 2U);
	KUNIT_EXPECT_EQ(test, fake.unlock_calls, 2U);
	KUNIT_EXPECT_EQ(test, fake.adapter.retries,
			DA9213_PROVIDER_TEST_RETRIES);
	KUNIT_EXPECT_FALSE(test, fake.transfer_unlocked);
	KUNIT_EXPECT_FALSE(test, fake.retry_nonzero);
	KUNIT_EXPECT_TRUE(test, fake.delay_locked);
	KUNIT_EXPECT_EQ(test, fake.delay_minimum, 1000UL);
	KUNIT_EXPECT_EQ(test, fake.delay_maximum, 1100UL);
}

static void da9213_provider_admission_one_shot(struct kunit *test)
{
	struct da9213_provider_test_fake fake;
	struct da9213_legacy_provider_result result;
	struct mt6797_a72_provider_request request =
		da9213_provider_test_request();
	struct mt6797_a72_provider_response response;
	struct mt6797_a72_provider_handle stale = { .generation = 17, .cookie = 30 };
	unsigned int calls;
	int ret;

	da9213_provider_test_init(&fake, &result);
	request.operation = MT6797_A72_PROVIDER_OPERATION_CPU8_UP + 1;
	ret = da9213_legacy_provider_transaction_acquire(&fake.adapter,
		DA9213_PROVIDER_TEST_ADDRESS,
		&da9213_provider_test_ops, &request, &result, &response);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	KUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_PROVIDER_IDLE);
	KUNIT_EXPECT_EQ(test, fake.total_calls, 0U);

	ret = da9213_provider_test_acquire(&fake, &result, &response);
	KUNIT_ASSERT_EQ(test, ret, 0);
	calls = fake.total_calls;
	ret = da9213_provider_test_acquire(&fake, &result, &response);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, fake.total_calls, calls);
	ret = da9213_legacy_provider_transaction_release(&fake.adapter,
		DA9213_PROVIDER_TEST_ADDRESS,
		&da9213_provider_test_ops, &stale, &result, &response);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_PROVIDER_HELD);
	KUNIT_EXPECT_EQ(test, fake.total_calls, calls);

	fake.operation_calls = 0;
	ret = da9213_legacy_provider_transaction_release(&fake.adapter,
		DA9213_PROVIDER_TEST_ADDRESS,
		&da9213_provider_test_ops, &result.held_handle, &result,
		&response);
	KUNIT_ASSERT_EQ(test, ret, 0);
	calls = fake.total_calls;
	ret = da9213_legacy_provider_transaction_release(&fake.adapter,
		DA9213_PROVIDER_TEST_ADDRESS,
		&da9213_provider_test_ops, &result.held_handle, &result,
		&response);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	ret = da9213_provider_test_acquire(&fake, &result, &response);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, fake.total_calls, calls);
}

static void da9213_provider_acquire_failures(struct kunit *test)
{
	unsigned int mode;
	unsigned int ordinal;

	for (mode = 0; mode < 2; mode++) {
		for (ordinal = 1; ordinal <= DA9213_LEGACY_PROVIDER_ACTIONS;
		     ordinal++) {
			struct da9213_provider_test_fake fake;
			struct da9213_legacy_provider_result result;
			struct mt6797_a72_provider_response response;
			enum da9213_legacy_provider_state expected;
			int ret;

			da9213_provider_test_init(&fake, &result);
			if (mode)
				fake.short_ordinal = ordinal;
			else
				fake.fail_ordinal = ordinal;
			expected = ordinal <= 5 ?
				DA9213_LEGACY_PROVIDER_FAILED_NO_MUTATION :
				DA9213_LEGACY_PROVIDER_FAULT_RETAINED;
			ret = da9213_provider_test_acquire(&fake, &result, &response);
			KUNIT_EXPECT_LT(test, ret, 0);
			KUNIT_EXPECT_EQ(test, result.state, expected);
			KUNIT_EXPECT_EQ(test, result.write_attempts,
					ordinal >= 6 ? 1U : 0U);
			KUNIT_EXPECT_EQ(test, result.inverse_write_attempts, 0U);
			KUNIT_EXPECT_EQ(test, fake.operation_calls, ordinal);
			KUNIT_EXPECT_EQ(test, fake.lock_calls, 1U);
			KUNIT_EXPECT_EQ(test, fake.unlock_calls, 1U);
			KUNIT_EXPECT_EQ(test, fake.adapter.retries,
					DA9213_PROVIDER_TEST_RETRIES);
		}
	}
}

static void da9213_provider_acquire_mismatches(struct kunit *test)
{
	static const unsigned int mismatch_ordinals[] = {
		1, 3, 4, 5, 7, 9, 10, 11,
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(mismatch_ordinals); i++) {
		struct da9213_provider_test_fake fake;
		struct da9213_legacy_provider_result result;
		struct mt6797_a72_provider_response response;
		enum da9213_legacy_provider_state expected;
		unsigned int ordinal = mismatch_ordinals[i];
		int ret;

		da9213_provider_test_init(&fake, &result);
		fake.mismatch_ordinal = ordinal;
		expected = ordinal <= 5 ?
			DA9213_LEGACY_PROVIDER_FAILED_NO_MUTATION :
			DA9213_LEGACY_PROVIDER_FAULT_RETAINED;
		ret = da9213_provider_test_acquire(&fake, &result, &response);
		KUNIT_EXPECT_EQ_MSG(test, ret, -ERANGE, "ordinal=%u", ordinal);
		KUNIT_EXPECT_EQ(test, result.state, expected);
		KUNIT_EXPECT_EQ(test, result.inverse_write_attempts, 0U);
	}

	{
		struct da9213_provider_test_fake fake;
		struct da9213_legacy_provider_result result;
		struct mt6797_a72_provider_response response;
		int ret;

		da9213_provider_test_init(&fake, &result);
		fake.mismatch_ordinal = 2;
		ret = da9213_provider_test_acquire(&fake, &result, &response);
		KUNIT_EXPECT_EQ(test, ret, 0);
		KUNIT_EXPECT_NE(test, result.prestate.status_b,
				result.held_state.status_b);
	}
}

static void da9213_provider_release_failures(struct kunit *test)
{
	unsigned int mode;
	unsigned int ordinal;

	for (mode = 0; mode < 2; mode++) {
		for (ordinal = 1; ordinal <= DA9213_LEGACY_PROVIDER_ACTIONS;
		     ordinal++) {
			struct da9213_provider_test_fake fake;
			struct da9213_legacy_provider_result result;
			struct mt6797_a72_provider_response response;
			int ret;

			da9213_provider_test_init(&fake, &result);
			ret = da9213_provider_test_acquire(&fake, &result, &response);
			KUNIT_ASSERT_EQ(test, ret, 0);
			fake.operation_calls = 0;
			if (mode)
				fake.short_ordinal = ordinal;
			else
				fake.fail_ordinal = ordinal;
			ret = da9213_legacy_provider_transaction_release(&fake.adapter,
				DA9213_PROVIDER_TEST_ADDRESS,
				&da9213_provider_test_ops, &result.held_handle,
				&result, &response);
			KUNIT_EXPECT_LT(test, ret, 0);
			KUNIT_EXPECT_EQ(test, result.state,
					DA9213_LEGACY_PROVIDER_FAULT_RETAINED);
			KUNIT_EXPECT_EQ(test, result.inverse_write_attempts,
					ordinal >= 6 ? 1U : 0U);
			KUNIT_EXPECT_EQ(test, fake.operation_calls, ordinal);
			KUNIT_EXPECT_EQ(test, fake.lock_calls, 2U);
			KUNIT_EXPECT_EQ(test, fake.unlock_calls, 2U);
			KUNIT_EXPECT_EQ(test, fake.adapter.retries,
					DA9213_PROVIDER_TEST_RETRIES);
		}
	}
}

static void da9213_provider_release_mismatches(struct kunit *test)
{
	static const unsigned int mismatch_ordinals[] = {
		1, 3, 4, 5, 7, 9, 10, 11,
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(mismatch_ordinals); i++) {
		struct da9213_provider_test_fake fake;
		struct da9213_legacy_provider_result result;
		struct mt6797_a72_provider_response response;
		unsigned int ordinal = mismatch_ordinals[i];
		int ret;

		da9213_provider_test_init(&fake, &result);
		ret = da9213_provider_test_acquire(&fake, &result, &response);
		KUNIT_ASSERT_EQ(test, ret, 0);
		fake.operation_calls = 0;
		fake.mismatch_ordinal = ordinal;
		ret = da9213_legacy_provider_transaction_release(&fake.adapter,
			DA9213_PROVIDER_TEST_ADDRESS,
			&da9213_provider_test_ops, &result.held_handle,
			&result, &response);
		KUNIT_EXPECT_EQ_MSG(test, ret, -ERANGE, "ordinal=%u", ordinal);
		KUNIT_EXPECT_EQ(test, result.state,
				DA9213_LEGACY_PROVIDER_FAULT_RETAINED);
		KUNIT_EXPECT_EQ(test, result.inverse_write_attempts,
				ordinal >= 6 ? 1U : 0U);
	}

	{
		struct da9213_provider_test_fake fake;
		struct da9213_legacy_provider_result result;
		struct mt6797_a72_provider_response response;
		int ret;

		da9213_provider_test_init(&fake, &result);
		ret = da9213_provider_test_acquire(&fake, &result, &response);
		KUNIT_ASSERT_EQ(test, ret, 0);
		fake.operation_calls = 0;
		fake.mismatch_ordinal = 2;
		ret = da9213_legacy_provider_transaction_release(&fake.adapter,
			DA9213_PROVIDER_TEST_ADDRESS,
			&da9213_provider_test_ops, &result.held_handle,
			&result, &response);
		KUNIT_EXPECT_EQ(test, ret, 0);
		KUNIT_EXPECT_NE(test, result.release_prestate.status_b,
				result.final_state.status_b);
	}
}

static struct kunit_case da9213_provider_test_cases[] = {
	KUNIT_CASE(da9213_provider_lifecycle_success),
	KUNIT_CASE(da9213_provider_admission_one_shot),
	KUNIT_CASE(da9213_provider_acquire_failures),
	KUNIT_CASE(da9213_provider_acquire_mismatches),
	KUNIT_CASE(da9213_provider_release_failures),
	KUNIT_CASE(da9213_provider_release_mismatches),
	{ }
};

static struct kunit_suite da9213_provider_test_suite = {
	.name = "da9213-legacy-positive-provider",
	.test_cases = da9213_provider_test_cases,
};

kunit_test_suite(da9213_provider_test_suite);

MODULE_LICENSE("GPL");
