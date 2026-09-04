// SPDX-License-Identifier: GPL-2.0-only
/* In-memory tests for the Gemini MT6797 retained thermal-stage ledger. */

#include <kunit/test.h>
#include <linux/bitops.h>
#include <linux/errno.h>
#include <linux/gemini_mt6797_thermal_ledger.h>
#include <linux/string.h>

#include "gemini_mt6797_thermal_ledger_internal.h"

#define THERMAL_TEST_WORDS 64

struct thermal_test_context {
	u32 words[THERMAL_TEST_WORDS];
	u32 writes;
	u32 syncs;
	int corrupt_word;
};

static u32 thermal_test_read(void *data, unsigned int word)
{
	struct thermal_test_context *context = data;
	u32 value = context->words[word];

	if ((int)word == context->corrupt_word)
		value ^= BIT(0);

	return value;
}

static void thermal_test_write(void *data, unsigned int word, u32 value)
{
	struct thermal_test_context *context = data;

	context->words[word] = value;
	context->writes++;
}

static void thermal_test_sync(void *data)
{
	struct thermal_test_context *context = data;

	context->syncs++;
}

static const struct gemini_mt6797_thermal_ledger_ops thermal_test_ops = {
	.read = thermal_test_read,
	.write = thermal_test_write,
	.sync = thermal_test_sync,
};

static void thermal_test_empty(struct thermal_test_context *context,
			       bool raw)
{
	memset(context, 0, sizeof(*context));
	memset(context->words, 0xff, sizeof(context->words));
	context->corrupt_word = -1;
	if (!raw) {
		context->words[0] =
			GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE;
		context->words[1] = 0;
		context->words[2] = 0;
	}
}

static int thermal_test_checkpoint(
	struct gemini_mt6797_thermal_ledger_owner *owner,
	struct thermal_test_context *context, u32 operation, u32 phase,
	u32 index, int result, u32 terminal)
{
	return gemini_mt6797_thermal_ledger_owner_checkpoint(
		owner, &thermal_test_ops, context, operation, phase, index,
		result, terminal);
}

static void thermal_ledger_accepts_pstore_empty(struct kunit *test)
{
	struct gemini_mt6797_thermal_ledger_record record;
	struct gemini_mt6797_thermal_ledger_owner owner = {};
	struct thermal_test_context context;
	u32 copy;
	int ret;

	thermal_test_empty(&context, false);
	ret = gemini_mt6797_thermal_ledger_owner_begin(
		&owner, &thermal_test_ops, &context);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, context.words[0],
			GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE);
	KUNIT_EXPECT_EQ(test, context.words[1],
			GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES);
	KUNIT_EXPECT_EQ(test, context.words[2],
			GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES);
	KUNIT_EXPECT_EQ(test, context.writes, 15U);
	KUNIT_EXPECT_TRUE(test, gemini_mt6797_thermal_ledger_read_latest(
		&thermal_test_ops, &context, &record, &copy));
	KUNIT_EXPECT_EQ(test, record.generation, 1U);
	KUNIT_EXPECT_EQ(test, record.operation,
			GEMINI_MT6797_THERMAL_PROBE);
	KUNIT_EXPECT_EQ(test, record.phase,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE);
	KUNIT_EXPECT_EQ(test, copy, 0U);
}

static void thermal_ledger_accepts_raw_empty(struct kunit *test)
{
	struct gemini_mt6797_thermal_ledger_owner owner = {};
	struct thermal_test_context context;
	int ret;

	thermal_test_empty(&context, true);
	ret = gemini_mt6797_thermal_ledger_owner_begin(
		&owner, &thermal_test_ops, &context);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, context.words[0],
			GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE);
	KUNIT_EXPECT_EQ(test, context.writes, 16U);
}

static void thermal_ledger_alternates_crc_copies(struct kunit *test)
{
	struct gemini_mt6797_thermal_ledger_record record;
	struct gemini_mt6797_thermal_ledger_owner owner = {};
	struct thermal_test_context context;
	u32 copy;
	int ret;

	thermal_test_empty(&context, false);
	KUNIT_ASSERT_EQ(test,
		gemini_mt6797_thermal_ledger_owner_begin(
			&owner, &thermal_test_ops, &context), 0);
	KUNIT_ASSERT_EQ(test, thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0), 0);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, context.writes, 28U);
	KUNIT_EXPECT_TRUE(test, gemini_mt6797_thermal_ledger_read_latest(
		&thermal_test_ops, &context, &record, &copy));
	KUNIT_EXPECT_EQ(test, record.generation, 2U);
	KUNIT_EXPECT_EQ(test, record.phase,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER);
	KUNIT_EXPECT_EQ(test, copy, 1U);
	context.words[GEMINI_MT6797_THERMAL_LEDGER_HEADER_WORDS +
		GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS + 4] ^= BIT(0);
	KUNIT_EXPECT_TRUE(test, gemini_mt6797_thermal_ledger_read_latest(
		&thermal_test_ops, &context, &record, &copy));
	KUNIT_EXPECT_EQ(test, record.generation, 1U);
}

static void thermal_ledger_rejects_nonempty_and_bad_shape(struct kunit *test)
{
	struct gemini_mt6797_thermal_ledger_owner owner = {};
	struct thermal_test_context context;
	int ret;

	thermal_test_empty(&context, false);
	context.words[1] = 4;
	ret = gemini_mt6797_thermal_ledger_owner_begin(
		&owner, &thermal_test_ops, &context);
	KUNIT_EXPECT_EQ(test, ret, -EBADMSG);

	memset(&owner, 0, sizeof(owner));
	thermal_test_empty(&context, false);
	KUNIT_ASSERT_EQ(test,
		gemini_mt6797_thermal_ledger_owner_begin(
			&owner, &thermal_test_ops, &context), 0);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PREPARE_BANK,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0, 0);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PREPARE_BANK,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 6, 0, 0);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_TRANSACTION,
		GEMINI_MT6797_THERMAL_LEDGER_TERMINAL,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0,
		GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
}

static void thermal_ledger_terminal_seals_owner(struct kunit *test)
{
	struct gemini_mt6797_thermal_ledger_record record;
	struct gemini_mt6797_thermal_ledger_owner owner = {};
	struct thermal_test_context context;
	u32 copy;
	int ret;

	thermal_test_empty(&context, false);
	KUNIT_ASSERT_EQ(test,
		gemini_mt6797_thermal_ledger_owner_begin(
			&owner, &thermal_test_ops, &context), 0);
	KUNIT_ASSERT_EQ(test, thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0), 0);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE_COMPLETE,
		GEMINI_MT6797_THERMAL_LEDGER_TERMINAL,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0,
		GEMINI_MT6797_THERMAL_LEDGER_SUCCESS);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, owner.sealed);
	KUNIT_EXPECT_FALSE(test, owner.active);
	KUNIT_EXPECT_TRUE(test, gemini_mt6797_thermal_ledger_read_latest(
		&thermal_test_ops, &context, &record, &copy));
	KUNIT_EXPECT_EQ(test, record.terminal,
			GEMINI_MT6797_THERMAL_LEDGER_SUCCESS);
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE_COMPLETE,
		GEMINI_MT6797_THERMAL_LEDGER_TERMINAL,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0,
		GEMINI_MT6797_THERMAL_LEDGER_SUCCESS);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
}

static void thermal_ledger_readback_mismatch_seals(struct kunit *test)
{
	struct gemini_mt6797_thermal_ledger_owner owner = {};
	struct thermal_test_context context;
	int ret;

	thermal_test_empty(&context, false);
	KUNIT_ASSERT_EQ(test,
		gemini_mt6797_thermal_ledger_owner_begin(
			&owner, &thermal_test_ops, &context), 0);
	context.corrupt_word =
		GEMINI_MT6797_THERMAL_LEDGER_HEADER_WORDS + 3;
	ret = thermal_test_checkpoint(
		&owner, &context, GEMINI_MT6797_THERMAL_PROBE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0, 0);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_TRUE(test, owner.failed);
	KUNIT_EXPECT_TRUE(test, owner.sealed);
	KUNIT_EXPECT_FALSE(test, owner.active);
}

static struct kunit_case thermal_ledger_cases[] = {
	KUNIT_CASE(thermal_ledger_accepts_pstore_empty),
	KUNIT_CASE(thermal_ledger_accepts_raw_empty),
	KUNIT_CASE(thermal_ledger_alternates_crc_copies),
	KUNIT_CASE(thermal_ledger_rejects_nonempty_and_bad_shape),
	KUNIT_CASE(thermal_ledger_terminal_seals_owner),
	KUNIT_CASE(thermal_ledger_readback_mismatch_seals),
	{}
};

static struct kunit_suite thermal_ledger_suite = {
	.name = "gemini-mt6797-thermal-ledger",
	.test_cases = thermal_ledger_cases,
};

kunit_test_suite(thermal_ledger_suite);

MODULE_LICENSE("GPL");
