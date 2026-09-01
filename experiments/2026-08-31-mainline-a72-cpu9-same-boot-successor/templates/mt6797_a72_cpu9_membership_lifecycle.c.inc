#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)

static bool
mt6797_a72_cpu9_cluster_budgets_empty(const struct mt6797_a72_transaction *transaction)
{
	const struct mt6797_a72_call_budgets *budgets = &transaction->budgets;

	return budgets->preparation == MT6797_A72_BUDGET_NONE &&
		budgets->provider_acquire == MT6797_A72_BUDGET_NONE &&
		budgets->postprovider_preparation == MT6797_A72_BUDGET_NONE &&
		budgets->affinity == MT6797_A72_BUDGET_NONE &&
		budgets->provider_release == MT6797_A72_BUDGET_NONE &&
		budgets->provider_abort == MT6797_A72_BUDGET_NONE;
}

static bool mt6797_a72_cpu9_retired_parent_valid_locked(void)
{
	const struct mt6797_a72_transaction *cpu8 = &a72_owner.retired[0];

	return a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
		a72_owner.bootstrap_valid && a72_owner.members_valid &&
		a72_owner.members == BIT(0) &&
		a72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
		mt6797_a72_provider_identity_valid(&a72_owner.provider_identity) &&
		(a72_owner.retired_mask & BIT(0)) &&
		!(a72_owner.retired_mask & BIT(1)) && cpu8->valid &&
		cpu8->identity.abi == MT6797_A72_TRANSACTION_ABI &&
		cpu8->identity.operation == ARM64_LATE_CPU_STARTUP_OP_CPU8_UP &&
		cpu8->identity.target_cpu == 8 &&
		cpu8->identity.cpuhp_target == CPUHP_ONLINE &&
		cpu8->identity.target_mpidr == 0x200 &&
		cpu8->public_preflight == MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
		cpu8->p17_p18_published && cpu8->p27_valid &&
		cpu8->provider_acquire_valid && cpu8->p28_valid &&
		cpu8->p30_token_valid && cpu8->cpu8_success_published &&
		!cpu8->cpu9_success_published && !cpu8->p29_valid &&
		!cpu8->p32_valid &&
		!memcmp(&cpu8->provider_identity, &a72_owner.provider_identity,
			sizeof(cpu8->provider_identity));
}

static bool
mt6797_a72_cpu9_active_valid_locked(const struct mt6797_a72_transaction *transaction)
{
	const struct mt6797_a72_transaction *active = &a72_owner.active;

	return transaction && active->valid && active->a36_valid &&
		active->p30_token_valid && active->p17_p18_published &&
		active->identity.abi == MT6797_A72_TRANSACTION_ABI &&
		active->identity.operation == ARM64_LATE_CPU_STARTUP_OP_CPU9_UP &&
		active->identity.target_cpu == 9 &&
		active->identity.cpuhp_target == CPUHP_ONLINE &&
		active->identity.target_mpidr == 0x201 &&
		active->controller_cookie == active->identity.cookie &&
		a72_owner.controller == current &&
		a72_owner.controller_cookie == active->identity.cookie &&
		mt6797_a72_cpu9_retired_parent_valid_locked() &&
		mt6797_a72_cpu9_cluster_budgets_empty(active) &&
		!active->p27_valid && !active->provider_acquire_valid &&
		!active->provider_rejection_valid &&
		!active->provider_abort_valid && !active->p28_valid &&
		!active->p29_valid && !active->p32_valid &&
		!memcmp(&active->provider_identity, &a72_owner.provider_identity,
			sizeof(active->provider_identity)) &&
		!memcmp(&active->identity, &transaction->identity,
			sizeof(active->identity));
}

int mt6797_a72_membership_publish_cpu9(struct mt6797_a72_transaction *transaction)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	mutex_lock(&a72_transition_lock);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.phase == MT6797_A72_PHASE_FROZEN &&
	    a72_owner.active.valid && a72_owner.active.a36_valid &&
	    a72_owner.active.p30_token_valid &&
	    !a72_owner.active.p17_p18_published &&
	    a72_owner.active.public_preflight ==
		    MT6797_A72_PUBLIC_ADMISSION_NONE &&
	    a72_owner.active.identity.operation ==
		    ARM64_LATE_CPU_STARTUP_OP_CPU9_UP &&
	    a72_owner.active.identity.target_cpu == 9 &&
	    a72_owner.active.identity.cpuhp_target == CPUHP_ONLINE &&
	    a72_owner.active.controller_cookie ==
		    a72_owner.active.identity.cookie &&
	    a72_owner.controller == current &&
	    a72_owner.controller_cookie == a72_owner.active.identity.cookie &&
	    mt6797_a72_cpu9_retired_parent_valid_locked() &&
	    mt6797_a72_cpu9_cluster_budgets_empty(&a72_owner.active) &&
	    a72_owner.active.budgets.cpu_on ==
		    MT6797_A72_BUDGET_AVAILABLE &&
	    !a72_owner.active.cpu9_success_published &&
	    !memcmp(&a72_owner.active.provider_identity,
		    &a72_owner.provider_identity,
		    sizeof(a72_owner.active.provider_identity)) &&
	    !memcmp(&a72_owner.active.identity, &transaction->identity,
		    sizeof(a72_owner.active.identity))) {
		a72_owner.active.p17_p18_published = 1;
		a72_owner.phase = MT6797_A72_PHASE_ON_ISSUED;
		*transaction = a72_owner.active;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	mutex_unlock(&a72_transition_lock);
	return ret;
}

static int mt6797_a72_preflight_cpu9_state(bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
	    mt6797_a72_cpu9_active_valid_locked(&a72_owner.active) &&
	    a72_owner.active.budgets.cpu_on ==
		    MT6797_A72_BUDGET_AVAILABLE &&
	    !a72_owner.active.cpu9_success_published &&
	    cpu8_online && !cpu9_online) {
		if (a72_owner.active.public_preflight ==
		    MT6797_A72_PUBLIC_ADMISSION_CLAIMED) {
			ret = -EALREADY;
		} else {
			a72_owner.active.public_preflight =
				MT6797_A72_PUBLIC_ADMISSION_PREFLIGHT;
			ret = 0;
		}
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_membership_preflight_cpu9(void)
{
	int ret;

	cpus_read_lock();
	ret = mt6797_a72_preflight_cpu9_state(cpu_online(8), cpu_online(9));
	cpus_read_unlock();
	return ret;
}

static int
mt6797_a72_claim_cpu9_state(struct mt6797_a72_transaction *transaction,
			    bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	memset(transaction, 0, sizeof(*transaction));
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
	    mt6797_a72_cpu9_active_valid_locked(&a72_owner.active) &&
	    a72_owner.active.public_preflight ==
		    MT6797_A72_PUBLIC_ADMISSION_PREFLIGHT &&
	    a72_owner.active.budgets.cpu_on ==
		    MT6797_A72_BUDGET_AVAILABLE &&
	    !a72_owner.active.cpu9_success_published &&
	    cpu8_online && !cpu9_online) {
		a72_owner.active.public_preflight =
			MT6797_A72_PUBLIC_ADMISSION_CLAIMED;
		*transaction = a72_owner.active;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction)
{
	int ret;

	cpus_read_lock();
	ret = mt6797_a72_claim_cpu9_state(transaction,
					 cpu_online(8), cpu_online(9));
	cpus_read_unlock();
	return ret;
}

static int
mt6797_a72_reject_cpu9_state(struct mt6797_a72_transaction *transaction,
			     bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	mutex_lock(&a72_transition_lock);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
	    mt6797_a72_cpu9_active_valid_locked(transaction) &&
	    a72_owner.active.public_preflight ==
		    MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
	    a72_owner.active.budgets.cpu_on ==
		    MT6797_A72_BUDGET_AVAILABLE &&
	    !a72_owner.active.cpu9_success_published &&
	    cpu8_online && !cpu9_online) {
		a72_owner.retired[1] = a72_owner.active;
		a72_owner.retired_mask |= BIT(1);
		*transaction = a72_owner.retired[1];
		memset(&a72_owner.active, 0, sizeof(a72_owner.active));
		a72_owner.controller = NULL;
		a72_owner.controller_cookie = 0;
		a72_owner.phase = MT6797_A72_PHASE_REJECTED;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	mutex_unlock(&a72_transition_lock);
	return ret;
}

int mt6797_a72_membership_reject_cpu9(struct mt6797_a72_transaction *transaction)
{
	int ret;

	cpus_read_lock();
	ret = mt6797_a72_reject_cpu9_state(transaction,
					  cpu_online(8), cpu_online(9));
	cpus_read_unlock();
	return ret;
}

static int
mt6797_a72_begin_cpu9_on_state(struct mt6797_a72_transaction *transaction,
			       bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	mutex_lock(&a72_transition_lock);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
	    mt6797_a72_cpu9_active_valid_locked(transaction) &&
	    a72_owner.active.public_preflight ==
		    MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
	    a72_owner.active.budgets.cpu_on ==
		    MT6797_A72_BUDGET_AVAILABLE &&
	    !a72_owner.active.cpu9_success_published &&
	    cpu8_online && !cpu9_online) {
		a72_owner.active.budgets.cpu_on = MT6797_A72_BUDGET_CONSUMED;
		*transaction = a72_owner.active;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	mutex_unlock(&a72_transition_lock);
	return ret;
}

int mt6797_a72_membership_begin_cpu9_on(struct mt6797_a72_transaction *transaction)
{
	int ret;

	cpus_read_lock();
	ret = mt6797_a72_begin_cpu9_on_state(transaction,
					    cpu_online(8), cpu_online(9));
	cpus_read_unlock();
	return ret;
}

static int
mt6797_a72_publish_cpu9_success_state(struct mt6797_a72_transaction *transaction,
				      bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	mutex_lock(&a72_transition_lock);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
	    mt6797_a72_cpu9_active_valid_locked(transaction) &&
	    a72_owner.active.public_preflight ==
		    MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
	    a72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_CONSUMED &&
	    !a72_owner.active.cpu9_success_published &&
	    cpu8_online && cpu9_online) {
		a72_owner.members = BIT(0) | BIT(1);
		a72_owner.active.cpu9_success_published = 1;
		a72_owner.phase = MT6797_A72_PHASE_VERIFYING;
		*transaction = a72_owner.active;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	mutex_unlock(&a72_transition_lock);
	return ret;
}

int
mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction)
{
	int ret;

	cpus_read_lock();
	ret = mt6797_a72_publish_cpu9_success_state(transaction,
						   cpu_online(8), cpu_online(9));
	cpus_read_unlock();
	return ret;
}

static int
mt6797_a72_finalize_cpu9_success_state(struct mt6797_a72_transaction *transaction,
				       bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	mutex_lock(&a72_transition_lock);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.phase == MT6797_A72_PHASE_VERIFYING &&
	    mt6797_a72_cpu9_active_valid_locked(transaction) &&
	    a72_owner.active.public_preflight ==
		    MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
	    a72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_CONSUMED &&
	    a72_owner.active.cpu9_success_published &&
	    a72_owner.members == (BIT(0) | BIT(1)) &&
	    cpu8_online && cpu9_online) {
		a72_owner.retired[1] = a72_owner.active;
		a72_owner.retired_mask |= BIT(1);
		*transaction = a72_owner.retired[1];
		memset(&a72_owner.active, 0, sizeof(a72_owner.active));
		a72_owner.controller = NULL;
		a72_owner.controller_cookie = 0;
		a72_owner.phase = MT6797_A72_PHASE_IDLE;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	mutex_unlock(&a72_transition_lock);
	return ret;
}

int
mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction)
{
	int ret;

	cpus_read_lock();
	ret = mt6797_a72_finalize_cpu9_success_state(transaction,
						    cpu_online(8), cpu_online(9));
	cpus_read_unlock();
	return ret;
}

#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED
int mt6797_a72_membership_test_preflight_cpu9(bool cpu8_online,
					      bool cpu9_online)
{
	return mt6797_a72_preflight_cpu9_state(cpu8_online, cpu9_online);
}

int
mt6797_a72_membership_test_claim_cpu9(struct mt6797_a72_transaction *transaction,
				      bool cpu8_online, bool cpu9_online)
{
	return mt6797_a72_claim_cpu9_state(transaction,
					  cpu8_online, cpu9_online);
}

int
mt6797_a72_membership_test_reject_cpu9(struct mt6797_a72_transaction *transaction,
				       bool cpu8_online, bool cpu9_online)
{
	return mt6797_a72_reject_cpu9_state(transaction,
					   cpu8_online, cpu9_online);
}

int
mt6797_a72_membership_test_begin_cpu9_on(struct mt6797_a72_transaction *transaction,
					 bool cpu8_online, bool cpu9_online)
{
	return mt6797_a72_begin_cpu9_on_state(transaction,
					     cpu8_online, cpu9_online);
}

int
mt6797_a72_membership_test_publish_cpu9_success(struct mt6797_a72_transaction *transaction,
						 bool cpu8_online, bool cpu9_online)
{
	return mt6797_a72_publish_cpu9_success_state(transaction,
						    cpu8_online, cpu9_online);
}

int
mt6797_a72_membership_test_finalize_cpu9_success(struct mt6797_a72_transaction *transaction,
						  bool cpu8_online, bool cpu9_online)
{
	return mt6797_a72_finalize_cpu9_success_state(transaction,
						     cpu8_online, cpu9_online);
}
#endif

#endif
