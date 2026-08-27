#define MT6797_BIGIDVFS_SRAM_OWNER_ABI		1U
#define MT6797_BIGIDVFS_FID_SRAM_LDO_SET	0xc20003bfUL
#define MT6797_BIGIDVFS_SRAM_CALIBRATION	0x102222b4U
#define MT6797_BIGIDVFS_SRAM_TARGET_MV_X100	110000U
#define MT6797_BIGIDVFS_SRAM_SELECTOR_MASK	GENMASK(11, 0)
#define MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED	0x8fbU
#define MT6797_BIGIDVFS_SRAM_CALIBRATION_MASK	GENMASK(15, 0)
#define MT6797_BIGIDVFS_SRAM_SETTLE_MIN_US	240U
#define MT6797_BIGIDVFS_SRAM_SETTLE_MAX_US	260U

enum mt6797_bigidvfs_sram_step {
	MT6797_BIGIDVFS_SRAM_SERVICE = BIT(0),
	MT6797_BIGIDVFS_SRAM_SETTLE = BIT(1),
	MT6797_BIGIDVFS_SRAM_SELECTOR_FIRST = BIT(2),
	MT6797_BIGIDVFS_SRAM_CALIBRATION_FIRST = BIT(3),
	MT6797_BIGIDVFS_SRAM_SELECTOR_SECOND = BIT(4),
	MT6797_BIGIDVFS_SRAM_CALIBRATION_SECOND = BIT(5),
	MT6797_BIGIDVFS_SRAM_SELECTOR_VALID = BIT(6),
	MT6797_BIGIDVFS_SRAM_CALIBRATION_VALID = BIT(7),
};

struct mt6797_bigidvfs_sram_request {
	u32 abi;
	u32 cpu;
	u64 attempt_id;
	u64 cookie;
	bool provider_held;
	bool isolation_crossed;
	bool cpu8_online;
	bool cpu9_online;
};

struct mt6797_bigidvfs_sram_result {
	u32 abi;
	u32 attempted_steps;
	u32 completed_steps;
	u32 requested_mv_x100;
	u32 selector_first;
	u32 calibration_first;
	u32 selector_second;
	u32 calibration_second;
	u64 attempt_id;
	u64 cookie;
	s32 error;
	bool effect_attempted;
	bool verified;
	bool sealed;
};

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER)
int mt6797_bigidvfs_sram_enable(
	struct device *dev, const struct mt6797_bigidvfs_sram_request *request,
	struct mt6797_bigidvfs_sram_result *result);
#else
static inline int mt6797_bigidvfs_sram_enable(
	struct device *dev, const struct mt6797_bigidvfs_sram_request *request,
	struct mt6797_bigidvfs_sram_result *result)
{
	(void)dev;
	(void)request;
	if (result)
		*result = (struct mt6797_bigidvfs_sram_result){};
	return -EOPNOTSUPP;
}
#endif
