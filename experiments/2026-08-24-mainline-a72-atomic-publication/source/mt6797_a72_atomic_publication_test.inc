// SPDX-License-Identifier: GPL-2.0-only

struct atomic_publication_test_state {
	struct mt6797_a72_direct_source_snapshot source;
	struct mt6797_a72_owner_snapshot owner_before;
	struct mt6797_a72_owner_snapshot owner_after;
	struct arm64_late_cpu_startup_snapshot p30_before;
	struct arm64_late_cpu_startup_snapshot p30_after;
	struct mt6797_a72_direct_topology topology;
	struct mt6797_a72_a34_replay replay;
	int source_result;
	int finalizer_result;
	u32 source_calls;
	u32 finalizer_calls;
};

static struct mt6797_a72_direct_topology atomic_topology(void)
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

static struct mt6797_a72_direct_source_snapshot atomic_source(void)
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

static struct mt6797_a72_a34_replay atomic_replay(void)
{
	return (struct mt6797_a72_a34_replay) {
		.abi = MT6797_A72_A34_REPLAY_ABI,
		.valid = 1,
		.proof =
			MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR,
	};
}

static int
atomic_source_snapshot(void *context,
		       struct mt6797_a72_direct_source_snapshot *snapshot)
{
	struct atomic_publication_test_state *state = context;

	state->source_calls++;
	if (state->source_result)
		return state->source_result;
	*snapshot = state->source;
	return 0;
}

static const struct mt6797_a72_direct_source_ops atomic_source_ops = {
	.snapshot = atomic_source_snapshot,
};

static void atomic_unregister_source(void *context)
{
	mt6797_a72_direct_source_unregister(&atomic_source_ops, context);
}

static int
atomic_register_source(struct kunit *test,
		       struct atomic_publication_test_state *state)
{
	int ret;

	ret = mt6797_a72_direct_source_register(&atomic_source_ops, state);
	if (ret)
		return ret;
	return kunit_add_action_or_reset(test, atomic_unregister_source, state);
}

static int atomic_finalize_callback(void *context)
{
	struct atomic_publication_test_state *state = context;

	state->finalizer_calls++;
	return state->finalizer_result;
}

static void expect_owner_equal(struct kunit *test,
			       const struct mt6797_a72_owner_snapshot *left,
			       const struct mt6797_a72_owner_snapshot *right)
{
	KUNIT_EXPECT_EQ(test, memcmp(left, right, sizeof(*left)), 0);
}

static void expect_p30_equal(struct kunit *test,
			     const struct arm64_late_cpu_startup_snapshot *left,
			     const struct arm64_late_cpu_startup_snapshot *right)
{
	KUNIT_EXPECT_EQ(test, memcmp(left, right, sizeof(*left)), 0);
}

static void
expect_available_owner(struct kunit *test,
		       const struct mt6797_a72_owner_snapshot *owner)
{
	KUNIT_EXPECT_PTR_EQ(test, memchr_inv(&owner->active, 0,
					     sizeof(owner->active)), NULL);
	KUNIT_EXPECT_PTR_EQ(test, memchr_inv(owner->retired, 0,
					     sizeof(owner->retired)), NULL);
	KUNIT_EXPECT_PTR_EQ(test, memchr_inv(&owner->provider_identity, 0,
					     sizeof(owner->provider_identity)), NULL);
	KUNIT_EXPECT_PTR_EQ(test, memchr_inv(&owner->first_fault, 0,
					     sizeof(owner->first_fault)), NULL);
	KUNIT_EXPECT_EQ(test, owner->diagnostic_blockers,
			MT6797_A72_BLOCK_MASK &
			~MT6797_A72_BLOCK_A34_BOOTSTRAP);
	KUNIT_EXPECT_EQ(test, owner->controller_cookie, (u64)0);
	KUNIT_EXPECT_EQ(test, owner->abi, (u32)MT6797_A72_TRANSACTION_ABI);
	KUNIT_EXPECT_EQ(test, owner->health,
			(u32)MT6797_A72_OWNER_AVAILABLE);
	KUNIT_EXPECT_EQ(test, owner->phase, (u32)MT6797_A72_PHASE_IDLE);
	KUNIT_EXPECT_EQ(test, owner->members, (u32)0);
	KUNIT_EXPECT_EQ(test, owner->provider_state,
			(u32)MT6797_A72_PROVIDER_NONE);
	KUNIT_EXPECT_EQ(test, owner->bootstrap_valid, (u32)1);
	KUNIT_EXPECT_EQ(test, owner->members_valid, (u32)1);
	KUNIT_EXPECT_EQ(test, owner->attempts_available,
			(u32)MT6797_A72_ATTEMPT_MASK);
	KUNIT_EXPECT_EQ(test, owner->attempts_consumed, (u32)0);
	KUNIT_EXPECT_EQ(test, owner->retired_mask, (u32)0);
	KUNIT_EXPECT_EQ(test, owner->controller_present, (u32)0);
}

static int atomic_publication_test_init(struct kunit *test)
{
	struct atomic_publication_test_state *state;

	mt6797_a72_membership_test_reset();
	arm64_late_cpu_startup_test_reset();
	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	if (!state)
		return -ENOMEM;
	state->source = atomic_source();
	state->topology = atomic_topology();
	state->replay = atomic_replay();
	test->priv = state;
	return 0;
}

static void atomic_finalizer_success_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;
	struct arm64_late_cpu_bootstrap_claim claim;
	struct arm64_late_cpu_bootstrap_claim second;

	arm64_late_cpu_startup_snapshot(&state->p30_before);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_finalize_pristine(&claim,
								 atomic_finalize_callback,
								 state), 0);
	KUNIT_EXPECT_EQ(test, state->finalizer_calls, (u32)1);
	KUNIT_EXPECT_EQ(test, claim.abi, (u32)0);
	KUNIT_EXPECT_EQ(test, claim.cookie, (u64)0);
	arm64_late_cpu_startup_snapshot(&state->p30_after);
	expect_p30_equal(test, &state->p30_before, &state->p30_after);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&second), 0);
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&second), 0);
}

static void atomic_finalizer_failure_identity_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;
	struct arm64_late_cpu_bootstrap_claim claim;
	struct arm64_late_cpu_bootstrap_claim wrong;

	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	wrong = claim;
	wrong.cookie++;
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_finalize_pristine(&wrong,
								 atomic_finalize_callback,
								 state), -ESTALE);
	KUNIT_EXPECT_EQ(test, state->finalizer_calls, (u32)0);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), 0);

	state->finalizer_result = -EPERM;
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_finalize_pristine(&claim,
								 atomic_finalize_callback,
								 state), -EPERM);
	KUNIT_EXPECT_EQ(test, state->finalizer_calls, (u32)1);
	KUNIT_EXPECT_EQ(test, claim.cookie, (u64)0);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), 0);
}

static void atomic_publication_success_repeat_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;
	struct arm64_late_cpu_bootstrap_claim claim;
	int ret;

	KUNIT_ASSERT_EQ(test, atomic_register_source(test, state), 0);
	mt6797_a72_membership_snapshot(&state->owner_before);
	arm64_late_cpu_startup_snapshot(&state->p30_before);
	ret = mt6797_a72_membership_test_publish_bootstrap(&state->topology,
							   &state->replay, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)1);
	mt6797_a72_membership_snapshot(&state->owner_after);
	arm64_late_cpu_startup_snapshot(&state->p30_after);
	expect_available_owner(test, &state->owner_after);
	expect_p30_equal(test, &state->p30_before, &state->p30_after);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE),
			-EOPNOTSUPP);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_validate_up(8, 0, CPUHP_ONLINE),
			-EOPNOTSUPP);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), 0);

	state->owner_before = state->owner_after;
	ret = mt6797_a72_membership_test_publish_bootstrap(&state->topology,
							   &state->replay, false);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)1);
	mt6797_a72_membership_snapshot(&state->owner_after);
	expect_owner_equal(test, &state->owner_before, &state->owner_after);
}

static void atomic_publication_replay_rejections_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;
	struct mt6797_a72_a34_replay replay;

	KUNIT_ASSERT_EQ(test, atomic_register_source(test, state), 0);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     NULL, false), -EINVAL);
	replay = state->replay;
	replay.abi++;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &replay, false), -EPROTO);
	replay = state->replay;
	replay.reserved[0] = 1;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &replay, false), -EPROTO);
	replay = state->replay;
	replay.valid = 0;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &replay, false), -ENODATA);
	replay = state->replay;
	replay.proof = MT6797_A72_A34_REPLAY_UNKNOWN;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &replay, false), -ENODATA);
	replay = state->replay;
	replay.private_replay_value = 1;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &replay, false), -EPERM);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)0);
	mt6797_a72_membership_snapshot(&state->owner_after);
	KUNIT_EXPECT_EQ(test, state->owner_after.health,
			(u32)MT6797_A72_OWNER_CLOSED);
}

static void atomic_publication_source_rejections_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;

	mt6797_a72_membership_snapshot(&state->owner_before);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &state->replay,
								     false),
			-ENODEV);
	KUNIT_ASSERT_EQ(test, atomic_register_source(test, state), 0);
	state->source_result = -EIO;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &state->replay, false), -EIO);
	state->source_result = 0;
	state->source.provider.control_a ^= 1;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &state->replay,
								     false),
			-EPERM);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)2);
	mt6797_a72_membership_snapshot(&state->owner_after);
	expect_owner_equal(test, &state->owner_before, &state->owner_after);
}

static void atomic_publication_topology_rejection_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;

	KUNIT_ASSERT_EQ(test, atomic_register_source(test, state), 0);
	state->topology.cpu9_present = 0;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &state->replay,
								     false),
			-EPERM);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)0);
	mt6797_a72_membership_snapshot(&state->owner_after);
	KUNIT_EXPECT_EQ(test, state->owner_after.health,
			(u32)MT6797_A72_OWNER_CLOSED);
}

static void atomic_publication_p30_busy_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;
	struct arm64_late_cpu_bootstrap_claim claim;

	KUNIT_ASSERT_EQ(test, atomic_register_source(test, state), 0);
	mt6797_a72_membership_snapshot(&state->owner_before);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &state->replay,
								     false),
			-EBUSY);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)1);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), 0);
	mt6797_a72_membership_snapshot(&state->owner_after);
	expect_owner_equal(test, &state->owner_before, &state->owner_after);
}

static void atomic_publication_final_owner_mismatch_test(struct kunit *test)
{
	struct atomic_publication_test_state *state = test->priv;
	struct arm64_late_cpu_bootstrap_claim claim;

	KUNIT_ASSERT_EQ(test, atomic_register_source(test, state), 0);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_publish_bootstrap(&state->topology,
								     &state->replay, true), -EPERM);
	KUNIT_EXPECT_EQ(test, state->source_calls, (u32)1);
	mt6797_a72_membership_snapshot(&state->owner_after);
	KUNIT_EXPECT_EQ(test, state->owner_after.health,
			(u32)MT6797_A72_OWNER_CLOSED);
	KUNIT_EXPECT_EQ(test, state->owner_after.phase,
			(u32)MT6797_A72_PHASE_UNINITIALIZED);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), 0);
}

static struct kunit_case atomic_publication_test_cases[] = {
	KUNIT_CASE(atomic_finalizer_success_test),
	KUNIT_CASE(atomic_finalizer_failure_identity_test),
	KUNIT_CASE(atomic_publication_success_repeat_test),
	KUNIT_CASE(atomic_publication_replay_rejections_test),
	KUNIT_CASE(atomic_publication_source_rejections_test),
	KUNIT_CASE(atomic_publication_topology_rejection_test),
	KUNIT_CASE(atomic_publication_p30_busy_test),
	KUNIT_CASE(atomic_publication_final_owner_mismatch_test),
	{}
};

static struct kunit_suite atomic_publication_test_suite = {
	.name = "mt6797-a72-atomic-publication",
	.init = atomic_publication_test_init,
	.test_cases = atomic_publication_test_cases,
};
