struct mt6797_observer_fixture {
	struct kunit *test;
	struct mt6797_thermal_observer owner;
	u32 clocks;
	u32 scans;
	int error;
};

static u64 mt6797_observer_fake_time(void *context)
{
	struct mt6797_observer_fixture *f = context;

	KUNIT_EXPECT_TRUE(f->test, mutex_is_locked(&f->owner.lock));
	return ++f->clocks;
}

static int mt6797_observer_fake_scan(void *context,
				     struct mt6797_thermal_snapshot *snapshot,
				     int *aggregate)
{
	static const u32 banks[] = { 0, 1, 2, 2, 3, 4, 5 };
	static const u32 sensors[] = { 0, 3, 1, 2, 1, 1, 1 };
	struct mt6797_observer_fixture *f = context;
	u32 i;

	KUNIT_EXPECT_TRUE(f->test, mutex_is_locked(&f->owner.lock));
	f->scans++;
	KUNIT_EXPECT_EQ(f->test, f->owner.budget.attempts, f->scans);
	if (f->error)
		return f->error;
	for (i = 0; i < ARRAY_SIZE(banks); i++)
		mt6797_thermal_snapshot_append(snapshot, banks[i], sensors[i],
					       35000 + i * 100, true);
	*aggregate = 35600;
	return 0;
}

static const struct mt6797_thermal_observer_ops mt6797_test_observer_ops = {
	.time_ns = mt6797_observer_fake_time,
	.scan = mt6797_observer_fake_scan,
};

static void mt6797_observer_budget_test(struct kunit *test)
{
	struct mt6797_observer_fixture f = { .test = test };
	struct mt6797_thermal_snapshot snapshot = {};
	int ret;
	u32 i;

	mt6797_thermal_observer_init(&f.owner);
	for (i = 1; i <= 3; i++) {
		ret = mt6797_thermal_observer_capture(&f.owner,
						      &mt6797_test_observer_ops, &f, &snapshot);
		KUNIT_ASSERT_EQ(test, ret, 0);
		KUNIT_EXPECT_EQ(test, snapshot.attempt, i);
		KUNIT_EXPECT_TRUE(test, snapshot.complete);
		KUNIT_EXPECT_FALSE(test, snapshot.active);
		KUNIT_EXPECT_EQ(test, snapshot.count, 7U);
		KUNIT_EXPECT_EQ(test, snapshot.end_ns - snapshot.start_ns, 1ULL);
		KUNIT_EXPECT_EQ(test, f.clocks, i * 2);
		KUNIT_EXPECT_EQ(test, f.scans, i);
	}
	ret = mt6797_thermal_observer_capture(&f.owner,
					      &mt6797_test_observer_ops, &f, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -ENOSPC);
	KUNIT_EXPECT_EQ(test, snapshot.error, -ENOSPC);
	KUNIT_EXPECT_EQ(test, snapshot.count, 0U);
	KUNIT_EXPECT_FALSE(test, snapshot.complete);
	KUNIT_EXPECT_EQ(test, f.clocks, 6U);
	KUNIT_EXPECT_EQ(test, f.scans, 3U);
	KUNIT_EXPECT_FALSE(test, mutex_is_locked(&f.owner.lock));
}

static void mt6797_observer_failure_test(struct kunit *test)
{
	struct mt6797_observer_fixture f = { .test = test, .error = -EIO };
	struct mt6797_thermal_snapshot snapshot = {};
	int ret;

	mt6797_thermal_observer_init(&f.owner);
	ret = mt6797_thermal_observer_capture(&f.owner,
					      &mt6797_test_observer_ops, &f, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, snapshot.error, -EIO);
	KUNIT_EXPECT_EQ(test, snapshot.attempt, 1U);
	KUNIT_EXPECT_FALSE(test, snapshot.active);
	KUNIT_EXPECT_FALSE(test, snapshot.complete);
	KUNIT_EXPECT_EQ(test, f.clocks, 2U);
	KUNIT_EXPECT_EQ(test, f.scans, 1U);
	KUNIT_EXPECT_FALSE(test, mutex_is_locked(&f.owner.lock));
	f.error = 0;
	ret = mt6797_thermal_observer_capture(&f.owner,
					      &mt6797_test_observer_ops, &f, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, snapshot.attempt, 2U);
	KUNIT_EXPECT_TRUE(test, snapshot.complete);
}

static void mt6797_observer_invalid_test(struct kunit *test)
{
	struct mt6797_observer_fixture f = { .test = test };
	struct mt6797_thermal_snapshot snapshot = {};
	int ret;
	struct mt6797_thermal_observer_ops ops = mt6797_test_observer_ops;

	mt6797_thermal_observer_init(&f.owner);
	ops.scan = NULL;
	ret = mt6797_thermal_observer_capture(&f.owner,
					      &ops, &f, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	KUNIT_EXPECT_EQ(test, f.owner.budget.attempts, 0U);
	KUNIT_EXPECT_EQ(test, f.clocks, 0U);
	KUNIT_EXPECT_EQ(test, f.scans, 0U);
	snapshot.active = true;
	ret = mt6797_thermal_observer_capture(&f.owner,
					      &mt6797_test_observer_ops, &f, &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EBUSY);
	KUNIT_EXPECT_EQ(test, f.owner.budget.attempts, 0U);
	KUNIT_EXPECT_EQ(test, f.clocks, 0U);
	KUNIT_EXPECT_EQ(test, f.scans, 0U);
	KUNIT_EXPECT_FALSE(test, mutex_is_locked(&f.owner.lock));
}
