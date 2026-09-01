// SPDX-License-Identifier: GPL-2.0-only
/* Injected tests for the retained-cluster MT6797 CPU9 executor. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>

#include "mt6797-a72-cpu9-executor-internal.h"

#define MT6797_CPU9_TEST_EVENT(stage, slot) ((unsigned int)(stage) * 4U + (slot))
#define MT6797_CPU9_TEST_BEFORE 0U
#define MT6797_CPU9_TEST_EFFECT 1U
#define MT6797_CPU9_TEST_AFTER 2U
#define MT6797_CPU9_TEST_TERMINAL 100U

struct mt6797_cpu9_executor_test_state {
	enum mt6797_a72_cpu9_executor_stage fail_stage;
	enum mt6797_a72_cpu9_executor_stage checkpoint_fail_stage;
	enum mt6797_a72_cpu9_executor_phase checkpoint_fail_phase;
	bool terminal_fails;
	unsigned int events[32];
	unsigned int event_count;
	unsigned int cpu_on_target;
	unsigned int secondary_target;
	unsigned int ipi_target;
	unsigned int membership_target;
};

static void mt6797_cpu9_test_record(
	struct mt6797_cpu9_executor_test_state *state, unsigned int event)
{
	if (state->event_count < ARRAY_SIZE(state->events))
		state->events[state->event_count++] = event;
}

static int mt6797_cpu9_test_effect(
	struct mt6797_cpu9_executor_test_state *state,
	enum mt6797_a72_cpu9_executor_stage stage)
{
	mt6797_cpu9_test_record(state,
		MT6797_CPU9_TEST_EVENT(stage, MT6797_CPU9_TEST_EFFECT));
	return state->fail_stage == stage ? -EIO : 0;
}

static int mt6797_cpu9_test_checkpoint(
	void *context, enum mt6797_a72_cpu9_executor_phase phase,
	enum mt6797_a72_cpu9_executor_stage stage,
	const struct mt6797_a72_cpu9_executor_result *result)
{
	struct mt6797_cpu9_executor_test_state *state = context;
	unsigned int slot = phase == MT6797_A72_CPU9_PHASE_BEFORE ?
		MT6797_CPU9_TEST_BEFORE : MT6797_CPU9_TEST_AFTER;

	(void)result;
	mt6797_cpu9_test_record(state, MT6797_CPU9_TEST_EVENT(stage, slot));
	if (state->checkpoint_fail_stage == stage &&
	    state->checkpoint_fail_phase == phase)
		return -EREMOTEIO;
	return 0;
}

static int mt6797_cpu9_test_prestate(
	void *context, const struct mt6797_a72_cpu9_executor_request *request)
{
	(void)request;
	return mt6797_cpu9_test_effect(context, MT6797_A72_CPU9_STAGE_PRESTATE);
}

static int mt6797_cpu9_test_cpu_on(void *context, unsigned int cpu)
{
	struct mt6797_cpu9_executor_test_state *state = context;

	state->cpu_on_target = cpu;
	return mt6797_cpu9_test_effect(state, MT6797_A72_CPU9_STAGE_CPU_ON);
}

static int mt6797_cpu9_test_secondary(void *context, unsigned int cpu)
{
	struct mt6797_cpu9_executor_test_state *state = context;

	state->secondary_target = cpu;
	return mt6797_cpu9_test_effect(state,
				       MT6797_A72_CPU9_STAGE_ONLINE_WAIT);
}

static int mt6797_cpu9_test_ipi(void *context, unsigned int cpu)
{
	struct mt6797_cpu9_executor_test_state *state = context;

	state->ipi_target = cpu;
	return mt6797_cpu9_test_effect(state, MT6797_A72_CPU9_STAGE_IPI);
}

static int mt6797_cpu9_test_membership(void *context, unsigned int cpu)
{
	struct mt6797_cpu9_executor_test_state *state = context;

	state->membership_target = cpu;
	return mt6797_cpu9_test_effect(state,
				       MT6797_A72_CPU9_STAGE_MEMBERSHIP);
}

static int mt6797_cpu9_test_terminal(
	void *context, const struct mt6797_a72_cpu9_executor_result *result)
{
	struct mt6797_cpu9_executor_test_state *state = context;

	(void)result;
	mt6797_cpu9_test_record(state, MT6797_CPU9_TEST_TERMINAL);
	return state->terminal_fails ? -ECOMM : 0;
}

static const struct mt6797_a72_cpu9_executor_ops mt6797_cpu9_test_ops = {
	.checkpoint = mt6797_cpu9_test_checkpoint,
	.prestate = mt6797_cpu9_test_prestate,
	.cpu_on = mt6797_cpu9_test_cpu_on,
	.secondary_complete = mt6797_cpu9_test_secondary,
	.ipi_proof = mt6797_cpu9_test_ipi,
	.membership_commit = mt6797_cpu9_test_membership,
	.terminal = mt6797_cpu9_test_terminal,
};

static struct mt6797_a72_cpu9_executor_request mt6797_cpu9_test_request(void)
{
	return (struct mt6797_a72_cpu9_executor_request) {
		.cpu = MT6797_A72_CPU9_EXECUTOR_CPU9,
		.cpu8_attempt_id = 0x4350553850524f4fULL,
		.cpu9_attempt_id = 0x435055394f4e4531ULL,
		.members = BIT(0),
		.retained_mask = MT6797_A72_CPU9_RETAINED_REQUIRED,
		.cpu8_terminal_exact = true,
		.cpu8_membership_published = true,
		.provider_retained = true,
		.cpu8_online = true,
		.cpu9_online = false,
	};
}

static void mt6797_cpu9_executor_success_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {};
	struct mt6797_a72_cpu9_executor_result result;
	unsigned int cursor = 0;
	int stage, ret;

	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, &request, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	for (stage = MT6797_A72_CPU9_STAGE_PRESTATE;
	     stage <= MT6797_A72_CPU9_STAGE_MEMBERSHIP; stage++) {
		KUNIT_EXPECT_EQ(test, state.events[cursor++],
			MT6797_CPU9_TEST_EVENT(stage, MT6797_CPU9_TEST_BEFORE));
		KUNIT_EXPECT_EQ(test, state.events[cursor++],
			MT6797_CPU9_TEST_EVENT(stage, MT6797_CPU9_TEST_EFFECT));
		KUNIT_EXPECT_EQ(test, state.events[cursor++],
			MT6797_CPU9_TEST_EVENT(stage, MT6797_CPU9_TEST_AFTER));
	}
	KUNIT_EXPECT_EQ(test, state.events[cursor++],
			(unsigned int)MT6797_CPU9_TEST_TERMINAL);
	KUNIT_EXPECT_EQ(test, state.event_count, cursor);
	KUNIT_EXPECT_EQ(test, result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
			MT6797_A72_CPU9_ONLINE_PROOF);
	KUNIT_EXPECT_EQ(test, result.last_stage,
			(enum mt6797_a72_cpu9_executor_stage)
			MT6797_A72_CPU9_STAGE_MEMBERSHIP);
	KUNIT_EXPECT_TRUE(test, result.attempted);
	KUNIT_EXPECT_TRUE(test, result.cpu_on_accepted);
	KUNIT_EXPECT_TRUE(test, result.membership_published);
	KUNIT_EXPECT_TRUE(test, result.cpu8_online);
	KUNIT_EXPECT_TRUE(test, result.cpu9_online);
	KUNIT_EXPECT_EQ(test, result.cpu_requests, 1U);
	KUNIT_EXPECT_EQ(test, result.cpu_off_requests, 0U);
	KUNIT_EXPECT_EQ(test, result.retries, 0U);
	KUNIT_EXPECT_EQ(test, result.checkpoints, 10U);
	KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);
	KUNIT_EXPECT_EQ(test, result.retained_mask,
			(u32)MT6797_A72_CPU9_RETAINED_REQUIRED);
	KUNIT_EXPECT_EQ(test, state.cpu_on_target,
			(unsigned int)MT6797_A72_CPU9_EXECUTOR_CPU9);
	KUNIT_EXPECT_EQ(test, state.secondary_target,
			(unsigned int)MT6797_A72_CPU9_EXECUTOR_CPU9);
	KUNIT_EXPECT_EQ(test, state.ipi_target,
			(unsigned int)MT6797_A72_CPU9_EXECUTOR_CPU9);
	KUNIT_EXPECT_EQ(test, state.membership_target,
			(unsigned int)MT6797_A72_CPU9_EXECUTOR_CPU9);
}

static void mt6797_cpu9_executor_split_success_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {};
	struct mt6797_a72_cpu9_executor_result result;
	int ret;

	ret = mt6797_a72_cpu9_executor_begin(&controller, &mt6797_cpu9_test_ops,
					     &state, &request, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, atomic_read(&controller.lifecycle),
			(int)MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED);
	KUNIT_EXPECT_EQ(test, result.checkpoints, 4U);
	ret = mt6797_a72_cpu9_executor_secondary_complete(
		&controller, &mt6797_cpu9_test_ops, &state,
		MT6797_A72_CPU9_EXECUTOR_CPU9, true, true, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, atomic_read(&controller.lifecycle),
			(int)MT6797_A72_CPU9_LIFECYCLE_SECONDARY_COMPLETE);
	KUNIT_EXPECT_EQ(test, result.checkpoints, 6U);
	ret = mt6797_a72_cpu9_executor_complete(
		&controller, &mt6797_cpu9_test_ops, &state,
		MT6797_A72_CPU9_EXECUTOR_CPU9, true, true, &result);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, atomic_read(&controller.lifecycle),
			(int)MT6797_A72_CPU9_LIFECYCLE_TERMINAL);
	KUNIT_EXPECT_EQ(test, result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
			MT6797_A72_CPU9_ONLINE_PROOF);
}

static void mt6797_cpu9_expect_entry_error(
	struct kunit *test,
	const struct mt6797_a72_cpu9_executor_request *request, int expected)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_test_state state = {};
	struct mt6797_a72_cpu9_executor_result result;
	int ret;

	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, request, &result);
	KUNIT_EXPECT_EQ(test, ret, expected);
	KUNIT_EXPECT_FALSE(test, result.attempted);
	KUNIT_EXPECT_EQ(test, state.event_count, 0U);
}

static void mt6797_cpu9_executor_entry_rejections_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {};
	struct mt6797_a72_cpu9_executor_result result;
	int ret;

	ret = mt6797_a72_cpu9_executor_run(NULL, &mt6797_cpu9_test_ops,
					   &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = mt6797_a72_cpu9_executor_run(&controller, NULL,
					   &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, NULL, &result);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, &request, NULL);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);

	request.cpu = MT6797_A72_CPU9_EXECUTOR_CPU8;
	mt6797_cpu9_expect_entry_error(test, &request, -EINVAL);
	request = mt6797_cpu9_test_request();
	request.cpu8_attempt_id = 0;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.cpu9_attempt_id = request.cpu8_attempt_id;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.members = BIT(1);
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.retained_mask &= ~MT6797_A72_CPU9_RETAINED_PROVIDER;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.cpu8_terminal_exact = false;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.cpu8_membership_published = false;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.provider_retained = false;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.cpu8_online = false;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
	request = mt6797_cpu9_test_request();
	request.cpu9_online = true;
	mt6797_cpu9_expect_entry_error(test, &request, -EPERM);
}

static void mt6797_cpu9_expect_missing_op(
	struct kunit *test, const struct mt6797_a72_cpu9_executor_ops *ops)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {};
	struct mt6797_a72_cpu9_executor_result result;
	int ret;

	ret = mt6797_a72_cpu9_executor_run(&controller, ops, &state,
					   &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	KUNIT_EXPECT_FALSE(test, result.attempted);
}

static void mt6797_cpu9_executor_missing_op_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_ops ops;

	ops = mt6797_cpu9_test_ops;
	ops.checkpoint = NULL;
	mt6797_cpu9_expect_missing_op(test, &ops);
	ops = mt6797_cpu9_test_ops;
	ops.prestate = NULL;
	mt6797_cpu9_expect_missing_op(test, &ops);
	ops = mt6797_cpu9_test_ops;
	ops.cpu_on = NULL;
	mt6797_cpu9_expect_missing_op(test, &ops);
	ops = mt6797_cpu9_test_ops;
	ops.secondary_complete = NULL;
	mt6797_cpu9_expect_missing_op(test, &ops);
	ops = mt6797_cpu9_test_ops;
	ops.ipi_proof = NULL;
	mt6797_cpu9_expect_missing_op(test, &ops);
	ops = mt6797_cpu9_test_ops;
	ops.membership_commit = NULL;
	mt6797_cpu9_expect_missing_op(test, &ops);
	ops = mt6797_cpu9_test_ops;
	ops.terminal = NULL;
	mt6797_cpu9_expect_missing_op(test, &ops);
}

static void mt6797_cpu9_executor_one_shot_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {
		.fail_stage = MT6797_A72_CPU9_STAGE_PRESTATE,
	};
	struct mt6797_a72_cpu9_executor_result result;
	unsigned int events;
	int ret;

	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, &request, &result);
	KUNIT_ASSERT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
			MT6797_A72_CPU9_REJECTED_PRESTATE);
	events = state.event_count;
	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, state.event_count, events);
}

static void mt6797_cpu9_executor_stage_failures_test(struct kunit *test)
{
	enum mt6797_a72_cpu9_executor_stage stage;

	for (stage = MT6797_A72_CPU9_STAGE_PRESTATE;
	     stage <= MT6797_A72_CPU9_STAGE_MEMBERSHIP; stage++) {
		struct mt6797_a72_cpu9_executor_controller controller =
			MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
		struct mt6797_a72_cpu9_executor_request request =
			mt6797_cpu9_test_request();
		struct mt6797_a72_cpu9_executor_test_state state = {
			.fail_stage = stage,
		};
		struct mt6797_a72_cpu9_executor_result result;
		int ret;

		ret = mt6797_a72_cpu9_executor_run(
			&controller, &mt6797_cpu9_test_ops,
			&state, &request, &result);
		KUNIT_EXPECT_EQ(test, ret, -EIO);
		KUNIT_EXPECT_EQ(test, result.last_stage, stage);
		KUNIT_EXPECT_EQ(test, result.stage_errno, -EIO);
		KUNIT_EXPECT_EQ(test, result.terminal,
			stage == MT6797_A72_CPU9_STAGE_PRESTATE ?
			MT6797_A72_CPU9_REJECTED_PRESTATE :
			MT6797_A72_CPU9_FAULT_RETAIN_CPU8);
		KUNIT_EXPECT_EQ(test, result.cpu_requests,
			stage >= MT6797_A72_CPU9_STAGE_CPU_ON ? 1U : 0U);
		KUNIT_EXPECT_EQ(test, result.cpu_off_requests, 0U);
		KUNIT_EXPECT_EQ(test, result.retries, 0U);
		KUNIT_EXPECT_EQ(test, result.retained_mask,
			(u32)MT6797_A72_CPU9_RETAINED_REQUIRED);
		KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);
	}
}

static void mt6797_cpu9_executor_checkpoint_failures_test(struct kunit *test)
{
	enum mt6797_a72_cpu9_executor_phase phase;
	enum mt6797_a72_cpu9_executor_stage stage;

	for (stage = MT6797_A72_CPU9_STAGE_PRESTATE;
	     stage <= MT6797_A72_CPU9_STAGE_MEMBERSHIP; stage++) {
		for (phase = MT6797_A72_CPU9_PHASE_BEFORE;
		     phase <= MT6797_A72_CPU9_PHASE_AFTER; phase++) {
			struct mt6797_a72_cpu9_executor_controller controller =
				MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
			struct mt6797_a72_cpu9_executor_request request =
				mt6797_cpu9_test_request();
			struct mt6797_a72_cpu9_executor_test_state state = {
				.checkpoint_fail_stage = stage,
				.checkpoint_fail_phase = phase,
			};
			struct mt6797_a72_cpu9_executor_result result;
			unsigned int requests = 0;
			int ret;

			ret = mt6797_a72_cpu9_executor_run(
				&controller, &mt6797_cpu9_test_ops,
				&state, &request, &result);
			KUNIT_EXPECT_EQ(test, ret, -EREMOTEIO);
			KUNIT_EXPECT_EQ(test, result.last_stage, stage);
			KUNIT_EXPECT_EQ(test, result.checkpoint_errno, -EREMOTEIO);
			if (stage > MT6797_A72_CPU9_STAGE_CPU_ON ||
			    (stage == MT6797_A72_CPU9_STAGE_CPU_ON &&
			     phase == MT6797_A72_CPU9_PHASE_AFTER))
				requests = 1;
			KUNIT_EXPECT_EQ(test, result.cpu_requests, requests);
			KUNIT_EXPECT_EQ(test, result.cpu_off_requests, 0U);
			KUNIT_EXPECT_EQ(test, result.retries, 0U);
			KUNIT_EXPECT_EQ(test, result.retained_mask,
				(u32)MT6797_A72_CPU9_RETAINED_REQUIRED);
			KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);
		}
	}
}

static void mt6797_cpu9_executor_lifecycle_guards_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {};
	struct mt6797_a72_cpu9_executor_result result = {};
	int ret;

	ret = mt6797_a72_cpu9_executor_secondary_complete(
		&controller, &mt6797_cpu9_test_ops, &state,
		MT6797_A72_CPU9_EXECUTOR_CPU9, true, true, &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	ret = mt6797_a72_cpu9_executor_begin(
		&controller, &mt6797_cpu9_test_ops, &state, &request, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_cpu9_executor_complete(
		&controller, &mt6797_cpu9_test_ops, &state,
		MT6797_A72_CPU9_EXECUTOR_CPU9, true, true, &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	ret = mt6797_a72_cpu9_executor_secondary_complete(
		&controller, &mt6797_cpu9_test_ops, &state,
		MT6797_A72_CPU9_EXECUTOR_CPU8, true, true, &result);
	KUNIT_EXPECT_EQ(test, ret, -EPROTO);
	KUNIT_EXPECT_EQ(test, result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
			MT6797_A72_CPU9_FAULT_RETAIN_CPU8);
}

static void mt6797_cpu9_executor_failure_dispatch_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {};
	struct mt6797_a72_cpu9_executor_result result;
	int ret;

	ret = mt6797_a72_cpu9_executor_begin(
		&controller, &mt6797_cpu9_test_ops, &state, &request, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_cpu9_executor_fail(
		&controller, &mt6797_cpu9_test_ops, &state,
		MT6797_A72_CPU9_EXECUTOR_CPU9, true, false,
		-ETIMEDOUT, &result);
	KUNIT_EXPECT_EQ(test, ret, -ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, result.last_stage,
			(enum mt6797_a72_cpu9_executor_stage)
			MT6797_A72_CPU9_STAGE_ONLINE_WAIT);
	KUNIT_EXPECT_EQ(test, result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
			MT6797_A72_CPU9_FAULT_RETAIN_CPU8);
	KUNIT_EXPECT_EQ(test, result.cpu_requests, 1U);
	KUNIT_EXPECT_EQ(test, result.retained_mask,
			(u32)MT6797_A72_CPU9_RETAINED_REQUIRED);
	ret = mt6797_a72_cpu9_executor_fail(
		&controller, &mt6797_cpu9_test_ops, &state,
		MT6797_A72_CPU9_EXECUTOR_CPU9, true, false, -EIO, &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
}

static void mt6797_cpu9_executor_terminal_failures_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_controller controller =
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_test_request();
	struct mt6797_a72_cpu9_executor_test_state state = {
		.terminal_fails = true,
	};
	struct mt6797_a72_cpu9_executor_result result;
	int ret;

	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -ECOMM);
	KUNIT_EXPECT_EQ(test, result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
			MT6797_A72_CPU9_FAULT_RETAIN_CPU8);
	KUNIT_EXPECT_EQ(test, result.stage_errno, -ECOMM);
	KUNIT_EXPECT_EQ(test, result.checkpoint_errno, -ECOMM);
	KUNIT_EXPECT_TRUE(test, result.membership_published);

	controller = (struct mt6797_a72_cpu9_executor_controller)
		MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT;
	state = (struct mt6797_cpu9_executor_test_state) {
		.fail_stage = MT6797_A72_CPU9_STAGE_PRESTATE,
		.terminal_fails = true,
	};
	ret = mt6797_a72_cpu9_executor_run(&controller, &mt6797_cpu9_test_ops,
					   &state, &request, &result);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
			MT6797_A72_CPU9_REJECTED_PRESTATE);
	KUNIT_EXPECT_EQ(test, result.checkpoint_errno, -ECOMM);
}

static struct kunit_case mt6797_cpu9_executor_test_cases[] = {
	KUNIT_CASE(mt6797_cpu9_executor_success_test),
	KUNIT_CASE(mt6797_cpu9_executor_split_success_test),
	KUNIT_CASE(mt6797_cpu9_executor_entry_rejections_test),
	KUNIT_CASE(mt6797_cpu9_executor_missing_op_test),
	KUNIT_CASE(mt6797_cpu9_executor_one_shot_test),
	KUNIT_CASE(mt6797_cpu9_executor_stage_failures_test),
	KUNIT_CASE(mt6797_cpu9_executor_checkpoint_failures_test),
	KUNIT_CASE(mt6797_cpu9_executor_lifecycle_guards_test),
	KUNIT_CASE(mt6797_cpu9_executor_failure_dispatch_test),
	KUNIT_CASE(mt6797_cpu9_executor_terminal_failures_test),
	{},
};

static struct kunit_suite mt6797_cpu9_executor_test_suite = {
	.name = "mt6797-a72-cpu9-executor",
	.test_cases = mt6797_cpu9_executor_test_cases,
};

kunit_test_suite(mt6797_cpu9_executor_test_suite);

MODULE_LICENSE("GPL");
