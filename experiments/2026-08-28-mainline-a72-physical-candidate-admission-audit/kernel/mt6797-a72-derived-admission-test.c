// SPDX-License-Identifier: GPL-2.0-only
/* Hardware-free tests for source-derived MT6797 CPU8 admission. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/string.h>

#include <asm/late_cpu_startup.h>
#include <asm/memory.h>
#include <asm/mt6797_a72_membership.h>
#include <asm/smp.h>

struct mt6797_a72_derived_test_state {
	struct mt6797_a72_direct_topology topology;
	struct mt6797_a72_direct_source_snapshot source;
	struct arm64_late_cpu_ready_token ready;
	struct mt6797_a72_transaction transaction;
	struct mt6797_a72_owner_snapshot owner;
	int source_result;
	u32 source_calls;
};

static struct mt6797_a72_direct_topology mt6797_a72_exact_topology(void)
{
	return (struct mt6797_a72_direct_topology) {
		.cpu8_possible = 1,
		.cpu9_possible = 1,
		.cpu8_present = 1,
		.cpu9_present = 1,
		.cpu8_method_valid = 1,
		.cpu9_method_valid = 1,
		.cpu8_mpidr = 0x200,
		.cpu9_mpidr = 0x201,
	};
}

static struct mt6797_a72_direct_source_snapshot mt6797_a72_exact_source(void)
{
	return (struct mt6797_a72_direct_source_snapshot) {
		.abi = MT6797_A72_DIRECT_SOURCE_ABI,
		.valid = 1,
		.provider = {
			.abi = MT6797_A72_PROVIDER_STATE_ABI,
			.valid = 1,
			.control_a = 0x7b,
			.status_b = 0xc1,
			.vbuckb_a = 0x46,
			.vbuckb_b = 0x46,
		},
		.platform = {
			.spm_pwr_status = 0x2a00005c,
			.spm_pwr_status_2nd = 0x2a00004c,
			.spm_cpu_pwr_status = 0x00350c08,
			.spm_cpu_pwr_status_2nd = 0x00350cff,
			.spm_mp2_cpusys_pwr_con = 0x00010132,
			.spm_cpu_ext_buck_iso = 0x00000002,
			.valid = true,
		},
		.clock = {
			.abi = MT6797_DVFSP_CLOCK_BACKEND_ABI,
			.sample_generation = 1,
		},
		.bigidvfs = {
			.abi = MT6797_BIGIDVFS_BACKEND_ABI,
			.sample_generation = 1,
		},
	};
}

static int
mt6797_a72_derived_source_snapshot(void *context,
				   struct mt6797_a72_direct_source_snapshot *snapshot)
{
	struct mt6797_a72_derived_test_state *state = context;

	state->source_calls++;
	if (state->source_result)
		return state->source_result;
	*snapshot = state->source;
	return 0;
}

static const struct mt6797_a72_direct_source_ops mt6797_a72_derived_source_ops = {
	.snapshot = mt6797_a72_derived_source_snapshot,
};

static void mt6797_a72_derived_source_unregister(void *context)
{
	mt6797_a72_direct_source_unregister(&mt6797_a72_derived_source_ops,
					    context);
}

static struct arm64_late_cpu_ready_token mt6797_a72_exact_ready(void)
{
	struct arm64_late_cpu_ready_token ready = {
		.abi = ARM64_LATE_CPU_PLAN_ABI,
		.plan_identity = { 1, 2, 3, 4 },
		.source_parent_identity = { 5, 6, 7, 8 },
		.config_input_identity = { 9, 10, 11, 12 },
		.evidence_identity = { 13, 14, 15, 16 },
		.target_cpu = { 8, 9 },
		.expected_target_mpidr = { 0x200, 0x201 },
		.observed_target_mpidr = { 0x200, 0x201 },
	};

	strscpy(ready.profile_id, "mt6797-a53-a72-a41-v7",
		sizeof(ready.profile_id));
	cpumask_set_cpu(8, &ready.target_cpus);
	cpumask_set_cpu(9, &ready.target_cpus);
	return ready;
}

static struct mt6797_a72_entry_snapshot mt6797_a72_legacy_entry(void)
{
	return (struct mt6797_a72_entry_snapshot) {
		.cpuhp_state_cpu8 = CPUHP_OFFLINE,
		.cpuhp_state_cpu9 = CPUHP_OFFLINE,
		.observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN,
		.flags = MT6797_A72_ENTRY_FLAGS_MASK,
		.cpu8_mpidr = 0x200,
		.cpu9_mpidr = 0x201,
	};
}

static struct mt6797_a72_a36_prestate mt6797_a72_legacy_assertions(void)
{
	return (struct mt6797_a72_a36_prestate) {
		.abi = MT6797_A72_A36_PRESTATE_ABI,
		.operation = ARM64_LATE_CPU_STARTUP_OP_CPU8_UP,
		.observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN,
		.call_shape = MT6797_A72_A36_CALL_SHAPE_TWO_ARG,
		.da921x_page = MT6797_A72_A36_DA921X_PAGE,
		.buckb_vsel = MT6797_A72_A36_BUCKB_VSEL,
		.spm_218 = MT6797_A72_A36_SPM_218,
		.spm_290 = MT6797_A72_A36_SPM_290,
		.secure_sentinels_stable = 1,
		.protected_clock_valid = 1,
		.pstore_console_available = 1,
		.watchdog_owned = 1,
		.target_mpidr = 0x200,
		.secondary_entry_pa = __pa_symbol(secondary_entry),
		.generation = 1,
		.cookie = 0xa7200001,
	};
}

static bool
mt6797_a72_transaction_empty(const struct mt6797_a72_transaction *transaction)
{
	return !memchr_inv(transaction, 0, sizeof(*transaction));
}

static void mt6797_a72_derived_reset_closed(void)
{
	arm64_late_cpu_startup_test_reset();
	mt6797_a72_membership_test_reset();
}

static void mt6797_a72_derived_seed_available(void)
{
	mt6797_a72_derived_reset_closed();
	mt6797_a72_membership_test_seed_available();
}

static int mt6797_a72_derived_test_init(struct kunit *test)
{
	struct mt6797_a72_derived_test_state *state;
	int ret;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	if (!state)
		return -ENOMEM;
	test->priv = state;
	state->topology = mt6797_a72_exact_topology();
	state->source = mt6797_a72_exact_source();
	state->ready = mt6797_a72_exact_ready();
	mt6797_a72_derived_reset_closed();
	ret = mt6797_a72_direct_source_register(&mt6797_a72_derived_source_ops,
						state);
	if (ret)
		return ret;
	return kunit_add_action_or_reset(test,
					 mt6797_a72_derived_source_unregister,
					 state);
}

static void mt6797_a72_derived_success_test(struct kunit *test)
{
	struct mt6797_a72_derived_test_state *state = test->priv;
	const struct mt6797_a72_a36_prestate *a36;
	int ret;

	state->topology = mt6797_a72_exact_topology();
	state->source = mt6797_a72_exact_source();
	state->ready = mt6797_a72_exact_ready();
	state->source_result = 0;
	state->source_calls = 0;
	mt6797_a72_derived_reset_closed();
	ret = mt6797_a72_membership_test_derive_cpu8(&state->topology,
						     &state->ready,
						     &state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)1);
	a36 = &state->transaction.a36_prestate;
	KUNIT_EXPECT_EQ(test, a36->abi, (u32)MT6797_A72_A36_PRESTATE_ABI);
	KUNIT_EXPECT_EQ(test, a36->da921x_page, (u32)0);
	KUNIT_EXPECT_EQ(test, a36->buckb_enabled, (u32)0);
	KUNIT_EXPECT_EQ(test, a36->buckb_vsel,
			(u32)MT6797_A72_A36_BUCKB_VSEL);
	KUNIT_EXPECT_EQ(test, a36->spm_218, (u32)MT6797_A72_A36_SPM_218);
	KUNIT_EXPECT_EQ(test, a36->spm_290, (u32)MT6797_A72_A36_SPM_290);
	KUNIT_EXPECT_EQ(test, a36->secure_sentinels_stable, (u32)0);
	KUNIT_EXPECT_EQ(test, a36->protected_clock_valid, (u32)1);
	KUNIT_EXPECT_EQ(test, a36->pstore_console_available, (u32)0);
	KUNIT_EXPECT_EQ(test, a36->watchdog_owned, (u32)0);
	KUNIT_EXPECT_EQ(test, a36->generation,
			state->transaction.identity.generation);
	KUNIT_EXPECT_EQ(test, a36->cookie, state->transaction.identity.cookie);
	mt6797_a72_membership_snapshot(&state->owner);
	KUNIT_EXPECT_EQ(test, state->owner.health,
			(u32)MT6797_A72_OWNER_AVAILABLE);
	KUNIT_EXPECT_EQ(test, state->owner.phase,
			(u32)MT6797_A72_PHASE_FROZEN);
	KUNIT_EXPECT_EQ(test, mt6797_a72_membership_publish_up(&state->transaction),
			0);
	mt6797_a72_membership_snapshot(&state->owner);
	KUNIT_EXPECT_EQ(test, state->owner.phase,
			(u32)MT6797_A72_PHASE_ON_ISSUED);
}

static void
mt6797_a72_expect_source_rejection(struct kunit *test,
				   struct mt6797_a72_derived_test_state *state,
				   int expected, u32 expected_calls)
{
	int ret;

	mt6797_a72_derived_reset_closed();
	state->source_calls = 0;
	memset(&state->transaction, 0xa5, sizeof(state->transaction));
	ret = mt6797_a72_membership_test_derive_cpu8(&state->topology,
						     &state->ready,
						     &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, expected);
	KUNIT_EXPECT_EQ(test, state->source_calls, expected_calls);
	KUNIT_EXPECT_TRUE(test, mt6797_a72_transaction_empty(&state->transaction));
	mt6797_a72_membership_snapshot(&state->owner);
	KUNIT_EXPECT_EQ(test, state->owner.health,
			(u32)MT6797_A72_OWNER_CLOSED);
	KUNIT_EXPECT_EQ(test, state->owner.phase,
			(u32)MT6797_A72_PHASE_UNINITIALIZED);
	KUNIT_EXPECT_EQ(test, state->owner.attempts_consumed, (u32)0);
}

static void mt6797_a72_derived_source_rejections_test(struct kunit *test)
{
	struct mt6797_a72_derived_test_state *state = test->priv;

	state->ready = mt6797_a72_exact_ready();
	state->topology = mt6797_a72_exact_topology();
	state->source = mt6797_a72_exact_source();
	state->source_result = -EPROBE_DEFER;
	mt6797_a72_expect_source_rejection(test, state, -EPROBE_DEFER, 1);
	state->source_result = 0;
	state->source = mt6797_a72_exact_source();
	state->source.valid = 0;
	mt6797_a72_expect_source_rejection(test, state, -EPROTO, 1);
	state->source = mt6797_a72_exact_source();
	state->source.provider.control_a ^= 1;
	mt6797_a72_expect_source_rejection(test, state, -EPERM, 1);
	state->source = mt6797_a72_exact_source();
	state->topology = mt6797_a72_exact_topology();
	state->topology.cpu8_possible = 0;
	mt6797_a72_expect_source_rejection(test, state, -EPERM, 0);
	state->topology = mt6797_a72_exact_topology();
	state->source.clock.sample_generation++;
	mt6797_a72_expect_source_rejection(test, state, -EPERM, 1);
}

static void mt6797_a72_derived_ready_rejection_test(struct kunit *test)
{
	struct mt6797_a72_derived_test_state *state = test->priv;
	int ret;

	state->ready = mt6797_a72_exact_ready();
	memset(state->ready.plan_identity, 0,
	       sizeof(state->ready.plan_identity));
	state->source_calls = 0;
	mt6797_a72_derived_reset_closed();
	ret = mt6797_a72_membership_test_derive_cpu8(&state->topology,
						     &state->ready,
						     &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)0);
	KUNIT_EXPECT_TRUE(test, mt6797_a72_transaction_empty(&state->transaction));
	mt6797_a72_membership_snapshot(&state->owner);
	KUNIT_EXPECT_EQ(test, state->owner.health,
			(u32)MT6797_A72_OWNER_CLOSED);
	KUNIT_EXPECT_EQ(test, state->owner.phase,
			(u32)MT6797_A72_PHASE_UNINITIALIZED);
	KUNIT_EXPECT_EQ(test, state->owner.attempts_consumed, (u32)0);
}

static void mt6797_a72_legacy_assertions_rejected_test(struct kunit *test)
{
	struct mt6797_a72_derived_test_state *state = test->priv;
	struct mt6797_a72_entry_snapshot entry = mt6797_a72_legacy_entry();
	struct mt6797_a72_a36_prestate a36 = mt6797_a72_legacy_assertions();
	int ret;

	state->ready = mt6797_a72_exact_ready();
	mt6797_a72_derived_seed_available();
	ret = mt6797_a72_membership_begin_up(8, CPUHP_ONLINE,
					     MT6797_A72_ATTEMPT_CPU8_UP,
					     &entry, &state->ready, &a36,
					     &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_TRUE(test, mt6797_a72_transaction_empty(&state->transaction));
	mt6797_a72_membership_snapshot(&state->owner);
	KUNIT_EXPECT_EQ(test, state->owner.phase,
			(u32)MT6797_A72_PHASE_REJECTED);
}

static void mt6797_a72_derived_repeat_rejected_test(struct kunit *test)
{
	struct mt6797_a72_derived_test_state *state = test->priv;
	struct mt6797_a72_transaction second;
	int ret;

	state->topology = mt6797_a72_exact_topology();
	state->source = mt6797_a72_exact_source();
	state->ready = mt6797_a72_exact_ready();
	state->source_result = 0;
	state->source_calls = 0;
	mt6797_a72_derived_reset_closed();
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_membership_test_derive_cpu8(&state->topology,
							       &state->ready,
							       &state->transaction), 0);
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_membership_publish_up(&state->transaction), 0);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)1);
	memset(&second, 0xa5, sizeof(second));
	ret = mt6797_a72_membership_test_derive_cpu8(&state->topology,
						     &state->ready, &second);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)1);
	KUNIT_EXPECT_TRUE(test, mt6797_a72_transaction_empty(&second));
}

static struct kunit_case mt6797_a72_derived_admission_cases[] = {
	KUNIT_CASE(mt6797_a72_derived_success_test),
	KUNIT_CASE(mt6797_a72_derived_source_rejections_test),
	KUNIT_CASE(mt6797_a72_derived_ready_rejection_test),
	KUNIT_CASE(mt6797_a72_legacy_assertions_rejected_test),
	KUNIT_CASE(mt6797_a72_derived_repeat_rejected_test),
	{}
};

static struct kunit_suite mt6797_a72_derived_admission_suite = {
	.name = "mt6797-a72-derived-admission",
	.init = mt6797_a72_derived_test_init,
	.test_cases = mt6797_a72_derived_admission_cases,
};

kunit_test_suite(mt6797_a72_derived_admission_suite);

MODULE_LICENSE("GPL");
