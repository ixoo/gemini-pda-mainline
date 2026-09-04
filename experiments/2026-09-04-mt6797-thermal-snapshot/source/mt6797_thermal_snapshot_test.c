// SPDX-License-Identifier: GPL-2.0-only
#include <kunit/test.h>
#include <linux/module.h>

#include "mt6797_thermal_snapshot.h"

static void mt6797_snapshot_fill(struct kunit *test,
				struct mt6797_thermal_snapshot *snapshot,
				u32 invalid_mask)
{
	static const u32 banks[] = { 0, 1, 2, 2, 3, 4, 5 };
	static const u32 sensors[] = { 0, 3, 1, 2, 1, 1, 1 };
	static const int temperatures[] = {
		35000, 35100, 36000, 36100, 35200, 35300, 35400,
	};
	u32 i;

	for (i = 0; i < ARRAY_SIZE(banks); i++)
		KUNIT_ASSERT_EQ(test,
			mt6797_thermal_snapshot_append(snapshot, banks[i],
						      sensors[i], temperatures[i],
						      !(invalid_mask & (1U << i))), 0);
}

static void mt6797_snapshot_complete_test(struct kunit *test)
{
	struct mt6797_thermal_snapshot_budget budget = {};
	struct mt6797_thermal_snapshot snapshot = {};

	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 10), 0);
	mt6797_snapshot_fill(test, &snapshot, 0);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 20, 36100), 0);
	KUNIT_EXPECT_TRUE(test, snapshot.complete);
	KUNIT_EXPECT_FALSE(test, snapshot.active);
	KUNIT_EXPECT_EQ(test, snapshot.valid_mask, 0x7fU);
	KUNIT_EXPECT_EQ(test, snapshot.winner, 3U);
	KUNIT_EXPECT_EQ(test, snapshot.samples[3].bank, 2U);
	KUNIT_EXPECT_EQ(test, snapshot.samples[3].sensor, 2U);
	KUNIT_EXPECT_EQ(test, snapshot.end_ns - snapshot.start_ns, 10ULL);
}

static void mt6797_snapshot_budget_test(struct kunit *test)
{
	struct mt6797_thermal_snapshot_budget budget = {};
	struct mt6797_thermal_snapshot snapshot = {};
	u32 i;

	for (i = 1; i <= MT6797_THERMAL_SNAPSHOT_ATTEMPTS; i++) {
		KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 0), 0);
		KUNIT_EXPECT_EQ(test, snapshot.attempt, i);
		KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 1, 0), -EINVAL);
	}
	for (i = 0; i < 2; i++)
		KUNIT_EXPECT_EQ(test,
			mt6797_thermal_snapshot_begin(&budget, &snapshot, 2), -ENOSPC);
	KUNIT_EXPECT_EQ(test, budget.attempts, MT6797_THERMAL_SNAPSHOT_ATTEMPTS);
	KUNIT_EXPECT_FALSE(test, snapshot.active);
}

static void mt6797_snapshot_order_test(struct kunit *test)
{
	struct mt6797_thermal_snapshot_budget budget = {};
	struct mt6797_thermal_snapshot snapshot = {};

	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 1), 0);
	KUNIT_EXPECT_EQ(test,
		mt6797_thermal_snapshot_append(&snapshot, 1, 3, 35000, true), -EINVAL);
	KUNIT_EXPECT_EQ(test,
		mt6797_thermal_snapshot_append(&snapshot, 0, 0, 35000, true), -EINVAL);
	KUNIT_EXPECT_EQ(test, snapshot.count, 0U);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 2, INT_MIN), -EINVAL);
	KUNIT_EXPECT_FALSE(test, snapshot.complete);
}

static void mt6797_snapshot_invalid_test(struct kunit *test)
{
	struct mt6797_thermal_snapshot_budget budget = {};
	struct mt6797_thermal_snapshot snapshot = {};

	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 1), 0);
	mt6797_snapshot_fill(test, &snapshot, 1U << 3);
	KUNIT_EXPECT_EQ(test, snapshot.maximum, 36000);
	KUNIT_EXPECT_EQ(test, snapshot.winner, 2U);
	KUNIT_EXPECT_EQ(test, snapshot.valid_mask, 0x77U);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 2, 36000), -ENODATA);
	KUNIT_EXPECT_FALSE(test, snapshot.complete);
	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 3), 0);
	mt6797_snapshot_fill(test, &snapshot, 0x7f);
	KUNIT_EXPECT_EQ(test, snapshot.winner, MT6797_THERMAL_SNAPSHOT_SAMPLES);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 4, INT_MIN), -ENODATA);
}

static void mt6797_snapshot_aggregate_time_test(struct kunit *test)
{
	struct mt6797_thermal_snapshot_budget budget = {};
	struct mt6797_thermal_snapshot snapshot = {};

	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 10), 0);
	mt6797_snapshot_fill(test, &snapshot, 0);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 20, 36101), -EBADMSG);
	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 10), 0);
	mt6797_snapshot_fill(test, &snapshot, 0);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 9, 36100), -EINVAL);
}

static void mt6797_snapshot_lifecycle_test(struct kunit *test)
{
	struct mt6797_thermal_snapshot_budget budget = {};
	struct mt6797_thermal_snapshot snapshot = {};

	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_begin(NULL, &snapshot, 1), -EINVAL);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_begin(&budget, NULL, 1), -EINVAL);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_append(&snapshot, 0, 0, 0, true), -EINVAL);
	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 1), 0);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 2), -EBUSY);
	KUNIT_EXPECT_EQ(test, budget.attempts, 1U);
	mt6797_snapshot_fill(test, &snapshot, 0);
	KUNIT_EXPECT_EQ(test,
		mt6797_thermal_snapshot_append(&snapshot, 5, 1, 35400, true), -EINVAL);
	KUNIT_EXPECT_EQ(test, snapshot.count, 7U);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 3, 36100), -EINVAL);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 4, 36100), -EINVAL);
}

static void mt6797_snapshot_tie_test(struct kunit *test)
{
	struct mt6797_thermal_snapshot_budget budget = {};
	struct mt6797_thermal_snapshot snapshot = {};

	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_begin(&budget, &snapshot, 1), 0);
	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_append(&snapshot, 0, 0, 35000, true), 0);
	KUNIT_ASSERT_EQ(test, mt6797_thermal_snapshot_append(&snapshot, 1, 3, 35000, true), 0);
	KUNIT_EXPECT_EQ(test, snapshot.winner, 0U);
	KUNIT_EXPECT_EQ(test, snapshot.maximum, 35000);
	KUNIT_EXPECT_EQ(test, mt6797_thermal_snapshot_finish(&snapshot, 2, 35000), -EINVAL);
}

static struct kunit_case mt6797_snapshot_cases[] = {
	KUNIT_CASE(mt6797_snapshot_complete_test),
	KUNIT_CASE(mt6797_snapshot_tie_test),
	KUNIT_CASE(mt6797_snapshot_budget_test),
	KUNIT_CASE(mt6797_snapshot_order_test),
	KUNIT_CASE(mt6797_snapshot_invalid_test),
	KUNIT_CASE(mt6797_snapshot_aggregate_time_test),
	KUNIT_CASE(mt6797_snapshot_lifecycle_test),
	{}
};

static struct kunit_suite mt6797_snapshot_suite = {
	.name = "mt6797-thermal-snapshot",
	.test_cases = mt6797_snapshot_cases,
};
kunit_test_suite(mt6797_snapshot_suite);

MODULE_LICENSE("GPL");
