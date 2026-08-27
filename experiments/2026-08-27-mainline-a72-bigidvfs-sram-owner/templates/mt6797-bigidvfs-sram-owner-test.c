// SPDX-License-Identifier: GPL-2.0-only

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/string.h>

#include "mt6797-bigidvfs-sram-internal.h"

#define MT6797_SRAM_TEST_LOG_CAPACITY 6U

enum mt6797_sram_test_action {
	MT6797_SRAM_TEST_SET = 1,
	MT6797_SRAM_TEST_DELAY,
	MT6797_SRAM_TEST_SELECTOR_FIRST,
	MT6797_SRAM_TEST_CALIBRATION_FIRST,
	MT6797_SRAM_TEST_SELECTOR_SECOND,
	MT6797_SRAM_TEST_CALIBRATION_SECOND,
};

struct mt6797_sram_test_state {
	u32 log[MT6797_SRAM_TEST_LOG_CAPACITY];
	u32 log_count;
	u32 read_count;
	u32 set_value;
	u32 delay_min;
	u32 delay_max;
	u32 selector_first;
	u32 selector_second;
	u32 calibration_first;
	u32 calibration_second;
	u32 fault_read;
	int set_error;
};

static void mt6797_sram_test_log(struct mt6797_sram_test_state *state,
				 u32 action)
{
	if (state->log_count < ARRAY_SIZE(state->log))
		state->log[state->log_count] = action;
	state->log_count++;
}

static int mt6797_sram_test_set(void *context, u32 mv_x100)
{
	struct mt6797_sram_test_state *state = context;

	mt6797_sram_test_log(state, MT6797_SRAM_TEST_SET);
	state->set_value = mv_x100;
	return state->set_error;
}

static int mt6797_sram_test_read(void *context, u32 address, u32 *value)
{
	struct mt6797_sram_test_state *state = context;

	state->read_count++;
	if (state->fault_read == state->read_count)
		return -EIO;
	if (address == MT6797_BIGIDVFS_SRAM_SELECTOR) {
		if (state->read_count == 1) {
			mt6797_sram_test_log(state,
					      MT6797_SRAM_TEST_SELECTOR_FIRST);
			*value = state->selector_first;
		} else {
			mt6797_sram_test_log(state,
					      MT6797_SRAM_TEST_SELECTOR_SECOND);
			*value = state->selector_second;
		}
		return 0;
	}
	if (address == MT6797_BIGIDVFS_SRAM_CALIBRATION) {
		if (state->read_count == 2) {
			mt6797_sram_test_log(state,
					      MT6797_SRAM_TEST_CALIBRATION_FIRST);
			*value = state->calibration_first;
		} else {
			mt6797_sram_test_log(state,
					      MT6797_SRAM_TEST_CALIBRATION_SECOND);
			*value = state->calibration_second;
		}
		return 0;
	}

	return -EINVAL;
}

static void mt6797_sram_test_delay(void *context, unsigned int min_us,
				   unsigned int max_us)
{
	struct mt6797_sram_test_state *state = context;

	mt6797_sram_test_log(state, MT6797_SRAM_TEST_DELAY);
	state->delay_min = min_us;
	state->delay_max = max_us;
}

static const struct mt6797_bigidvfs_sram_ops mt6797_sram_test_ops = {
	.set = mt6797_sram_test_set,
	.read = mt6797_sram_test_read,
	.delay = mt6797_sram_test_delay,
};

static struct mt6797_bigidvfs_sram_request mt6797_sram_test_request(void)
{
	return (struct mt6797_bigidvfs_sram_request) {
		.abi = MT6797_BIGIDVFS_SRAM_OWNER_ABI,
		.cpu = 8,
		.attempt_id = 17,
		.cookie = 29,
		.provider_held = true,
		.isolation_crossed = true,
	};
}

static void mt6797_sram_test_state_init(
	struct mt6797_sram_test_state *state)
{
	*state = (struct mt6797_sram_test_state) {
		.selector_first = MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED,
		.selector_second = MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED,
		.calibration_first = 0x7777,
		.calibration_second = 0x7777,
	};
}

static void mt6797_bigidvfs_sram_success_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_owner owner = {};
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	struct mt6797_bigidvfs_sram_result result;
	struct mt6797_sram_test_state state;
	static const u32 expected[] = {
		MT6797_SRAM_TEST_SET,
		MT6797_SRAM_TEST_DELAY,
		MT6797_SRAM_TEST_SELECTOR_FIRST,
		MT6797_SRAM_TEST_CALIBRATION_FIRST,
		MT6797_SRAM_TEST_SELECTOR_SECOND,
		MT6797_SRAM_TEST_CALIBRATION_SECOND,
	};
	unsigned int i;
	int ret;

	mt6797_sram_test_state_init(&state);
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, owner.state,
			MT6797_BIGIDVFS_SRAM_OWNER_VERIFIED);
	KUNIT_EXPECT_EQ(test, state.log_count, ARRAY_SIZE(expected));
	for (i = 0; i < ARRAY_SIZE(expected); i++)
		KUNIT_EXPECT_EQ(test, state.log[i], expected[i]);
	KUNIT_EXPECT_EQ(test, state.set_value,
			MT6797_BIGIDVFS_SRAM_TARGET_MV_X100);
	KUNIT_EXPECT_EQ(test, state.delay_min,
			MT6797_BIGIDVFS_SRAM_SETTLE_MIN_US);
	KUNIT_EXPECT_EQ(test, state.delay_max,
			MT6797_BIGIDVFS_SRAM_SETTLE_MAX_US);
	KUNIT_EXPECT_EQ(test, result.attempted_steps, 0xffU);
	KUNIT_EXPECT_EQ(test, result.completed_steps, 0xffU);
	KUNIT_EXPECT_TRUE(test, result.effect_attempted);
	KUNIT_EXPECT_TRUE(test, result.verified);
	KUNIT_EXPECT_TRUE(test, result.sealed);
	KUNIT_EXPECT_EQ(test, result.error, 0);
}

static void mt6797_bigidvfs_sram_guards_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_owner owner = {};
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	struct mt6797_bigidvfs_sram_result result;
	struct mt6797_sram_test_state state;
	int ret;

	mt6797_sram_test_state_init(&state);
	request.abi++;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	request = mt6797_sram_test_request();
	request.cpu = 9;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	request = mt6797_sram_test_request();
	request.provider_held = false;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	request = mt6797_sram_test_request();
	request.isolation_crossed = false;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	request = mt6797_sram_test_request();
	request.cpu8_online = true;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	request = mt6797_sram_test_request();
	request.cpu9_online = true;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, owner.state,
			MT6797_BIGIDVFS_SRAM_OWNER_UNUSED);
	KUNIT_EXPECT_EQ(test, state.log_count, 0U);
}

static void mt6797_bigidvfs_sram_one_shot_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_owner owner = {};
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	struct mt6797_bigidvfs_sram_result result;
	struct mt6797_sram_test_state state;
	u32 calls;
	int ret;

	mt6797_sram_test_state_init(&state);
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	calls = state.log_count;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	request.cookie++;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, state.log_count, calls);
}

static void mt6797_bigidvfs_sram_service_failure_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_owner owner = {};
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	struct mt6797_bigidvfs_sram_result result;
	struct mt6797_sram_test_state state;
	int ret;

	mt6797_sram_test_state_init(&state);
	state.set_error = -ETIMEDOUT;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, owner.state,
			MT6797_BIGIDVFS_SRAM_OWNER_FAULTED);
	KUNIT_EXPECT_EQ(test, state.log_count, 1U);
	KUNIT_EXPECT_EQ(test, result.attempted_steps,
			MT6797_BIGIDVFS_SRAM_SERVICE);
	KUNIT_EXPECT_EQ(test, result.completed_steps, 0U);
	KUNIT_EXPECT_TRUE(test, result.effect_attempted);
	KUNIT_EXPECT_TRUE(test, result.sealed);
}

static void mt6797_bigidvfs_sram_read_failures_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	unsigned int fault;

	for (fault = 1; fault <= 4; fault++) {
		struct mt6797_bigidvfs_sram_owner owner = {};
		struct mt6797_bigidvfs_sram_result result;
		struct mt6797_sram_test_state state;
		int ret;

		mt6797_sram_test_state_init(&state);
		state.fault_read = fault;
		ret = mt6797_bigidvfs_sram_owner_execute(&owner,
					&mt6797_sram_test_ops, &state,
					&request, &result);
		KUNIT_EXPECT_EQ(test, ret, -EIO);
		KUNIT_EXPECT_EQ(test, owner.state,
				MT6797_BIGIDVFS_SRAM_OWNER_FAULTED);
		KUNIT_EXPECT_EQ(test, state.read_count, fault);
		KUNIT_EXPECT_TRUE(test, result.effect_attempted);
		KUNIT_EXPECT_TRUE(test, result.sealed);
	}
}

static void mt6797_bigidvfs_sram_instability_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	struct mt6797_bigidvfs_sram_result result;
	struct mt6797_bigidvfs_sram_owner owner = {};
	struct mt6797_sram_test_state state;
	int ret;

	mt6797_sram_test_state_init(&state);
	state.selector_second ^= 1;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	memset(&owner, 0, sizeof(owner));
	mt6797_sram_test_state_init(&state);
	state.calibration_second ^= 1;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
}

static void mt6797_bigidvfs_sram_selector_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_owner owner = {};
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	struct mt6797_bigidvfs_sram_result result;
	struct mt6797_sram_test_state state;
	int ret;

	mt6797_sram_test_state_init(&state);
	state.selector_first = 0x8fa;
	state.selector_second = 0x8fa;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -ERANGE);
	KUNIT_EXPECT_FALSE(test, result.verified);
	KUNIT_EXPECT_TRUE(test, result.sealed);
}

static void mt6797_bigidvfs_sram_calibration_test(struct kunit *test)
{
	struct mt6797_bigidvfs_sram_request request =
		mt6797_sram_test_request();
	struct mt6797_bigidvfs_sram_result result;
	struct mt6797_bigidvfs_sram_owner owner = {};
	struct mt6797_sram_test_state state;
	int ret;

	mt6797_sram_test_state_init(&state);
	state.calibration_first = 0;
	state.calibration_second = 0;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -ERANGE);
	memset(&owner, 0, sizeof(owner));
	mt6797_sram_test_state_init(&state);
	state.calibration_first = 0x10001;
	state.calibration_second = 0x10001;
	ret = mt6797_bigidvfs_sram_owner_execute(&owner,
				&mt6797_sram_test_ops, &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -ERANGE);
}

static struct kunit_case mt6797_bigidvfs_sram_cases[] = {
	KUNIT_CASE(mt6797_bigidvfs_sram_success_test),
	KUNIT_CASE(mt6797_bigidvfs_sram_guards_test),
	KUNIT_CASE(mt6797_bigidvfs_sram_one_shot_test),
	KUNIT_CASE(mt6797_bigidvfs_sram_service_failure_test),
	KUNIT_CASE(mt6797_bigidvfs_sram_read_failures_test),
	KUNIT_CASE(mt6797_bigidvfs_sram_instability_test),
	KUNIT_CASE(mt6797_bigidvfs_sram_selector_test),
	KUNIT_CASE(mt6797_bigidvfs_sram_calibration_test),
	{ }
};

static struct kunit_suite mt6797_bigidvfs_sram_suite = {
	.name = "mt6797-bigidvfs-sram-owner",
	.test_cases = mt6797_bigidvfs_sram_cases,
};

kunit_test_suite(mt6797_bigidvfs_sram_suite);

MODULE_LICENSE("GPL");
