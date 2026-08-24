#!/usr/bin/env python3
"""Move the large physical-source KUnit snapshots off the kernel stack."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one stack fixture, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = (
        args.source_root.resolve()
        / "drivers/soc/mediatek/mt6797-a72-physical-source-observer-test.c"
    )

    replace_once(
        path,
        """static void mt6797_source_lifecycle_test(struct kunit *test)
{
	struct mt6797_a72_physical_source_context context;
	struct mt6797_a72_physical_source_test_state state = {
		.fail_stage = -1,
	};
	struct mt6797_a72_direct_state_snapshot snapshot;
	int ret;

	mt6797_source_context_init(&context, &state);
	ret = mt6797_a72_physical_source_run(&context, &test_runtime,
					     &snapshot);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state.events[0], MT6797_SOURCE_REGISTER);
	KUNIT_EXPECT_EQ(test, state.events[1], MT6797_SOURCE_DIRECT_SNAPSHOT);
	KUNIT_EXPECT_EQ(test, state.events[state.event_count - 1],
			MT6797_SOURCE_UNREGISTER);
	KUNIT_EXPECT_PTR_EQ(test, state.registered_ops, NULL);
	KUNIT_EXPECT_PTR_EQ(test, state.registered_context, NULL);
	KUNIT_EXPECT_EQ(test, snapshot.abi, MT6797_A72_DIRECT_STATE_ABI);
	KUNIT_EXPECT_EQ(test, snapshot.valid, 1U);
}
""",
        """static void mt6797_source_lifecycle_test(struct kunit *test)
{
	struct mt6797_a72_physical_source_context context;
	struct mt6797_a72_physical_source_test_state state = {
		.fail_stage = -1,
	};
	struct mt6797_a72_direct_state_snapshot *snapshot;
	int ret;

	snapshot = kunit_kzalloc(test, sizeof(*snapshot), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, snapshot);
	mt6797_source_context_init(&context, &state);
	ret = mt6797_a72_physical_source_run(&context, &test_runtime,
					     snapshot);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state.events[0], MT6797_SOURCE_REGISTER);
	KUNIT_EXPECT_EQ(test, state.events[1], MT6797_SOURCE_DIRECT_SNAPSHOT);
	KUNIT_EXPECT_EQ(test, state.events[state.event_count - 1],
			MT6797_SOURCE_UNREGISTER);
	KUNIT_EXPECT_PTR_EQ(test, state.registered_ops, NULL);
	KUNIT_EXPECT_PTR_EQ(test, state.registered_context, NULL);
	KUNIT_EXPECT_EQ(test, snapshot->abi, MT6797_A72_DIRECT_STATE_ABI);
	KUNIT_EXPECT_EQ(test, snapshot->valid, 1U);
}
""",
    )
    replace_once(
        path,
        """static void mt6797_source_lifecycle_failures_test(struct kunit *test)
{
	struct mt6797_a72_physical_source_context context;
	struct mt6797_a72_physical_source_test_state state = {
		.register_ret = -EBUSY,
	};
	struct mt6797_a72_direct_state_snapshot snapshot;
	struct mt6797_a72_direct_state_snapshot zero = { };
	int ret;

	mt6797_source_context_init(&context, &state);
	memset(&snapshot, 0xa5, sizeof(snapshot));
	ret = mt6797_a72_physical_source_run(&context, &test_runtime,
					     &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EBUSY);
	KUNIT_EXPECT_EQ(test, state.event_count, 1U);
	KUNIT_EXPECT_EQ(test, memcmp(&snapshot, &zero, sizeof(snapshot)), 0);

	memset(&state, 0, sizeof(state));
	state.fail_stage = -1;
	state.direct_ret = -EPERM;
	mt6797_source_context_init(&context, &state);
	memset(&snapshot, 0xa5, sizeof(snapshot));
	ret = mt6797_a72_physical_source_run(&context, &test_runtime,
					     &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, state.event_count, 3U);
	KUNIT_EXPECT_EQ(test, state.events[2], MT6797_SOURCE_UNREGISTER);
	KUNIT_EXPECT_EQ(test, memcmp(&snapshot, &zero, sizeof(snapshot)), 0);
}
""",
        """static void mt6797_source_lifecycle_failures_test(struct kunit *test)
{
	struct mt6797_a72_physical_source_context context;
	struct mt6797_a72_physical_source_test_state state = {
		.register_ret = -EBUSY,
	};
	struct mt6797_a72_direct_state_snapshot *snapshot;
	int ret;

	snapshot = kunit_kzalloc(test, sizeof(*snapshot), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, snapshot);
	mt6797_source_context_init(&context, &state);
	memset(snapshot, 0xa5, sizeof(*snapshot));
	ret = mt6797_a72_physical_source_run(&context, &test_runtime,
					     snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EBUSY);
	KUNIT_EXPECT_EQ(test, state.event_count, 1U);
	KUNIT_EXPECT_PTR_EQ(test, memchr_inv(snapshot, 0, sizeof(*snapshot)),
			    NULL);

	memset(&state, 0, sizeof(state));
	state.fail_stage = -1;
	state.direct_ret = -EPERM;
	mt6797_source_context_init(&context, &state);
	memset(snapshot, 0xa5, sizeof(*snapshot));
	ret = mt6797_a72_physical_source_run(&context, &test_runtime,
					     snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	KUNIT_EXPECT_EQ(test, state.event_count, 3U);
	KUNIT_EXPECT_EQ(test, state.events[2], MT6797_SOURCE_UNREGISTER);
	KUNIT_EXPECT_PTR_EQ(test, memchr_inv(snapshot, 0, sizeof(*snapshot)),
			    NULL);
}
""",
    )


if __name__ == "__main__":
    main()
