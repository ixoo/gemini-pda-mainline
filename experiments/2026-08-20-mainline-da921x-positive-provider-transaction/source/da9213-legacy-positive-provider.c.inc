#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)

static const u8 da9213_legacy_provider_snapshot_regs[] = {
	0x56, 0x51, 0x5e, 0xd9, 0xda,
};

const char *da9213_legacy_provider_state_name(
	enum da9213_legacy_provider_state state)
{
	switch (state) {
	case DA9213_LEGACY_PROVIDER_IDLE:
		return "idle";
	case DA9213_LEGACY_PROVIDER_ACQUIRING:
		return "acquiring";
	case DA9213_LEGACY_PROVIDER_HELD:
		return "held";
	case DA9213_LEGACY_PROVIDER_RELEASING:
		return "releasing";
	case DA9213_LEGACY_PROVIDER_RELEASED:
		return "released";
	case DA9213_LEGACY_PROVIDER_FAILED_NO_MUTATION:
		return "failed-no-mutation";
	case DA9213_LEGACY_PROVIDER_FAULT_RETAINED:
		return "fault-retained-reset-only";
	default:
		return "invalid";
	}
}

static int da9213_legacy_provider_read(
	struct i2c_adapter *adapter, u16 address, u8 reg, u8 *value,
	const struct da9213_legacy_provider_transport_ops *ops,
	struct da9213_legacy_provider_result *result)
{
	struct i2c_msg messages[2] = { };
	u8 data = 0;
	int ret;

	messages[0].addr = address;
	messages[0].len = 1;
	messages[0].buf = &reg;
	messages[1].addr = address;
	messages[1].flags = I2C_M_RD;
	messages[1].len = 1;
	messages[1].buf = &data;

	ret = ops->transfer(adapter, messages, ARRAY_SIZE(messages));
	result->operation_transfers++;
	result->total_transfers++;
	if (ret < 0)
		return ret;
	if (ret != ARRAY_SIZE(messages))
		return -EIO;

	*value = data;
	return 0;
}

static int da9213_legacy_provider_snapshot(
	struct i2c_adapter *adapter, u16 address,
	const struct da9213_legacy_provider_transport_ops *ops,
	struct da9213_legacy_provider_result *result,
	struct da9213_legacy_provider_snapshot *snapshot)
{
	u8 *values = (u8 *)snapshot;
	unsigned int i;
	int ret;

	BUILD_BUG_ON(sizeof(*snapshot) !=
		     ARRAY_SIZE(da9213_legacy_provider_snapshot_regs));
	for (i = 0; i < ARRAY_SIZE(da9213_legacy_provider_snapshot_regs); i++) {
		ret = da9213_legacy_provider_read(
			adapter, address,
			da9213_legacy_provider_snapshot_regs[i], &values[i],
			ops, result);
		if (ret)
			return ret;
	}

	return 0;
}

static int da9213_legacy_provider_write_cont(
	struct i2c_adapter *adapter, u16 address, u8 value, bool inverse,
	const struct da9213_legacy_provider_transport_ops *ops,
	struct da9213_legacy_provider_result *result)
{
	u8 payload[2] = { 0x5e, value };
	struct i2c_msg message = {
		.addr = address,
		.len = ARRAY_SIZE(payload),
		.buf = payload,
	};
	int ret;

	if (inverse)
		result->inverse_write_attempts++;
	else
		result->write_attempts++;
	ret = ops->transfer(adapter, &message, 1);
	result->operation_transfers++;
	result->total_transfers++;
	if (ret < 0)
		return ret;
	if (ret != 1)
		return -EIO;

	return 0;
}

static bool da9213_legacy_provider_request_valid(
	const struct mt6797_a72_provider_request *request)
{
	return request &&
		request->abi == MT6797_A72_PROVIDER_CALL_ABI &&
		request->operation == MT6797_A72_PROVIDER_OPERATION_CPU8_UP &&
		request->settle_us == DA9213_LEGACY_PROVIDER_SETTLE_US &&
		request->da921x_page == MT6797_A72_PROVIDER_CALL_DA921X_PAGE &&
		request->buckb_vsel == MT6797_A72_PROVIDER_CALL_BUCKB_VSEL &&
		!request->reserved && request->transaction_generation &&
		request->transaction_generation != ~0ULL &&
		request->transaction_cookie && request->transaction_cookie != ~0ULL;
}

static bool da9213_legacy_provider_initial_state_valid(
	const struct da9213_legacy_provider_snapshot *snapshot)
{
	return snapshot->control_a == 0x7b &&
		!(snapshot->control_a & 0x80) &&
		snapshot->buckb_cont == 0x00 &&
		snapshot->vbuckb_a == MT6797_A72_PROVIDER_CALL_BUCKB_VSEL &&
		snapshot->vbuckb_b == MT6797_A72_PROVIDER_CALL_BUCKB_VSEL;
}

static bool da9213_legacy_provider_owned_state_matches(
	const struct da9213_legacy_provider_snapshot *snapshot,
	const struct da9213_legacy_provider_snapshot *prestate, u8 buckb_cont)
{
	return snapshot->control_a == prestate->control_a &&
		!(snapshot->control_a & 0x80) &&
		snapshot->buckb_cont == buckb_cont &&
		snapshot->vbuckb_a == prestate->vbuckb_a &&
		snapshot->vbuckb_b == prestate->vbuckb_b;
}

static bool da9213_legacy_provider_transport_valid(
	struct i2c_adapter *adapter,
	const struct da9213_legacy_provider_transport_ops *ops)
{
	return adapter && ops && ops->transfer && ops->delay &&
		adapter->lock_ops && adapter->lock_ops->lock_bus &&
		adapter->lock_ops->unlock_bus;
}

static void da9213_legacy_provider_restore_retries(
	struct i2c_adapter *adapter, unsigned int saved_retries)
{
	adapter->retries = saved_retries;
}

static void da9213_legacy_provider_acquire_response(
	const struct mt6797_a72_provider_request *request,
	struct da9213_legacy_provider_result *result,
	struct mt6797_a72_provider_response *response)
{
	response->abi = MT6797_A72_PROVIDER_CALL_ABI;
	response->returned = 1;
	response->vote_requested = 1;
	response->provider_mutated = 1;
	response->rail_mutated = 1;
	response->settle_us = DA9213_LEGACY_PROVIDER_SETTLE_US;
	response->da921x_page = MT6797_A72_PROVIDER_CALL_DA921X_PAGE;
	response->buckb_enabled = 1;
	response->buckb_vsel = result->held_state.vbuckb_a;
	response->origin = 1;
	response->origin_generation = request->transaction_generation;
	response->held_handle = result->held_handle;
}

int da9213_legacy_provider_transaction_acquire(
	struct i2c_adapter *adapter, u16 address,
	const struct da9213_legacy_provider_transport_ops *ops,
	const struct mt6797_a72_provider_request *request,
	struct da9213_legacy_provider_result *result,
	struct mt6797_a72_provider_response *response)
{
	unsigned int saved_retries;
	int ret;

	if (!result || !response ||
	    !da9213_legacy_provider_transport_valid(adapter, ops) ||
	    !da9213_legacy_provider_request_valid(request))
		return -EINVAL;
	memset(response, 0, sizeof(*response));
	if (result->state != DA9213_LEGACY_PROVIDER_IDLE)
		return -EALREADY;

	result->state = DA9213_LEGACY_PROVIDER_ACQUIRING;
	result->acquire_attempts = 1;
	result->operation_transfers = 0;
	result->error = 0;
	i2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);
	saved_retries = adapter->retries;
	adapter->retries = 0;

	ret = da9213_legacy_provider_snapshot(adapter, address, ops, result,
					      &result->prestate);
	if (ret)
		goto out_failed;
	if (!da9213_legacy_provider_initial_state_valid(&result->prestate)) {
		ret = -ERANGE;
		goto out_failed;
	}

	ret = da9213_legacy_provider_write_cont(adapter, address, 0x01, false,
						ops, result);
	if (ret)
		goto out_failed;
	ops->delay(DA9213_LEGACY_PROVIDER_SETTLE_US,
		   DA9213_LEGACY_PROVIDER_SETTLE_US + 100);
	ret = da9213_legacy_provider_snapshot(adapter, address, ops, result,
					      &result->held_state);
	if (ret)
		goto out_failed;
	if (!da9213_legacy_provider_owned_state_matches(
			&result->held_state, &result->prestate, 0x01)) {
		ret = -ERANGE;
		goto out_failed;
	}

	result->held_handle.generation = request->transaction_generation;
	result->held_handle.cookie = request->transaction_cookie;
	result->state = DA9213_LEGACY_PROVIDER_HELD;
	result->error = 0;
	da9213_legacy_provider_acquire_response(request, result, response);
	da9213_legacy_provider_restore_retries(adapter, saved_retries);
	i2c_unlock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);
	return 0;

out_failed:
	result->error = ret;
	if (result->write_attempts)
		result->state = DA9213_LEGACY_PROVIDER_FAULT_RETAINED;
	else
		result->state = DA9213_LEGACY_PROVIDER_FAILED_NO_MUTATION;
	da9213_legacy_provider_restore_retries(adapter, saved_retries);
	i2c_unlock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);
	return ret;
}

static bool da9213_legacy_provider_handle_matches(
	const struct mt6797_a72_provider_handle *left,
	const struct mt6797_a72_provider_handle *right)
{
	return left && right && left->generation == right->generation &&
		left->cookie == right->cookie;
}

static void da9213_legacy_provider_release_response(
	struct da9213_legacy_provider_result *result,
	struct mt6797_a72_provider_response *response)
{
	response->abi = MT6797_A72_PROVIDER_CALL_ABI;
	response->returned = 1;
	response->vote_requested = 1;
	response->provider_mutated = 1;
	response->rail_mutated = 1;
	response->settle_us = DA9213_LEGACY_PROVIDER_SETTLE_US;
	response->da921x_page = MT6797_A72_PROVIDER_CALL_DA921X_PAGE;
	response->buckb_enabled = 0;
	response->buckb_vsel = result->final_state.vbuckb_a;
	response->origin = 1;
	response->origin_generation = result->held_handle.generation;
	response->held_handle = result->held_handle;
}

int da9213_legacy_provider_transaction_release(
	struct i2c_adapter *adapter, u16 address,
	const struct da9213_legacy_provider_transport_ops *ops,
	const struct mt6797_a72_provider_handle *handle,
	struct da9213_legacy_provider_result *result,
	struct mt6797_a72_provider_response *response)
{
	unsigned int saved_retries;
	int ret;

	if (!result || !response ||
	    !da9213_legacy_provider_transport_valid(adapter, ops) || !handle)
		return -EINVAL;
	memset(response, 0, sizeof(*response));
	if (result->state != DA9213_LEGACY_PROVIDER_HELD)
		return -EALREADY;
	if (!da9213_legacy_provider_handle_matches(handle,
						   &result->held_handle))
		return -EPERM;

	result->state = DA9213_LEGACY_PROVIDER_RELEASING;
	result->release_attempts = 1;
	result->operation_transfers = 0;
	result->error = 0;
	i2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);
	saved_retries = adapter->retries;
	adapter->retries = 0;

	ret = da9213_legacy_provider_snapshot(adapter, address, ops, result,
					      &result->release_prestate);
	if (ret)
		goto out_fault;
	if (!da9213_legacy_provider_owned_state_matches(
			&result->release_prestate, &result->prestate, 0x01)) {
		ret = -ERANGE;
		goto out_fault;
	}

	ret = da9213_legacy_provider_write_cont(adapter, address, 0x00, true,
						ops, result);
	if (ret)
		goto out_fault;
	ret = da9213_legacy_provider_snapshot(adapter, address, ops, result,
					      &result->final_state);
	if (ret)
		goto out_fault;
	if (!da9213_legacy_provider_owned_state_matches(
			&result->final_state, &result->prestate, 0x00)) {
		ret = -ERANGE;
		goto out_fault;
	}

	result->state = DA9213_LEGACY_PROVIDER_RELEASED;
	result->error = 0;
	da9213_legacy_provider_release_response(result, response);
	da9213_legacy_provider_restore_retries(adapter, saved_retries);
	i2c_unlock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);
	return 0;

out_fault:
	result->error = ret;
	result->state = DA9213_LEGACY_PROVIDER_FAULT_RETAINED;
	da9213_legacy_provider_restore_retries(adapter, saved_retries);
	i2c_unlock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);
	return ret;
}

static const struct da9213_legacy_provider_transport_ops
da9213_legacy_positive_provider_ops = {
	.transfer = __i2c_transfer,
	.delay = usleep_range,
};

#endif
