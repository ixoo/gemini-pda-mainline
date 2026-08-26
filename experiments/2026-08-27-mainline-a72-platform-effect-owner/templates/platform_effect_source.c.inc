static bool mt6797_a72_platform_effect_ops_valid(
	const struct mt6797_a72_platform_effect_ops *ops)
{
	return ops && ops->spm_read && ops->spm_update_bits &&
		ops->mcucfg_read && ops->mcucfg_write &&
		ops->pwrap_assert && ops->pwrap_deassert &&
		ops->pwrap_status && ops->delay;
}

static bool mt6797_a72_platform_effect_handle_valid(
	const struct mt6797_a72_platform_effect_handle *handle)
{
	return handle && handle->attempt_id && handle->cookie;
}

static bool mt6797_a72_platform_effect_handle_matches(
	const struct mt6797_a72_platform_effect_handle *left,
	const struct mt6797_a72_platform_effect_handle *right)
{
	return mt6797_a72_platform_effect_handle_valid(left) &&
		mt6797_a72_platform_effect_handle_valid(right) &&
		left->attempt_id == right->attempt_id &&
		left->cookie == right->cookie;
}

static bool mt6797_a72_platform_effect_provider_matches(
	const struct mt6797_a72_platform_effect_handle *handle,
	const struct mt6797_a72_provider_handle *provider)
{
	return provider && provider->generation == handle->attempt_id &&
		provider->cookie == handle->cookie;
}

static void mt6797_a72_platform_effect_output(
	const struct mt6797_a72_platform_effect_owner *owner,
	struct mt6797_a72_platform_effect_result *result)
{
	*result = owner->result;
}

static int mt6797_a72_platform_effect_fail(
	struct mt6797_a72_platform_effect_owner *owner,
	enum mt6797_a72_platform_effect_state state, int error,
	struct mt6797_a72_platform_effect_result *result)
{
	owner->state = state;
	owner->result.error = error;
	owner->result.sealed = true;
	mt6797_a72_platform_effect_output(owner, result);
	return error;
}

static int mt6797_a72_platform_effect_read_exact_spm(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	u32 offset, u32 expected, u32 *observed,
	struct mt6797_a72_platform_effect_result *result)
{
	int ret;

	ret = ops->spm_read(context, offset, observed);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	if (*observed != expected)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -ERANGE, result);
	return 0;
}

int mt6797_a72_platform_effect_owner_p27_acquire(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	struct mt6797_a72_platform_effect_result *result)
{
	u32 value;
	int status;
	int ret;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_a72_platform_effect_result){};
	if (!owner || !mt6797_a72_platform_effect_ops_valid(ops) ||
	    !mt6797_a72_platform_effect_handle_valid(handle))
		return -EINVAL;
	if (owner->state != MT6797_A72_EFFECT_UNUSED) {
		mt6797_a72_platform_effect_output(owner, result);
		return -EALREADY;
	}

	owner->state = MT6797_A72_EFFECT_P27_INFLIGHT;
	owner->handle = *handle;
	owner->result = (struct mt6797_a72_platform_effect_result) {
		.abi = MT6797_A72_PLATFORM_EFFECT_ABI,
		.operation = MT6797_A72_PLATFORM_EFFECT_P27_ACQUIRE,
	};
	ret = ops->spm_read(context, MT6797_A72_EFFECT_SPM_P27, &value);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_REJECTED, ret, result);
	owner->result.spm_p27_before = value;
	if (value != MT6797_A72_EFFECT_P27_BEFORE)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_REJECTED, -ERANGE, result);

	owner->result.p27_owned = true;
	owner->result.attempted_effects |=
		MT6797_A72_EFFECT_P27_RESET_RELEASED;
	ret = ops->spm_update_bits(context, MT6797_A72_EFFECT_SPM_P27,
				   BIT(0), BIT(0));
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	ret = mt6797_a72_platform_effect_read_exact_spm(
		owner, ops, context, MT6797_A72_EFFECT_SPM_P27,
		MT6797_A72_EFFECT_P27_HELD, &owner->result.spm_p27_after,
		result);
	if (ret)
		return ret;
	owner->result.completed_effects |=
		MT6797_A72_EFFECT_P27_RESET_RELEASED;

	owner->result.attempted_effects |= MT6797_A72_EFFECT_BPLL_ORDER_READ;
	ret = ops->mcucfg_read(context, MT6797_A72_EFFECT_MCUCFG_BPLL,
				&owner->result.bpll_ordering_value);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	owner->result.completed_effects |= MT6797_A72_EFFECT_BPLL_ORDER_READ;

	owner->result.attempted_effects |= MT6797_A72_EFFECT_PWRAP_ASSERTED;
	ret = ops->pwrap_assert(context);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	status = ops->pwrap_status(context);
	if (status < 0)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, status, result);
	if (status != 1)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EIO, result);
	owner->result.completed_effects |= MT6797_A72_EFFECT_PWRAP_ASSERTED;
	owner->state = MT6797_A72_EFFECT_P27_HELD;
	mt6797_a72_platform_effect_output(owner, result);
	return 0;
}

int mt6797_a72_platform_effect_owner_p27_release(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	struct mt6797_a72_platform_effect_result *result)
{
	u32 value;
	int status;
	int ret;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_a72_platform_effect_result){};
	if (!owner || !mt6797_a72_platform_effect_ops_valid(ops) ||
	    !mt6797_a72_platform_effect_handle_valid(handle))
		return -EINVAL;
	if (!mt6797_a72_platform_effect_handle_matches(&owner->handle, handle)) {
		mt6797_a72_platform_effect_output(owner, result);
		return -EPERM;
	}
	if (owner->state != MT6797_A72_EFFECT_P27_HELD) {
		mt6797_a72_platform_effect_output(owner, result);
		return -EALREADY;
	}

	owner->state = MT6797_A72_EFFECT_RELEASE_INFLIGHT;
	owner->result.operation = MT6797_A72_PLATFORM_EFFECT_P27_RELEASE;
	ret = mt6797_a72_platform_effect_read_exact_spm(
		owner, ops, context, MT6797_A72_EFFECT_SPM_P27,
		MT6797_A72_EFFECT_P27_HELD, &value, result);
	if (ret)
		return ret;
	status = ops->pwrap_status(context);
	if (status < 0)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, status, result);
	if (status != 1)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EIO, result);

	owner->result.attempted_effects |= MT6797_A72_EFFECT_PWRAP_DEASSERTED;
	ret = ops->pwrap_deassert(context);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	status = ops->pwrap_status(context);
	if (status < 0)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, status, result);
	if (status != 0)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EIO, result);
	owner->result.completed_effects |= MT6797_A72_EFFECT_PWRAP_DEASSERTED;

	owner->result.attempted_effects |=
		MT6797_A72_EFFECT_P27_RESET_RESTORED;
	ret = ops->spm_update_bits(context, MT6797_A72_EFFECT_SPM_P27,
				   BIT(0), 0);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	ret = mt6797_a72_platform_effect_read_exact_spm(
		owner, ops, context, MT6797_A72_EFFECT_SPM_P27,
		MT6797_A72_EFFECT_P27_BEFORE, &value, result);
	if (ret)
		return ret;
	owner->result.completed_effects |=
		MT6797_A72_EFFECT_P27_RESET_RESTORED;
	owner->result.p27_owned = false;
	owner->result.error = 0;
	owner->result.sealed = true;
	owner->state = MT6797_A72_EFFECT_RELEASED;
	mt6797_a72_platform_effect_output(owner, result);
	return 0;
}

int mt6797_a72_platform_effect_owner_isolation_clear(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	const struct mt6797_a72_provider_handle *provider,
	struct mt6797_a72_platform_effect_result *result)
{
	u32 value;
	int status;
	int ret;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_a72_platform_effect_result){};
	if (!owner || !mt6797_a72_platform_effect_ops_valid(ops) ||
	    !mt6797_a72_platform_effect_handle_valid(handle))
		return -EINVAL;
	if (!mt6797_a72_platform_effect_handle_matches(&owner->handle, handle) ||
	    !mt6797_a72_platform_effect_provider_matches(handle, provider)) {
		mt6797_a72_platform_effect_output(owner, result);
		return -EPERM;
	}
	if (owner->state != MT6797_A72_EFFECT_P27_HELD) {
		mt6797_a72_platform_effect_output(owner, result);
		return -EALREADY;
	}

	owner->state = MT6797_A72_EFFECT_ISOLATION_INFLIGHT;
	owner->result.operation = MT6797_A72_PLATFORM_EFFECT_ISOLATION_CLEAR;
	owner->result.isolation_attempted = true;
	ret = mt6797_a72_platform_effect_read_exact_spm(
		owner, ops, context, MT6797_A72_EFFECT_SPM_P27,
		MT6797_A72_EFFECT_P27_HELD, &value, result);
	if (ret)
		return ret;
	ret = mt6797_a72_platform_effect_read_exact_spm(
		owner, ops, context, MT6797_A72_EFFECT_SPM_ISOLATION,
		MT6797_A72_EFFECT_ISOLATION_BEFORE,
		&owner->result.isolation_before, result);
	if (ret)
		return ret;
	status = ops->pwrap_status(context);
	if (status < 0)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, status, result);
	if (status != 1)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EIO, result);

	owner->result.attempted_effects |= MT6797_A72_EFFECT_ISOLATION_CLEARED;
	ret = ops->spm_update_bits(context, MT6797_A72_EFFECT_SPM_ISOLATION,
				   MT6797_A72_EFFECT_ISOLATION_MASK, 0);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	ret = mt6797_a72_platform_effect_read_exact_spm(
		owner, ops, context, MT6797_A72_EFFECT_SPM_ISOLATION,
		MT6797_A72_EFFECT_ISOLATION_AFTER,
		&owner->result.isolation_after, result);
	if (ret)
		return ret;
	owner->result.completed_effects |= MT6797_A72_EFFECT_ISOLATION_CLEARED;
	owner->result.isolation_crossed = true;

	owner->result.attempted_effects |= MT6797_A72_EFFECT_PWRAP_DEASSERTED;
	ret = ops->pwrap_deassert(context);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	status = ops->pwrap_status(context);
	if (status < 0)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, status, result);
	if (status != 0)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EIO, result);
	owner->result.completed_effects |= MT6797_A72_EFFECT_PWRAP_DEASSERTED;

	owner->result.attempted_effects |= MT6797_A72_EFFECT_ISOLATION_GUARD;
	ops->delay(context, MT6797_A72_EFFECT_GUARD_MIN_US,
		   MT6797_A72_EFFECT_GUARD_MAX_US);
	owner->result.completed_effects |= MT6797_A72_EFFECT_ISOLATION_GUARD;
	owner->state = MT6797_A72_EFFECT_ISOLATED;
	mt6797_a72_platform_effect_output(owner, result);
	return 0;
}

int mt6797_a72_platform_effect_owner_dcm_update(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_platform_effect_result *result)
{
	u32 expected;
	u32 value;
	int ret;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_a72_platform_effect_result){};
	if (!owner || !mt6797_a72_platform_effect_ops_valid(ops) ||
	    !mt6797_a72_platform_effect_handle_valid(handle))
		return -EINVAL;
	if (!mt6797_a72_platform_effect_handle_matches(&owner->handle, handle)) {
		mt6797_a72_platform_effect_output(owner, result);
		return -EPERM;
	}
	if (owner->state != MT6797_A72_EFFECT_ISOLATED) {
		mt6797_a72_platform_effect_output(owner, result);
		return -EALREADY;
	}

	owner->state = MT6797_A72_EFFECT_DCM_INFLIGHT;
	owner->result.operation = MT6797_A72_PLATFORM_EFFECT_DCM_UPDATE;
	if (!cpu8_online || cpu9_online)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EPERM, result);
	ret = ops->mcucfg_read(context, MT6797_A72_EFFECT_MCUCFG_DCM,
				&owner->result.dcm_before);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	if (owner->result.dcm_before & MT6797_A72_EFFECT_DCM_MASK)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -ERANGE, result);

	expected = owner->result.dcm_before & ~MT6797_A72_EFFECT_DCM_MASK;
	expected |= MT6797_A72_EFFECT_DCM_TOGGLE_VALUE;
	owner->result.attempted_effects |= MT6797_A72_EFFECT_DCM_TOGGLE;
	ops->mcucfg_write(context, MT6797_A72_EFFECT_MCUCFG_DCM, expected);
	ret = ops->mcucfg_read(context, MT6797_A72_EFFECT_MCUCFG_DCM, &value);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	owner->result.dcm_toggle = value;
	if (value != expected)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EIO, result);
	owner->result.completed_effects |= MT6797_A72_EFFECT_DCM_TOGGLE;

	expected &= ~BIT(1);
	owner->result.attempted_effects |= MT6797_A72_EFFECT_DCM_FINAL;
	ops->mcucfg_write(context, MT6797_A72_EFFECT_MCUCFG_DCM, expected);
	ret = ops->mcucfg_read(context, MT6797_A72_EFFECT_MCUCFG_DCM, &value);
	if (ret)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, ret, result);
	owner->result.dcm_final = value;
	if (value != expected)
		return mt6797_a72_platform_effect_fail(
			owner, MT6797_A72_EFFECT_FAULTED, -EIO, result);
	owner->result.completed_effects |= MT6797_A72_EFFECT_DCM_FINAL;
	owner->result.error = 0;
	owner->result.sealed = true;
	owner->state = MT6797_A72_EFFECT_COMPLETE;
	mt6797_a72_platform_effect_output(owner, result);
	return 0;
}

static int mt6797_platform_effect_spm_read(void *context, u32 offset,
					    u32 *value)
{
	struct mt6797_a72_platform_state_source *source = context;

	return regmap_read(source->spm, offset, value);
}

static int mt6797_platform_effect_spm_update_bits(void *context, u32 offset,
						   u32 mask, u32 value)
{
	struct mt6797_a72_platform_state_source *source = context;

	return regmap_update_bits(source->spm, offset, mask, value);
}

static int mt6797_platform_effect_mcucfg_read(void *context, u32 offset,
						 u32 *value)
{
	struct mt6797_a72_platform_state_source *source = context;

	*value = readl(source->mcucfg + offset);
	return 0;
}

static void mt6797_platform_effect_mcucfg_write(void *context, u32 offset,
						   u32 value)
{
	struct mt6797_a72_platform_state_source *source = context;

	writel(value, source->mcucfg + offset);
}

static int mt6797_platform_effect_pwrap_assert(void *context)
{
	struct mt6797_a72_platform_state_source *source = context;

	return reset_control_assert(source->pwrap_reset);
}

static int mt6797_platform_effect_pwrap_deassert(void *context)
{
	struct mt6797_a72_platform_state_source *source = context;

	return reset_control_deassert(source->pwrap_reset);
}

static int mt6797_platform_effect_pwrap_status(void *context)
{
	struct mt6797_a72_platform_state_source *source = context;

	return reset_control_status(source->pwrap_reset);
}

static void mt6797_platform_effect_delay(void *context, unsigned int min_us,
					 unsigned int max_us)
{
	(void)context;
	usleep_range(min_us, max_us);
}

static const struct mt6797_a72_platform_effect_ops
mt6797_platform_effect_ops = {
	.spm_read = mt6797_platform_effect_spm_read,
	.spm_update_bits = mt6797_platform_effect_spm_update_bits,
	.mcucfg_read = mt6797_platform_effect_mcucfg_read,
	.mcucfg_write = mt6797_platform_effect_mcucfg_write,
	.pwrap_assert = mt6797_platform_effect_pwrap_assert,
	.pwrap_deassert = mt6797_platform_effect_pwrap_deassert,
	.pwrap_status = mt6797_platform_effect_pwrap_status,
	.delay = mt6797_platform_effect_delay,
};

static struct mt6797_a72_platform_state_source *
mt6797_platform_effect_source(struct device *dev,
			       struct mt6797_a72_platform_effect_result *result)
{
	if (result)
		*result = (struct mt6797_a72_platform_effect_result){};
	if (!dev || !result)
		return NULL;
	return dev_get_drvdata(dev);
}

int mt6797_a72_platform_effect_p27_acquire(
	struct device *dev,
	const struct mt6797_a72_platform_effect_handle *handle,
	struct mt6797_a72_platform_effect_result *result)
{
	struct mt6797_a72_platform_state_source *source;
	int ret;

	source = mt6797_platform_effect_source(dev, result);
	if (!source)
		return dev && result ? -ENODEV : -EINVAL;
	mutex_lock(&source->lock);
	ret = mt6797_a72_platform_effect_owner_p27_acquire(
		&source->effect_owner, &mt6797_platform_effect_ops, source,
		handle, result);
	mutex_unlock(&source->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_p27_acquire);

int mt6797_a72_platform_effect_p27_release(
	struct device *dev,
	const struct mt6797_a72_platform_effect_handle *handle,
	struct mt6797_a72_platform_effect_result *result)
{
	struct mt6797_a72_platform_state_source *source;
	int ret;

	source = mt6797_platform_effect_source(dev, result);
	if (!source)
		return dev && result ? -ENODEV : -EINVAL;
	mutex_lock(&source->lock);
	ret = mt6797_a72_platform_effect_owner_p27_release(
		&source->effect_owner, &mt6797_platform_effect_ops, source,
		handle, result);
	mutex_unlock(&source->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_p27_release);

int mt6797_a72_platform_effect_isolation_clear(
	struct device *dev,
	const struct mt6797_a72_platform_effect_handle *handle,
	const struct mt6797_a72_provider_handle *provider,
	struct mt6797_a72_platform_effect_result *result)
{
	struct mt6797_a72_platform_state_source *source;
	int ret;

	source = mt6797_platform_effect_source(dev, result);
	if (!source)
		return dev && result ? -ENODEV : -EINVAL;
	mutex_lock(&source->lock);
	ret = mt6797_a72_platform_effect_owner_isolation_clear(
		&source->effect_owner, &mt6797_platform_effect_ops, source,
		handle, provider, result);
	mutex_unlock(&source->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_isolation_clear);

int mt6797_a72_platform_effect_dcm_update(
	struct device *dev,
	const struct mt6797_a72_platform_effect_handle *handle,
	bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_platform_effect_result *result)
{
	struct mt6797_a72_platform_state_source *source;
	int ret;

	source = mt6797_platform_effect_source(dev, result);
	if (!source)
		return dev && result ? -ENODEV : -EINVAL;
	mutex_lock(&source->lock);
	ret = mt6797_a72_platform_effect_owner_dcm_update(
		&source->effect_owner, &mt6797_platform_effect_ops, source,
		handle, cpu8_online, cpu9_online, result);
	mutex_unlock(&source->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_a72_platform_effect_dcm_update);
