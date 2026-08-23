#define MT6797_A72_DIRECT_STATE_ABI 1

struct mt6797_a72_direct_topology {
	u32 cpu8_possible;
	u32 cpu9_possible;
	u32 cpu8_present;
	u32 cpu9_present;
	u32 cpu8_online;
	u32 cpu9_online;
};

struct mt6797_a72_direct_state_snapshot {
	u32 abi;
	u32 valid;
	u32 cpu8_possible;
	u32 cpu9_possible;
	u32 cpu8_present;
	u32 cpu9_present;
	u32 cpu8_online;
	u32 cpu9_online;
	struct mt6797_a72_direct_source_snapshot source;
	struct mt6797_a72_owner_snapshot owner;
};

#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR
int mt6797_a72_direct_source_register(const struct mt6797_a72_direct_source_ops *ops,
				       void *context);
void mt6797_a72_direct_source_unregister(const struct mt6797_a72_direct_source_ops *ops,
					 void *context);
int mt6797_a72_direct_state_snapshot(struct mt6797_a72_direct_state_snapshot *snapshot);
#else
static inline int
mt6797_a72_direct_source_register(const struct mt6797_a72_direct_source_ops *ops,
				  void *context)
{
	(void)ops;
	(void)context;
	return -EOPNOTSUPP;
}

static inline void
mt6797_a72_direct_source_unregister(const struct mt6797_a72_direct_source_ops *ops,
				    void *context)
{
	(void)ops;
	(void)context;
}

static inline int
mt6797_a72_direct_state_snapshot(struct mt6797_a72_direct_state_snapshot *snapshot)
{
	if (snapshot)
		memset(snapshot, 0, sizeof(*snapshot));
	return -EOPNOTSUPP;
}
#endif

#ifdef CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST
int mt6797_a72_direct_state_test_snapshot(const struct mt6797_a72_direct_topology *topology,
					  struct mt6797_a72_direct_state_snapshot *snapshot);
#endif
