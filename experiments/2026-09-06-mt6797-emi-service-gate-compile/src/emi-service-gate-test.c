/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include "emi-service-gate.h"

struct callback_context {
	struct mt6797_emi_service_gate *gate;
	u64 raw;
	unsigned int calls;
	unsigned int function_id;
	u64 start;
	u64 end;
	unsigned int region_permission;
	int saw_attempted;
};

static u64 callback(void *opaque, unsigned int function_id, u64 start, u64 end,
			    unsigned int region_permission)
{
	struct callback_context *context = opaque;

	context->calls++;
	context->function_id = function_id;
	context->start = start;
	context->end = end;
	context->region_permission = region_permission;
	context->saw_attempted = context->gate->state ==
		MT6797_EMI_SERVICE_GATE_ATTEMPTED;
	return context->raw;
}

static u64 other_callback(void *opaque, unsigned int function_id, u64 start,
				  u64 end, unsigned int region_permission)
{
	(void)opaque;
	(void)function_id;
	(void)start;
	(void)end;
	(void)region_permission;
	assert(0 && "mutated source callback was used");
	return 0;
}

static struct mt6797_resource_layout valid_layout(
	unsigned long long generation, enum mt6797_emi_selector selector)
{
	struct mt6797_image_reserved_info info = {
		.generation = generation,
		.start = 0x80000000ULL,
		.end = 0x802fffffULL,
		.wlan_start = 0x80000000ULL,
		.wlan_end = 0x8007ffffULL,
		.wmt_start = 0x80080000ULL,
		.wmt_end = 0x800fffffULL,
	};
	struct mt6797_resource_layout layout;

	assert(!mt6797_resource_layout_build(&info, selector, &layout));
	return layout;
}

static struct mt6797_resource_layout remap_overflow_layout(void)
{
	const u64 start = 0x100000000ULL;
	const u64 end = start + 0x2fffffULL;
	const u64 wlan_end = start + 0x7ffffULL;
	const u64 wmt_start = start + 0x80000ULL;
	const u64 wmt_end = start + 0xfffffULL;

	return (struct mt6797_resource_layout){
		.generation = 4,
		.start = start,
		.end = end,
		.wlan_start = start,
		.wlan_end = wlan_end,
		.wmt_start = wmt_start,
		.wmt_end = wmt_end,
		.common_field = 0,
		.region18 = {
			.start = start,
			.end = wlan_end,
			.selector = MT6797_EMI_SELECTOR_BIT13_SET,
			.region = 18,
		},
		.region19 = {
			.start = wmt_start,
			.end = wmt_end,
			.selector = MT6797_EMI_SELECTOR_BIT13_SET,
			.region = 19,
		},
	};
}

static struct mt6797_emi_service_backend backend(
	struct callback_context *context)
{
	return (struct mt6797_emi_service_backend){
		.call = callback,
		.context = context,
	};
}

static struct mt6797_emi_service_gate poisoned_gate(void)
{
	return (struct mt6797_emi_service_gate){
		.layout = valid_layout(77, MT6797_EMI_SELECTOR_BIT13_SET),
		.backend = {.call = other_callback, .context = (void *)1},
		.expected_generation = 77,
		.state = MT6797_EMI_SERVICE_GATE_FAULT_HELD,
	};
}

static struct mt6797_emi_service_result poisoned_result(void)
{
	return (struct mt6797_emi_service_result){
		.generation = 66,
		.arguments = {
			.function_id = 1,
			.start = 2,
			.end = 3,
			.region_permission = 4,
			.range_word = 5,
		},
		.raw = 6,
		.status = 7,
	};
}

static void expect_init_error(struct mt6797_resource_layout *layout,
				      struct mt6797_emi_service_backend *backend_desc,
				      int expected)
{
	struct mt6797_emi_service_gate gate = poisoned_gate();

	assert(mt6797_emi_service_gate_init(&gate, layout, backend_desc) ==
		expected);
	assert(!memcmp(&gate, &(struct mt6797_emi_service_gate){0},
		       sizeof(gate)));
}

static void expect_apply_refusal(struct mt6797_emi_service_gate *gate,
					 struct callback_context *context, u64 generation,
					 unsigned int permissions, int expected)
{
	struct mt6797_emi_service_gate gate_before = *gate;
	struct mt6797_emi_service_result result = poisoned_result();
	struct callback_context context_before = *context;

	assert(mt6797_emi_service_gate_apply(gate, generation, permissions,
						    &result) == expected);
	assert(!memcmp(&result, &(struct mt6797_emi_service_result){0},
			       sizeof(result)));
	assert(!memcmp(gate, &gate_before, sizeof(*gate)));
	assert(context->calls == context_before.calls &&
	       !memcmp(context, &context_before, sizeof(*context)));
}

static void expect_success(u64 raw, u64 generation, unsigned int permissions,
				   int expected_status)
{
	struct mt6797_resource_layout layout =
		valid_layout(generation, MT6797_EMI_SELECTOR_BIT13_SET);
	struct mt6797_emi_service_gate gate;
	struct callback_context context = {.raw = raw};
	struct mt6797_emi_service_backend backend_desc = backend(&context);
	struct mt6797_emi_service_result result = poisoned_result();

	assert(!mt6797_emi_service_gate_init(&gate, &layout, &backend_desc));
	context.gate = &gate;
	assert(mt6797_emi_service_gate_apply(&gate, generation, permissions,
						    &result) == expected_status);
	assert(context.calls == 1 && context.saw_attempted);
	assert(context.function_id == MT6797_EMI_SMC32_SET &&
	       context.start == 0x80000000ULL && context.end == 0x8007ffffULL &&
	       context.region_permission == ((18U << 27) | permissions));
	assert(result.generation == generation && result.arguments.function_id ==
	       MT6797_EMI_SMC32_SET && result.arguments.start == context.start &&
	       result.arguments.end == context.end &&
	       result.arguments.region_permission == context.region_permission &&
	       result.arguments.range_word == 0x80008007U &&
	       result.raw == raw && result.status == expected_status);
	assert(gate.state == (expected_status == 0 ?
		MT6797_EMI_SERVICE_GATE_COMPLETED :
		MT6797_EMI_SERVICE_GATE_FAULT_HELD));
	{
		struct mt6797_emi_service_gate terminal_gate = gate;
		struct callback_context terminal_context = context;

		result = poisoned_result();
		assert(mt6797_emi_service_gate_apply(&gate, generation, permissions,
						    &result) == -EALREADY);
		assert(!memcmp(&result, &(struct mt6797_emi_service_result){0},
			       sizeof(result)));
		assert(!memcmp(&gate, &terminal_gate, sizeof(gate)));
		assert(!memcmp(&context, &terminal_context, sizeof(context)));
	}
}

int main(void)
{
	struct mt6797_emi_service_gate gate;
	struct mt6797_resource_layout layout;
	struct mt6797_emi_service_backend backend_desc;
	struct callback_context context = {0};
	struct callback_context replacement_context = {.raw = 0xdeadbeef};
	struct mt6797_emi_service_result result;
	unsigned int bit;

	/* Valid boundaries, including the largest nonzero generation. */
	backend_desc = backend(&context);
	layout = valid_layout(1, MT6797_EMI_SELECTOR_BIT13_SET);
	assert(!mt6797_emi_service_gate_init(&gate, &layout, &backend_desc));
	assert(gate.state == MT6797_EMI_SERVICE_GATE_READY &&
	       gate.expected_generation == 1);
	layout = valid_layout(ULLONG_MAX, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	assert(!mt6797_emi_service_gate_init(&gate, &layout, &backend_desc));
	assert(gate.expected_generation == ULLONG_MAX);

	/* Nulls, missing callback, and every exact init-storage alias. */
	layout = valid_layout(2, MT6797_EMI_SELECTOR_BIT13_SET);
	backend_desc = backend(&context);
	gate = poisoned_gate();
	assert(mt6797_emi_service_gate_init(NULL, &layout, &backend_desc) ==
	       -EINVAL);
	expect_init_error(&layout, NULL, -EINVAL);
	expect_init_error(NULL, &backend_desc, -EINVAL);
	expect_init_error(&layout, &(struct mt6797_emi_service_backend){0},
			  -EOPNOTSUPP);
	gate = poisoned_gate();
	{
		struct mt6797_emi_service_gate before = gate;
		assert(mt6797_emi_service_gate_init(&gate,
			(const struct mt6797_resource_layout *)(const void *)&gate,
			&backend_desc) == -EINVAL);
		assert(!memcmp(&gate, &before, sizeof(gate)));
	}
	gate = poisoned_gate();
	{
		struct mt6797_emi_service_gate before = gate;
		assert(mt6797_emi_service_gate_init(&gate, &layout,
			(const struct mt6797_emi_service_backend *)(const void *)&gate) ==
			-EINVAL);
		assert(!memcmp(&gate, &before, sizeof(gate)));
	}
	{
		union {
			struct mt6797_resource_layout layout;
			struct mt6797_emi_service_backend backend;
		} aliased;
		struct mt6797_emi_service_gate before = poisoned_gate();
		unsigned char aliased_before[sizeof(aliased)];

		aliased.backend = backend_desc;
		memcpy(aliased_before, &aliased, sizeof(aliased));
		assert(mt6797_emi_service_gate_init(&before,
			(const struct mt6797_resource_layout *)(const void *)&aliased,
			&aliased.backend) == -EINVAL);
		assert(before.state == MT6797_EMI_SERVICE_GATE_FAULT_HELD);
		assert(!memcmp(&aliased, aliased_before, sizeof(aliased)));
	}

	/* Layout range and first-MiB split errors. */
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.generation = 0;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.start = layout.end + 1;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.start = ULLONG_MAX - 0xffffeULL;
	layout.end = ULLONG_MAX;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.end = layout.start + 0xffffeULL;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.wlan_start++;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.wlan_end--;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.wmt_start++;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.wmt_end--;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region18.start--;
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region19.end = layout.end + 1;
	expect_init_error(&layout, &backend_desc, -ERANGE);

	/* Region identity/selector and common-field composition errors. */
	for (bit = 0; bit < 3; bit++) {
		layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
		layout.region18.selector =
			(enum mt6797_emi_selector[]){MT6797_EMI_SELECTOR_UNSET,
				(enum mt6797_emi_selector)3,
				(enum mt6797_emi_selector)99}[bit];
		expect_init_error(&layout, &backend_desc, -EINVAL);
	}
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region18.region = 17;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region19.region = 20;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region18.selector = MT6797_EMI_SELECTOR_BIT13_CLEAR;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region18.start++;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region18.end--;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region19.start++;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.region19.end--;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.common_field++;
	expect_init_error(&layout, &backend_desc, -EINVAL);
	layout = remap_overflow_layout();
	expect_init_error(&layout, &backend_desc, -ERANGE);
	layout = valid_layout(3, MT6797_EMI_SELECTOR_BIT13_SET);
	layout.start = 0x20000000ULL;
	layout.end = 0x202fffffULL;
	layout.wlan_start = 0x20000000ULL;
	layout.wlan_end = 0x2007ffffULL;
	layout.wmt_start = 0x20080000ULL;
	layout.wmt_end = 0x200fffffULL;
	assert(!mt6797_remap_encode_common(layout.start, 1,
					   &layout.common_field));
	layout.region18.start = layout.wlan_start;
	layout.region18.end = layout.wlan_end;
	layout.region18.selector = MT6797_EMI_SELECTOR_BIT13_CLEAR;
	layout.region18.region = 18;
	layout.region19.start = layout.wmt_start;
	layout.region19.end = layout.wmt_end;
	layout.region19.selector = MT6797_EMI_SELECTOR_BIT13_CLEAR;
	layout.region19.region = 19;
	expect_init_error(&layout, &backend_desc, -ERANGE);

	/* Apply aliases, nulls, EMPTY, generations, permissions, and clearing. */
	gate = poisoned_gate();
	result = poisoned_result();
	{
		union {
			struct mt6797_emi_service_gate gate;
			struct mt6797_emi_service_result result;
		} aliased;
		unsigned char before[sizeof(aliased)];

		aliased.gate = gate;
		memcpy(before, &aliased, sizeof(aliased));
		assert(mt6797_emi_service_gate_apply(
			&aliased.gate, 1, 0,
			(struct mt6797_emi_service_result *)(void *)&aliased.gate) ==
			-EINVAL);
		assert(!memcmp(&aliased, before, sizeof(aliased)));
	}
	assert(mt6797_emi_service_gate_apply(NULL, 1, 0, &result) == -EINVAL);
	assert(!memcmp(&result, &(struct mt6797_emi_service_result){0},
		       sizeof(result)));
	assert(mt6797_emi_service_gate_apply(&gate, 1, 0, NULL) == -EINVAL);
	gate = (struct mt6797_emi_service_gate){0};
	result = poisoned_result();
	assert(mt6797_emi_service_gate_apply(&gate, 1, 0, &result) == -EINVAL);
	assert(!memcmp(&result, &(struct mt6797_emi_service_result){0},
		       sizeof(result)) && gate.state ==
	       MT6797_EMI_SERVICE_GATE_EMPTY);
	layout = valid_layout(9, MT6797_EMI_SELECTOR_BIT13_SET);
	assert(!mt6797_emi_service_gate_init(&gate, &layout, &backend_desc));
	context.gate = &gate;
	expect_apply_refusal(&gate, &context, 0, 0, -EINVAL);
	expect_apply_refusal(&gate, &context, 8, 0, -ESTALE);
	for (bit = 24; bit < 32; bit++)
		expect_apply_refusal(&gate, &context, 9, 1U << bit, -EINVAL);
	assert(!mt6797_emi_service_gate_apply(&gate, 9, 0xffffffU, &result));
	assert(gate.state == MT6797_EMI_SERVICE_GATE_COMPLETED);
	{
		struct mt6797_emi_service_gate terminal_gate = gate;
		struct callback_context terminal_context = context;

		result = poisoned_result();
		assert(mt6797_emi_service_gate_apply(&gate, 9, 0xffffffU,
						    &result) == -EALREADY);
		assert(!memcmp(&result, &(struct mt6797_emi_service_result){0},
		       sizeof(result)));
		assert(!memcmp(&gate, &terminal_gate, sizeof(gate)));
		assert(!memcmp(&context, &terminal_context, sizeof(context)));
	}

	/* A direct ATTEMPTED state is terminal even without a prior callback. */
	gate.state = MT6797_EMI_SERVICE_GATE_ATTEMPTED;
	expect_apply_refusal(&gate, &context, 9, 0, -EALREADY);

	/* ULLONG_MAX is a valid copied generation and apply token. */
	layout = valid_layout(ULLONG_MAX, MT6797_EMI_SELECTOR_BIT13_SET);
	context = (struct callback_context){.raw = 0};
	backend_desc = backend(&context);
	assert(!mt6797_emi_service_gate_init(&gate, &layout, &backend_desc));
	context.gate = &gate;
	assert(!mt6797_emi_service_gate_apply(&gate, ULLONG_MAX, 0, &result));
	assert(result.generation == ULLONG_MAX && context.calls == 1);

	/* The copied descriptor survives source mutation and observes ATTEMPTED. */
	layout = valid_layout(10, MT6797_EMI_SELECTOR_BIT13_SET);
	context = (struct callback_context){.raw = 0x1234567800000001ULL};
	backend_desc = backend(&context);
	assert(!mt6797_emi_service_gate_init(&gate, &layout, &backend_desc));
	context.gate = &gate;
	layout.generation = 99;
	layout.start = 0;
	layout.end = 1;
	layout.wlan_start = 0;
	layout.wlan_end = 1;
	layout.wmt_start = 2;
	layout.wmt_end = 3;
	layout.common_field = 4;
	layout.region18.start = 5;
	layout.region18.end = 6;
	layout.region18.selector = MT6797_EMI_SELECTOR_UNSET;
	layout.region18.region = 7;
	layout.region19.start = 8;
	layout.region19.end = 9;
	layout.region19.selector = MT6797_EMI_SELECTOR_UNSET;
	layout.region19.region = 10;
	backend_desc.call = other_callback;
	backend_desc.context = &replacement_context;
	assert(mt6797_emi_service_gate_apply(&gate, 10, 0xb6da2d, &result) == 1);
	assert(context.calls == 1 && context.saw_attempted &&
	       result.generation == 10 && result.raw == 0x1234567800000001ULL);

	/* Zero, declared, unknown, and boundary signed statuses retain raw words. */
	expect_success(0, 11, 0, 0);
	expect_success(0xffffffffULL, 12, 0, -1);
	expect_success(0xfffffffeULL, 13, 0, -2);
	expect_success(0xfffffffdULL, 14, 0, -3);
	expect_success(0xfffffffcULL, 15, 0, -4);
	expect_success(0xfffffffbULL, 16, 0, -5);
	expect_success(1, 17, 0, 1);
	expect_success(0x7fffffffULL, 18, 0, INT_MAX);
	expect_success(0x80000000ULL, 19, 0, INT_MIN);
	expect_success(0x80000001ULL, 20, 0, INT_MIN + 1);
	expect_success(0xdeadbeeffffffffdULL, 21, 0, -3);

	puts("emi_service_gate_alias_copy_prepare_attempt_result_status=pass");
	return 0;
}
