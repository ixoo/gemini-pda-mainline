static int mt6797_bigidvfs_secure_sram_set(void *context, u32 mv_x100)
{
	struct arm_smccc_res result;

	(void)context;
	arm_smccc_smc(MT6797_BIGIDVFS_FID_SRAM_LDO_SET, mv_x100,
		      0, 0, 0, 0, 0, 0, &result);
	if (result.a0)
		return -EIO;

	return 0;
}

static void mt6797_bigidvfs_sram_delay(void *context, unsigned int min_us,
				       unsigned int max_us)
{
	(void)context;
	usleep_range(min_us, max_us);
}

static const struct mt6797_bigidvfs_sram_ops mt6797_bigidvfs_sram_ops = {
	.set = mt6797_bigidvfs_secure_sram_set,
	.read = mt6797_bigidvfs_secure_read,
	.delay = mt6797_bigidvfs_sram_delay,
};

static bool mt6797_bigidvfs_sram_ops_valid(
	const struct mt6797_bigidvfs_sram_ops *ops)
{
	return ops && ops->set && ops->read && ops->delay;
}

static bool mt6797_bigidvfs_sram_request_valid(
	const struct mt6797_bigidvfs_sram_request *request)
{
	return request && request->abi == MT6797_BIGIDVFS_SRAM_OWNER_ABI &&
	       request->attempt_id && request->cookie;
}

static bool mt6797_bigidvfs_sram_request_matches(
	const struct mt6797_bigidvfs_sram_request *left,
	const struct mt6797_bigidvfs_sram_request *right)
{
	return mt6797_bigidvfs_sram_request_valid(left) &&
	       mt6797_bigidvfs_sram_request_valid(right) &&
	       left->attempt_id == right->attempt_id &&
	       left->cookie == right->cookie;
}

static void mt6797_bigidvfs_sram_output(
	const struct mt6797_bigidvfs_sram_owner *owner,
	struct mt6797_bigidvfs_sram_result *result)
{
	*result = owner->result;
}

static int mt6797_bigidvfs_sram_fail(
	struct mt6797_bigidvfs_sram_owner *owner, int error,
	struct mt6797_bigidvfs_sram_result *result)
{
	owner->state = MT6797_BIGIDVFS_SRAM_OWNER_FAULTED;
	owner->result.error = error;
	owner->result.sealed = true;
	mt6797_bigidvfs_sram_output(owner, result);
	return error;
}

static int mt6797_bigidvfs_sram_read(
	struct mt6797_bigidvfs_sram_owner *owner,
	const struct mt6797_bigidvfs_sram_ops *ops, void *context,
	u32 address, u32 step, u32 *value,
	struct mt6797_bigidvfs_sram_result *result)
{
	int ret;

	owner->result.attempted_steps |= step;
	ret = ops->read(context, address, value);
	if (ret)
		return mt6797_bigidvfs_sram_fail(owner, ret, result);
	owner->result.completed_steps |= step;
	return 0;
}

int mt6797_bigidvfs_sram_owner_execute(
	struct mt6797_bigidvfs_sram_owner *owner,
	const struct mt6797_bigidvfs_sram_ops *ops, void *context,
	const struct mt6797_bigidvfs_sram_request *request,
	struct mt6797_bigidvfs_sram_result *result)
{
	int ret;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_bigidvfs_sram_result){};
	if (!owner || !mt6797_bigidvfs_sram_ops_valid(ops) ||
	    !mt6797_bigidvfs_sram_request_valid(request))
		return -EINVAL;
	if (owner->state != MT6797_BIGIDVFS_SRAM_OWNER_UNUSED) {
		mt6797_bigidvfs_sram_output(owner, result);
		if (!mt6797_bigidvfs_sram_request_matches(&owner->request,
							request))
			return -EPERM;
		return -EALREADY;
	}
	if (request->cpu != 8 || !request->provider_held ||
	    !request->isolation_crossed || request->cpu8_online ||
	    request->cpu9_online)
		return -EPERM;

	owner->state = MT6797_BIGIDVFS_SRAM_OWNER_INFLIGHT;
	owner->request = *request;
	owner->result = (struct mt6797_bigidvfs_sram_result) {
		.abi = MT6797_BIGIDVFS_SRAM_OWNER_ABI,
		.requested_mv_x100 = MT6797_BIGIDVFS_SRAM_TARGET_MV_X100,
		.attempt_id = request->attempt_id,
		.cookie = request->cookie,
		.effect_attempted = true,
	};
	owner->result.attempted_steps |= MT6797_BIGIDVFS_SRAM_SERVICE;
	ret = ops->set(context, MT6797_BIGIDVFS_SRAM_TARGET_MV_X100);
	if (ret)
		return mt6797_bigidvfs_sram_fail(owner, ret, result);
	owner->result.completed_steps |= MT6797_BIGIDVFS_SRAM_SERVICE;

	owner->result.attempted_steps |= MT6797_BIGIDVFS_SRAM_SETTLE;
	ops->delay(context, MT6797_BIGIDVFS_SRAM_SETTLE_MIN_US,
		   MT6797_BIGIDVFS_SRAM_SETTLE_MAX_US);
	owner->result.completed_steps |= MT6797_BIGIDVFS_SRAM_SETTLE;

	ret = mt6797_bigidvfs_sram_read(owner, ops, context,
					 MT6797_BIGIDVFS_SRAM_SELECTOR,
					 MT6797_BIGIDVFS_SRAM_SELECTOR_FIRST,
					 &owner->result.selector_first, result);
	if (ret)
		return ret;
	ret = mt6797_bigidvfs_sram_read(owner, ops, context,
					 MT6797_BIGIDVFS_SRAM_CALIBRATION,
					 MT6797_BIGIDVFS_SRAM_CALIBRATION_FIRST,
					 &owner->result.calibration_first, result);
	if (ret)
		return ret;
	ret = mt6797_bigidvfs_sram_read(owner, ops, context,
					 MT6797_BIGIDVFS_SRAM_SELECTOR,
					 MT6797_BIGIDVFS_SRAM_SELECTOR_SECOND,
					 &owner->result.selector_second, result);
	if (ret)
		return ret;
	ret = mt6797_bigidvfs_sram_read(owner, ops, context,
					 MT6797_BIGIDVFS_SRAM_CALIBRATION,
					 MT6797_BIGIDVFS_SRAM_CALIBRATION_SECOND,
					 &owner->result.calibration_second, result);
	if (ret)
		return ret;

	if (owner->result.selector_first != owner->result.selector_second ||
	    owner->result.calibration_first != owner->result.calibration_second)
		return mt6797_bigidvfs_sram_fail(owner, -EAGAIN, result);
	owner->result.attempted_steps |= MT6797_BIGIDVFS_SRAM_SELECTOR_VALID;
	if ((owner->result.selector_second &
	     MT6797_BIGIDVFS_SRAM_SELECTOR_MASK) !=
	    MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED)
		return mt6797_bigidvfs_sram_fail(owner, -ERANGE, result);
	owner->result.completed_steps |= MT6797_BIGIDVFS_SRAM_SELECTOR_VALID;
	owner->result.attempted_steps |= MT6797_BIGIDVFS_SRAM_CALIBRATION_VALID;
	if ((owner->result.calibration_second &
	     ~MT6797_BIGIDVFS_SRAM_CALIBRATION_MASK) ||
	    !(owner->result.calibration_second &
	      MT6797_BIGIDVFS_SRAM_CALIBRATION_MASK))
		return mt6797_bigidvfs_sram_fail(owner, -ERANGE, result);
	owner->result.completed_steps |= MT6797_BIGIDVFS_SRAM_CALIBRATION_VALID;
	owner->state = MT6797_BIGIDVFS_SRAM_OWNER_VERIFIED;
	owner->result.verified = true;
	owner->result.sealed = true;
	mt6797_bigidvfs_sram_output(owner, result);
	return 0;
}
