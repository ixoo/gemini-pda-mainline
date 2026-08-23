// SPDX-License-Identifier: GPL-2.0-only

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/string.h>

#include <asm/mt6797_a72_membership.h>

enum direct_source_mutation {
	DIRECT_MUTATION_NONE,
	DIRECT_MUTATION_ABI,
	DIRECT_MUTATION_VALID,
	DIRECT_MUTATION_RESERVED,
	DIRECT_MUTATION_PROVIDER_ABI,
	DIRECT_MUTATION_PROVIDER_VALID,
	DIRECT_MUTATION_PROVIDER_RESERVED,
	DIRECT_MUTATION_PROVIDER_WIDTH,
	DIRECT_MUTATION_PLATFORM_VALID,
	DIRECT_MUTATION_CLOCK_ABI,
	DIRECT_MUTATION_CLOCK_RESERVED,
	DIRECT_MUTATION_CLOCK_GENERATION,
	DIRECT_MUTATION_BIGIDVFS_ABI,
	DIRECT_MUTATION_BIGIDVFS_RESERVED,
	DIRECT_MUTATION_BIGIDVFS_GENERATION,
};

struct direct_test_state {
	struct mt6797_a72_direct_source_snapshot source;
	enum direct_source_mutation mutation;
	int callback_result;
	u32 calls;
};

static struct mt6797_a72_direct_topology direct_topology(void)
{
	return (struct mt6797_a72_direct_topology) {
		.cpu8_possible = 1,
		.cpu9_possible = 1,
		.cpu8_present = 1,
		.cpu9_present = 1,
	};
}

static struct mt6797_a72_direct_source_snapshot direct_source(void)
{
	return (struct mt6797_a72_direct_source_snapshot) {
		.abi = MT6797_A72_DIRECT_SOURCE_ABI,
		.valid = 1,
		.provider = {
			.abi = MT6797_A72_PROVIDER_STATE_ABI,
			.valid = 1,
			.control_a = 0x7b,
			.status_b = 0xc1,
			.buckb_cont = 0x00,
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

static int direct_snapshot_callback(
	void *context, struct mt6797_a72_direct_source_snapshot *snapshot)
{
	struct direct_test_state *state = context;

	state->calls++;
	if (state->callback_result)
		return state->callback_result;
	*snapshot = state->source;

	switch (state->mutation) {
	case DIRECT_MUTATION_NONE:
		break;
	case DIRECT_MUTATION_ABI:
		snapshot->abi++;
		break;
	case DIRECT_MUTATION_VALID:
		snapshot->valid = 0;
		break;
	case DIRECT_MUTATION_RESERVED:
		snapshot->reserved[0] = 1;
		break;
	case DIRECT_MUTATION_PROVIDER_ABI:
		snapshot->provider.abi++;
		break;
	case DIRECT_MUTATION_PROVIDER_VALID:
		snapshot->provider.valid = 0;
		break;
	case DIRECT_MUTATION_PROVIDER_RESERVED:
		snapshot->provider.reserved = 1;
		break;
	case DIRECT_MUTATION_PROVIDER_WIDTH:
		snapshot->provider.control_a = 0x100;
		break;
	case DIRECT_MUTATION_PLATFORM_VALID:
		snapshot->platform.valid = false;
		break;
	case DIRECT_MUTATION_CLOCK_ABI:
		snapshot->clock.abi++;
		break;
	case DIRECT_MUTATION_CLOCK_RESERVED:
		snapshot->clock.reserved = 1;
		break;
	case DIRECT_MUTATION_CLOCK_GENERATION:
		snapshot->clock.sample_generation = 0;
		break;
	case DIRECT_MUTATION_BIGIDVFS_ABI:
		snapshot->bigidvfs.abi++;
		break;
	case DIRECT_MUTATION_BIGIDVFS_RESERVED:
		snapshot->bigidvfs.reserved = 1;
		break;
	case DIRECT_MUTATION_BIGIDVFS_GENERATION:
		snapshot->bigidvfs.sample_generation = 0;
		break;
	}

	return 0;
}

static const struct mt6797_a72_direct_source_ops direct_source_ops = {
	.snapshot = direct_snapshot_callback,
};

static void direct_unregister(void *context)
{
	mt6797_a72_direct_source_unregister(&direct_source_ops, context);
}

static int direct_register(struct kunit *test, struct direct_test_state *state)
{
	int ret;

	ret = mt6797_a72_direct_source_register(&direct_source_ops, state);
	if (ret)
		return ret;
	return kunit_add_action_or_reset(test, direct_unregister, state);
}

static void expect_zero(struct kunit *test,
			const struct mt6797_a72_direct_state_snapshot *snapshot)
{
	const struct mt6797_a72_direct_state_snapshot zero = { };

	KUNIT_EXPECT_EQ(test, memcmp(snapshot, &zero, sizeof(zero)), 0);
}

static int direct_test_init(struct kunit *test)
{
	struct direct_test_state *state;

	mt6797_a72_membership_test_reset();
	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	if (!state)
		return -ENOMEM;
	state->source = direct_source();
	test->priv = state;
	return 0;
}

static void direct_snapshot_success(struct kunit *test)
{
	struct direct_test_state *state = test->priv;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_owner_snapshot before;
	struct mt6797_a72_owner_snapshot after;
	struct mt6797_a72_direct_topology topology = direct_topology();
	struct arm64_late_cpu_startup_snapshot p30_before;
	struct arm64_late_cpu_startup_snapshot p30_after;
	int preflight_before;
	int preflight_after;
	int ret;

	KUNIT_ASSERT_EQ(test, direct_register(test, state), 0);
	mt6797_a72_membership_snapshot(&before);
	arm64_late_cpu_startup_snapshot(&p30_before);
	preflight_before = mt6797_a72_membership_preflight_up(8, CPUHP_OFFLINE);
	memset(&observed, 0xa5, sizeof(observed));
	ret = mt6797_a72_direct_state_test_snapshot(&topology, &observed);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, observed.abi, MT6797_A72_DIRECT_STATE_ABI);
	KUNIT_EXPECT_EQ(test, observed.valid, 1U);
	KUNIT_EXPECT_EQ(test, observed.cpu8_possible, 1U);
	KUNIT_EXPECT_EQ(test, observed.cpu9_possible, 1U);
	KUNIT_EXPECT_EQ(test, observed.cpu8_present, 1U);
	KUNIT_EXPECT_EQ(test, observed.cpu9_present, 1U);
	KUNIT_EXPECT_EQ(test, observed.cpu8_online, 0U);
	KUNIT_EXPECT_EQ(test, observed.cpu9_online, 0U);
	KUNIT_EXPECT_EQ(test, observed.source.provider.vbuckb_a, 0x46U);
	KUNIT_EXPECT_EQ(test, observed.owner.health,
			MT6797_A72_OWNER_CLOSED);
	KUNIT_EXPECT_EQ(test, state->calls, 1U);
	mt6797_a72_membership_snapshot(&after);
	arm64_late_cpu_startup_snapshot(&p30_after);
	preflight_after = mt6797_a72_membership_preflight_up(8, CPUHP_OFFLINE);
	KUNIT_EXPECT_EQ(test, memcmp(&before, &after, sizeof(before)), 0);
	KUNIT_EXPECT_EQ(test, memcmp(&p30_before, &p30_after,
				     sizeof(p30_before)), 0);
	KUNIT_EXPECT_EQ(test, preflight_before, -EAGAIN);
	KUNIT_EXPECT_EQ(test, preflight_after, preflight_before);
}

static void direct_registry_guards(struct kunit *test)
{
	struct direct_test_state *state = test->priv;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_direct_topology topology = direct_topology();
	int ret;

	memset(&observed, 0xa5, sizeof(observed));
	ret = mt6797_a72_direct_state_test_snapshot(&topology, &observed);
	KUNIT_EXPECT_EQ(test, ret, -ENODEV);
	expect_zero(test, &observed);
	KUNIT_ASSERT_EQ(test, direct_register(test, state), 0);
	ret = mt6797_a72_direct_source_register(&direct_source_ops, state);
	KUNIT_EXPECT_EQ(test, ret, -EBUSY);
	mt6797_a72_direct_source_unregister(&direct_source_ops, test);
	ret = mt6797_a72_direct_state_test_snapshot(&topology, &observed);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->calls, 1U);
}

static void direct_callback_failure_zeroes(struct kunit *test)
{
	struct direct_test_state *state = test->priv;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_direct_topology topology = direct_topology();
	int ret;

	KUNIT_ASSERT_EQ(test, direct_register(test, state), 0);
	state->callback_result = -EIO;
	memset(&observed, 0xa5, sizeof(observed));
	ret = mt6797_a72_direct_state_test_snapshot(&topology, &observed);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	expect_zero(test, &observed);
	KUNIT_EXPECT_EQ(test, state->calls, 1U);
}

static void direct_source_mutations_rejected(struct kunit *test)
{
	struct direct_test_state *state = test->priv;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_direct_topology topology = direct_topology();
	enum direct_source_mutation mutation;
	int ret;

	KUNIT_ASSERT_EQ(test, direct_register(test, state), 0);
	for (mutation = DIRECT_MUTATION_ABI;
	     mutation <= DIRECT_MUTATION_BIGIDVFS_GENERATION; mutation++) {
		state->mutation = mutation;
		memset(&observed, 0xa5, sizeof(observed));
		ret = mt6797_a72_direct_state_test_snapshot(&topology,
						     &observed);
		KUNIT_EXPECT_EQ_MSG(test, ret, -EPROTO,
				    "mutation %u accepted", mutation);
		expect_zero(test, &observed);
	}
	KUNIT_EXPECT_EQ(test, state->calls,
			(u32)DIRECT_MUTATION_BIGIDVFS_GENERATION);
}

static void direct_topology_mutations_rejected(struct kunit *test)
{
	struct direct_test_state *state = test->priv;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_direct_topology topology;
	unsigned int index;
	int ret;

	KUNIT_ASSERT_EQ(test, direct_register(test, state), 0);
	for (index = 0; index < 6; index++) {
		topology = direct_topology();
		switch (index) {
		case 0:
			topology.cpu8_possible ^= 1;
			break;
		case 1:
			topology.cpu9_possible ^= 1;
			break;
		case 2:
			topology.cpu8_present ^= 1;
			break;
		case 3:
			topology.cpu9_present ^= 1;
			break;
		case 4:
			topology.cpu8_online ^= 1;
			break;
		default:
			topology.cpu9_online ^= 1;
			break;
		}
		memset(&observed, 0xa5, sizeof(observed));
		ret = mt6797_a72_direct_state_test_snapshot(&topology,
						     &observed);
		KUNIT_EXPECT_EQ_MSG(test, ret, -EPERM,
				    "topology field %u accepted", index);
		expect_zero(test, &observed);
	}
	KUNIT_EXPECT_EQ(test, state->calls, 0U);
}

static void direct_open_owner_rejected(struct kunit *test)
{
	struct direct_test_state *state = test->priv;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_direct_topology topology = direct_topology();
	int ret;

	KUNIT_ASSERT_EQ(test, direct_register(test, state), 0);
	mt6797_a72_membership_test_seed_available();
	memset(&observed, 0xa5, sizeof(observed));
	ret = mt6797_a72_direct_state_test_snapshot(&topology, &observed);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	expect_zero(test, &observed);
	KUNIT_EXPECT_EQ(test, state->calls, 0U);
}

static void direct_unregister_closes_source(struct kunit *test)
{
	struct direct_test_state *state = test->priv;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_direct_topology topology = direct_topology();
	int ret;

	KUNIT_ASSERT_EQ(test, direct_register(test, state), 0);
	ret = mt6797_a72_direct_state_test_snapshot(&topology, &observed);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_direct_source_unregister(&direct_source_ops, state);
	memset(&observed, 0xa5, sizeof(observed));
	ret = mt6797_a72_direct_state_test_snapshot(&topology, &observed);
	KUNIT_EXPECT_EQ(test, ret, -ENODEV);
	expect_zero(test, &observed);
}

static struct kunit_case direct_state_cases[] = {
	KUNIT_CASE(direct_snapshot_success),
	KUNIT_CASE(direct_registry_guards),
	KUNIT_CASE(direct_callback_failure_zeroes),
	KUNIT_CASE(direct_source_mutations_rejected),
	KUNIT_CASE(direct_topology_mutations_rejected),
	KUNIT_CASE(direct_open_owner_rejected),
	KUNIT_CASE(direct_unregister_closes_source),
	{ }
};

static struct kunit_suite direct_state_suite = {
	.name = "mt6797-a72-direct-state",
	.init = direct_test_init,
	.test_cases = direct_state_cases,
};

kunit_test_suite(direct_state_suite);

MODULE_LICENSE("GPL");
