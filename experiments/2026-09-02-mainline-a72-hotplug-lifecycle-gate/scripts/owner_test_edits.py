#!/usr/bin/env python3
"""Add focused KUnit coverage for the hardware-free CPU9 hotplug owner."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    test = (args.source_root.resolve() /
            "arch/arm64/kernel/mt6797_a72_membership_test.c")

    replace_once(
        test,
        "\tstruct mt6797_a72_transaction transaction;\n"
        "\tstruct mt6797_a72_owner_snapshot snapshot;\n",
        "\tstruct mt6797_a72_transaction transaction;\n"
        "\tstruct mt6797_a72_owner_snapshot snapshot;\n"
        "\tstruct mt6797_a72_hotplug_transaction hotplug;\n"
        "\tstruct mt6797_a72_hotplug_snapshot hotplug_snapshot;\n",
    )
    replace_once(
        test,
        "static void mt6797_a72_owner_cpu9_parent_gate(struct kunit *test)\n",
        r'''static int
mt6797_a72_test_seed_cpu9_terminal(struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_direct_topology topology =
		mt6797_a72_cpu9_topology();
	struct arm64_late_cpu_ready_token ready =
		mt6797_a72_ready_token_for_up();
	int ret;

	ret = mt6797_a72_test_seed_cpu8_terminal(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_test_derive_cpu9(&topology, &ready,
						     transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_publish_cpu9(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_test_preflight_cpu9(true, false);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_test_claim_cpu9(transaction, true, false);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_test_begin_cpu9_on(transaction, true, false);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_test_publish_cpu9_success(transaction,
							      true, true);
	if (ret)
		return ret;
	return mt6797_a72_membership_test_finalize_cpu9_success(transaction,
							       true, true);
}

static struct mt6797_a72_cpu9_off_proof
mt6797_a72_test_off_proof(const struct mt6797_a72_hotplug_transaction *transaction)
{
	return (struct mt6797_a72_cpu9_off_proof) {
		.abi = MT6797_A72_CPU9_OFF_PROOF_ABI,
		.valid = 1,
		.affinity_attempted = 1,
		.affinity_level = MT6797_A72_AFFINITY_LEVEL0,
		.affinity_state = MT6797_A72_AFFINITY_STATE_OFF,
		.cpu9_per_core_off = 1,
		.cpu8_responsive = 1,
		.shared_state_unchanged = 1,
		.members_before = BIT(0) | BIT(1),
		.online_mask_after = BIT(0),
		.provider_identity = transaction->provider_identity,
		.transaction_generation = transaction->identity.generation,
		.transaction_cookie = transaction->identity.cookie,
	};
}

static int
mt6797_a72_test_complete_cpu9_down(struct mt6797_a72_transaction *up,
	struct mt6797_a72_hotplug_transaction *hotplug)
{
	struct mt6797_a72_cpu9_off_proof proof;
	int ret;

	ret = mt6797_a72_test_seed_cpu9_terminal(up);
	if (ret)
		return ret;
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
					       true, true, hotplug);
	if (ret)
		return ret;
	ret = mt6797_a72_hotplug_validate_down(hotplug, 0, CPUHP_OFFLINE,
						true, true);
	if (ret)
		return ret;
	ret = mt6797_a72_hotplug_commit_off(9);
	if (ret)
		return ret;
	proof = mt6797_a72_test_off_proof(hotplug);
	ret = mt6797_a72_hotplug_prove_off(hotplug, &proof);
	if (ret)
		return ret;
	return mt6797_a72_hotplug_complete_down(hotplug, true, false);
}

static void mt6797_a72_owner_cpu9_parent_gate(struct kunit *test)
''',
    )
    replace_once(
        test,
        "}\n#endif\n\n"
        "static void mt6797_a72_owner_forged_token_rejected",
        r'''}

static void mt6797_a72_hotplug_success_lifecycle(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	struct mt6797_a72_cpu9_off_proof proof;
	struct mt6797_a72_hotplug_identity down_identity;
	int ret;

	ret = mt6797_a72_test_seed_cpu9_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
					       true, true, &state->hotplug);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->hotplug.identity.operation,
			(u32)MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN);
	KUNIT_EXPECT_EQ(test, state->hotplug.budgets.cpu_off,
			(u8)MT6797_A72_BUDGET_AVAILABLE);
	KUNIT_EXPECT_EQ(test, state->hotplug.budgets.affinity,
			(u8)MT6797_A72_BUDGET_AVAILABLE);
	down_identity = state->hotplug.identity;

	ret = mt6797_a72_hotplug_validate_down(&state->hotplug, 0,
						CPUHP_OFFLINE, true, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_commit_off(9);
	KUNIT_ASSERT_EQ(test, ret, 0);
	proof = mt6797_a72_test_off_proof(&state->hotplug);
	ret = mt6797_a72_hotplug_prove_off(&state->hotplug, &proof);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->hotplug.budgets.cpu_off,
			(u8)MT6797_A72_BUDGET_CONSUMED);
	KUNIT_EXPECT_EQ(test, state->hotplug.budgets.affinity,
			(u8)MT6797_A72_BUDGET_CONSUMED);
	ret = mt6797_a72_hotplug_complete_down(&state->hotplug, true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_hotplug_snapshot(&state->hotplug_snapshot);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.phase,
			(u32)MT6797_A72_HOTPLUG_OFFLINE);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.members, (u32)BIT(0));
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.retired_mask,
			(u32)BIT(0));
	KUNIT_EXPECT_TRUE(test, state->hotplug_snapshot.retired[0].off_proven);
	KUNIT_EXPECT_FALSE(test, state->hotplug_snapshot.controller_present);

	ret = mt6797_a72_hotplug_prepare_restore(9, CPUHP_ONLINE,
						  true, false, &state->hotplug);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state->hotplug.identity.operation,
			(u32)MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE);
	KUNIT_EXPECT_NE(test, state->hotplug.identity.generation,
			down_identity.generation);
	KUNIT_EXPECT_NE(test, state->hotplug.identity.cookie,
			down_identity.cookie);
	KUNIT_EXPECT_EQ(test, state->hotplug.identity.parent_generation,
			down_identity.generation);
	KUNIT_EXPECT_EQ(test, state->hotplug.identity.parent_cookie,
			down_identity.cookie);
	ret = mt6797_a72_hotplug_begin_restore(&state->hotplug, true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_complete_restore(&state->hotplug, true, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_hotplug_snapshot(&state->hotplug_snapshot);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.phase,
			(u32)MT6797_A72_HOTPLUG_RESTORED);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.members,
			(u32)(BIT(0) | BIT(1)));
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.retired_mask,
			(u32)(BIT(0) | BIT(1)));
	KUNIT_EXPECT_TRUE(test, state->hotplug_snapshot.retired[1].restored);
	KUNIT_EXPECT_TRUE(test, state->hotplug_snapshot.attempts_consumed &
			  MT6797_A72_ATTEMPT_CPU9_OFF);
	KUNIT_EXPECT_TRUE(test, state->hotplug_snapshot.attempts_consumed &
			  MT6797_A72_ATTEMPT_CPU9_RESTORE);
}

static void mt6797_a72_hotplug_entry_rejections(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	int ret;

	ret = mt6797_a72_test_seed_cpu9_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_prepare_down(8, CPUHP_OFFLINE,
					       true, true, &state->hotplug);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_ONLINE,
					       true, true, &state->hotplug);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
					       false, true, &state->hotplug);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	mt6797_a72_hotplug_snapshot(&state->hotplug_snapshot);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.phase,
			(u32)MT6797_A72_HOTPLUG_IDLE);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.retired_mask, (u32)0);
	KUNIT_EXPECT_FALSE(test, state->hotplug_snapshot.active.valid);
}

static void mt6797_a72_hotplug_precommit_rejection(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	int ret;

	ret = mt6797_a72_test_seed_cpu9_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
					       true, true, &state->hotplug);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_validate_down(&state->hotplug, 1,
						CPUHP_OFFLINE, true, true);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	ret = mt6797_a72_hotplug_fail_down(&state->hotplug, -EPERM);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_hotplug_snapshot(&state->hotplug_snapshot);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.phase,
			(u32)MT6797_A72_HOTPLUG_REJECTED);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.members,
			(u32)(BIT(0) | BIT(1)));
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.retired[0].failure_error,
			(s32)-EPERM);
	KUNIT_EXPECT_FALSE(test, state->hotplug_snapshot.active.valid);
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
					       true, true, &state->hotplug);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
}

static void mt6797_a72_hotplug_postcommit_fault(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	struct mt6797_a72_cpu9_off_proof proof;
	int ret;

	ret = mt6797_a72_test_seed_cpu9_terminal(&state->transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
					       true, true, &state->hotplug);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_validate_down(&state->hotplug, 0,
						CPUHP_OFFLINE, true, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_commit_off(9);
	KUNIT_ASSERT_EQ(test, ret, 0);
	proof = mt6797_a72_test_off_proof(&state->hotplug);
	proof.shared_state_unchanged = 0;
	ret = mt6797_a72_hotplug_prove_off(&state->hotplug, &proof);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	mt6797_a72_hotplug_snapshot(&state->hotplug_snapshot);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.phase,
			(u32)MT6797_A72_HOTPLUG_FAULT);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.owner_health,
			(u32)MT6797_A72_OWNER_FAULTED);
	KUNIT_EXPECT_TRUE(test, state->hotplug_snapshot.active.off_committed);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.active.budgets.affinity,
			(u8)MT6797_A72_BUDGET_CONSUMED);
	ret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
					       true, true, &state->hotplug);
	KUNIT_EXPECT_EQ(test, ret, -ESHUTDOWN);
}

static void mt6797_a72_hotplug_restore_fault(struct kunit *test)
{
	struct mt6797_a72_owner_test_state *state = test->priv;
	int ret;

	ret = mt6797_a72_test_complete_cpu9_down(&state->transaction,
						 &state->hotplug);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_prepare_restore(9, CPUHP_ONLINE,
						  true, false, &state->hotplug);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_begin_restore(&state->hotplug, true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_hotplug_fail_restore(&state->hotplug, -ETIMEDOUT);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_hotplug_snapshot(&state->hotplug_snapshot);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.phase,
			(u32)MT6797_A72_HOTPLUG_FAULT);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.members, (u32)BIT(0));
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.active.failure_error,
			(s32)-ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, state->hotplug_snapshot.active.budgets.cpu_on,
			(u8)MT6797_A72_BUDGET_CONSUMED);
	ret = mt6797_a72_hotplug_prepare_restore(9, CPUHP_ONLINE,
						  true, false, &state->hotplug);
	KUNIT_EXPECT_EQ(test, ret, -ESHUTDOWN);
}
#endif

static void mt6797_a72_owner_forged_token_rejected''',
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_rejection_one_shot),\n"
        "#endif\n",
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_rejection_one_shot),\n"
        "\tKUNIT_CASE(mt6797_a72_hotplug_success_lifecycle),\n"
        "\tKUNIT_CASE(mt6797_a72_hotplug_entry_rejections),\n"
        "\tKUNIT_CASE(mt6797_a72_hotplug_precommit_rejection),\n"
        "\tKUNIT_CASE(mt6797_a72_hotplug_postcommit_fault),\n"
        "\tKUNIT_CASE(mt6797_a72_hotplug_restore_fault),\n"
        "#endif\n",
    )


if __name__ == "__main__":
    main()
