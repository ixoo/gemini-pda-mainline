// SPDX-License-Identifier: GPL-2.0-only

#include <asm/late_cpu_profile.h>

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/string.h>

#include "mt6797-a72-admission-controller-internal.h"

enum mt6797_a72_admission_test_event {
	MT6797_ADMISSION_BINDER_READY,
	MT6797_ADMISSION_READY_TOKEN,
	MT6797_ADMISSION_SOURCE_REGISTER,
	MT6797_ADMISSION_DERIVE,
	MT6797_ADMISSION_PUBLISH,
	MT6797_ADMISSION_ADD_CPU,
	MT6797_ADMISSION_SOURCE_UNREGISTER,
};

struct mt6797_a72_admission_test_context {
	struct mt6797_a72_admission_controller_state controller;
	struct arm64_late_cpu_ready_token ready;
	enum mt6797_a72_admission_test_event events[16];
	unsigned int event_count;
	int fail_event;
	bool binder_ready;
	bool ready_available;
	bool consumed_before_operation;
	bool same_task;
	struct task_struct *operation_task;
	unsigned int requested_cpu;
};

static void
mt6797_a72_admission_test_event(struct mt6797_a72_admission_test_context *context,
				enum mt6797_a72_admission_test_event event,
				bool operation)
{
	if (context->event_count < ARRAY_SIZE(context->events))
		context->events[context->event_count++] = event;
	if (!operation)
		return;
	if (!atomic_read(&context->controller.consumed))
		context->consumed_before_operation = false;
	if (!context->operation_task)
		context->operation_task = current;
	else if (context->operation_task != current)
		context->same_task = false;
}

static bool mt6797_a72_admission_test_binder_ready(void *data)
{
	struct mt6797_a72_admission_test_context *context = data;

	mt6797_a72_admission_test_event(context,
					MT6797_ADMISSION_BINDER_READY, false);
	return context->binder_ready;
}

static const struct arm64_late_cpu_ready_token *
mt6797_a72_admission_test_ready_token(void *data)
{
	struct mt6797_a72_admission_test_context *context = data;

	mt6797_a72_admission_test_event(context,
					MT6797_ADMISSION_READY_TOKEN, false);
	return context->ready_available ? &context->ready : NULL;
}

static int mt6797_a72_admission_test_register(void *data)
{
	struct mt6797_a72_admission_test_context *context = data;

	mt6797_a72_admission_test_event(context,
					MT6797_ADMISSION_SOURCE_REGISTER, true);
	return context->fail_event == MT6797_ADMISSION_SOURCE_REGISTER ?
		-EIO : 0;
}

static void mt6797_a72_admission_test_unregister(void *data)
{
	struct mt6797_a72_admission_test_context *context = data;

	mt6797_a72_admission_test_event(context,
					MT6797_ADMISSION_SOURCE_UNREGISTER, true);
}

static int
mt6797_a72_admission_test_derive(void *data,
				 const struct arm64_late_cpu_ready_token *ready,
				 struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_admission_test_context *context = data;

	mt6797_a72_admission_test_event(context, MT6797_ADMISSION_DERIVE, true);
	if (ready != &context->ready)
		return -EINVAL;
	if (context->fail_event == MT6797_ADMISSION_DERIVE)
		return -EIO;
	transaction->valid = 1;
	return 0;
}

static int
mt6797_a72_admission_test_publish(void *data,
				  struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_admission_test_context *context = data;

	mt6797_a72_admission_test_event(context, MT6797_ADMISSION_PUBLISH, true);
	if (!transaction->valid)
		return -EINVAL;
	return context->fail_event == MT6797_ADMISSION_PUBLISH ? -EIO : 0;
}

static int
mt6797_a72_admission_test_add_cpu(void *data, unsigned int cpu)
{
	struct mt6797_a72_admission_test_context *context = data;

	mt6797_a72_admission_test_event(context, MT6797_ADMISSION_ADD_CPU, true);
	context->requested_cpu = cpu;
	return context->fail_event == MT6797_ADMISSION_ADD_CPU ? -EIO : 0;
}

static const struct mt6797_a72_admission_controller_ops test_ops = {
	.binder_ready = mt6797_a72_admission_test_binder_ready,
	.ready_token = mt6797_a72_admission_test_ready_token,
	.source_register = mt6797_a72_admission_test_register,
	.source_unregister = mt6797_a72_admission_test_unregister,
	.derive_cpu8 = mt6797_a72_admission_test_derive,
	.publish_up = mt6797_a72_admission_test_publish,
	.add_cpu = mt6797_a72_admission_test_add_cpu,
};

static struct mt6797_a72_admission_test_context *
mt6797_a72_admission_test_context(struct kunit *test)
{
	struct mt6797_a72_admission_test_context *context;

	context = kunit_kzalloc(test, sizeof(*context), GFP_KERNEL);
	if (!context)
		return NULL;
	mt6797_a72_admission_state_init(&context->controller);
	context->fail_event = -1;
	context->binder_ready = true;
	context->ready_available = true;
	context->consumed_before_operation = true;
	context->same_task = true;
	return context;
}

static void mt6797_a72_admission_success_test(struct kunit *test)
{
	static const enum mt6797_a72_admission_test_event expected[] = {
		MT6797_ADMISSION_BINDER_READY,
		MT6797_ADMISSION_READY_TOKEN,
		MT6797_ADMISSION_SOURCE_REGISTER,
		MT6797_ADMISSION_DERIVE,
		MT6797_ADMISSION_PUBLISH,
		MT6797_ADMISSION_ADD_CPU,
		MT6797_ADMISSION_SOURCE_UNREGISTER,
	};
	struct mt6797_a72_admission_test_context *context =
		mt6797_a72_admission_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, context->event_count, ARRAY_SIZE(expected));
	KUNIT_EXPECT_EQ(test, memcmp(context->events, expected,
				     sizeof(expected)), 0);
	KUNIT_EXPECT_EQ(test, atomic_read(&context->controller.consumed), 1);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)1);
	KUNIT_EXPECT_EQ(test, context->requested_cpu, 8U);
	KUNIT_EXPECT_TRUE(test, context->consumed_before_operation);
	KUNIT_EXPECT_TRUE(test, context->same_task);
}

static void mt6797_a72_admission_preconsume_gates_test(struct kunit *test)
{
	struct mt6797_a72_admission_test_context *context;
	int ret;

	context = mt6797_a72_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->binder_ready = false;
	ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EPROBE_DEFER);
	KUNIT_EXPECT_EQ(test, atomic_read(&context->controller.consumed), 0);
	KUNIT_EXPECT_EQ(test, context->event_count, 1U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);

	context = mt6797_a72_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->ready_available = false;
	ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	KUNIT_EXPECT_EQ(test, atomic_read(&context->controller.consumed), 0);
	KUNIT_EXPECT_EQ(test, context->event_count, 2U);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);
}

static void mt6797_a72_admission_terminal_failures_test(struct kunit *test)
{
	static const int failures[] = {
		MT6797_ADMISSION_SOURCE_REGISTER,
		MT6797_ADMISSION_DERIVE,
		MT6797_ADMISSION_PUBLISH,
	};
	struct mt6797_a72_admission_test_context *context;
	unsigned int events;
	size_t failure;
	int ret;

	for (failure = 0; failure < ARRAY_SIZE(failures); failure++) {
		context = mt6797_a72_admission_test_context(test);
		KUNIT_ASSERT_NOT_NULL(test, context);
		context->fail_event = failures[failure];
		ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
		KUNIT_EXPECT_EQ(test, ret, -EIO);
		KUNIT_EXPECT_EQ(test,
				atomic_read(&context->controller.consumed), 1);
		KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);
		KUNIT_EXPECT_TRUE(test, context->consumed_before_operation);
		events = context->event_count;
		ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
		KUNIT_EXPECT_EQ(test, ret, -EALREADY);
		KUNIT_EXPECT_EQ(test, context->event_count, events);
	}
}

static void mt6797_a72_admission_request_failure_test(struct kunit *test)
{
	struct mt6797_a72_admission_test_context *context =
		mt6797_a72_admission_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	context->fail_event = MT6797_ADMISSION_ADD_CPU;
	ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)1);
	KUNIT_EXPECT_EQ(test, context->requested_cpu, 8U);
	KUNIT_EXPECT_EQ(test, context->events[context->event_count - 1],
			MT6797_ADMISSION_SOURCE_UNREGISTER);
	KUNIT_EXPECT_TRUE(test, context->consumed_before_operation);
}

static void mt6797_a72_admission_repeat_closed_test(struct kunit *test)
{
	struct mt6797_a72_admission_test_context *context =
		mt6797_a72_admission_test_context(test);
	unsigned int events;
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
	KUNIT_ASSERT_EQ(test, ret, 0);
	events = context->event_count;
	ret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, context->event_count, events);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)1);
}

static struct kunit_case mt6797_a72_admission_controller_cases[] = {
	KUNIT_CASE(mt6797_a72_admission_success_test),
	KUNIT_CASE(mt6797_a72_admission_preconsume_gates_test),
	KUNIT_CASE(mt6797_a72_admission_terminal_failures_test),
	KUNIT_CASE(mt6797_a72_admission_request_failure_test),
	KUNIT_CASE(mt6797_a72_admission_repeat_closed_test),
	{ }
};

static struct kunit_suite mt6797_a72_admission_controller_suite = {
	.name = "mt6797-a72-admission-controller",
	.test_cases = mt6797_a72_admission_controller_cases,
};

kunit_test_suite(mt6797_a72_admission_controller_suite);

MODULE_LICENSE("GPL");
