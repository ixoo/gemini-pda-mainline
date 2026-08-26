// SPDX-License-Identifier: GPL-2.0-only
/* In-memory tests for the Gemini retained transition ledger. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/gemini_transition_ledger.h>
#include <linux/module.h>
#include <linux/string.h>

#include "gemini_transition_ledger_internal.h"

#define GEMINI_LEDGER_TEST_WORDS 32U
#define GEMINI_LEDGER_TEST_WRITES 256U

struct gemini_transition_ledger_test_state {
	u32 words[GEMINI_LEDGER_TEST_WORDS];
	u32 write_words[GEMINI_LEDGER_TEST_WRITES];
	u32 write_values[GEMINI_LEDGER_TEST_WRITES];
	unsigned int writes;
	unsigned int barriers;
	unsigned int drop_word;
	bool drop_enabled;
};

static u32 gemini_transition_ledger_test_read(void *context,
					      unsigned int word)
{
	struct gemini_transition_ledger_test_state *state = context;

	return word < GEMINI_LEDGER_TEST_WORDS ? state->words[word] : 0;
}

static void gemini_transition_ledger_test_write(void *context,
						unsigned int word, u32 value)
{
	struct gemini_transition_ledger_test_state *state = context;

	if (state->writes < GEMINI_LEDGER_TEST_WRITES) {
		state->write_words[state->writes] = word;
		state->write_values[state->writes] = value;
	}
	state->writes++;
	if (word < GEMINI_LEDGER_TEST_WORDS &&
	    (!state->drop_enabled || word != state->drop_word))
		state->words[word] = value;
}

static void gemini_transition_ledger_test_barrier(void *context)
{
	struct gemini_transition_ledger_test_state *state = context;

	state->barriers++;
}

static const struct gemini_transition_ledger_ops
gemini_transition_ledger_test_ops = {
	.read = gemini_transition_ledger_test_read,
	.write = gemini_transition_ledger_test_write,
	.barrier = gemini_transition_ledger_test_barrier,
};

static void gemini_transition_ledger_test_empty(
	struct gemini_transition_ledger_test_state *state)
{
	memset(state, 0, sizeof(*state));
	state->words[0] = GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE;
}

static unsigned int gemini_transition_ledger_test_copy_word(
	unsigned int copy, unsigned int word)
{
	return GEMINI_TRANSITION_LEDGER_HEADER_WORDS +
		copy * GEMINI_TRANSITION_LEDGER_COPY_WORDS + word;
}

static void gemini_transition_ledger_sequence_test(struct kunit *test)
{
	struct gemini_transition_ledger_test_state state;
	struct gemini_transition_ledger_record latest;
	struct gemini_transition_ledger_owner owner = {};
	const u64 attempt = 0x1122334455667788ULL;
	u32 copy;
	u32 stage;
	int ret;

	gemini_transition_ledger_test_empty(&state);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &gemini_transition_ledger_test_ops, &state, attempt);
	KUNIT_ASSERT_EQ(test, ret, 0);
	for (stage = 1; stage <= GEMINI_TRANSITION_LEDGER_MAX_STAGE; stage++) {
		ret = gemini_transition_ledger_owner_checkpoint(
			&owner, &gemini_transition_ledger_test_ops, &state,
			attempt, GEMINI_TRANSITION_LEDGER_BEFORE, stage, 0);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = gemini_transition_ledger_owner_checkpoint(
			&owner, &gemini_transition_ledger_test_ops, &state,
			attempt, GEMINI_TRANSITION_LEDGER_AFTER, stage, 0);
		KUNIT_ASSERT_EQ(test, ret, 0);
	}
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, attempt,
		GEMINI_TRANSITION_LEDGER_TERMINAL,
		GEMINI_TRANSITION_LEDGER_MAX_STAGE, 5);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, owner.sealed);
	KUNIT_EXPECT_FALSE(test, owner.active);
	KUNIT_EXPECT_FALSE(test, owner.failed);
	KUNIT_EXPECT_EQ(test, state.words[1],
			GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES);
	KUNIT_EXPECT_EQ(test, state.words[2],
			GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES);
	KUNIT_ASSERT_TRUE(test, gemini_transition_ledger_read_latest(
		&gemini_transition_ledger_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.attempt_id, attempt);
	KUNIT_EXPECT_EQ(test, latest.generation, 19U);
	KUNIT_EXPECT_EQ(test, latest.phase,
			(u32)GEMINI_TRANSITION_LEDGER_TERMINAL);
	KUNIT_EXPECT_EQ(test, latest.stage,
			GEMINI_TRANSITION_LEDGER_MAX_STAGE);
	KUNIT_EXPECT_EQ(test, latest.terminal, 5U);
	KUNIT_EXPECT_EQ(test, copy, 0U);
}

static void gemini_transition_ledger_raw_header_test(struct kunit *test)
{
	struct gemini_transition_ledger_test_state state;
	struct gemini_transition_ledger_record latest;
	struct gemini_transition_ledger_owner owner = {};
	u32 copy;
	int ret;

	memset(&state, 0xff, sizeof(state));
	state.writes = 0;
	state.barriers = 0;
	state.drop_enabled = false;
	ret = gemini_transition_ledger_owner_begin(
		&owner, &gemini_transition_ledger_test_ops, &state, 3);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 3,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state.words[0],
			GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE);
	KUNIT_EXPECT_EQ(test, state.write_words[state.writes - 1], 0U);
	KUNIT_EXPECT_EQ(test, state.write_values[state.writes - 1],
			GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE);
	KUNIT_ASSERT_TRUE(test, gemini_transition_ledger_read_latest(
		&gemini_transition_ledger_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.attempt_id, 3ULL);
	KUNIT_EXPECT_EQ(test, latest.generation, 1U);
}

static void gemini_transition_ledger_rejections_test(struct kunit *test)
{
	struct gemini_transition_ledger_test_state state;
	struct gemini_transition_ledger_owner malformed = {};
	struct gemini_transition_ledger_owner owner = {};
	unsigned int writes;
	int ret;

	gemini_transition_ledger_test_empty(&state);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &gemini_transition_ledger_test_ops, &state, 0);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	state.words[1] = 1;
	state.words[2] = 2;
	ret = gemini_transition_ledger_owner_begin(
		&malformed, &gemini_transition_ledger_test_ops, &state, 9);
	KUNIT_EXPECT_EQ(test, ret, -EBADMSG);
	gemini_transition_ledger_test_empty(&state);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &gemini_transition_ledger_test_ops, &state, 9);
	KUNIT_ASSERT_EQ(test, ret, 0);
	writes = state.writes;
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 9,
		GEMINI_TRANSITION_LEDGER_AFTER, 1, 0);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 9,
		GEMINI_TRANSITION_LEDGER_BEFORE, 0, 0);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 9,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 1);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 10,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 0);
	KUNIT_EXPECT_EQ(test, ret, -EACCES);
	KUNIT_EXPECT_EQ(test, state.writes, writes);
}

static void gemini_transition_ledger_torn_write_test(struct kunit *test)
{
	struct gemini_transition_ledger_test_state state;
	struct gemini_transition_ledger_record latest;
	struct gemini_transition_ledger_owner owner = {};
	u32 copy;
	int ret;

	gemini_transition_ledger_test_empty(&state);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &gemini_transition_ledger_test_ops, &state, 11);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 11,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	state.drop_word = gemini_transition_ledger_test_copy_word(
		1, GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD);
	state.drop_enabled = true;
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 11,
		GEMINI_TRANSITION_LEDGER_AFTER, 1, 0);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_TRUE(test, owner.failed);
	KUNIT_EXPECT_TRUE(test, owner.sealed);
	state.drop_enabled = false;
	KUNIT_ASSERT_TRUE(test, gemini_transition_ledger_read_latest(
		&gemini_transition_ledger_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.generation, 1U);
	KUNIT_EXPECT_EQ(test, latest.phase,
			(u32)GEMINI_TRANSITION_LEDGER_BEFORE);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 11,
		GEMINI_TRANSITION_LEDGER_AFTER, 1, 0);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
}

static void gemini_transition_ledger_corrupt_copy_test(struct kunit *test)
{
	struct gemini_transition_ledger_test_state state;
	struct gemini_transition_ledger_record latest;
	struct gemini_transition_ledger_owner first = {};
	struct gemini_transition_ledger_owner second = {};
	u32 copy;
	int ret;

	gemini_transition_ledger_test_empty(&state);
	ret = gemini_transition_ledger_owner_begin(
		&first, &gemini_transition_ledger_test_ops, &state, 21);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(
		&first, &gemini_transition_ledger_test_ops, &state, 21,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(
		&first, &gemini_transition_ledger_test_ops, &state, 21,
		GEMINI_TRANSITION_LEDGER_AFTER, 1, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	state.words[gemini_transition_ledger_test_copy_word(
		1, GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD)] ^= BIT(0);
	ret = gemini_transition_ledger_owner_begin(
		&second, &gemini_transition_ledger_test_ops, &state, 22);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(
		&second, &gemini_transition_ledger_test_ops, &state, 22,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_ASSERT_TRUE(test, gemini_transition_ledger_read_latest(
		&gemini_transition_ledger_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.attempt_id, 22ULL);
	KUNIT_EXPECT_EQ(test, latest.generation, 2U);
	KUNIT_EXPECT_EQ(test, copy, 1U);
}

static void gemini_transition_ledger_terminal_one_shot_test(struct kunit *test)
{
	struct gemini_transition_ledger_test_state state;
	struct gemini_transition_ledger_owner owner = {};
	unsigned int writes;
	int ret;

	gemini_transition_ledger_test_empty(&state);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &gemini_transition_ledger_test_ops, &state, 31);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 31,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 31,
		GEMINI_TRANSITION_LEDGER_TERMINAL, 1, 1);
	KUNIT_ASSERT_EQ(test, ret, 0);
	writes = state.writes;
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &gemini_transition_ledger_test_ops, &state, 31,
		GEMINI_TRANSITION_LEDGER_AFTER, 1, 0);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &gemini_transition_ledger_test_ops, &state, 32);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, state.writes, writes);
}

static struct kunit_case gemini_transition_ledger_cases[] = {
	KUNIT_CASE(gemini_transition_ledger_sequence_test),
	KUNIT_CASE(gemini_transition_ledger_raw_header_test),
	KUNIT_CASE(gemini_transition_ledger_rejections_test),
	KUNIT_CASE(gemini_transition_ledger_torn_write_test),
	KUNIT_CASE(gemini_transition_ledger_corrupt_copy_test),
	KUNIT_CASE(gemini_transition_ledger_terminal_one_shot_test),
	{}
};

static struct kunit_suite gemini_transition_ledger_suite = {
	.name = "gemini-transition-ledger",
	.test_cases = gemini_transition_ledger_cases,
};

kunit_test_suite(gemini_transition_ledger_suite);

MODULE_LICENSE("GPL");
