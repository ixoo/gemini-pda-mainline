#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR
static DEFINE_MUTEX(a72_direct_source_registry_lock);

static const struct mt6797_a72_direct_source_ops *a72_direct_source_ops;
static void *a72_direct_source_context;

int mt6797_a72_direct_source_register(
	const struct mt6797_a72_direct_source_ops *ops, void *context)
{
	int ret = 0;

	if (!ops || !ops->snapshot)
		return -EINVAL;

	mutex_lock(&a72_direct_source_registry_lock);
	if (a72_direct_source_ops) {
		ret = -EBUSY;
	} else {
		a72_direct_source_ops = ops;
		a72_direct_source_context = context;
	}
	mutex_unlock(&a72_direct_source_registry_lock);

	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_a72_direct_source_register);

void mt6797_a72_direct_source_unregister(
	const struct mt6797_a72_direct_source_ops *ops, void *context)
{
	mutex_lock(&a72_direct_source_registry_lock);
	if (a72_direct_source_ops == ops &&
	    a72_direct_source_context == context) {
		a72_direct_source_ops = NULL;
		a72_direct_source_context = NULL;
	}
	mutex_unlock(&a72_direct_source_registry_lock);
}
EXPORT_SYMBOL_GPL(mt6797_a72_direct_source_unregister);

static void mt6797_a72_direct_owner_snapshot_locked(
	struct mt6797_a72_owner_snapshot *snapshot)
{
	memset(snapshot, 0, sizeof(*snapshot));
	snapshot->active = a72_owner.active;
	memcpy(snapshot->retired, a72_owner.retired,
	       sizeof(snapshot->retired));
	snapshot->provider_identity = a72_owner.provider_identity;
	snapshot->first_fault = a72_owner.first_fault;
	snapshot->diagnostic_blockers = a72_owner.diagnostic_blockers;
	snapshot->controller_cookie = a72_owner.controller_cookie;
	snapshot->abi = MT6797_A72_TRANSACTION_ABI;
	snapshot->health = a72_owner.health;
	snapshot->phase = a72_owner.phase;
	snapshot->members = a72_owner.members;
	snapshot->provider_state = a72_owner.provider_state;
	snapshot->bootstrap_valid = a72_owner.bootstrap_valid;
	snapshot->members_valid = a72_owner.members_valid;
	snapshot->attempts_available = a72_owner.attempts_available;
	snapshot->attempts_consumed = a72_owner.attempts_consumed;
	snapshot->retired_mask = a72_owner.retired_mask;
	snapshot->controller_present = !!a72_owner.controller;
}

static bool mt6797_a72_direct_owner_pristine_locked(
	struct mt6797_a72_owner_snapshot *snapshot)
{
	const struct mt6797_a72_owner_snapshot expected = {
		.diagnostic_blockers = MT6797_A72_BLOCK_MASK,
		.abi = MT6797_A72_TRANSACTION_ABI,
		.health = MT6797_A72_OWNER_CLOSED,
		.phase = MT6797_A72_PHASE_UNINITIALIZED,
		.provider_state = MT6797_A72_PROVIDER_NONE,
	};

	mt6797_a72_direct_owner_snapshot_locked(snapshot);
	return !memcmp(snapshot, &expected, sizeof(expected)) &&
		!a72_owner.controller && !a72_owner.next_generation &&
		!a72_owner.next_cookie;
}

static bool mt6797_a72_direct_topology_valid(
	const struct mt6797_a72_direct_topology *topology)
{
	return topology->cpu8_possible == 1 &&
		topology->cpu9_possible == 1 &&
		topology->cpu8_present == 1 &&
		topology->cpu9_present == 1 &&
		!topology->cpu8_online && !topology->cpu9_online;
}

static bool mt6797_a72_direct_source_valid(
	const struct mt6797_a72_direct_source_snapshot *source)
{
	u32 provider_raw;

	provider_raw = source->provider.control_a |
		source->provider.status_b | source->provider.buckb_cont |
		source->provider.vbuckb_a | source->provider.vbuckb_b;
	return source->abi == MT6797_A72_DIRECT_SOURCE_ABI &&
		source->valid == 1 && !source->reserved[0] &&
		!source->reserved[1] &&
		source->provider.abi == MT6797_A72_PROVIDER_STATE_ABI &&
		source->provider.valid == 1 && !source->provider.reserved &&
		!(provider_raw & ~0xffU) && source->platform.valid &&
		source->clock.abi == MT6797_DVFSP_CLOCK_BACKEND_ABI &&
		!source->clock.reserved && source->clock.sample_generation &&
		source->bigidvfs.abi == MT6797_BIGIDVFS_BACKEND_ABI &&
		!source->bigidvfs.reserved &&
		source->bigidvfs.sample_generation;
}

static int mt6797_a72_direct_state_snapshot_locked(
	const struct mt6797_a72_direct_topology *topology,
	struct mt6797_a72_direct_state_snapshot *snapshot)
{
	struct mt6797_a72_direct_state_snapshot observed = { };
	struct mt6797_a72_owner_snapshot owner_after;
	unsigned long flags;
	int ret;

	if (!mt6797_a72_direct_topology_valid(topology))
		return -EPERM;

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!mt6797_a72_direct_owner_pristine_locked(&observed.owner)) {
		raw_spin_unlock_irqrestore(&a72_state_lock, flags);
		return -EPERM;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);

	mutex_lock(&a72_direct_source_registry_lock);
	if (!a72_direct_source_ops) {
		ret = -ENODEV;
		goto out_unlock;
	}
	ret = a72_direct_source_ops->snapshot(a72_direct_source_context,
					      &observed.source);
	if (ret)
		goto out_unlock;
	if (!mt6797_a72_direct_source_valid(&observed.source)) {
		ret = -EPROTO;
		goto out_unlock;
	}

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!mt6797_a72_direct_owner_pristine_locked(&owner_after) ||
	    memcmp(&observed.owner, &owner_after, sizeof(owner_after)))
		ret = -EPERM;
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	if (ret)
		goto out_unlock;

	observed.abi = MT6797_A72_DIRECT_STATE_ABI;
	observed.valid = 1;
	observed.cpu8_possible = topology->cpu8_possible;
	observed.cpu9_possible = topology->cpu9_possible;
	observed.cpu8_present = topology->cpu8_present;
	observed.cpu9_present = topology->cpu9_present;
	observed.cpu8_online = topology->cpu8_online;
	observed.cpu9_online = topology->cpu9_online;
	*snapshot = observed;
out_unlock:
	mutex_unlock(&a72_direct_source_registry_lock);
	return ret;
}

int mt6797_a72_direct_state_snapshot(
	struct mt6797_a72_direct_state_snapshot *snapshot)
{
	struct mt6797_a72_direct_topology topology;
	int ret;

	if (!snapshot)
		return -EINVAL;
	memset(snapshot, 0, sizeof(*snapshot));

	cpus_read_lock();
	mutex_lock(&a72_transition_lock);
	if (nr_cpu_ids <= 9) {
		ret = -ENODEV;
		goto out_unlock;
	}
	topology.cpu8_possible = cpu_possible(8);
	topology.cpu9_possible = cpu_possible(9);
	topology.cpu8_present = cpu_present(8);
	topology.cpu9_present = cpu_present(9);
	topology.cpu8_online = cpu_online(8);
	topology.cpu9_online = cpu_online(9);
	ret = mt6797_a72_direct_state_snapshot_locked(&topology, snapshot);
out_unlock:
	mutex_unlock(&a72_transition_lock);
	cpus_read_unlock();
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_a72_direct_state_snapshot);

#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST
int mt6797_a72_direct_state_test_snapshot(
	const struct mt6797_a72_direct_topology *topology,
	struct mt6797_a72_direct_state_snapshot *snapshot)
{
	int ret;

	if (!topology || !snapshot)
		return -EINVAL;
	memset(snapshot, 0, sizeof(*snapshot));
	cpus_read_lock();
	mutex_lock(&a72_transition_lock);
	ret = mt6797_a72_direct_state_snapshot_locked(topology, snapshot);
	mutex_unlock(&a72_transition_lock);
	cpus_read_unlock();
	return ret;
}
#endif
#endif
