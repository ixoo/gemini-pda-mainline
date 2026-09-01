// SPDX-License-Identifier: GPL-2.0-only
/* Hardware-free tests for the same-boot CPU8-to-CPU9 admission chain. */

#include <asm/late_cpu_profile.h>

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/string.h>

#include "mt6797-a72-cpu9-admission-controller-internal.h"

enum mt6797_a72_cpu9_admission_test_event {
	MT6797_CPU9_ADMISSION_RUN_CPU8,
	MT6797_CPU9_ADMISSION_CPU8_PROOF,
	MT6797_CPU9_ADMISSION_READY_TOKEN,
	MT6797_CPU9_ADMISSION_DERIVE,
	MT6797_CPU9_ADMISSION_PUBLISH,
	MT6797_CPU9_ADMISSION_PREPARE,
	MT6797_CPU9_ADMISSION_ADD_CPU,
};

enum mt6797_a72_cpu9_admission_test_failure {
	MT6797_CPU9_ADMISSION_FAIL_NONE,
	MT6797_CPU9_ADMISSION_FAIL_CPU8,
	MT6797_CPU9_ADMISSION_FAIL_PROOF,
	MT6797_CPU9_ADMISSION_FAIL_READY,
	MT6797_CPU9_ADMISSION_FAIL_DERIVE,
	MT6797_CPU9_ADMISSION_FAIL_PUBLISH,
	MT6797_CPU9_ADMISSION_FAIL_PREPARE,
	MT6797_CPU9_ADMISSION_FAIL_ADD_CPU,
};

struct mt6797_a72_cpu9_admission_test_context {
	struct mt6797_a72_cpu9_admission_state controller;
	struct arm64_late_cpu_ready_token ready;
	struct mt6797_a72_cpu9_admission_cpu8_proof proof;
	enum mt6797_a72_cpu9_admission_test_failure failure;
	enum mt6797_a72_cpu9_admission_test_event events[8];
	unsigned int event_count;
	unsigned int requested_cpu;
	bool same_task;
	struct task_struct *task;
	struct mt6797_a72_cpu9_executor_request prepared;
};

static void mt6797_a72_cpu9_admission_test_event(
	struct mt6797_a72_cpu9_admission_test_context *context,
	enum mt6797_a72_cpu9_admission_test_event event)
{
	if (context->event_count < ARRAY_SIZE(context->events))
		context->events[context->event_count++] = event;
	if (!context->task)
		context->task = current;
	else if (context->task != current)
		context->same_task = false;
}

static int mt6797_a72_cpu9_admission_test_run_cpu8(void *data)
{
	struct mt6797_a72_cpu9_admission_test_context *context = data;

	mt6797_a72_cpu9_admission_test_event(
		context, MT6797_CPU9_ADMISSION_RUN_CPU8);
	return context->failure == MT6797_CPU9_ADMISSION_FAIL_CPU8 ? -EIO : 0;
}

static int mt6797_a72_cpu9_admission_test_cpu8_proof(
	void *data, struct mt6797_a72_cpu9_admission_cpu8_proof *proof)
{
	struct mt6797_a72_cpu9_admission_test_context *context = data;

	mt6797_a72_cpu9_admission_test_event(
		context, MT6797_CPU9_ADMISSION_CPU8_PROOF);
	if (context->failure == MT6797_CPU9_ADMISSION_FAIL_PROOF)
		return -EPROTO;
	*proof = context->proof;
	return 0;
}

static const struct arm64_late_cpu_ready_token *
mt6797_a72_cpu9_admission_test_ready(void *data)
{
	struct mt6797_a72_cpu9_admission_test_context *context = data;

	mt6797_a72_cpu9_admission_test_event(
		context, MT6797_CPU9_ADMISSION_READY_TOKEN);
	return context->failure == MT6797_CPU9_ADMISSION_FAIL_READY ? NULL :
							      &context->ready;
}

static int mt6797_a72_cpu9_admission_test_derive(
	void *data, const struct arm64_late_cpu_ready_token *ready,
	struct mt6797_a72_transaction *transaction, u32 *derive_stage)
{
	struct mt6797_a72_cpu9_admission_test_context *context = data;

	mt6797_a72_cpu9_admission_test_event(
		context, MT6797_CPU9_ADMISSION_DERIVE);
	if (ready != &context->ready)
		return -EINVAL;
	if (context->failure == MT6797_CPU9_ADMISSION_FAIL_DERIVE)
		return -EIO;
	transaction->valid = 1;
	transaction->a36_valid = 1;
	transaction->p30_token_valid = 1;
	transaction->identity.abi = MT6797_A72_TRANSACTION_ABI;
	transaction->identity.owner = ARM64_LATE_CPU_STARTUP_OWNER_MEMBERSHIP;
	transaction->identity.operation = ARM64_LATE_CPU_STARTUP_OP_CPU9_UP;
	transaction->identity.target_cpu = MT6797_A72_CPU9_EXECUTOR_CPU9;
	transaction->identity.cpuhp_target = CPUHP_ONLINE;
	transaction->identity.target_mpidr = 0x201;
	transaction->identity.generation = 0x435055394f4e4531ULL;
	transaction->identity.cookie = 0xa72000f1;
	transaction->provider_identity.generation = 0xa72000e0;
	transaction->provider_identity.cookie = 0xa72000e1;
	transaction->budgets.cpu_on = MT6797_A72_BUDGET_AVAILABLE;
	*derive_stage = MT6797_A72_CPU9_DERIVE_COMPLETE;
	return 0;
}

static int mt6797_a72_cpu9_admission_test_publish(
	void *data, struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_cpu9_admission_test_context *context = data;

	mt6797_a72_cpu9_admission_test_event(
		context, MT6797_CPU9_ADMISSION_PUBLISH);
	if (context->failure == MT6797_CPU9_ADMISSION_FAIL_PUBLISH)
		return -EIO;
	transaction->p17_p18_published = 1;
	return 0;
}

static int mt6797_a72_cpu9_admission_test_prepare(
	void *data, const struct mt6797_a72_cpu9_executor_request *request)
{
	struct mt6797_a72_cpu9_admission_test_context *context = data;

	mt6797_a72_cpu9_admission_test_event(
		context, MT6797_CPU9_ADMISSION_PREPARE);
	context->prepared = *request;
	return context->failure == MT6797_CPU9_ADMISSION_FAIL_PREPARE ? -EIO :
								       0;
}

static int mt6797_a72_cpu9_admission_test_add_cpu(void *data,
						  unsigned int cpu)
{
	struct mt6797_a72_cpu9_admission_test_context *context = data;

	mt6797_a72_cpu9_admission_test_event(
		context, MT6797_CPU9_ADMISSION_ADD_CPU);
	context->requested_cpu = cpu;
	return context->failure == MT6797_CPU9_ADMISSION_FAIL_ADD_CPU ? -EIO :
								       0;
}

static const struct mt6797_a72_cpu9_admission_ops
	mt6797_a72_cpu9_admission_test_ops = {
		.run_cpu8 = mt6797_a72_cpu9_admission_test_run_cpu8,
		.cpu8_proof = mt6797_a72_cpu9_admission_test_cpu8_proof,
		.ready_token = mt6797_a72_cpu9_admission_test_ready,
		.derive_cpu9 = mt6797_a72_cpu9_admission_test_derive,
		.publish_cpu9 = mt6797_a72_cpu9_admission_test_publish,
		.prepare_cpu9 = mt6797_a72_cpu9_admission_test_prepare,
		.add_cpu = mt6797_a72_cpu9_admission_test_add_cpu,
	};

static struct mt6797_a72_cpu9_admission_test_context *
mt6797_a72_cpu9_admission_test_context(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context;

	context = kunit_kzalloc(test, sizeof(*context), GFP_KERNEL);
	if (!context)
		return NULL;
	mt6797_a72_cpu9_admission_state_init(&context->controller);
	context->same_task = true;
	context->proof = (struct mt6797_a72_cpu9_admission_cpu8_proof){
		.attempt_id = 0x4350553850524f4fULL,
		.cpu_requests = 1,
		.lifecycle_terminal = true,
		.terminal_exact = true,
		.membership_published = true,
		.p27_retained = true,
		.provider_retained = true,
		.cpu8_online = true,
		.cpu9_online = false,
	};
	return context;
}

static void mt6797_a72_cpu9_admission_success_test(struct kunit *test)
{
	static const enum mt6797_a72_cpu9_admission_test_event expected[] = {
		MT6797_CPU9_ADMISSION_RUN_CPU8,
		MT6797_CPU9_ADMISSION_CPU8_PROOF,
		MT6797_CPU9_ADMISSION_READY_TOKEN,
		MT6797_CPU9_ADMISSION_DERIVE,
		MT6797_CPU9_ADMISSION_PUBLISH,
		MT6797_CPU9_ADMISSION_PREPARE,
		MT6797_CPU9_ADMISSION_ADD_CPU,
	};
	struct mt6797_a72_cpu9_admission_test_context *context =
		mt6797_a72_cpu9_admission_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, context->event_count, ARRAY_SIZE(expected));
	KUNIT_EXPECT_EQ(test, memcmp(context->events, expected,
				     sizeof(expected)), 0);
	KUNIT_EXPECT_TRUE(test, context->same_task);
	KUNIT_EXPECT_EQ(test, context->controller.cpu8_requests, 1U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 1U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_off_requests, 0U);
	KUNIT_EXPECT_EQ(test, context->controller.retries, 0U);
	KUNIT_EXPECT_EQ(test, context->requested_cpu, 9U);
	KUNIT_EXPECT_EQ(test, context->prepared.cpu8_attempt_id,
			context->proof.attempt_id);
	KUNIT_EXPECT_EQ(test, context->prepared.cpu9_attempt_id,
			context->controller.cpu9_transaction.identity.generation);
	KUNIT_EXPECT_EQ(test, context->prepared.members, (u32)BIT(0));
	KUNIT_EXPECT_EQ(test, context->prepared.retained_mask,
			(u32)MT6797_A72_CPU9_RETAINED_REQUIRED);
	KUNIT_EXPECT_TRUE(test, context->prepared.cpu8_terminal_exact);
	KUNIT_EXPECT_TRUE(test, context->prepared.cpu8_membership_published);
	KUNIT_EXPECT_TRUE(test, context->prepared.provider_retained);
	KUNIT_EXPECT_TRUE(test, context->prepared.cpu8_online);
	KUNIT_EXPECT_FALSE(test, context->prepared.cpu9_online);
}

static void mt6797_a72_cpu9_admission_invalid_repeat_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context =
		mt6797_a72_cpu9_admission_test_context(test);
	unsigned int events;
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	ret = mt6797_a72_cpu9_admission_run(&context->controller, NULL, context);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	KUNIT_EXPECT_EQ(test, atomic_read(&context->controller.consumed), 0);
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_ASSERT_EQ(test, ret, 0);
	events = context->event_count;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, context->event_count, events);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 1U);
}

static void mt6797_a72_cpu9_admission_cpu8_failure_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context =
		mt6797_a72_cpu9_admission_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	context->failure = MT6797_CPU9_ADMISSION_FAIL_CPU8;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->event_count, 1U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 0U);
	KUNIT_EXPECT_EQ(test, context->controller.failure_stage,
			(u32)MT6797_A72_CPU9_ADMISSION_FAILURE_CPU8);
}

static void mt6797_a72_cpu9_admission_proof_failures_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context;
	int ret;

	context = mt6797_a72_cpu9_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->failure = MT6797_CPU9_ADMISSION_FAIL_PROOF;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EPROTO);
	KUNIT_EXPECT_EQ(test, context->event_count, 2U);

	context = mt6797_a72_cpu9_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->proof.cpu9_online = true;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EPROTO);
	KUNIT_EXPECT_EQ(test, context->event_count, 2U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 0U);
}

static void mt6797_a72_cpu9_admission_ready_derive_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context;
	int ret;

	context = mt6797_a72_cpu9_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->failure = MT6797_CPU9_ADMISSION_FAIL_READY;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	KUNIT_EXPECT_EQ(test, context->event_count, 3U);

	context = mt6797_a72_cpu9_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->failure = MT6797_CPU9_ADMISSION_FAIL_DERIVE;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->event_count, 4U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 0U);
}

static void mt6797_a72_cpu9_admission_publish_failure_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context =
		mt6797_a72_cpu9_admission_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	context->failure = MT6797_CPU9_ADMISSION_FAIL_PUBLISH;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->event_count, 5U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 0U);
	KUNIT_EXPECT_EQ(test, context->controller.failure_stage,
			(u32)MT6797_A72_CPU9_ADMISSION_FAILURE_PUBLISH);
}

static void mt6797_a72_cpu9_admission_prepare_failure_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context =
		mt6797_a72_cpu9_admission_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	context->failure = MT6797_CPU9_ADMISSION_FAIL_PREPARE;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->event_count, 6U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 0U);
	KUNIT_EXPECT_EQ(test, context->controller.failure_stage,
			(u32)MT6797_A72_CPU9_ADMISSION_FAILURE_PREPARE);
}

static void mt6797_a72_cpu9_admission_request_failure_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_admission_test_context *context =
		mt6797_a72_cpu9_admission_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	context->failure = MT6797_CPU9_ADMISSION_FAIL_ADD_CPU;
	ret = mt6797_a72_cpu9_admission_run(
		&context->controller, &mt6797_a72_cpu9_admission_test_ops,
		context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->event_count, 7U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu8_requests, 1U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 1U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_off_requests, 0U);
	KUNIT_EXPECT_EQ(test, context->controller.retries, 0U);
	KUNIT_EXPECT_EQ(test, context->requested_cpu, 9U);
	KUNIT_EXPECT_EQ(test, context->controller.failure_stage,
			(u32)MT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST);
}

static struct kunit_case mt6797_a72_cpu9_admission_controller_cases[] = {
	KUNIT_CASE(mt6797_a72_cpu9_admission_success_test),
	KUNIT_CASE(mt6797_a72_cpu9_admission_invalid_repeat_test),
	KUNIT_CASE(mt6797_a72_cpu9_admission_cpu8_failure_test),
	KUNIT_CASE(mt6797_a72_cpu9_admission_proof_failures_test),
	KUNIT_CASE(mt6797_a72_cpu9_admission_ready_derive_test),
	KUNIT_CASE(mt6797_a72_cpu9_admission_publish_failure_test),
	KUNIT_CASE(mt6797_a72_cpu9_admission_prepare_failure_test),
	KUNIT_CASE(mt6797_a72_cpu9_admission_request_failure_test),
	{ }
};

static struct kunit_suite mt6797_a72_cpu9_admission_controller_suite = {
	.name = "mt6797-a72-cpu9-admission-controller",
	.test_cases = mt6797_a72_cpu9_admission_controller_cases,
};

kunit_test_suite(mt6797_a72_cpu9_admission_controller_suite);

MODULE_LICENSE("GPL");
