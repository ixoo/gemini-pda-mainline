struct mt6797_a72_provider_handle;

#define MT6797_A72_PLATFORM_EFFECT_ABI 1U

enum mt6797_a72_platform_effect_operation {
	MT6797_A72_PLATFORM_EFFECT_NONE,
	MT6797_A72_PLATFORM_EFFECT_P27_ACQUIRE,
	MT6797_A72_PLATFORM_EFFECT_P27_RELEASE,
	MT6797_A72_PLATFORM_EFFECT_ISOLATION_CLEAR,
	MT6797_A72_PLATFORM_EFFECT_DCM_UPDATE,
};

enum mt6797_a72_platform_effect_bit {
	MT6797_A72_EFFECT_P27_RESET_RELEASED = BIT(0),
	MT6797_A72_EFFECT_BPLL_ORDER_READ = BIT(1),
	MT6797_A72_EFFECT_PWRAP_ASSERTED = BIT(2),
	MT6797_A72_EFFECT_PWRAP_DEASSERTED = BIT(3),
	MT6797_A72_EFFECT_P27_RESET_RESTORED = BIT(4),
	MT6797_A72_EFFECT_ISOLATION_CLEARED = BIT(5),
	MT6797_A72_EFFECT_ISOLATION_GUARD = BIT(6),
	MT6797_A72_EFFECT_DCM_TOGGLE = BIT(7),
	MT6797_A72_EFFECT_DCM_FINAL = BIT(8),
};

struct mt6797_a72_platform_effect_handle {
	u64 attempt_id;
	u64 cookie;
};

struct mt6797_a72_platform_effect_result {
	u32 abi;
	u32 operation;
	u32 attempted_effects;
	u32 completed_effects;
	u32 spm_p27_before;
	u32 spm_p27_after;
	u32 isolation_before;
	u32 isolation_after;
	u32 bpll_ordering_value;
	u32 dcm_before;
	u32 dcm_toggle;
	u32 dcm_final;
	s32 error;
	bool p27_owned;
	bool isolation_attempted;
	bool isolation_crossed;
	bool sealed;
};

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS)
int
mt6797_a72_platform_effect_p27_acquire(struct device *dev,
				       const struct mt6797_a72_platform_effect_handle *handle,
				       struct mt6797_a72_platform_effect_result *result);
int
mt6797_a72_platform_effect_p27_release(struct device *dev,
				       const struct mt6797_a72_platform_effect_handle *handle,
				       struct mt6797_a72_platform_effect_result *result);
int
mt6797_a72_platform_effect_isolation_clear(struct device *dev,
					   const struct mt6797_a72_platform_effect_handle *handle,
					   const struct mt6797_a72_provider_handle *provider,
					   struct mt6797_a72_platform_effect_result *result);
int
mt6797_a72_platform_effect_dcm_update(struct device *dev,
				      const struct mt6797_a72_platform_effect_handle *handle,
				      bool cpu8_online, bool cpu9_online,
				      struct mt6797_a72_platform_effect_result *result);
#else
static inline int
mt6797_a72_platform_effect_p27_acquire(struct device *dev,
				       const struct mt6797_a72_platform_effect_handle *handle,
				       struct mt6797_a72_platform_effect_result *result)
{
	(void)dev;
	(void)handle;
	if (result)
		*result = (struct mt6797_a72_platform_effect_result){};
	return -EOPNOTSUPP;
}

static inline int
mt6797_a72_platform_effect_p27_release(struct device *dev,
				       const struct mt6797_a72_platform_effect_handle *handle,
				       struct mt6797_a72_platform_effect_result *result)
{
	(void)dev;
	(void)handle;
	if (result)
		*result = (struct mt6797_a72_platform_effect_result){};
	return -EOPNOTSUPP;
}

static inline int
mt6797_a72_platform_effect_isolation_clear(struct device *dev,
					   const struct mt6797_a72_platform_effect_handle *handle,
					   const struct mt6797_a72_provider_handle *provider,
					   struct mt6797_a72_platform_effect_result *result)
{
	(void)dev;
	(void)handle;
	(void)provider;
	if (result)
		*result = (struct mt6797_a72_platform_effect_result){};
	return -EOPNOTSUPP;
}

static inline int
mt6797_a72_platform_effect_dcm_update(struct device *dev,
				      const struct mt6797_a72_platform_effect_handle *handle,
				      bool cpu8_online, bool cpu9_online,
				      struct mt6797_a72_platform_effect_result *result)
{
	(void)dev;
	(void)handle;
	(void)cpu8_online;
	(void)cpu9_online;
	if (result)
		*result = (struct mt6797_a72_platform_effect_result){};
	return -EOPNOTSUPP;
}
#endif
