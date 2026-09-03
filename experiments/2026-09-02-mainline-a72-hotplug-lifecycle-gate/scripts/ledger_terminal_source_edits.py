#!/usr/bin/env python3
"""Repair record-4 terminal shapes needed by the production binder."""

from __future__ import annotations

import argparse
from pathlib import Path


SOURCE_OLD = """\
\tif (record->stage >= GEMINI_A72_HOTPLUG_DOWN_PREPARED &&
\t    (!record->down_generation || !record->down_cookie))
\t\treturn false;
"""
SOURCE_NEW = """\
\tif (record->stage >= GEMINI_A72_HOTPLUG_DOWN_PREPARED &&
\t    (!record->down_generation || !record->down_cookie) &&
\t    !(record->stage == GEMINI_A72_HOTPLUG_DOWN_PREPARED &&
\t      record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT))
\t\treturn false;
"""
RESTORE_OLD = """\
\tif (record->stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&
\t    (!record->restore_generation || !record->restore_cookie))
\t\treturn false;
"""
RESTORE_NEW = """\
\tif (record->stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&
\t    (!record->restore_generation || !record->restore_cookie) &&
\t    !(record->stage == GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&
\t      record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT))
\t\treturn false;
"""
SEQUENCE_OLD = """\
\tif (record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT)
\t\treturn record->stage <= GEMINI_A72_HOTPLUG_TARGET_DISABLE_VALID;
"""
SEQUENCE_NEW = """\
\tif (record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT)
\t\treturn record->stage <= GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED;
"""

TESTS = r'''
static void hotplug_down_prepare_terminal_test(struct kunit *test)
{
	struct gemini_a72_hotplug_ledger_record latest;
	struct gemini_a72_hotplug_ledger_record record;
	struct gemini_a72_hotplug_ledger_owner owner = {};
	struct hotplug_test_state state;
	u32 copy = 0;

	hotplug_test_raw(&state);
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL), 0);
	hotplug_test_fill(&record, GEMINI_A72_HOTPLUG_BINDING_PARENT, 0, 0);
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL, &record), 0);
	hotplug_test_fill(&record, GEMINI_A72_HOTPLUG_DOWN_PREPARED,
			  GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT, -EPERM);
	record.down_generation = 0;
	record.down_cookie = 0;
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL, &record), 0);
	KUNIT_EXPECT_TRUE(test, owner.sealed);
	KUNIT_ASSERT_TRUE(test, gemini_a72_hotplug_ledger_read_latest(
		&hotplug_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.stage,
			(u32)GEMINI_A72_HOTPLUG_DOWN_PREPARED);
	KUNIT_EXPECT_EQ(test, latest.terminal,
			(u32)GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT);
	KUNIT_EXPECT_EQ(test, latest.down_generation, 0U);
	KUNIT_EXPECT_EQ(test, latest.down_cookie, 0ULL);
}

static void hotplug_off_commit_terminal_test(struct kunit *test)
{
	struct gemini_a72_hotplug_ledger_record latest;
	struct gemini_a72_hotplug_ledger_record record;
	struct gemini_a72_hotplug_ledger_owner owner = {};
	struct hotplug_test_state state;
	u32 copy = 0;
	u32 stage;

	hotplug_test_raw(&state);
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL), 0);
	for (stage = GEMINI_A72_HOTPLUG_BINDING_PARENT;
	     stage < GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED; stage++) {
		hotplug_test_fill(&record, stage, 0, 0);
		KUNIT_ASSERT_EQ(test,
				gemini_a72_hotplug_ledger_owner_checkpoint(
					&owner, &hotplug_test_ops, &state,
					0x1234567887654321ULL, &record), 0);
	}
	hotplug_test_fill(&record, GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED,
			  GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT, -EIO);
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL, &record), 0);
	KUNIT_EXPECT_TRUE(test, owner.sealed);
	KUNIT_ASSERT_TRUE(test, gemini_a72_hotplug_ledger_read_latest(
		&hotplug_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.stage,
			(u32)GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED);
	KUNIT_EXPECT_EQ(test, latest.terminal,
			(u32)GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT);
	KUNIT_EXPECT_EQ(test, latest.cpu_off_calls, 0U);
}

static void hotplug_restore_prepare_terminal_test(struct kunit *test)
{
	static const u32 stages[] = { 1, 2, 3, 4, 5, 6, 7,
				      9, 10, 11, 12, 13 };
	struct gemini_a72_hotplug_ledger_record latest;
	struct gemini_a72_hotplug_ledger_record record;
	struct gemini_a72_hotplug_ledger_owner owner = {};
	struct hotplug_test_state state;
	u32 copy = 0;
	unsigned int index;

	hotplug_test_raw(&state);
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL), 0);
	for (index = 0; index < ARRAY_SIZE(stages); index++) {
		hotplug_test_fill(&record, stages[index], 0, 0);
		KUNIT_ASSERT_EQ(test,
				gemini_a72_hotplug_ledger_owner_checkpoint(
					&owner, &hotplug_test_ops, &state,
					0x1234567887654321ULL, &record), 0);
	}
	hotplug_test_fill(&record, GEMINI_A72_HOTPLUG_RESTORE_PREPARED,
			  GEMINI_A72_HOTPLUG_RESTORE_FAULT, -EIO);
	record.restore_generation = 0;
	record.restore_cookie = 0;
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL, &record), 0);
	KUNIT_EXPECT_TRUE(test, owner.sealed);
	KUNIT_ASSERT_TRUE(test, gemini_a72_hotplug_ledger_read_latest(
		&hotplug_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.stage,
			(u32)GEMINI_A72_HOTPLUG_RESTORE_PREPARED);
	KUNIT_EXPECT_EQ(test, latest.terminal,
			(u32)GEMINI_A72_HOTPLUG_RESTORE_FAULT);
	KUNIT_EXPECT_EQ(test, latest.restore_generation, 0U);
	KUNIT_EXPECT_EQ(test, latest.restore_cookie, 0ULL);
}

'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"edit anchor changed: {path}: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    source = root / "fs/pstore/gemini_a72_hotplug_ledger.c"
    test = root / "fs/pstore/gemini_a72_hotplug_ledger_test.c"

    replace_once(source, SOURCE_OLD, SOURCE_NEW)
    replace_once(source, RESTORE_OLD, RESTORE_NEW)
    replace_once(source, SEQUENCE_OLD, SEQUENCE_NEW)
    replace_once(
        test,
        "static struct kunit_case hotplug_ledger_cases[] = {\n",
        TESTS + "static struct kunit_case hotplug_ledger_cases[] = {\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(hotplug_precommit_terminal_test),\n",
        "\tKUNIT_CASE(hotplug_precommit_terminal_test),\n"
        "\tKUNIT_CASE(hotplug_down_prepare_terminal_test),\n"
        "\tKUNIT_CASE(hotplug_off_commit_terminal_test),\n"
        "\tKUNIT_CASE(hotplug_restore_prepare_terminal_test),\n",
    )


if __name__ == "__main__":
    main()
