#!/usr/bin/env python3
"""Apply stage attribution and the live A34 predicate repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


MEMBERSHIP_C = Path("arch/arm64/kernel/mt6797_a72_membership.c")
MEMBERSHIP_H = Path("arch/arm64/include/asm/mt6797_a72_membership.h")
MEMBERSHIP_TEST = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")
A34_TEST = Path("arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c")
DERIVED_TEST = Path("arch/arm64/kernel/mt6797_a72_derived_admission_test.c")
CONTROLLER_C = Path("drivers/soc/mediatek/mt6797-a72-admission-controller.c")
CONTROLLER_H = Path("drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h")
CONTROLLER_TEST = Path("drivers/soc/mediatek/mt6797-a72-admission-controller-test.c")

PARENT_SHA256 = {
    MEMBERSHIP_C: "d9cd9d378e0be9c7b8ee07cc0cfceb681d78f8f3deea7d0cb64bbce93a118ad9",
    MEMBERSHIP_H: "c4dba8d89bb29d6d9785a37e25ee720d1e42ed847077d6c0c997cc29cc5201d1",
    MEMBERSHIP_TEST: "d0fdfc03e20da44990153e13d6db0bf2f8e13b50108121da015290da16f57fb3",
    A34_TEST: "586ef1e1dfdbff813477189c192e6d8d02acc7a90bfa67c8614a76c1467fdf78",
    DERIVED_TEST: "6322c9ce062d3c622fa6c32d74166f0a41c5bb5c3d87ec43a8b904ee9b6e4089",
    CONTROLLER_C: "91b614753d9eafba04c29d544166ea283bc15a2d7482ad4f4fe8959f0a1e2f3f",
    CONTROLLER_H: "10df0c42c97bc53df99d9e00462efa5ebc7b18f4c2ccb0b7091db5bf72abaea0",
    CONTROLLER_TEST: "13add57c4f4e019b529f9f12e207d636b0e28c8fb574bbabf8b335ca407b6e58",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"anchor changed ({label}): {text.count(old)}")
    return text.replace(old, new, 1)


def read_parent(root: Path, relative: Path) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"missing or unsafe source: {relative}")
    if sha256(path) != PARENT_SHA256[relative]:
        raise SystemExit(f"post-0441 source changed: {relative}")
    return path.read_text(encoding="utf-8")


def apply_stage_attribution(root: Path) -> None:
    header = read_parent(root, MEMBERSHIP_H)
    header = replace_once(
        header,
        """enum mt6797_a72_membership_operation {
	MT6797_A72_OPERATION_NONE,
	MT6797_A72_OPERATION_CPU8_UP,
	MT6797_A72_OPERATION_CPU9_UP,
	MT6797_A72_OPERATION_CPU9_OFF,
	MT6797_A72_OPERATION_CPU8_LAST_OFF,
};
""",
        """enum mt6797_a72_membership_operation {
	MT6797_A72_OPERATION_NONE,
	MT6797_A72_OPERATION_CPU8_UP,
	MT6797_A72_OPERATION_CPU9_UP,
	MT6797_A72_OPERATION_CPU9_OFF,
	MT6797_A72_OPERATION_CPU8_LAST_OFF,
};

enum mt6797_a72_cpu8_derive_stage {
	MT6797_A72_DERIVE_NONE,
	MT6797_A72_DERIVE_TOPOLOGY,
	MT6797_A72_DERIVE_READY_TOKEN,
	MT6797_A72_DERIVE_BOOTSTRAP_OWNER,
	MT6797_A72_DERIVE_BOOTSTRAP_REPLAY,
	MT6797_A72_DERIVE_DIRECT_STATE,
	MT6797_A72_DERIVE_A34,
	MT6797_A72_DERIVE_P30_CLAIM,
	MT6797_A72_DERIVE_BOOTSTRAP_FINALIZE,
	MT6797_A72_DERIVE_P30_RELEASE,
	MT6797_A72_DERIVE_P31_CONSUME,
	MT6797_A72_DERIVE_ENTRY_VALIDATE,
	MT6797_A72_DERIVE_TOKEN_MINT,
	MT6797_A72_DERIVE_PRESTATE_VALIDATE,
	MT6797_A72_DERIVE_PRESTATE_BIND,
	MT6797_A72_DERIVE_COMPLETE,
};
""",
        "derive enum",
    )
    header = replace_once(
        header,
        """int
mt6797_a72_membership_derive_cpu8(const struct arm64_late_cpu_ready_token *ready,
				  struct mt6797_a72_transaction *transaction);
#else
static inline int
mt6797_a72_membership_derive_cpu8(const struct arm64_late_cpu_ready_token *ready,
				  struct mt6797_a72_transaction *transaction)
{
	(void)ready;
	if (transaction)
		memset(transaction, 0, sizeof(*transaction));
	return -EOPNOTSUPP;
}
""",
        """int
mt6797_a72_membership_derive_cpu8(const struct arm64_late_cpu_ready_token *ready,
				  struct mt6797_a72_transaction *transaction);
int
mt6797_a72_membership_derive_cpu8_diagnostic(
	const struct arm64_late_cpu_ready_token *ready,
	struct mt6797_a72_transaction *transaction, u32 *derive_stage);
#else
static inline int
mt6797_a72_membership_derive_cpu8_diagnostic(
	const struct arm64_late_cpu_ready_token *ready,
	struct mt6797_a72_transaction *transaction, u32 *derive_stage)
{
	(void)ready;
	if (transaction)
		memset(transaction, 0, sizeof(*transaction));
	if (derive_stage)
		*derive_stage = MT6797_A72_DERIVE_NONE;
	return -EOPNOTSUPP;
}

static inline int
mt6797_a72_membership_derive_cpu8(const struct arm64_late_cpu_ready_token *ready,
				  struct mt6797_a72_transaction *transaction)
{
	return mt6797_a72_membership_derive_cpu8_diagnostic(ready, transaction,
							    NULL);
}
""",
        "derive declaration",
    )
    (root / MEMBERSHIP_H).write_text(header, encoding="utf-8")

    source = read_parent(root, MEMBERSHIP_C)
    source = replace_once(
        source,
        """static int
mt6797_a72_membership_publish_bootstrap_locked(const struct mt6797_a72_direct_topology *topology,
					       const struct mt6797_a72_a34_replay *replay,
					       bool dirty_owner_before_finalize,
					       struct mt6797_a72_direct_state_snapshot *published)
{
	struct mt6797_a72_bootstrap_workspace *workspace =
		&a72_bootstrap_workspace;
	int release_ret;
	int ret;
#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
	unsigned long flags;
#endif

	memset(workspace, 0, sizeof(*workspace));
	ret = mt6797_a72_bootstrap_owner_precheck();
	if (ret)
		goto out_clear;
	ret = mt6797_a72_bootstrap_replay_valid(replay);
	if (ret)
		goto out_clear;
	ret = mt6797_a72_direct_state_snapshot_locked(topology,
						      &workspace->observation.direct);
	if (ret)
		goto out_clear;
	workspace->observation.abi = MT6797_A72_A34_ELIGIBILITY_ABI;
	workspace->observation.replay = *replay;
	ret = mt6797_a72_a34_evaluate(&workspace->observation);
	if (ret)
		goto out_clear;
	mt6797_a72_bootstrap_prepare_plan(&workspace->plan);
	ret = arm64_late_cpu_startup_claim_pristine(&workspace->claim);
	if (ret)
		goto out_clear;
#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
	if (dirty_owner_before_finalize) {
		raw_spin_lock_irqsave(&a72_state_lock, flags);
		a72_owner.next_cookie = 1;
		raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	}
#else
	(void)dirty_owner_before_finalize;
#endif
	ret = arm64_late_cpu_startup_finalize_pristine(&workspace->claim,
						       mt6797_a72_bootstrap_commit,
						       workspace);
	if (workspace->claim.cookie) {
		release_ret = arm64_late_cpu_startup_release_pristine(&workspace->claim);
		if (release_ret)
			ret = release_ret;
	}
	if (!ret && published)
		*published = workspace->observation.direct;
out_clear:
	memset(workspace, 0, sizeof(*workspace));
	return ret;
}
""",
        """static void mt6797_a72_derive_stage_set(u32 *stage, u32 value)
{
	if (stage)
		*stage = value;
}

static int
mt6797_a72_membership_publish_bootstrap_locked(const struct mt6797_a72_direct_topology *topology,
					       const struct mt6797_a72_a34_replay *replay,
					       bool dirty_owner_before_finalize,
					       struct mt6797_a72_direct_state_snapshot *published,
					       u32 *derive_stage)
{
	struct mt6797_a72_bootstrap_workspace *workspace =
		&a72_bootstrap_workspace;
	int release_ret;
	int ret;
#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
	unsigned long flags;
#endif

	memset(workspace, 0, sizeof(*workspace));
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_BOOTSTRAP_OWNER);
	ret = mt6797_a72_bootstrap_owner_precheck();
	if (ret)
		goto out_clear;
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_BOOTSTRAP_REPLAY);
	ret = mt6797_a72_bootstrap_replay_valid(replay);
	if (ret)
		goto out_clear;
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_DIRECT_STATE);
	ret = mt6797_a72_direct_state_snapshot_locked(topology,
						      &workspace->observation.direct);
	if (ret)
		goto out_clear;
	workspace->observation.abi = MT6797_A72_A34_ELIGIBILITY_ABI;
	workspace->observation.replay = *replay;
	mt6797_a72_derive_stage_set(derive_stage, MT6797_A72_DERIVE_A34);
	ret = mt6797_a72_a34_evaluate(&workspace->observation);
	if (ret)
		goto out_clear;
	mt6797_a72_bootstrap_prepare_plan(&workspace->plan);
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_P30_CLAIM);
	ret = arm64_late_cpu_startup_claim_pristine(&workspace->claim);
	if (ret)
		goto out_clear;
#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
	if (dirty_owner_before_finalize) {
		raw_spin_lock_irqsave(&a72_state_lock, flags);
		a72_owner.next_cookie = 1;
		raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	}
#else
	(void)dirty_owner_before_finalize;
#endif
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_BOOTSTRAP_FINALIZE);
	ret = arm64_late_cpu_startup_finalize_pristine(&workspace->claim,
						       mt6797_a72_bootstrap_commit,
						       workspace);
	if (workspace->claim.cookie) {
		mt6797_a72_derive_stage_set(derive_stage,
						   MT6797_A72_DERIVE_P30_RELEASE);
		release_ret = arm64_late_cpu_startup_release_pristine(&workspace->claim);
		if (release_ret)
			ret = release_ret;
	}
	if (!ret && published)
		*published = workspace->observation.direct;
out_clear:
	memset(workspace, 0, sizeof(*workspace));
	return ret;
}
""",
        "bootstrap diagnostic",
    )
    source = replace_once(source, "false, NULL);", "false, NULL, NULL);", "public bootstrap call")
    source = replace_once(source, "dirty_owner_before_finalize, NULL);", "dirty_owner_before_finalize, NULL, NULL);", "test bootstrap call")

    start = source.index("static int\nmt6797_a72_membership_derive_cpu8_locked(")
    end = source.index("\nstatic void\nmt6797_a72_membership_fill_cpu8_topology", start)
    locked = r'''static int
mt6797_a72_membership_derive_cpu8_locked(const struct mt6797_a72_direct_topology *topology,
					 const struct arm64_late_cpu_ready_token *ready,
					 struct mt6797_a72_transaction *transaction,
					 u32 *derive_stage)
{
	struct mt6797_a72_derived_workspace *workspace = &a72_derived_workspace;
	int ret;

	memset(workspace, 0, sizeof(*workspace));
	mt6797_a72_derive_stage_set(derive_stage, MT6797_A72_DERIVE_READY_TOKEN);
	ret = mt6797_a72_ready_token_validate(8, ready);
	if (ret)
		goto out_clear;
	workspace->replay.abi = MT6797_A72_A34_REPLAY_ABI;
	workspace->replay.valid = 1;
	workspace->replay.proof =
		MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR;
	ret = mt6797_a72_membership_publish_bootstrap_locked(topology,
							     &workspace->replay, false,
							     &workspace->direct,
							     derive_stage);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_cpu8_entry(&workspace->direct, &workspace->entry);
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_P31_CONSUME);
	ret = mt6797_a72_membership_p31_consume_attempt(8, CPUHP_ONLINE,
							MT6797_A72_ATTEMPT_CPU8_UP,
							&workspace->entry);
	if (ret)
		goto out_clear;
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_ENTRY_VALIDATE);
	ret = mt6797_a72_membership_validate_entry(8, CPUHP_ONLINE,
						   MT6797_A72_ATTEMPT_CPU8_UP,
						   &workspace->entry);
	if (ret)
		goto out_clear;
	mt6797_a72_derive_stage_set(derive_stage, MT6797_A72_DERIVE_TOKEN_MINT);
	ret = mt6797_a72_membership_mint_up_token(8, CPUHP_ONLINE,
						  MT6797_A72_ATTEMPT_CPU8_UP,
						  &workspace->entry, ready, transaction);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_cpu8_prestate(&workspace->direct, transaction,
					&workspace->prestate);
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_PRESTATE_VALIDATE);
	ret = mt6797_a72_membership_validate_up_prestate(transaction,
							 &workspace->prestate);
	if (ret)
		goto reject_frozen;
	mt6797_a72_derive_stage_set(derive_stage,
					   MT6797_A72_DERIVE_PRESTATE_BIND);
	ret = mt6797_a72_membership_bind_a36_prestate(&transaction->identity,
						      &workspace->prestate, transaction);
	if (ret)
		goto reject_frozen;
	mt6797_a72_derive_stage_set(derive_stage, MT6797_A72_DERIVE_COMPLETE);
	goto out_clear;

reject_frozen:
	mt6797_a72_membership_reject_frozen(&transaction->identity);
	memset(transaction, 0, sizeof(*transaction));
out_clear:
	memset(workspace, 0, sizeof(*workspace));
	return ret;
}
'''
    source = source[:start] + locked + source[end:]

    start = source.index("int\nmt6797_a72_membership_derive_cpu8(")
    end = source.index("\n#ifdef CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST", start)
    public = r'''int
mt6797_a72_membership_derive_cpu8_diagnostic(
	const struct arm64_late_cpu_ready_token *ready,
	struct mt6797_a72_transaction *transaction, u32 *derive_stage)
{
	struct mt6797_a72_direct_topology topology = {};
	int ret;

	mt6797_a72_derive_stage_set(derive_stage, MT6797_A72_DERIVE_NONE);
	if (!transaction)
		return -EINVAL;
	memset(transaction, 0, sizeof(*transaction));
	cpus_read_lock();
	mutex_lock(&a72_transition_lock);
	mt6797_a72_derive_stage_set(derive_stage, MT6797_A72_DERIVE_TOPOLOGY);
	if (nr_cpu_ids <= 9) {
		ret = -ENODEV;
		goto out_unlock;
	}
	mt6797_a72_membership_fill_cpu8_topology(&topology);
	ret = mt6797_a72_membership_derive_cpu8_locked(&topology, ready,
						       transaction, derive_stage);
out_unlock:
	mutex_unlock(&a72_transition_lock);
	cpus_read_unlock();
	return ret;
}

int
mt6797_a72_membership_derive_cpu8(const struct arm64_late_cpu_ready_token *ready,
				  struct mt6797_a72_transaction *transaction)
{
	return mt6797_a72_membership_derive_cpu8_diagnostic(ready, transaction,
							    NULL);
}
'''
    source = source[:start] + public + source[end:]
    source = replace_once(
        source,
        """ret = mt6797_a72_membership_derive_cpu8_locked(topology, ready,
						       transaction);""",
        """ret = mt6797_a72_membership_derive_cpu8_locked(topology, ready,
						       transaction, NULL);""",
        "derived test helper",
    )
    (root / MEMBERSHIP_C).write_text(source, encoding="utf-8")

    controller_h = read_parent(root, CONTROLLER_H)
    controller_h = replace_once(
        controller_h,
        """	u32 cpu_requests;
	int trace_entry_ret;
""",
        """	u32 cpu_requests;
	u32 failure_stage;
	u32 derive_stage;
	int trace_entry_ret;
""",
        "controller state fields",
    )
    (root / CONTROLLER_H).write_text(controller_h, encoding="utf-8")

    controller = read_parent(root, CONTROLLER_C)
    controller = replace_once(
        controller,
        """	if (!state->cpu_requests && zero_result) {
		state->trace_ret = ops->trace_zero_request(context, zero_result);
""",
        """	state->failure_stage = zero_result;
	if (!state->cpu_requests && zero_result) {
		state->trace_ret = ops->trace_zero_request(context, zero_result);
""",
        "retain failure stage",
    )
    controller = replace_once(
        controller,
        """{
	(void)context;
	return mt6797_a72_membership_derive_cpu8(ready, transaction);
}
""",
        """{
	struct mt6797_a72_admission_controller *controller = context;

	return mt6797_a72_membership_derive_cpu8_diagnostic(
		ready, transaction, &controller->state.derive_stage);
}
""",
        "production derive diagnostic",
    )
    controller = replace_once(
        controller,
        """len += sysfs_emit_at(buf, len,
			     "entry_trace_ret=%d terminal_trace_ret=%d ",
			     READ_ONCE(controller->state.trace_entry_ret),
			     READ_ONCE(controller->state.trace_ret));
""",
        """len += sysfs_emit_at(buf, len,
			     "entry_trace_ret=%d terminal_trace_ret=%d ",
			     READ_ONCE(controller->state.trace_entry_ret),
			     READ_ONCE(controller->state.trace_ret));
	len += sysfs_emit_at(buf, len,
			     "failure_stage=%u derive_stage=%u ",
			     READ_ONCE(controller->state.failure_stage),
			     READ_ONCE(controller->state.derive_stage));
""",
        "status stages",
    )
    controller = replace_once(
        controller,
        """		 "entry_trace_ret=%d terminal_trace_ret=%d "
		 "requests=%u/0/0 retries=0\n",
""",
        """		 "entry_trace_ret=%d terminal_trace_ret=%d "
		 "failure_stage=%u derive_stage=%u "
		 "requests=%u/0/0 retries=0\n",
""",
        "terminal format",
    )
    controller = replace_once(
        controller,
        """		 READ_ONCE(controller->state.trace_entry_ret),
		 READ_ONCE(controller->state.trace_ret),
		 READ_ONCE(controller->state.cpu_requests));
""",
        """		 READ_ONCE(controller->state.trace_entry_ret),
		 READ_ONCE(controller->state.trace_ret),
		 READ_ONCE(controller->state.failure_stage),
		 READ_ONCE(controller->state.derive_stage),
		 READ_ONCE(controller->state.cpu_requests));
""",
        "terminal arguments",
    )
    (root / CONTROLLER_C).write_text(controller, encoding="utf-8")

    controller_test = read_parent(root, CONTROLLER_TEST)
    controller_test = replace_once(
        controller_test,
        """		KUNIT_EXPECT_EQ(test, context->zero_result,
				results[failure]);
""",
        """		KUNIT_EXPECT_EQ(test, context->zero_result,
				results[failure]);
		KUNIT_EXPECT_EQ(test, context->controller.failure_stage,
				(u32)results[failure]);
""",
        "controller stage test",
    )
    (root / CONTROLLER_TEST).write_text(controller_test, encoding="utf-8")


def add_live_platform_fields(text: str, label: str) -> str:
    return replace_once(
        text,
        """			.spm_cpu_pwr_status = 0x00350c08,
			.spm_cpu_pwr_status_2nd = 0x00350cff,
			.spm_mp2_cpusys_pwr_con = 0x00010132,
			.spm_cpu_ext_buck_iso = 0x00000002,
			.valid = true,
""",
        """			.spm_cpu_pwr_status = 0x003dce08,
			.spm_cpu_pwr_status_2nd = 0x003dceff,
			.spm_mp2_cpusys_pwr_con = 0x00010132,
			.spm_mp2_cpu0_pwr_con = 0x00010332,
			.spm_mp2_cpu1_pwr_con = 0x00010332,
			.spm_cpu_ext_buck_iso = 0x00000002,
			.cci_mp2_port_control = 0xc0000000,
			.valid = true,
""",
        label,
    )


def apply_a34_repair(root: Path) -> None:
    source_path = root / MEMBERSHIP_C
    source = source_path.read_text(encoding="utf-8")
    start = source.index("static const struct mt6797_a72_a34_observation a34_expected = {")
    end_marker = "\n#endif\n\n#ifdef CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER"
    end = source.index(end_marker, start)
    evaluator = r'''#define MT6797_A72_A34_CPU_STATUS_MASK GENMASK(7, 6)

static bool
mt6797_a72_a34_direct_valid(const struct mt6797_a72_direct_state_snapshot *direct)
{
	const struct mt6797_a72_direct_source_snapshot *source = &direct->source;
	const struct mt6797_a72_provider_snapshot *provider = &source->provider;
	const struct mt6797_a72_platform_state *platform = &source->platform;

	return direct->abi == MT6797_A72_DIRECT_STATE_ABI && direct->valid == 1 &&
		direct->cpu8_possible == 1 && direct->cpu9_possible == 1 &&
		direct->cpu8_present == 1 && direct->cpu9_present == 1 &&
		!direct->cpu8_online && !direct->cpu9_online &&
		direct->cpu8_method_valid == 1 &&
		direct->cpu9_method_valid == 1 &&
		direct->cpu8_mpidr == 0x200 && direct->cpu9_mpidr == 0x201 &&
		source->abi == MT6797_A72_DIRECT_SOURCE_ABI &&
		source->valid == 1 && !source->reserved[0] &&
		!source->reserved[1] &&
		provider->abi == MT6797_A72_PROVIDER_STATE_ABI &&
		provider->valid == 1 && provider->control_a == 0x7b &&
		provider->status_b == 0xc1 && !provider->buckb_cont &&
		provider->vbuckb_a == 0x46 && provider->vbuckb_b == 0x46 &&
		!provider->reserved && platform->valid &&
		platform->spm_pwr_status == 0x2a00005c &&
		platform->spm_pwr_status_2nd == 0x2a00004c &&
		!(platform->spm_cpu_pwr_status &
		  MT6797_A72_A34_CPU_STATUS_MASK) &&
		!(platform->spm_cpu_pwr_status_2nd &
		  MT6797_A72_A34_CPU_STATUS_MASK) &&
		platform->spm_mp2_cpusys_pwr_con == 0x00010132 &&
		platform->spm_mp2_cpu0_pwr_con == 0x00010332 &&
		platform->spm_mp2_cpu1_pwr_con == 0x00010332 &&
		platform->spm_cpu_ext_buck_iso == 0x00000002 &&
		!platform->mp2_sync_dcm &&
		platform->cci_mp2_port_control == 0xc0000000 &&
		!platform->cci_status_before && !platform->cci_status_after &&
		!platform->pwrap_reset_asserted &&
		source->clock.abi == MT6797_DVFSP_CLOCK_BACKEND_ABI &&
		!source->clock.reserved && source->clock.sample_generation &&
		source->bigidvfs.abi == MT6797_BIGIDVFS_BACKEND_ABI &&
		!source->bigidvfs.reserved &&
		source->bigidvfs.sample_generation &&
		!memcmp(&direct->owner, &a72_direct_expected_owner,
			 sizeof(direct->owner));
}

int
mt6797_a72_a34_evaluate(const struct mt6797_a72_a34_observation *observation)
{
	const struct mt6797_a72_a34_replay *replay;

	if (!observation)
		return -EINVAL;
	replay = &observation->replay;
	if (observation->abi != MT6797_A72_A34_ELIGIBILITY_ABI ||
	    observation->reserved[0] || observation->reserved[1] ||
	    observation->reserved[2] ||
	    !mt6797_a72_a34_direct_valid(&observation->direct) ||
	    replay->abi != MT6797_A72_A34_REPLAY_ABI || replay->valid != 1 ||
	    replay->proof !=
		MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR ||
	    replay->private_replay_value || replay->reserved[0] ||
	    replay->reserved[1] || replay->reserved[2] || replay->reserved[3])
		return -EPERM;
	return 0;
}
'''
    source = source[:start] + evaluator + source[end:]
    source_path.write_text(source, encoding="utf-8")

    a34_path = root / A34_TEST
    a34 = read_parent(root, A34_TEST)
    a34 = add_live_platform_fields(a34, "A34 live platform fixture")
    start = a34.index("static void mt6797_a34_every_byte_mutation_test(")
    end = a34.index("\nstatic void mt6797_a34_missing_replay_test", start)
    tests = r'''static void mt6797_a34_irrelevant_payload_test(struct kunit *test)
{
	struct mt6797_a34_test_state *state = test->priv;
	struct mt6797_a72_direct_source_snapshot *source =
		&state->observation->direct.source;

	source->platform.spm_cpu_pwr_status ^= BIT(11);
	source->platform.spm_cpu_pwr_status_2nd ^= BIT(13);
	source->clock.sample_generation = 9;
	source->clock.armplldiv_muxsel = 0x12345678;
	source->clock.cspm_hwsta[3] = 0x89abcdef;
	source->bigidvfs.sample_generation = 7;
	source->bigidvfs.pll_pcw = 0x10203040;
	source->bigidvfs.control = 0x50607080;
	mt6797_a34_expect_result_unchanged(test, state, 0);
}

static void mt6797_a34_relevant_mutation_test(struct kunit *test)
{
	struct mt6797_a34_test_state *state = test->priv;

	state->observation->direct.cpu8_online = 1;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
	mt6797_a34_fill_valid(state->observation);
	state->observation->direct.source.provider.buckb_cont = 1;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
	mt6797_a34_fill_valid(state->observation);
	state->observation->direct.source.platform.spm_cpu_pwr_status |= BIT(6);
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
	mt6797_a34_fill_valid(state->observation);
	state->observation->direct.source.platform.spm_mp2_cpu0_pwr_con ^= 1;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
	mt6797_a34_fill_valid(state->observation);
	state->observation->direct.source.platform.cci_mp2_port_control ^= 1;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
	mt6797_a34_fill_valid(state->observation);
	state->observation->direct.source.clock.sample_generation = 0;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
	mt6797_a34_fill_valid(state->observation);
	state->observation->direct.owner.diagnostic_blockers ^= 1;
	mt6797_a34_expect_result_unchanged(test, state, -EPERM);
}
'''
    a34 = a34[:start] + tests + a34[end:]
    a34 = replace_once(
        a34,
        "\tKUNIT_CASE(mt6797_a34_every_byte_mutation_test),",
        "\tKUNIT_CASE(mt6797_a34_irrelevant_payload_test),\n\tKUNIT_CASE(mt6797_a34_relevant_mutation_test),",
        "A34 test cases",
    )
    a34_path.write_text(a34, encoding="utf-8")

    derived = read_parent(root, DERIVED_TEST)
    derived = add_live_platform_fields(derived, "derived live platform fixture")
    derived = replace_once(
        derived,
        """state->source.clock.sample_generation++;
	mt6797_a72_expect_source_rejection(test, state, -EPERM, 1);""",
        """state->source.clock.sample_generation = 0;
	mt6797_a72_expect_source_rejection(test, state, -EPROTO, 1);""",
        "derived generation rejection",
    )
    (root / DERIVED_TEST).write_text(derived, encoding="utf-8")

    membership_test = read_parent(root, MEMBERSHIP_TEST)
    membership_test = add_live_platform_fields(
        membership_test, "atomic publication live platform fixture"
    )
    (root / MEMBERSHIP_TEST).write_text(membership_test, encoding="utf-8")


def verify_parent(root: Path) -> None:
    for relative in PARENT_SHA256:
        read_parent(root, relative)


if __name__ == "__main__":
    raise SystemExit("import this module and select an explicit phase")
