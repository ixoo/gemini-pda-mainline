// SPDX-License-Identifier: GPL-2.0-only

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/slab.h>

#include <asm/mt6797_a72_membership.h>

struct mt6797_a34_test_state {
	struct mt6797_a72_a34_observation *observation;
	struct mt6797_a72_owner_snapshot *before;
	struct mt6797_a72_owner_snapshot *after;
};

static void
mt6797_a34_fill_valid(struct mt6797_a72_a34_observation *observation)
{
	memset(observation, 0, sizeof(*observation));
	observation->abi = MT6797_A72_A34_ELIGIBILITY_ABI;
	observation->direct.abi = MT6797_A72_DIRECT_STATE_ABI;
	observation->direct.valid = 1;
	observation->direct.cpu8_possible = 1;
	observation->direct.cpu9_possible = 1;
	observation->direct.cpu8_present = 1;
	observation->direct.cpu9_present = 1;
	observation->direct.cpu8_method_valid = 1;
	observation->direct.cpu9_method_valid = 1;
	observation->direct.cpu8_mpidr = 0x200;
	observation->direct.cpu9_mpidr = 0x201;
	observation->direct.source.abi = MT6797_A72_DIRECT_SOURCE_ABI;
	observation->direct.source.valid = 1;
	observation->direct.source.provider.abi =
		MT6797_A72_PROVIDER_STATE_ABI;
	observation->direct.source.provider.valid = 1;
	observation->direct.source.provider.control_a = 0x7b;
	observation->direct.source.provider.status_b = 0xc1;
	observation->direct.source.provider.vbuckb_a = 0x46;
	observation->direct.source.provider.vbuckb_b = 0x46;
	observation->direct.source.platform.spm_pwr_status = 0x2a00005c;
	observation->direct.source.platform.spm_pwr_status_2nd = 0x2a00004c;
	observation->direct.source.platform.spm_cpu_pwr_status = 0x00350c08;
	observation->direct.source.platform.spm_cpu_pwr_status_2nd = 0x00350cff;
	observation->direct.source.platform.spm_mp2_cpusys_pwr_con =
		0x00010132;
	observation->direct.source.platform.spm_cpu_ext_buck_iso = 0x00000002;
	observation->direct.source.platform.valid = true;
	observation->direct.source.clock.abi =
		MT6797_DVFSP_CLOCK_BACKEND_ABI;
	observation->direct.source.clock.sample_generation = 1;
	observation->direct.source.bigidvfs.abi = MT6797_BIGIDVFS_BACKEND_ABI;
	observation->direct.source.bigidvfs.sample_generation = 1;
	observation->direct.owner.diagnostic_blockers = MT6797_A72_BLOCK_MASK;
	observation->direct.owner.abi = MT6797_A72_TRANSACTION_ABI;
	observation->direct.owner.health = MT6797_A72_OWNER_CLOSED;
	observation->direct.owner.phase = MT6797_A72_PHASE_UNINITIALIZED;
	observation->direct.owner.provider_state = MT6797_A72_PROVIDER_NONE;
	observation->replay.abi = MT6797_A72_A34_REPLAY_ABI;
	observation->replay.valid = 1;
	observation->replay.proof =
		MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR;
}

static int mt6797_a34_test_init(struct kunit *test)
{
	struct mt6797_a34_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	if (!state)
		return -ENOMEM;
	state->observation = kunit_kzalloc(test, sizeof(*state->observation),
					   GFP_KERNEL);
	if (!state->observation)
		return -ENOMEM;
	state->before = kunit_kzalloc(test, sizeof(*state->before), GFP_KERNEL);
	if (!state->before)
		return -ENOMEM;
	state->after = kunit_kzalloc(test, sizeof(*state->after), GFP_KERNEL);
	if (!state->after)
		return -ENOMEM;
	test->priv = state;
	mt6797_a72_membership_test_reset();
	mt6797_a34_fill_valid(state->observation);
	return 0;
}

static void mt6797_a34_test_exit(struct kunit *test)
{
	(void)test;
	mt6797_a72_membership_test_reset();
}

static void
mt6797_a34_expect_result_unchanged(struct kunit *test,
				   struct mt6797_a34_test_state *state,
				   int expected)
{
	int ret;

	mt6797_a72_membership_snapshot(state->before);
	ret = mt6797_a72_a34_evaluate(state->observation);
	mt6797_a72_membership_snapshot(state->after);
	KUNIT_EXPECT_EQ(test, ret, expected);
	KUNIT_EXPECT_MEMEQ(test, state->before, state->after,
			   sizeof(*state->before));
}

static void mt6797_a34_exact_direct_replay_test(struct kunit *test)
{
	struct mt6797_a34_test_state *state = test->priv;

	mt6797_a34_expect_result_unchanged(test, state, 0);
}

static void mt6797_a34_null_test(struct kunit *test)
{
	struct mt6797_a34_test_state *state = test->priv;
	int ret;

	mt6797_a72_membership_snapshot(state->before);
	ret = mt6797_a72_a34_evaluate(NULL);
	mt6797_a72_membership_snapshot(state->after);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	KUNIT_EXPECT_MEMEQ(test, state->before, state->after,
			   sizeof(*state->before));
}

static void mt6797_a34_every_byte_mutation_test(struct kunit *test)
{
	struct mt6797_a34_test_state *state = test->priv;
	u8 *bytes = (u8 *)state->observation;
	size_t offset;
	int ret;

	mt6797_a72_membership_snapshot(state->before);
	for (offset = 0; offset < sizeof(*state->observation); offset++) {
		mt6797_a34_fill_valid(state->observation);
		bytes[offset] ^= 1;
		ret = mt6797_a72_a34_evaluate(state->observation);
		KUNIT_EXPECT_EQ_MSG(test, ret, -EPERM,
				    "mutation offset %zu", offset);
	}
	mt6797_a72_membership_snapshot(state->after);
	KUNIT_EXPECT_MEMEQ(test, state->before, state->after,
			   sizeof(*state->before));
}

static void mt6797_a34_missing_replay_test(struct kunit *test)
{
	struct mt6797_a34_test_state *state = test->priv;

	state->observation->replay.proof = MT6797_A72_A34_REPLAY_UNKNOWN;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
	mt6797_a34_fill_valid(state->observation);
	state->observation->replay.valid = 0;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
}

static void mt6797_a34_admission_remains_closed_test(struct kunit *test)
{
	struct mt6797_a34_test_state *state = test->priv;
	int ret;

	mt6797_a34_expect_result_unchanged(test, state, 0);
	mt6797_a72_membership_snapshot(state->after);
	KUNIT_EXPECT_EQ(test, state->after->health, MT6797_A72_OWNER_CLOSED);
	KUNIT_EXPECT_EQ(test, state->after->phase,
			MT6797_A72_PHASE_UNINITIALIZED);
	KUNIT_EXPECT_EQ(test, state->after->attempts_available, 0U);
	ret = mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
}

static struct kunit_case mt6797_a34_test_cases[] = {
	KUNIT_CASE(mt6797_a34_exact_direct_replay_test),
	KUNIT_CASE(mt6797_a34_null_test),
	KUNIT_CASE(mt6797_a34_every_byte_mutation_test),
	KUNIT_CASE(mt6797_a34_missing_replay_test),
	KUNIT_CASE(mt6797_a34_admission_remains_closed_test),
	{}
};

static struct kunit_suite mt6797_a34_test_suite = {
	.name = "mt6797-a72-a34-eligibility",
	.init = mt6797_a34_test_init,
	.exit = mt6797_a34_test_exit,
	.test_cases = mt6797_a34_test_cases,
};

kunit_test_suite(mt6797_a34_test_suite);

MODULE_LICENSE("GPL");
