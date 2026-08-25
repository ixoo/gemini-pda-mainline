// SPDX-License-Identifier: GPL-2.0-only
/* Injected tests for the MT6797 A72 platform/provider observer. */

#include <kunit/test.h>
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-platform-provider-snapshot-observer-internal.h"

enum mt6797_a72_platform_provider_event {
	MT6797_PLATFORM_PROVIDER_PLATFORM,
	MT6797_PLATFORM_PROVIDER_BEFORE,
	MT6797_PLATFORM_PROVIDER_PROVIDER,
	MT6797_PLATFORM_PROVIDER_AFTER,
};

struct mt6797_a72_platform_provider_test_state {
	enum mt6797_a72_platform_provider_event events[4];
	unsigned int event_count;
	unsigned int platform_calls;
	unsigned int provider_calls;
	bool checkpoint_result[2];
	bool platform_valid;
	bool provider_valid;
	int platform_ret;
	int provider_ret;
};

static int
mt6797_platform_provider_test_platform(void *context, struct device *dev,
				       struct mt6797_a72_platform_state *snapshot)
{
	struct mt6797_a72_platform_provider_test_state *state = context;

	state->events[state->event_count++] = MT6797_PLATFORM_PROVIDER_PLATFORM;
	state->platform_calls++;
	snapshot->spm_pwr_status = 0x12345678;
	snapshot->valid = state->platform_valid;
	return state->platform_ret;
}

static bool mt6797_platform_provider_test_checkpoint(void *context,
						       unsigned int checkpoint)
{
	struct mt6797_a72_platform_provider_test_state *state = context;

	state->events[state->event_count++] = checkpoint ?
		MT6797_PLATFORM_PROVIDER_AFTER : MT6797_PLATFORM_PROVIDER_BEFORE;
	return state->checkpoint_result[checkpoint];
}

static int
mt6797_platform_provider_test_provider(void *context,
				       struct mt6797_a72_provider_snapshot *snapshot)
{
	struct mt6797_a72_platform_provider_test_state *state = context;

	state->events[state->event_count++] = MT6797_PLATFORM_PROVIDER_PROVIDER;
	state->provider_calls++;
	snapshot->abi = MT6797_A72_PROVIDER_STATE_ABI;
	snapshot->valid = state->provider_valid;
	snapshot->control_a = 0x7b;
	return state->provider_ret;
}

static const struct mt6797_a72_platform_provider_observer_ops test_ops = {
	.platform = mt6797_platform_provider_test_platform,
	.checkpoint = mt6797_platform_provider_test_checkpoint,
	.provider = mt6797_platform_provider_test_provider,
};

static void
mt6797_platform_provider_expect_zero(struct kunit *test,
	const struct mt6797_a72_platform_provider_snapshot *snapshot)
{
	struct mt6797_a72_platform_provider_snapshot zero = { };

	KUNIT_EXPECT_MEMEQ(test, snapshot, &zero, sizeof(zero));
}

static struct mt6797_a72_platform_provider_test_state
mt6797_platform_provider_success_state(void)
{
	return (struct mt6797_a72_platform_provider_test_state) {
		.checkpoint_result = { true, true },
		.platform_valid = true,
		.provider_valid = true,
	};
}

static void mt6797_platform_provider_success_test(struct kunit *test)
{
	struct mt6797_a72_platform_provider_test_state state =
		mt6797_platform_provider_success_state();
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device platform = { };
	int ret;

	ret = mt6797_platform_provider_snapshot_capture(&platform, &test_ops,
						       &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, snapshot.valid);
	KUNIT_EXPECT_TRUE(test, snapshot.platform.valid);
	KUNIT_EXPECT_EQ(test, snapshot.platform.spm_pwr_status,
			(u32)0x12345678);
	KUNIT_EXPECT_TRUE(test, snapshot.provider.valid);
	KUNIT_EXPECT_EQ(test, snapshot.provider.control_a, (u32)0x7b);
	KUNIT_EXPECT_EQ(test, state.platform_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 1U);
	KUNIT_ASSERT_EQ(test, state.event_count, 4U);
	KUNIT_EXPECT_EQ(test, state.events[0],
			MT6797_PLATFORM_PROVIDER_PLATFORM);
	KUNIT_EXPECT_EQ(test, state.events[1], MT6797_PLATFORM_PROVIDER_BEFORE);
	KUNIT_EXPECT_EQ(test, state.events[2],
			MT6797_PLATFORM_PROVIDER_PROVIDER);
	KUNIT_EXPECT_EQ(test, state.events[3], MT6797_PLATFORM_PROVIDER_AFTER);
}

static void mt6797_platform_provider_platform_error_test(struct kunit *test)
{
	struct mt6797_a72_platform_provider_test_state state =
		mt6797_platform_provider_success_state();
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device platform = { };
	int ret;

	state.platform_ret = -EAGAIN;
	ret = mt6797_platform_provider_snapshot_capture(&platform, &test_ops,
						       &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	KUNIT_EXPECT_EQ(test, state.platform_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.event_count, 1U);
	mt6797_platform_provider_expect_zero(test, &snapshot);
}

static void mt6797_platform_provider_platform_invalid_test(struct kunit *test)
{
	struct mt6797_a72_platform_provider_test_state state =
		mt6797_platform_provider_success_state();
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device platform = { };
	int ret;

	state.platform_valid = false;
	ret = mt6797_platform_provider_snapshot_capture(&platform, &test_ops,
						       &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENODATA);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.event_count, 1U);
	mt6797_platform_provider_expect_zero(test, &snapshot);
}

static void mt6797_platform_provider_before_failure_test(struct kunit *test)
{
	struct mt6797_a72_platform_provider_test_state state =
		mt6797_platform_provider_success_state();
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device platform = { };
	int ret;

	state.checkpoint_result[0] = false;
	ret = mt6797_platform_provider_snapshot_capture(&platform, &test_ops,
						       &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 0U);
	KUNIT_ASSERT_EQ(test, state.event_count, 2U);
	KUNIT_EXPECT_EQ(test, state.events[1], MT6797_PLATFORM_PROVIDER_BEFORE);
	mt6797_platform_provider_expect_zero(test, &snapshot);
}

static void mt6797_platform_provider_provider_failure_test(struct kunit *test)
{
	struct mt6797_a72_platform_provider_test_state state =
		mt6797_platform_provider_success_state();
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device platform = { };
	int ret;

	state.provider_ret = -EIO;
	ret = mt6797_platform_provider_snapshot_capture(&platform, &test_ops,
						       &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.event_count, 3U);
	mt6797_platform_provider_expect_zero(test, &snapshot);

	state = mt6797_platform_provider_success_state();
	state.provider_valid = false;
	ret = mt6797_platform_provider_snapshot_capture(&platform, &test_ops,
						       &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENODATA);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 1U);
	mt6797_platform_provider_expect_zero(test, &snapshot);
}

static void mt6797_platform_provider_after_failure_test(struct kunit *test)
{
	struct mt6797_a72_platform_provider_test_state state =
		mt6797_platform_provider_success_state();
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device platform = { };
	int ret;

	state.checkpoint_result[1] = false;
	ret = mt6797_platform_provider_snapshot_capture(&platform, &test_ops,
						       &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.event_count, 4U);
	mt6797_platform_provider_expect_zero(test, &snapshot);
}

static struct kunit_case mt6797_a72_platform_provider_cases[] = {
	KUNIT_CASE(mt6797_platform_provider_success_test),
	KUNIT_CASE(mt6797_platform_provider_platform_error_test),
	KUNIT_CASE(mt6797_platform_provider_platform_invalid_test),
	KUNIT_CASE(mt6797_platform_provider_before_failure_test),
	KUNIT_CASE(mt6797_platform_provider_provider_failure_test),
	KUNIT_CASE(mt6797_platform_provider_after_failure_test),
	{ }
};

static struct kunit_suite mt6797_a72_platform_provider_suite = {
	.name = "mt6797-a72-platform-provider-snapshot",
	.test_cases = mt6797_a72_platform_provider_cases,
};

kunit_test_suite(mt6797_a72_platform_provider_suite);

MODULE_LICENSE("GPL");
