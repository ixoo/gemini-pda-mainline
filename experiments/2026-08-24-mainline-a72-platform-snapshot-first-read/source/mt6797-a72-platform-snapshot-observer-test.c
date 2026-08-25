// SPDX-License-Identifier: GPL-2.0-only
/* Injected tests for the MT6797 A72 platform-snapshot observer. */

#include <kunit/test.h>
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-platform-snapshot-observer-internal.h"

enum mt6797_a72_platform_snapshot_event {
	MT6797_PLATFORM_CHECKPOINT_0,
	MT6797_PLATFORM_SNAPSHOT,
	MT6797_PLATFORM_CHECKPOINT_1,
};

struct mt6797_a72_platform_snapshot_test_state {
	enum mt6797_a72_platform_snapshot_event events[3];
	unsigned int event_count;
	unsigned int snapshot_calls;
	bool checkpoint_result[2];
	bool snapshot_valid;
	int snapshot_ret;
};

static bool mt6797_platform_test_checkpoint(void *context,
					    unsigned int checkpoint)
{
	struct mt6797_a72_platform_snapshot_test_state *state = context;

	state->events[state->event_count++] = checkpoint ?
		MT6797_PLATFORM_CHECKPOINT_1 : MT6797_PLATFORM_CHECKPOINT_0;
	return state->checkpoint_result[checkpoint];
}

static int mt6797_platform_test_snapshot(void *context, struct device *dev,
					 struct mt6797_a72_platform_state *snapshot)
{
	struct mt6797_a72_platform_snapshot_test_state *state = context;

	state->events[state->event_count++] = MT6797_PLATFORM_SNAPSHOT;
	state->snapshot_calls++;
	snapshot->spm_pwr_status = 0x12345678;
	snapshot->valid = state->snapshot_valid;
	return state->snapshot_ret;
}

static const struct mt6797_a72_platform_snapshot_observer_ops test_ops = {
	.checkpoint = mt6797_platform_test_checkpoint,
	.snapshot = mt6797_platform_test_snapshot,
};

static void mt6797_platform_expect_zero(struct kunit *test,
					const struct mt6797_a72_platform_state *snapshot)
{
	struct mt6797_a72_platform_state zero = { };

	KUNIT_EXPECT_MEMEQ(test, snapshot, &zero, sizeof(zero));
}

static void mt6797_platform_snapshot_success_test(struct kunit *test)
{
	struct mt6797_a72_platform_snapshot_test_state state = {
		.checkpoint_result = { true, true },
		.snapshot_valid = true,
	};
	struct mt6797_a72_platform_state snapshot;
	struct device platform = { };
	int ret;

	ret = mt6797_platform_snapshot_capture(&platform, &test_ops, &state,
					       &snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, snapshot.valid);
	KUNIT_EXPECT_EQ(test, snapshot.spm_pwr_status, (u32)0x12345678);
	KUNIT_EXPECT_EQ(test, state.snapshot_calls, 1U);
	KUNIT_ASSERT_EQ(test, state.event_count, 3U);
	KUNIT_EXPECT_EQ(test, state.events[0], MT6797_PLATFORM_CHECKPOINT_0);
	KUNIT_EXPECT_EQ(test, state.events[1], MT6797_PLATFORM_SNAPSHOT);
	KUNIT_EXPECT_EQ(test, state.events[2], MT6797_PLATFORM_CHECKPOINT_1);
}

static void mt6797_platform_snapshot_before_failure_test(struct kunit *test)
{
	struct mt6797_a72_platform_snapshot_test_state state = { };
	struct mt6797_a72_platform_state snapshot = {
		.valid = true,
	};
	struct device platform = { };
	int ret;

	ret = mt6797_platform_snapshot_capture(&platform, &test_ops, &state,
					       &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.snapshot_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.event_count, 1U);
	mt6797_platform_expect_zero(test, &snapshot);
}

static void mt6797_platform_snapshot_read_failure_test(struct kunit *test)
{
	struct mt6797_a72_platform_snapshot_test_state state = {
		.checkpoint_result = { true, true },
		.snapshot_valid = true,
		.snapshot_ret = -EAGAIN,
	};
	struct mt6797_a72_platform_state snapshot;
	struct device platform = { };
	int ret;

	ret = mt6797_platform_snapshot_capture(&platform, &test_ops, &state,
					       &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	KUNIT_EXPECT_EQ(test, state.snapshot_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.event_count, 2U);
	mt6797_platform_expect_zero(test, &snapshot);

	state.snapshot_ret = 0;
	state.snapshot_valid = false;
	state.event_count = 0;
	state.snapshot_calls = 0;
	ret = mt6797_platform_snapshot_capture(&platform, &test_ops, &state,
					       &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENODATA);
	KUNIT_EXPECT_EQ(test, state.snapshot_calls, 1U);
	mt6797_platform_expect_zero(test, &snapshot);
}

static void mt6797_platform_snapshot_after_failure_test(struct kunit *test)
{
	struct mt6797_a72_platform_snapshot_test_state state = {
		.checkpoint_result = { true, false },
		.snapshot_valid = true,
	};
	struct mt6797_a72_platform_state snapshot;
	struct device platform = { };
	int ret;

	ret = mt6797_platform_snapshot_capture(&platform, &test_ops, &state,
					       &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.snapshot_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.event_count, 3U);
	mt6797_platform_expect_zero(test, &snapshot);
}

static struct kunit_case mt6797_a72_platform_snapshot_cases[] = {
	KUNIT_CASE(mt6797_platform_snapshot_success_test),
	KUNIT_CASE(mt6797_platform_snapshot_before_failure_test),
	KUNIT_CASE(mt6797_platform_snapshot_read_failure_test),
	KUNIT_CASE(mt6797_platform_snapshot_after_failure_test),
	{ }
};

static struct kunit_suite mt6797_a72_platform_snapshot_suite = {
	.name = "mt6797-a72-platform-snapshot",
	.test_cases = mt6797_a72_platform_snapshot_cases,
};

kunit_test_suite(mt6797_a72_platform_snapshot_suite);

MODULE_LICENSE("GPL");
