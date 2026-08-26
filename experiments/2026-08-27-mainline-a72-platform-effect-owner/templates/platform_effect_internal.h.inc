#define MT6797_A72_EFFECT_SPM_P27		0x218U
#define MT6797_A72_EFFECT_SPM_ISOLATION		0x290U
#define MT6797_A72_EFFECT_MCUCFG_DCM		0x274U
#define MT6797_A72_EFFECT_MCUCFG_BPLL		0x4a0U

#define MT6797_A72_EFFECT_P27_BEFORE		0x00010132U
#define MT6797_A72_EFFECT_P27_HELD		0x00010133U
#define MT6797_A72_EFFECT_ISOLATION_BEFORE	0x00000002U
#define MT6797_A72_EFFECT_ISOLATION_AFTER	0x00000000U
#define MT6797_A72_EFFECT_ISOLATION_MASK		GENMASK(1, 0)
#define MT6797_A72_EFFECT_DCM_MASK		GENMASK(6, 0)
#define MT6797_A72_EFFECT_DCM_TOGGLE_VALUE	0x0fU
#define MT6797_A72_EFFECT_DCM_FINAL_VALUE	0x0dU
#define MT6797_A72_EFFECT_GUARD_MIN_US		240U
#define MT6797_A72_EFFECT_GUARD_MAX_US		260U

enum mt6797_a72_platform_effect_state {
	MT6797_A72_EFFECT_UNUSED,
	MT6797_A72_EFFECT_P27_INFLIGHT,
	MT6797_A72_EFFECT_P27_HELD,
	MT6797_A72_EFFECT_RELEASE_INFLIGHT,
	MT6797_A72_EFFECT_RELEASED,
	MT6797_A72_EFFECT_ISOLATION_INFLIGHT,
	MT6797_A72_EFFECT_ISOLATED,
	MT6797_A72_EFFECT_DCM_INFLIGHT,
	MT6797_A72_EFFECT_COMPLETE,
	MT6797_A72_EFFECT_REJECTED,
	MT6797_A72_EFFECT_FAULTED,
};

struct mt6797_a72_platform_effect_ops {
	int (*spm_read)(void *context, u32 offset, u32 *value);
	int (*spm_update_bits)(void *context, u32 offset, u32 mask, u32 value);
	int (*mcucfg_read)(void *context, u32 offset, u32 *value);
	void (*mcucfg_write)(void *context, u32 offset, u32 value);
	int (*pwrap_assert)(void *context);
	int (*pwrap_deassert)(void *context);
	int (*pwrap_status)(void *context);
	void (*delay)(void *context, unsigned int min_us,
		      unsigned int max_us);
};

struct mt6797_a72_platform_effect_owner {
	enum mt6797_a72_platform_effect_state state;
	struct mt6797_a72_platform_effect_handle handle;
	struct mt6797_a72_platform_effect_result result;
};

int mt6797_a72_platform_effect_owner_p27_acquire(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	struct mt6797_a72_platform_effect_result *result);
int mt6797_a72_platform_effect_owner_p27_release(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	struct mt6797_a72_platform_effect_result *result);
int mt6797_a72_platform_effect_owner_isolation_clear(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	const struct mt6797_a72_provider_handle *provider,
	struct mt6797_a72_platform_effect_result *result);
int mt6797_a72_platform_effect_owner_dcm_update(
	struct mt6797_a72_platform_effect_owner *owner,
	const struct mt6797_a72_platform_effect_ops *ops, void *context,
	const struct mt6797_a72_platform_effect_handle *handle,
	bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_platform_effect_result *result);
