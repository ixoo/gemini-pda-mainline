#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)

struct mt6797_a72_cpu9_derived_workspace {
	struct mt6797_a72_owner_snapshot parent;
	struct mt6797_a72_entry_snapshot entry;
	struct mt6797_a72_a36_prestate prestate;
};

static struct mt6797_a72_cpu9_derived_workspace a72_cpu9_derived_workspace;

static int
mt6797_a72_cpu9_parent_validate(const struct mt6797_a72_owner_snapshot *parent,
				const struct mt6797_a72_direct_topology *topology)
{
	const struct mt6797_a72_transaction *cpu8;

	if (!parent || !topology)
		return -EINVAL;
	cpu8 = &parent->retired[0];
	if (parent->abi != MT6797_A72_TRANSACTION_ABI ||
	    parent->health != MT6797_A72_OWNER_AVAILABLE ||
	    parent->phase != MT6797_A72_PHASE_IDLE ||
	    parent->members != BIT(0) ||
	    parent->provider_state != MT6797_A72_PROVIDER_HELD ||
	    !parent->bootstrap_valid || !parent->members_valid ||
	    parent->active.valid || parent->controller_present ||
	    !(parent->attempts_consumed & MT6797_A72_ATTEMPT_CPU8_UP) ||
	    (parent->attempts_consumed & MT6797_A72_ATTEMPT_CPU9_UP) ||
	    !(parent->attempts_available & MT6797_A72_ATTEMPT_CPU9_UP) ||
	    !(parent->retired_mask & BIT(0)) ||
	    (parent->retired_mask & BIT(1)) ||
	    !mt6797_a72_provider_identity_valid(&parent->provider_identity))
		return -EPERM;

	if (!cpu8->valid ||
	    cpu8->identity.abi != MT6797_A72_TRANSACTION_ABI ||
	    cpu8->identity.owner != ARM64_LATE_CPU_STARTUP_OWNER_MEMBERSHIP ||
	    cpu8->identity.operation != ARM64_LATE_CPU_STARTUP_OP_CPU8_UP ||
	    cpu8->identity.target_cpu != 8 ||
	    cpu8->identity.cpuhp_target != CPUHP_ONLINE ||
	    cpu8->identity.target_mpidr != 0x200 ||
	    cpu8->public_preflight != MT6797_A72_PUBLIC_ADMISSION_CLAIMED ||
	    !cpu8->a36_valid || !cpu8->p17_p18_published ||
	    !cpu8->p27_valid || !cpu8->provider_acquire_valid ||
	    !cpu8->p28_valid || !cpu8->p30_token_valid ||
	    !cpu8->cpu8_success_published || cpu8->cpu9_success_published ||
	    cpu8->p29_valid || cpu8->p32_valid ||
	    cpu8->p27_preparation.stage != MT6797_A72_P27_STAGE_COMPLETE ||
	    cpu8->p28_preparation.stage != MT6797_A72_P28_STAGE_COMPLETE ||
	    cpu8->budgets.preparation != MT6797_A72_BUDGET_CONSUMED ||
	    cpu8->budgets.provider_acquire != MT6797_A72_BUDGET_CONSUMED ||
	    cpu8->budgets.postprovider_preparation !=
		    MT6797_A72_BUDGET_CONSUMED ||
	    cpu8->budgets.cpu_on != MT6797_A72_BUDGET_CONSUMED ||
	    memcmp(&cpu8->provider_identity, &parent->provider_identity,
		   sizeof(cpu8->provider_identity)))
		return -EPERM;

	if (topology->cpu8_possible != 1 || topology->cpu9_possible != 1 ||
	    topology->cpu8_present != 1 || topology->cpu9_present != 1 ||
	    topology->cpu8_online != 1 || topology->cpu9_online ||
	    topology->cpu8_method_valid != 1 ||
	    topology->cpu9_method_valid != 1 ||
	    topology->cpu8_mpidr != 0x200 || topology->cpu9_mpidr != 0x201)
		return -EPERM;

	return 0;
}

static void
mt6797_a72_derive_cpu9_entry(const struct mt6797_a72_owner_snapshot *parent,
			     const struct mt6797_a72_direct_topology *topology,
			     struct mt6797_a72_entry_snapshot *entry)
{
	entry->members = parent->members;
	entry->provider_state = parent->provider_state;
	entry->online_mask = BIT(0);
	entry->cpuhp_state_cpu8 = CPUHP_ONLINE;
	entry->cpuhp_state_cpu9 = CPUHP_OFFLINE;
	entry->observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN;
	entry->flags = MT6797_A72_ENTRY_FLAGS_MASK;
	entry->cpu8_mpidr = topology->cpu8_mpidr;
	entry->cpu9_mpidr = topology->cpu9_mpidr;
}

static void
mt6797_a72_derive_cpu9_prestate(const struct mt6797_a72_transaction *transaction,
				struct mt6797_a72_a36_prestate *prestate)
{
	prestate->abi = MT6797_A72_A36_PRESTATE_ABI;
	prestate->operation = ARM64_LATE_CPU_STARTUP_OP_CPU9_UP;
	prestate->observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN;
	prestate->call_shape = MT6797_A72_A36_CALL_SHAPE_TWO_ARG;
	prestate->cpu8_online = 1;
	prestate->cpu8_cluster_dcm_published = 1;
	prestate->target_mpidr = 0x201;
	prestate->secondary_entry_pa = transaction->identity.cpu_on_entry_pa;
	prestate->generation = transaction->identity.generation;
	prestate->cookie = transaction->identity.cookie;
}

static int
mt6797_a72_membership_derive_cpu9_locked(const struct mt6797_a72_direct_topology *topology,
					 const struct arm64_late_cpu_ready_token *ready,
					 struct mt6797_a72_transaction *transaction,
					 u32 *derive_stage)
{
	struct mt6797_a72_cpu9_derived_workspace *workspace =
		&a72_cpu9_derived_workspace;
	unsigned long flags;
	int ret;

	memset(workspace, 0, sizeof(*workspace));
	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_READY_TOKEN);
	ret = mt6797_a72_ready_token_validate(9, ready);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_CPU8_TERMINAL);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	mt6797_a72_direct_owner_snapshot_locked(&workspace->parent);
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	ret = mt6797_a72_cpu9_parent_validate(&workspace->parent, topology);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_cpu9_entry(&workspace->parent, topology,
				     &workspace->entry);
	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_ENTRY_VALIDATE);
	ret = mt6797_a72_membership_validate_entry(9, CPUHP_ONLINE,
					   MT6797_A72_ATTEMPT_CPU9_UP,
					   &workspace->entry);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_P31_CONSUME);
	ret = mt6797_a72_membership_p31_consume_attempt(9, CPUHP_ONLINE,
						MT6797_A72_ATTEMPT_CPU9_UP,
						&workspace->entry);
	if (ret)
		goto out_clear;
	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_TOKEN_MINT);
	ret = mt6797_a72_membership_mint_up_token(9, CPUHP_ONLINE,
					  MT6797_A72_ATTEMPT_CPU9_UP,
					  &workspace->entry, ready, transaction);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_cpu9_prestate(transaction, &workspace->prestate);
	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_PRESTATE_VALIDATE);
	ret = mt6797_a72_membership_validate_up_prestate(transaction,
							 &workspace->prestate);
	if (ret)
		goto reject_frozen;
	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_PRESTATE_BIND);
	ret = mt6797_a72_membership_bind_a36_prestate(&transaction->identity,
						      &workspace->prestate,
						      transaction);
	if (ret)
		goto reject_frozen;
	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_COMPLETE);
	goto out_clear;

reject_frozen:
	mt6797_a72_membership_reject_frozen(&transaction->identity);
	memset(transaction, 0, sizeof(*transaction));
out_clear:
	memset(workspace, 0, sizeof(*workspace));
	return ret;
}

int
mt6797_a72_membership_derive_cpu9_diagnostic(const struct arm64_late_cpu_ready_token *ready,
					      struct mt6797_a72_transaction *transaction,
					      u32 *derive_stage)
{
	struct mt6797_a72_direct_topology topology = {};
	int ret;

	mt6797_a72_derive_stage_set(derive_stage, MT6797_A72_CPU9_DERIVE_NONE);
	if (!transaction)
		return -EINVAL;
	memset(transaction, 0, sizeof(*transaction));
	cpus_read_lock();
	mutex_lock(&a72_transition_lock);
	mt6797_a72_derive_stage_set(derive_stage,
				     MT6797_A72_CPU9_DERIVE_TOPOLOGY);
	if (nr_cpu_ids <= 9) {
		ret = -ENODEV;
		goto out_unlock;
	}
	mt6797_a72_membership_fill_cpu8_topology(&topology);
	ret = mt6797_a72_membership_derive_cpu9_locked(&topology, ready,
						      transaction, derive_stage);
out_unlock:
	mutex_unlock(&a72_transition_lock);
	cpus_read_unlock();
	return ret;
}

int
mt6797_a72_membership_derive_cpu9(const struct arm64_late_cpu_ready_token *ready,
				  struct mt6797_a72_transaction *transaction)
{
	return mt6797_a72_membership_derive_cpu9_diagnostic(ready, transaction,
							    NULL);
}

#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED
int
mt6797_a72_membership_test_derive_cpu9(const struct mt6797_a72_direct_topology *topology,
				       const struct arm64_late_cpu_ready_token *ready,
				       struct mt6797_a72_transaction *transaction)
{
	int ret;

	if (!topology || !transaction)
		return -EINVAL;
	memset(transaction, 0, sizeof(*transaction));
	cpus_read_lock();
	mutex_lock(&a72_transition_lock);
	ret = mt6797_a72_membership_derive_cpu9_locked(topology, ready,
						      transaction, NULL);
	mutex_unlock(&a72_transition_lock);
	cpus_read_unlock();
	return ret;
}

int
mt6797_a72_membership_test_validate_cpu9_parent(const struct mt6797_a72_owner_snapshot *parent,
						 const struct mt6797_a72_direct_topology *topology)
{
	return mt6797_a72_cpu9_parent_validate(parent, topology);
}
#endif

#endif
