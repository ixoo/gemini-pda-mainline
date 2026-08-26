// SPDX-License-Identifier: GPL-2.0-only
/* Injected tests for the MT6797 A72 serialized platform-effect owner. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/mt6797-a72-provider.h>

#include "mt6797-a72-platform-state-internal.h"

enum mt6797_effect_test_action {
	MT6797_EFFECT_TEST_READ_P27 = 1,
	MT6797_EFFECT_TEST_WRITE_P27_SET,
	MT6797_EFFECT_TEST_WRITE_P27_RESTORE,
	MT6797_EFFECT_TEST_READ_BPLL,
	MT6797_EFFECT_TEST_PWRAP_ASSERT,
	MT6797_EFFECT_TEST_PWRAP_DEASSERT,
	MT6797_EFFECT_TEST_PWRAP_STATUS,
	MT6797_EFFECT_TEST_READ_ISOLATION,
	MT6797_EFFECT_TEST_WRITE_ISOLATION,
	MT6797_EFFECT_TEST_DELAY,
	MT6797_EFFECT_TEST_READ_DCM,
	MT6797_EFFECT_TEST_WRITE_DCM,
	MT6797_EFFECT_TEST_ACTION_COUNT,
};

#define MT6797_EFFECT_TEST_LOG_ENTRIES 32U

struct mt6797_effect_test_state {
	u32 spm_p27;
	u32 isolation;
	u32 bpll;
	u32 dcm;
	int pwrap_status;
	u32 actions[MT6797_EFFECT_TEST_LOG_ENTRIES];
	u32 values[MT6797_EFFECT_TEST_LOG_ENTRIES];
	unsigned int action_counts[MT6797_EFFECT_TEST_ACTION_COUNT];
	unsigned int calls;
	u32 fail_action;
	unsigned int fail_occurrence;
	u32 ignore_action;
	unsigned int ignore_occurrence;
};

static const struct mt6797_a72_platform_effect_handle test_handle = {
	.attempt_id = 0x1020304050607080ULL,
	.cookie = 0x8877665544332211ULL,
};

static const struct mt6797_a72_provider_handle test_provider = {
	.generation = 0x1020304050607080ULL,
	.cookie = 0x8877665544332211ULL,
};

static void
mt6797_effect_test_init(struct mt6797_effect_test_state *state)
{
	*state = (struct mt6797_effect_test_state){
		.spm_p27 = MT6797_A72_EFFECT_P27_BEFORE,
		.isolation = MT6797_A72_EFFECT_ISOLATION_BEFORE,
		.bpll = 0xa5a55a5a,
		.dcm = 0xa5000000,
	};
}

static bool
mt6797_effect_test_record(struct mt6797_effect_test_state *state, u32 action, u32 value)
{
	unsigned int occurrence;

	if (state->calls < ARRAY_SIZE(state->actions)) {
		state->actions[state->calls] = action;
		state->values[state->calls] = value;
	}
	state->calls++;
	occurrence = ++state->action_counts[action];
	return state->fail_action == action && state->fail_occurrence == occurrence;
}

static bool
mt6797_effect_test_ignore(struct mt6797_effect_test_state *state, u32 action)
{
	return state->ignore_action == action &&
	       state->ignore_occurrence == state->action_counts[action];
}

static int
mt6797_effect_test_spm_read(void *context, u32 offset, u32 *value)
{
	struct mt6797_effect_test_state *state = context;
	u32 action;

	if (offset == MT6797_A72_EFFECT_SPM_P27) {
		action = MT6797_EFFECT_TEST_READ_P27;
		*value = state->spm_p27;
	} else if (offset == MT6797_A72_EFFECT_SPM_ISOLATION) {
		action = MT6797_EFFECT_TEST_READ_ISOLATION;
		*value = state->isolation;
	} else {
		return -EINVAL;
	}
	return mt6797_effect_test_record(state, action, *value) ? -EIO : 0;
}

static int
mt6797_effect_test_spm_update_bits(void *context, u32 offset, u32 mask, u32 value)
{
	struct mt6797_effect_test_state *state = context;
	u32 action;
	u32 *word;

	if (offset == MT6797_A72_EFFECT_SPM_P27 && value == BIT(0)) {
		action = MT6797_EFFECT_TEST_WRITE_P27_SET;
		word = &state->spm_p27;
	} else if (offset == MT6797_A72_EFFECT_SPM_P27 && !value) {
		action = MT6797_EFFECT_TEST_WRITE_P27_RESTORE;
		word = &state->spm_p27;
	} else if (offset == MT6797_A72_EFFECT_SPM_ISOLATION && !value) {
		action = MT6797_EFFECT_TEST_WRITE_ISOLATION;
		word = &state->isolation;
	} else {
		return -EINVAL;
	}
	if (mt6797_effect_test_record(state, action, value))
		return -EIO;
	if (!mt6797_effect_test_ignore(state, action))
		*word = (*word & ~mask) | (value & mask);
	return 0;
}

static int
mt6797_effect_test_mcucfg_read(void *context, u32 offset, u32 *value)
{
	struct mt6797_effect_test_state *state = context;
	u32 action;

	if (offset == MT6797_A72_EFFECT_MCUCFG_BPLL) {
		action = MT6797_EFFECT_TEST_READ_BPLL;
		*value = state->bpll;
	} else if (offset == MT6797_A72_EFFECT_MCUCFG_DCM) {
		action = MT6797_EFFECT_TEST_READ_DCM;
		*value = state->dcm;
	} else {
		return -EINVAL;
	}
	return mt6797_effect_test_record(state, action, *value) ? -EIO : 0;
}

static void
mt6797_effect_test_mcucfg_write(void *context, u32 offset, u32 value)
{
	struct mt6797_effect_test_state *state = context;
	u32 action = MT6797_EFFECT_TEST_WRITE_DCM;

	if (offset != MT6797_A72_EFFECT_MCUCFG_DCM)
		return;
	mt6797_effect_test_record(state, action, value);
	if (!mt6797_effect_test_ignore(state, action))
		state->dcm = value;
}

static int
mt6797_effect_test_pwrap_assert(void *context)
{
	struct mt6797_effect_test_state *state = context;
	u32 action = MT6797_EFFECT_TEST_PWRAP_ASSERT;

	if (mt6797_effect_test_record(state, action, 1))
		return -EIO;
	if (!mt6797_effect_test_ignore(state, action))
		state->pwrap_status = 1;
	return 0;
}

static int
mt6797_effect_test_pwrap_deassert(void *context)
{
	struct mt6797_effect_test_state *state = context;
	u32 action = MT6797_EFFECT_TEST_PWRAP_DEASSERT;

	if (mt6797_effect_test_record(state, action, 0))
		return -EIO;
	if (!mt6797_effect_test_ignore(state, action))
		state->pwrap_status = 0;
	return 0;
}

static int
mt6797_effect_test_pwrap_status(void *context)
{
	struct mt6797_effect_test_state *state = context;
	u32 action = MT6797_EFFECT_TEST_PWRAP_STATUS;

	return mt6797_effect_test_record(state, action, state->pwrap_status) ? -EIO
									     : state->pwrap_status;
}

static void
mt6797_effect_test_delay(void *context, unsigned int min_us, unsigned int max_us)
{
	struct mt6797_effect_test_state *state = context;

	mt6797_effect_test_record(state, MT6797_EFFECT_TEST_DELAY, min_us << 16 | max_us);
}

static const struct mt6797_a72_platform_effect_ops test_ops = {
	.spm_read = mt6797_effect_test_spm_read,
	.spm_update_bits = mt6797_effect_test_spm_update_bits,
	.mcucfg_read = mt6797_effect_test_mcucfg_read,
	.mcucfg_write = mt6797_effect_test_mcucfg_write,
	.pwrap_assert = mt6797_effect_test_pwrap_assert,
	.pwrap_deassert = mt6797_effect_test_pwrap_deassert,
	.pwrap_status = mt6797_effect_test_pwrap_status,
	.delay = mt6797_effect_test_delay,
};

static int
mt6797_effect_test_acquire(struct mt6797_a72_platform_effect_owner *owner,
			   struct mt6797_effect_test_state *state,
			   struct mt6797_a72_platform_effect_result *result)
{
	return mt6797_a72_platform_effect_owner_p27_acquire(owner, &test_ops, state, &test_handle,
							    result);
}

static int
mt6797_effect_test_isolate(struct mt6797_a72_platform_effect_owner *owner,
			   struct mt6797_effect_test_state *state,
			   struct mt6797_a72_platform_effect_result *result)
{
	return mt6797_a72_effect_owner_isolate(owner, &test_ops, state, &test_handle,
					       &test_provider, result);
}

static void
mt6797_platform_effect_success_test(struct kunit *test)
{
	static const u32 expected_actions[] = {
		MT6797_EFFECT_TEST_READ_P27,	   MT6797_EFFECT_TEST_WRITE_P27_SET,
		MT6797_EFFECT_TEST_READ_P27,	   MT6797_EFFECT_TEST_READ_BPLL,
		MT6797_EFFECT_TEST_PWRAP_ASSERT,   MT6797_EFFECT_TEST_PWRAP_STATUS,
		MT6797_EFFECT_TEST_READ_P27,	   MT6797_EFFECT_TEST_READ_ISOLATION,
		MT6797_EFFECT_TEST_PWRAP_STATUS,   MT6797_EFFECT_TEST_WRITE_ISOLATION,
		MT6797_EFFECT_TEST_READ_ISOLATION, MT6797_EFFECT_TEST_PWRAP_DEASSERT,
		MT6797_EFFECT_TEST_PWRAP_STATUS,   MT6797_EFFECT_TEST_DELAY,
		MT6797_EFFECT_TEST_READ_DCM,	   MT6797_EFFECT_TEST_WRITE_DCM,
		MT6797_EFFECT_TEST_READ_DCM,	   MT6797_EFFECT_TEST_WRITE_DCM,
		MT6797_EFFECT_TEST_READ_DCM,
	};
	struct mt6797_a72_platform_effect_owner owner = {};
	struct mt6797_a72_platform_effect_result result;
	struct mt6797_effect_test_state state;
	int ret;

	mt6797_effect_test_init(&state);
	ret = mt6797_effect_test_acquire(&owner, &state, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, result.p27_owned);
	KUNIT_EXPECT_EQ(test, result.bpll_ordering_value, state.bpll);
	ret = mt6797_effect_test_isolate(&owner, &state, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, result.isolation_attempted);
	KUNIT_EXPECT_TRUE(test, result.isolation_crossed);
	ret = mt6797_a72_platform_effect_owner_dcm_update(&owner, &test_ops, &state, &test_handle,
							  true, false, &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, result.sealed);
	KUNIT_EXPECT_EQ(test, result.error, 0);
	KUNIT_EXPECT_EQ(test, result.dcm_toggle, (u32)0xa500000f);
	KUNIT_EXPECT_EQ(test, result.dcm_final, (u32)0xa500000d);
	KUNIT_EXPECT_EQ(test, state.dcm, (u32)0xa500000d);
	KUNIT_EXPECT_EQ(test, result.completed_effects,
			(u32)(GENMASK(8, 0) & ~MT6797_A72_EFFECT_P27_RESET_RESTORED));
	KUNIT_ASSERT_EQ(test, state.calls, (unsigned int)ARRAY_SIZE(expected_actions));
	KUNIT_EXPECT_MEMEQ(test, state.actions, expected_actions, sizeof(expected_actions));
}

static void
mt6797_platform_effect_p27_rejections_test(struct kunit *test)
{
	struct mt6797_a72_platform_effect_handle zero = {};
	struct mt6797_a72_platform_effect_owner owner = {};
	struct mt6797_a72_platform_effect_result result;
	struct mt6797_effect_test_state state;
	int ret;

	mt6797_effect_test_init(&state);
	ret = mt6797_a72_platform_effect_owner_p27_acquire(&owner, &test_ops, &state, &zero,
							   &result);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	KUNIT_EXPECT_EQ(test, state.calls, 0U);
	state.spm_p27 = MT6797_A72_EFFECT_P27_HELD;
	ret = mt6797_effect_test_acquire(&owner, &state, &result);
	KUNIT_EXPECT_EQ(test, ret, -ERANGE);
	KUNIT_EXPECT_TRUE(test, result.sealed);
	KUNIT_EXPECT_FALSE(test, result.p27_owned);
	KUNIT_EXPECT_EQ(test, state.calls, 1U);
	state.spm_p27 = MT6797_A72_EFFECT_P27_BEFORE;
	ret = mt6797_effect_test_acquire(&owner, &state, &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, state.calls, 1U);
}

static void
mt6797_platform_effect_p27_failures_test(struct kunit *test)
{
	static const struct {
		u32 fail_action;
		unsigned int fail_occurrence;
		u32 ignore_action;
		unsigned int ignore_occurrence;
		bool owned;
	} cases[] = {
		{ MT6797_EFFECT_TEST_READ_P27, 1, 0, 0, false },
		{ MT6797_EFFECT_TEST_WRITE_P27_SET, 1, 0, 0, true },
		{ MT6797_EFFECT_TEST_READ_P27, 2, 0, 0, true },
		{ 0, 0, MT6797_EFFECT_TEST_WRITE_P27_SET, 1, true },
		{ MT6797_EFFECT_TEST_READ_BPLL, 1, 0, 0, true },
		{ MT6797_EFFECT_TEST_PWRAP_ASSERT, 1, 0, 0, true },
		{ MT6797_EFFECT_TEST_PWRAP_STATUS, 1, 0, 0, true },
		{ 0, 0, MT6797_EFFECT_TEST_PWRAP_ASSERT, 1, true },
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(cases); i++) {
		struct mt6797_a72_platform_effect_owner owner = {};
		struct mt6797_a72_platform_effect_result result;
		struct mt6797_effect_test_state state;
		int ret;

		mt6797_effect_test_init(&state);
		state.fail_action = cases[i].fail_action;
		state.fail_occurrence = cases[i].fail_occurrence;
		state.ignore_action = cases[i].ignore_action;
		state.ignore_occurrence = cases[i].ignore_occurrence;
		ret = mt6797_effect_test_acquire(&owner, &state, &result);
		KUNIT_EXPECT_LT_MSG(test, ret, 0, "case=%u", i);
		KUNIT_EXPECT_TRUE(test, result.sealed);
		KUNIT_EXPECT_EQ_MSG(test, result.p27_owned, cases[i].owned, "case=%u", i);
	}
}

static void
mt6797_platform_effect_release_test(struct kunit *test)
{
	struct mt6797_a72_platform_effect_handle foreign = test_handle;
	struct mt6797_a72_platform_effect_owner owner = {};
	struct mt6797_a72_platform_effect_result result;
	struct mt6797_effect_test_state state;
	unsigned int calls;
	int ret;

	mt6797_effect_test_init(&state);
	KUNIT_ASSERT_EQ(test, mt6797_effect_test_acquire(&owner, &state, &result), 0);
	foreign.cookie++;
	calls = state.calls;
	ret = mt6797_a72_platform_effect_owner_p27_release(&owner, &test_ops, &state, &foreign,
							   &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, state.calls, calls);
	ret = mt6797_a72_platform_effect_owner_p27_release(&owner, &test_ops, &state, &test_handle,
							   &result);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_FALSE(test, result.p27_owned);
	KUNIT_EXPECT_TRUE(test, result.sealed);
	KUNIT_EXPECT_EQ(test, state.spm_p27, MT6797_A72_EFFECT_P27_BEFORE);
	KUNIT_EXPECT_EQ(test, state.pwrap_status, 0);
	ret = mt6797_a72_platform_effect_owner_p27_release(&owner, &test_ops, &state, &test_handle,
							   &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
}

static void
mt6797_platform_effect_release_failures_test(struct kunit *test)
{
	static const struct {
		u32 fail_action;
		unsigned int fail_occurrence;
		u32 ignore_action;
		unsigned int ignore_occurrence;
	} cases[] = {
		{ MT6797_EFFECT_TEST_PWRAP_DEASSERT, 1, 0, 0 },
		{ MT6797_EFFECT_TEST_PWRAP_STATUS, 2, 0, 0 },
		{ 0, 0, MT6797_EFFECT_TEST_PWRAP_DEASSERT, 1 },
		{ MT6797_EFFECT_TEST_WRITE_P27_RESTORE, 1, 0, 0 },
		{ MT6797_EFFECT_TEST_READ_P27, 4, 0, 0 },
		{ 0, 0, MT6797_EFFECT_TEST_WRITE_P27_RESTORE, 1 },
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(cases); i++) {
		struct mt6797_a72_platform_effect_owner owner = {};
		struct mt6797_a72_platform_effect_result result;
		struct mt6797_effect_test_state state;
		int ret;

		mt6797_effect_test_init(&state);
		KUNIT_ASSERT_EQ(test, mt6797_effect_test_acquire(&owner, &state, &result), 0);
		state.fail_action = cases[i].fail_action;
		state.fail_occurrence = cases[i].fail_occurrence;
		state.ignore_action = cases[i].ignore_action;
		state.ignore_occurrence = cases[i].ignore_occurrence;
		ret = mt6797_a72_platform_effect_owner_p27_release(&owner, &test_ops, &state,
								   &test_handle, &result);
		KUNIT_EXPECT_LT_MSG(test, ret, 0, "case=%u", i);
		KUNIT_EXPECT_TRUE(test, result.sealed);
		KUNIT_EXPECT_TRUE(test, result.p27_owned);
	}
}

static void
mt6797_platform_effect_isolation_guards_test(struct kunit *test)
{
	struct mt6797_a72_provider_handle foreign = test_provider;
	struct mt6797_a72_platform_effect_owner owner = {};
	struct mt6797_a72_platform_effect_result result;
	struct mt6797_effect_test_state state;
	unsigned int calls;
	int ret;

	mt6797_effect_test_init(&state);
	KUNIT_ASSERT_EQ(test, mt6797_effect_test_acquire(&owner, &state, &result), 0);
	foreign.cookie++;
	calls = state.calls;
	ret = mt6797_a72_effect_owner_isolate(&owner, &test_ops, &state, &test_handle, &foreign,
					      &result);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, state.calls, calls);
	KUNIT_EXPECT_FALSE(test, result.isolation_attempted);
	ret = mt6797_effect_test_isolate(&owner, &state, &result);
	KUNIT_EXPECT_EQ(test, ret, 0);
	ret = mt6797_a72_platform_effect_owner_p27_release(&owner, &test_ops, &state, &test_handle,
							   &result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
}

static void
mt6797_platform_effect_isolation_failures_test(struct kunit *test)
{
	static const struct {
		u32 fail_action;
		unsigned int fail_occurrence;
		u32 ignore_action;
		unsigned int ignore_occurrence;
	} cases[] = {
		{ MT6797_EFFECT_TEST_READ_ISOLATION, 1, 0, 0 },
		{ MT6797_EFFECT_TEST_WRITE_ISOLATION, 1, 0, 0 },
		{ MT6797_EFFECT_TEST_READ_ISOLATION, 2, 0, 0 },
		{ 0, 0, MT6797_EFFECT_TEST_WRITE_ISOLATION, 1 },
		{ MT6797_EFFECT_TEST_PWRAP_DEASSERT, 1, 0, 0 },
		{ MT6797_EFFECT_TEST_PWRAP_STATUS, 2, 0, 0 },
		{ 0, 0, MT6797_EFFECT_TEST_PWRAP_DEASSERT, 1 },
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(cases); i++) {
		struct mt6797_a72_platform_effect_owner owner = {};
		struct mt6797_a72_platform_effect_result result;
		struct mt6797_effect_test_state state;
		int ret;

		mt6797_effect_test_init(&state);
		KUNIT_ASSERT_EQ(test, mt6797_effect_test_acquire(&owner, &state, &result), 0);
		state.fail_action = cases[i].fail_action;
		state.fail_occurrence = cases[i].fail_occurrence;
		state.ignore_action = cases[i].ignore_action;
		state.ignore_occurrence = cases[i].ignore_occurrence;
		ret = mt6797_effect_test_isolate(&owner, &state, &result);
		KUNIT_EXPECT_LT_MSG(test, ret, 0, "case=%u", i);
		KUNIT_EXPECT_TRUE(test, result.sealed);
		KUNIT_EXPECT_TRUE(test, result.isolation_attempted);
		KUNIT_EXPECT_TRUE(test, result.p27_owned);
	}
}

static void
mt6797_platform_effect_dcm_failures_test(struct kunit *test)
{
	static const struct {
		bool cpu8_online;
		bool cpu9_online;
		u32 initial_dcm;
		u32 fail_action;
		unsigned int fail_occurrence;
		u32 ignore_action;
		unsigned int ignore_occurrence;
	} cases[] = {
		{ false, false, 0xa5000000, 0, 0, 0, 0 },
		{ true, true, 0xa5000000, 0, 0, 0, 0 },
		{ true, false, 0xa5000001, 0, 0, 0, 0 },
		{ true, false, 0xa5000000, MT6797_EFFECT_TEST_READ_DCM, 1, 0, 0 },
		{ true, false, 0xa5000000, MT6797_EFFECT_TEST_READ_DCM, 2, 0, 0 },
		{ true, false, 0xa5000000, 0, 0, MT6797_EFFECT_TEST_WRITE_DCM, 1 },
		{ true, false, 0xa5000000, MT6797_EFFECT_TEST_READ_DCM, 3, 0, 0 },
		{ true, false, 0xa5000000, 0, 0, MT6797_EFFECT_TEST_WRITE_DCM, 2 },
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(cases); i++) {
		struct mt6797_a72_platform_effect_owner owner = {};
		struct mt6797_a72_platform_effect_result result;
		struct mt6797_effect_test_state state;
		int ret;

		mt6797_effect_test_init(&state);
		KUNIT_ASSERT_EQ(test, mt6797_effect_test_acquire(&owner, &state, &result), 0);
		KUNIT_ASSERT_EQ(test, mt6797_effect_test_isolate(&owner, &state, &result), 0);
		state.dcm = cases[i].initial_dcm;
		state.fail_action = cases[i].fail_action;
		state.fail_occurrence = cases[i].fail_occurrence;
		state.ignore_action = cases[i].ignore_action;
		state.ignore_occurrence = cases[i].ignore_occurrence;
		ret = mt6797_a72_platform_effect_owner_dcm_update(&owner, &test_ops, &state,
			&test_handle, cases[i].cpu8_online,
			cases[i].cpu9_online, &result);
		KUNIT_EXPECT_LT_MSG(test, ret, 0, "case=%u", i);
		KUNIT_EXPECT_TRUE(test, result.sealed);
		KUNIT_EXPECT_TRUE(test, result.p27_owned);
		KUNIT_EXPECT_TRUE(test, result.isolation_crossed);
	}
}

static struct kunit_case mt6797_platform_effect_cases[] = {
	KUNIT_CASE(mt6797_platform_effect_success_test),
	KUNIT_CASE(mt6797_platform_effect_p27_rejections_test),
	KUNIT_CASE(mt6797_platform_effect_p27_failures_test),
	KUNIT_CASE(mt6797_platform_effect_release_test),
	KUNIT_CASE(mt6797_platform_effect_release_failures_test),
	KUNIT_CASE(mt6797_platform_effect_isolation_guards_test),
	KUNIT_CASE(mt6797_platform_effect_isolation_failures_test),
	KUNIT_CASE(mt6797_platform_effect_dcm_failures_test),
	{}
};

static struct kunit_suite mt6797_platform_effect_suite = {
	.name = "mt6797-a72-platform-effects",
	.test_cases = mt6797_platform_effect_cases,
};

kunit_test_suite(mt6797_platform_effect_suite);

MODULE_LICENSE("GPL");
