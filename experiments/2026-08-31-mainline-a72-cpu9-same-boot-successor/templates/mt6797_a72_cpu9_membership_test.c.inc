#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)
static struct mt6797_a72_direct_topology mt6797_a72_cpu9_topology(void)
{
	return (struct mt6797_a72_direct_topology) {
		.cpu8_possible = 1,
		.cpu9_possible = 1,
		.cpu8_present = 1,
		.cpu9_present = 1,
		.cpu8_online = 1,
		.cpu9_online = 0,
		.cpu8_method_valid = 1,
		.cpu9_method_valid = 1,
		.cpu8_mpidr = 0x200,
		.cpu9_mpidr = 0x201,
	};
}

static bool
mt6797_a72_test_cpu9_cluster_budgets_empty(const struct mt6797_a72_transaction *transaction)
{
	const struct mt6797_a72_call_budgets *budgets = &transaction->budgets;

	return budgets->preparation == MT6797_A72_BUDGET_NONE &&
		budgets->provider_acquire == MT6797_A72_BUDGET_NONE &&
		budgets->postprovider_preparation == MT6797_A72_BUDGET_NONE &&
		budgets->affinity == MT6797_A72_BUDGET_NONE &&
		budgets->provider_release == MT6797_A72_BUDGET_NONE &&
		budgets->provider_abort == MT6797_A72_BUDGET_NONE;
}

static int
mt6797_a72_test_seed_cpu8_terminal(struct mt6797_a72_transaction *transaction)
{
	int ret;

	ret = mt6797_a72_test_seed_cpu8_claimed_p28(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_begin_cpu8_on(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_test_publish_cpu8_success(transaction,
							      true, false);
	if (ret)
		return ret;
	return mt6797_a72_membership_test_finalize_cpu8_success(transaction,
							       true, false);
}

static void mt6797_a72_owner_cpu9_parent_gate(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	struct mt6797_a72_direct_topology topology =
		mt6797_a72_cpu9_topology();
	struct arm64_late_cpu_ready_token ready = mt6797_a72_ready_token_for_up();
	int ret;

	mt6797_a72_owner_seed_available_cpu9();
	owner_observe(&state->before);
	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						    &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	owner_observe(&state->after);
	expect_unchanged(test, &state->before, &state->after);

	ret = mt6797_a72_test_seed_cpu8_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	owner_observe(&state->before);
	topology.cpu8_online = 0;
	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						    &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	owner_observe(&state->after);
	expect_unchanged(test, &state->before, &state->after);

	topology = mt6797_a72_cpu9_topology();
	topology.cpu9_online = 1;
	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						    &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	owner_observe(&state->after);
	expect_unchanged(test, &state->before, &state->after);

	topology = mt6797_a72_cpu9_topology();
	topology.cpu9_method_valid = 0;
	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						    &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	owner_observe(&state->after);
	expect_unchanged(test, &state->before, &state->after);
}

static void mt6797_a72_owner_cpu9_parent_mutations(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	struct mt6797_a72_direct_topology topology =
		mt6797_a72_cpu9_topology();
	int ret;

	ret = mt6797_a72_test_seed_cpu8_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&state->snapshot);
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->snapshot, &topology), 0);

	state->before.owner = state->snapshot;
	state->before.owner.members = 0;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->before.owner, &topology), -EPERM);
	state->before.owner = state->snapshot;
	state->before.owner.provider_state = MT6797_A72_PROVIDER_NONE;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->before.owner, &topology), -EPERM);
	state->before.owner = state->snapshot;
	state->before.owner.retired_mask &= ~BIT(0);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->before.owner, &topology), -EPERM);
	state->before.owner = state->snapshot;
	state->before.owner.attempts_consumed |= MT6797_A72_ATTEMPT_CPU9_UP;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->before.owner, &topology), -EPERM);
	state->before.owner = state->snapshot;
	state->before.owner.retired[0].cpu8_success_published = 0;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->before.owner, &topology), -EPERM);
	state->before.owner = state->snapshot;
	state->before.owner.retired[0].provider_identity.cookie++;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->before.owner, &topology), -EPERM);
	state->before.owner = state->snapshot;
	state->before.owner.retired[0].p28_valid = 0;
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_test_validate_cpu9_parent(
				&state->before.owner, &topology), -EPERM);
}

static void mt6797_a72_owner_cpu9_success_lifecycle(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	struct mt6797_a72_direct_topology topology =
		mt6797_a72_cpu9_topology();
	struct arm64_late_cpu_ready_token ready = mt6797_a72_ready_token_for_up();
	int difference;
	int ret;

	ret = mt6797_a72_test_seed_cpu8_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	owner_observe(&state->before);
	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						    &state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->transaction.identity.target_cpu, (u32)9);
	KUNIT_EXPECT_EQ(test, state->transaction.identity.target_mpidr,
			(u64)0x201);
	KUNIT_EXPECT_EQ(test, state->transaction.budgets.cpu_on,
			(u8)MT6797_A72_BUDGET_AVAILABLE);
	KUNIT_EXPECT_TRUE(test,
			mt6797_a72_test_cpu9_cluster_budgets_empty(
				&state->transaction));
	KUNIT_EXPECT_TRUE(test, state->transaction.a36_valid);
	KUNIT_EXPECT_EQ(test, state->transaction.a36_prestate.cpu8_online,
			(u32)1);
	KUNIT_EXPECT_EQ(test,
			state->transaction.a36_prestate.cpu8_cluster_dcm_published,
			(u32)1);

	ret = mt6797_a72_membership_publish_cpu9(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_preflight_cpu9(true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_claim_cpu9(&state->transaction,
						   true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_begin_cpu9_on(&state->transaction,
						      true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->transaction.budgets.cpu_on,
			(u8)MT6797_A72_BUDGET_CONSUMED);
	KUNIT_EXPECT_TRUE(test,
			mt6797_a72_test_cpu9_cluster_budgets_empty(
				&state->transaction));
	ret = mt6797_a72_membership_test_publish_cpu9_success(
		&state->transaction, true, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&state->snapshot);
	KUNIT_EXPECT_EQ(test, state->snapshot.phase,
			(u32)MT6797_A72_PHASE_VERIFYING);
	KUNIT_EXPECT_EQ(test, state->snapshot.members,
			(u32)(BIT(0) | BIT(1)));
	KUNIT_EXPECT_TRUE(test, state->snapshot.active.cpu9_success_published);

	ret = mt6797_a72_membership_test_finalize_cpu9_success(
		&state->transaction, true, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	owner_observe(&state->after);
	KUNIT_EXPECT_EQ(test, state->after.owner.phase,
			(u32)MT6797_A72_PHASE_IDLE);
	KUNIT_EXPECT_EQ(test, state->after.owner.members,
			(u32)(BIT(0) | BIT(1)));
	KUNIT_EXPECT_EQ(test, state->after.owner.retired_mask,
			(u32)(BIT(0) | BIT(1)));
	KUNIT_EXPECT_TRUE(test,
			state->after.owner.retired[1].cpu9_success_published);
	KUNIT_EXPECT_EQ(test, state->after.owner.provider_identity.cookie,
			state->before.owner.provider_identity.cookie);
	difference = memcmp(&state->before.owner.retired[0],
			    &state->after.owner.retired[0],
			    sizeof(state->before.owner.retired[0]));
	KUNIT_EXPECT_EQ(test, difference, 0);
}

static void mt6797_a72_owner_cpu9_rejection_one_shot(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	struct mt6797_a72_direct_topology topology =
		mt6797_a72_cpu9_topology();
	struct arm64_late_cpu_ready_token ready = mt6797_a72_ready_token_for_up();
	int ret;

	ret = mt6797_a72_test_seed_cpu8_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						    &state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_publish_cpu9(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_preflight_cpu9(true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_claim_cpu9(&state->transaction,
						   true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_reject_cpu9(&state->transaction,
						    true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&state->snapshot);
	KUNIT_EXPECT_EQ(test, state->snapshot.phase,
			(u32)MT6797_A72_PHASE_REJECTED);
	KUNIT_EXPECT_EQ(test, state->snapshot.members, (u32)BIT(0));
	KUNIT_EXPECT_EQ(test, state->snapshot.provider_state,
			(u32)MT6797_A72_PROVIDER_HELD);
	KUNIT_EXPECT_TRUE(test,
			state->snapshot.attempts_consumed &
			MT6797_A72_ATTEMPT_CPU9_UP);
	KUNIT_EXPECT_TRUE(test, state->snapshot.retired_mask & BIT(1));
	KUNIT_EXPECT_FALSE(test,
			state->snapshot.retired[1].cpu9_success_published);
	KUNIT_EXPECT_FALSE(test, state->snapshot.retired[1].p27_valid);
	KUNIT_EXPECT_FALSE(test, state->snapshot.retired[1].p28_valid);

	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						    &state->transaction);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
}
#endif
