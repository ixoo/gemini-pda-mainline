// SPDX-License-Identifier: GPL-2.0-only
/* Injected tests for the MT6797 A72 platform/provider/clock observer. */

#include <kunit/test.h>
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-platform-provider-clock-observer-internal.h"

enum mt6797_a72_ppc_event {
	MT6797_A72_PPC_PLATFORM,
	MT6797_A72_PPC_PROVIDER,
	MT6797_A72_PPC_BEFORE_CLOCK,
	MT6797_A72_PPC_CLOCK,
	MT6797_A72_PPC_AFTER_CLOCK,
};

struct mt6797_a72_ppc_test_state {
	enum mt6797_a72_ppc_event events[5];
	unsigned int event_count;
	unsigned int platform_calls;
	unsigned int provider_calls;
	unsigned int clock_calls;
	bool checkpoint_result[2];
	bool platform_valid;
	bool provider_valid;
	u32 clock_abi;
	u64 clock_generation;
	int platform_ret;
	int provider_ret;
	int clock_ret;
};

static int mt6797_a72_ppc_test_platform(
	void *context, struct device *dev,
	struct mt6797_a72_platform_state *snapshot)
{
	struct mt6797_a72_ppc_test_state *state = context;

	state->events[state->event_count++] = MT6797_A72_PPC_PLATFORM;
	state->platform_calls++;
	snapshot->spm_pwr_status = 0x12345678;
	snapshot->valid = state->platform_valid;
	return state->platform_ret;
}

static int mt6797_a72_ppc_test_provider(
	void *context, struct mt6797_a72_provider_snapshot *snapshot)
{
	struct mt6797_a72_ppc_test_state *state = context;

	state->events[state->event_count++] = MT6797_A72_PPC_PROVIDER;
	state->provider_calls++;
	snapshot->abi = MT6797_A72_PROVIDER_STATE_ABI;
	snapshot->valid = state->provider_valid;
	snapshot->control_a = 0x7b;
	return state->provider_ret;
}

static bool mt6797_a72_ppc_test_checkpoint(
	void *context, unsigned int checkpoint)
{
	struct mt6797_a72_ppc_test_state *state = context;

	state->events[state->event_count++] = checkpoint ?
		MT6797_A72_PPC_AFTER_CLOCK : MT6797_A72_PPC_BEFORE_CLOCK;
	return state->checkpoint_result[checkpoint];
}

static int mt6797_a72_ppc_test_clock(
	void *context, struct device *dev,
	struct mt6797_dvfsp_clock_readback *snapshot)
{
	struct mt6797_a72_ppc_test_state *state = context;

	state->events[state->event_count++] = MT6797_A72_PPC_CLOCK;
	state->clock_calls++;
	snapshot->abi = state->clock_abi;
	snapshot->sample_generation = state->clock_generation;
	snapshot->armplldiv_muxsel = 0x54;
	return state->clock_ret;
}

static const struct mt6797_a72_platform_provider_clock_ops test_ops = {
	.platform = mt6797_a72_ppc_test_platform,
	.provider = mt6797_a72_ppc_test_provider,
	.checkpoint = mt6797_a72_ppc_test_checkpoint,
	.clock = mt6797_a72_ppc_test_clock,
};

static struct mt6797_a72_ppc_test_state mt6797_a72_ppc_success_state(void)
{
	return (struct mt6797_a72_ppc_test_state) {
		.checkpoint_result = { true, true },
		.platform_valid = true,
		.provider_valid = true,
		.clock_abi = MT6797_DVFSP_CLOCK_BACKEND_ABI,
		.clock_generation = 1,
	};
}

static void mt6797_a72_ppc_expect_zero(
	struct kunit *test,
	const struct mt6797_a72_platform_provider_clock_snapshot *snapshot)
{
	struct mt6797_a72_platform_provider_clock_snapshot zero = { };

	KUNIT_EXPECT_MEMEQ(test, snapshot, &zero, sizeof(zero));
}

static int mt6797_a72_ppc_run(
	struct mt6797_a72_ppc_test_state *state,
	struct mt6797_a72_platform_provider_clock_snapshot *snapshot)
{
	struct device platform = { };
	struct device provider = { };
	struct device clock = { };

	return mt6797_a72_ppc_capture(&platform, &provider, &clock, &test_ops,
				       state, snapshot);
}

static void mt6797_a72_ppc_success_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	int ret;

	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, snapshot.valid);
	KUNIT_EXPECT_TRUE(test, snapshot.clock_returned);
	KUNIT_EXPECT_TRUE(test, snapshot.after_checkpoint);
	KUNIT_EXPECT_EQ(test, snapshot.clock_ret, 0);
	KUNIT_EXPECT_EQ(test, snapshot.clock.abi,
			(u32)MT6797_DVFSP_CLOCK_BACKEND_ABI);
	KUNIT_EXPECT_EQ(test, snapshot.clock.sample_generation, (u64)1);
	KUNIT_EXPECT_EQ(test, state.platform_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.clock_calls, 1U);
	KUNIT_ASSERT_EQ(test, state.event_count, 5U);
	KUNIT_EXPECT_EQ(test, state.events[0], MT6797_A72_PPC_PLATFORM);
	KUNIT_EXPECT_EQ(test, state.events[1], MT6797_A72_PPC_PROVIDER);
	KUNIT_EXPECT_EQ(test, state.events[2], MT6797_A72_PPC_BEFORE_CLOCK);
	KUNIT_EXPECT_EQ(test, state.events[3], MT6797_A72_PPC_CLOCK);
	KUNIT_EXPECT_EQ(test, state.events[4], MT6797_A72_PPC_AFTER_CLOCK);
}

static void mt6797_a72_ppc_not_ready_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	struct device device = { };
	int ret;

	ret = mt6797_a72_ppc_capture(&device, &device, NULL, &test_ops,
				      &state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EPROBE_DEFER);
	KUNIT_EXPECT_EQ(test, state.event_count, 0U);
	mt6797_a72_ppc_expect_zero(test, &snapshot);
}

static void mt6797_a72_ppc_platform_failure_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	int ret;

	state.platform_ret = -EAGAIN;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.clock_calls, 0U);
	mt6797_a72_ppc_expect_zero(test, &snapshot);

	state = mt6797_a72_ppc_success_state();
	state.platform_valid = false;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENODATA);
	mt6797_a72_ppc_expect_zero(test, &snapshot);
}

static void mt6797_a72_ppc_provider_failure_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	int ret;

	state.provider_ret = -EIO;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.clock_calls, 0U);
	mt6797_a72_ppc_expect_zero(test, &snapshot);

	state = mt6797_a72_ppc_success_state();
	state.provider_valid = false;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENODATA);
	mt6797_a72_ppc_expect_zero(test, &snapshot);
}

static void mt6797_a72_ppc_before_failure_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	int ret;

	state.checkpoint_result[0] = false;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.clock_calls, 0U);
	KUNIT_ASSERT_EQ(test, state.event_count, 3U);
	KUNIT_EXPECT_EQ(test, state.events[2], MT6797_A72_PPC_BEFORE_CLOCK);
	mt6797_a72_ppc_expect_zero(test, &snapshot);
}

static void mt6797_a72_ppc_clock_error_terminal_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	int ret;

	state.clock_ret = -ETIMEDOUT;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
	KUNIT_EXPECT_TRUE(test, snapshot.clock_returned);
	KUNIT_EXPECT_TRUE(test, snapshot.after_checkpoint);
	KUNIT_EXPECT_EQ(test, snapshot.clock_ret, -ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, state.clock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.event_count, 5U);
}

static void mt6797_a72_ppc_after_failure_terminal_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	int ret;

	state.checkpoint_result[1] = false;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
	KUNIT_EXPECT_TRUE(test, snapshot.clock_returned);
	KUNIT_EXPECT_FALSE(test, snapshot.after_checkpoint);
	KUNIT_EXPECT_EQ(test, state.clock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.event_count, 5U);
}

static void mt6797_a72_ppc_clock_identity_terminal_test(struct kunit *test)
{
	struct mt6797_a72_ppc_test_state state = mt6797_a72_ppc_success_state();
	struct mt6797_a72_platform_provider_clock_snapshot snapshot;
	int ret;

	state.clock_abi = 1;
	ret = mt6797_a72_ppc_run(&state, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
	KUNIT_EXPECT_TRUE(test, snapshot.clock_returned);
	KUNIT_EXPECT_EQ(test, state.clock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.event_count, 5U);
}

static struct kunit_case mt6797_a72_ppc_cases[] = {
	KUNIT_CASE(mt6797_a72_ppc_success_test),
	KUNIT_CASE(mt6797_a72_ppc_not_ready_test),
	KUNIT_CASE(mt6797_a72_ppc_platform_failure_test),
	KUNIT_CASE(mt6797_a72_ppc_provider_failure_test),
	KUNIT_CASE(mt6797_a72_ppc_before_failure_test),
	KUNIT_CASE(mt6797_a72_ppc_clock_error_terminal_test),
	KUNIT_CASE(mt6797_a72_ppc_after_failure_terminal_test),
	KUNIT_CASE(mt6797_a72_ppc_clock_identity_terminal_test),
	{ }
};

static struct kunit_suite mt6797_a72_ppc_suite = {
	.name = "mt6797-a72-platform-provider-clock",
	.test_cases = mt6797_a72_ppc_cases,
};

kunit_test_suite(mt6797_a72_ppc_suite);

MODULE_LICENSE("GPL");
