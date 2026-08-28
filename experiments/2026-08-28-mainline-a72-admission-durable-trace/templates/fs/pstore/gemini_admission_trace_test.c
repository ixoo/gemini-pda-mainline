// SPDX-License-Identifier: GPL-2.0-only
/* In-memory tests for the immutable Gemini CPU8 admission trace. */

#include <kunit/test.h>
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/unaligned.h>

#include "gemini_admission_trace_internal.h"

static const char trace_test_entry[] =
	"====0.000000-D\n"
	"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
	"kind=entry slot=2\n";

static const char * const trace_test_terminal[] = {
	[GEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER] =
		"====0.000000-D\n"
		"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
		"kind=zero-source-register slot=3\n",
	[GEMINI_ADMISSION_TRACE_ZERO_DERIVE] =
		"====0.000000-D\n"
		"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
		"kind=zero-derive slot=3\n",
	[GEMINI_ADMISSION_TRACE_ZERO_PUBLISH] =
		"====0.000000-D\n"
		"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
		"kind=zero-publish slot=3\n",
};

struct trace_test_context {
	u8 slots[GEMINI_ADMISSION_TRACE_SLOT_COUNT]
		[GEMINI_ADMISSION_TRACE_SLOT_SIZE];
	unsigned int byte_writes[GEMINI_ADMISSION_TRACE_SLOT_COUNT];
	unsigned int word_writes[GEMINI_ADMISSION_TRACE_SLOT_COUNT];
	unsigned int syncs[GEMINI_ADMISSION_TRACE_SLOT_COUNT];
	unsigned int active_slot;
	bool payload_after_metadata;
	bool metadata_before_sync;
	bool drop_size;
};

static u32 trace_test_read_word(void *data, unsigned int slot,
				unsigned int word)
{
	struct trace_test_context *context = data;

	return get_unaligned_le32(&context->slots[slot][word * sizeof(u32)]);
}

static void trace_test_write_word(void *data, unsigned int slot,
				  unsigned int word, u32 value)
{
	struct trace_test_context *context = data;

	context->active_slot = slot;
	if ((word == 1 && context->syncs[slot] < 1) ||
	    (word == 2 && context->syncs[slot] < 2))
		context->metadata_before_sync = true;
	context->word_writes[slot]++;
	if (context->drop_size && word == 2)
		return;
	put_unaligned_le32(value,
			   &context->slots[slot][word * sizeof(u32)]);
}

static u8 trace_test_read_byte(void *data, unsigned int slot,
			       unsigned int offset)
{
	struct trace_test_context *context = data;

	return context->slots[slot][offset];
}

static void trace_test_write_byte(void *data, unsigned int slot,
				  unsigned int offset, u8 value)
{
	struct trace_test_context *context = data;

	context->active_slot = slot;
	if (context->word_writes[slot])
		context->payload_after_metadata = true;
	context->slots[slot][offset] = value;
	context->byte_writes[slot]++;
}

static void trace_test_sync(void *data)
{
	struct trace_test_context *context = data;

	context->syncs[context->active_slot]++;
}

static const struct gemini_admission_trace_ops trace_test_ops = {
	.read_word = trace_test_read_word,
	.write_word = trace_test_write_word,
	.read_byte = trace_test_read_byte,
	.write_byte = trace_test_write_byte,
	.sync = trace_test_sync,
};

static struct trace_test_context *trace_test_context(struct kunit *test)
{
	struct trace_test_context *context;
	unsigned int slot;

	context = kunit_kzalloc(test, sizeof(*context), GFP_KERNEL);
	if (!context)
		return NULL;
	for (slot = 0; slot < GEMINI_ADMISSION_TRACE_SLOT_COUNT; slot++)
		put_unaligned_le32(GEMINI_ADMISSION_TRACE_PSTORE_SIGNATURE,
				   &context->slots[slot][0]);
	return context;
}

static void trace_test_expect_record(struct kunit *test,
				     struct trace_test_context *context,
				     unsigned int slot, const char *record)
{
	size_t length = strlen(record);

	KUNIT_EXPECT_EQ(test, trace_test_read_word(context, slot, 0),
			GEMINI_ADMISSION_TRACE_PSTORE_SIGNATURE);
	KUNIT_EXPECT_EQ(test, trace_test_read_word(context, slot, 1),
			(u32)length);
	KUNIT_EXPECT_EQ(test, trace_test_read_word(context, slot, 2),
			(u32)length);
	KUNIT_EXPECT_EQ(test,
			memcmp(&context->slots[slot]
			       [GEMINI_ADMISSION_TRACE_HEADER_SIZE],
			       record, length), 0);
}

static void gemini_admission_trace_entry_commit_test(struct kunit *test)
{
	struct gemini_admission_trace_owner owner = { };
	struct trace_test_context *context = trace_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, owner.entry_committed);
	KUNIT_EXPECT_FALSE(test, owner.terminal_committed);
	KUNIT_EXPECT_EQ(test, owner.commits, 1U);
	KUNIT_EXPECT_EQ(test, context->word_writes[0], 2U);
	KUNIT_EXPECT_EQ(test, context->syncs[0], 3U);
	KUNIT_EXPECT_FALSE(test, context->payload_after_metadata);
	KUNIT_EXPECT_FALSE(test, context->metadata_before_sync);
	trace_test_expect_record(test, context, 0, trace_test_entry);
	KUNIT_EXPECT_EQ(test, trace_test_read_word(context, 1, 1), 0U);
}

static void gemini_admission_trace_entry_reentry_test(struct kunit *test)
{
	struct gemini_admission_trace_owner owner = { };
	struct trace_test_context *context = trace_test_context(test);
	unsigned int byte_writes;
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
	KUNIT_ASSERT_EQ(test, ret, 0);
	byte_writes = context->byte_writes[0];
	ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, owner.commits, 1U);
	KUNIT_EXPECT_EQ(test, context->byte_writes[0], byte_writes);
	KUNIT_EXPECT_EQ(test, context->word_writes[0], 2U);
}

static void gemini_admission_trace_foreign_refusal_test(struct kunit *test)
{
	struct gemini_admission_trace_owner owner = { };
	struct trace_test_context *context = trace_test_context(test);
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	put_unaligned_le32(1, &context->slots[0][4]);
	ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_TRUE(test, owner.failed);
	KUNIT_EXPECT_EQ(test, owner.commits, 0U);
	KUNIT_EXPECT_EQ(test, context->byte_writes[0], 0U);
	KUNIT_EXPECT_EQ(test, context->word_writes[0], 0U);
}

static void gemini_admission_trace_terminal_records_test(struct kunit *test)
{
	enum gemini_admission_trace_zero_result result;

	for (result = GEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER;
	     result <= GEMINI_ADMISSION_TRACE_ZERO_PUBLISH; result++) {
		struct gemini_admission_trace_owner owner = { };
		struct trace_test_context *context = trace_test_context(test);
		int ret;

		KUNIT_ASSERT_NOT_NULL(test, context);
		ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = gemini_admission_trace_owner_zero_request(&owner, &trace_test_ops, context, result);
		KUNIT_EXPECT_EQ(test, ret, 0);
		KUNIT_EXPECT_TRUE(test, owner.terminal_committed);
		KUNIT_EXPECT_EQ(test, owner.commits, 2U);
		KUNIT_EXPECT_EQ(test, context->word_writes[1], 2U);
		KUNIT_EXPECT_EQ(test, context->syncs[1], 3U);
		trace_test_expect_record(test, context, 1,
					 trace_test_terminal[result]);
	}
}

static void gemini_admission_trace_terminal_gates_test(struct kunit *test)
{
	struct gemini_admission_trace_owner owner = { };
	struct trace_test_context *context = trace_test_context(test);
	const enum gemini_admission_trace_zero_result result =
		GEMINI_ADMISSION_TRACE_ZERO_DERIVE;
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	ret = gemini_admission_trace_owner_zero_request(&owner, &trace_test_ops, context, result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
	KUNIT_ASSERT_EQ(test, ret, 0);
	put_unaligned_le32(1, &context->slots[1][4]);
	ret = gemini_admission_trace_owner_zero_request(&owner, &trace_test_ops, context, result);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_TRUE(test, owner.failed);
	KUNIT_EXPECT_EQ(test, owner.commits, 1U);
	ret = gemini_admission_trace_owner_zero_request(&owner, &trace_test_ops, context, result);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
}

static void gemini_admission_trace_torn_write_test(struct kunit *test)
{
	struct gemini_admission_trace_owner owner = { };
	struct trace_test_context *context = trace_test_context(test);
	unsigned int writes;
	int ret;

	KUNIT_ASSERT_NOT_NULL(test, context);
	context->drop_size = true;
	ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_TRUE(test, owner.failed);
	KUNIT_EXPECT_EQ(test, owner.commits, 0U);
	writes = context->byte_writes[0] + context->word_writes[0];
	ret = gemini_admission_trace_owner_entry(&owner, &trace_test_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test,
			context->byte_writes[0] + context->word_writes[0], writes);
}

static struct kunit_case gemini_admission_trace_cases[] = {
	KUNIT_CASE(gemini_admission_trace_entry_commit_test),
	KUNIT_CASE(gemini_admission_trace_entry_reentry_test),
	KUNIT_CASE(gemini_admission_trace_foreign_refusal_test),
	KUNIT_CASE(gemini_admission_trace_terminal_records_test),
	KUNIT_CASE(gemini_admission_trace_terminal_gates_test),
	KUNIT_CASE(gemini_admission_trace_torn_write_test),
	{ }
};

static struct kunit_suite gemini_admission_trace_suite = {
	.name = "gemini-admission-trace",
	.test_cases = gemini_admission_trace_cases,
};

kunit_test_suite(gemini_admission_trace_suite);

MODULE_LICENSE("GPL");
