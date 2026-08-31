// SPDX-License-Identifier: GPL-2.0-only
/* In-memory tests for the Gemini independent CPU9 transition ledger. */

#include <kunit/test.h>
#include <linux/bitops.h>
#include <linux/errno.h>
#include <linux/gemini_cpu9_transition_ledger.h>
#include <linux/module.h>
#include <linux/string.h>

#include "gemini_cpu9_transition_ledger_internal.h"

#define GEMINI_CPU9_LEDGER_TEST_WORDS 32U

struct gemini_cpu9_ledger_test_state {
	u32 words[GEMINI_CPU9_LEDGER_TEST_WORDS];
	unsigned int writes;
	unsigned int syncs;
};

static u32 cpu9_ledger_test_read(void *context, unsigned int word)
{
	struct gemini_cpu9_ledger_test_state *state = context;

	return word < GEMINI_CPU9_LEDGER_TEST_WORDS ? state->words[word] : 0;
}

static void cpu9_ledger_test_write(void *context, unsigned int word, u32 value)
{
	struct gemini_cpu9_ledger_test_state *state = context;

	state->writes++;
	if (word < GEMINI_CPU9_LEDGER_TEST_WORDS)
		state->words[word] = value;
}

static void cpu9_ledger_test_sync(void *context)
{
	struct gemini_cpu9_ledger_test_state *state = context;

	state->syncs++;
}

static const struct gemini_transition_ledger_ops cpu9_ledger_test_ops = {
	.read = cpu9_ledger_test_read,
	.write = cpu9_ledger_test_write,
	.sync = cpu9_ledger_test_sync,
};

static void cpu9_ledger_test_empty(struct gemini_cpu9_ledger_test_state *state)
{
	memset(state, 0, sizeof(*state));
	state->words[0] = GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE;
}

static void cpu9_ledger_test_raw(struct gemini_cpu9_ledger_test_state *state)
{
	memset(state, 0xff, sizeof(*state));
	state->writes = 0;
	state->syncs = 0;
}

static unsigned int
cpu9_ledger_test_copy_word(unsigned int copy, unsigned int word)
{
	return GEMINI_TRANSITION_LEDGER_HEADER_WORDS +
		copy * GEMINI_TRANSITION_LEDGER_COPY_WORDS + word;
}

static int
cpu9_ledger_test_seed_cpu8(struct gemini_cpu9_ledger_test_state *state,
			   u64 attempt, bool terminal)
{
	struct gemini_transition_ledger_owner owner = {};
	u32 stage;
	int ret;

	ret = gemini_transition_ledger_owner_begin(&owner,
					   &cpu9_ledger_test_ops, state, attempt);
	if (ret)
		return ret;
	for (stage = 1; stage <= GEMINI_TRANSITION_LEDGER_MAX_STAGE; stage++) {
		ret = gemini_transition_ledger_owner_checkpoint(&owner,
			&cpu9_ledger_test_ops, state, attempt,
			GEMINI_TRANSITION_LEDGER_BEFORE, stage, 0);
		if (ret || (!terminal && stage == 1))
			return ret;
		ret = gemini_transition_ledger_owner_checkpoint(&owner,
			&cpu9_ledger_test_ops, state, attempt,
			GEMINI_TRANSITION_LEDGER_AFTER, stage, 0);
		if (ret)
			return ret;
	}
	return gemini_transition_ledger_owner_checkpoint(&owner,
		&cpu9_ledger_test_ops, state, attempt,
		GEMINI_TRANSITION_LEDGER_TERMINAL,
		GEMINI_TRANSITION_LEDGER_MAX_STAGE,
		GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF);
}

static int
cpu9_ledger_test_begin(struct gemini_cpu9_transition_ledger_owner *owner,
	struct gemini_cpu9_ledger_test_state *cpu8,
	struct gemini_cpu9_ledger_test_state *cpu9,
	u64 cpu8_attempt, u64 cpu9_attempt)
{
	return cpu9_ledger_owner_begin(owner, &cpu9_ledger_test_ops, cpu8,
		&cpu9_ledger_test_ops, cpu9,
		cpu8_attempt, cpu9_attempt);
}

static int
cpu9_ledger_test_checkpoint(struct gemini_cpu9_transition_ledger_owner *owner,
	struct gemini_cpu9_ledger_test_state *cpu9, u64 attempt,
	u32 phase, u32 stage, u32 terminal)
{
	return cpu9_ledger_owner_checkpoint(owner, &cpu9_ledger_test_ops, cpu9,
		attempt, phase, stage,
		terminal);
}

static void gemini_cpu9_transition_ledger_sequence_test(struct kunit *test)
{
	struct gemini_cpu9_ledger_test_state cpu8;
	struct gemini_cpu9_ledger_test_state cpu9;
	struct gemini_cpu9_transition_ledger_owner owner = {};
	struct gemini_transition_ledger_record latest;
	const u64 cpu8_attempt = 0x1122334455667788ULL;
	const u64 cpu9_attempt = 0x8877665544332211ULL;
	bool valid;
	u32 copy;
	u32 stage;
	int ret;

	cpu9_ledger_test_empty(&cpu8);
	cpu9_ledger_test_empty(&cpu9);
	ret = cpu9_ledger_test_seed_cpu8(&cpu8, cpu8_attempt, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_begin(&owner, &cpu8, &cpu9, cpu8_attempt,
				     cpu9_attempt);
	KUNIT_ASSERT_EQ(test, ret, 0);
	for (stage = GEMINI_CPU9_LEDGER_PRESTATE;
	     stage <= GEMINI_CPU9_LEDGER_MEMBERSHIP; stage++) {
		ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, cpu9_attempt,
			GEMINI_TRANSITION_LEDGER_BEFORE, stage, 0);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, cpu9_attempt,
			GEMINI_TRANSITION_LEDGER_AFTER, stage, 0);
		KUNIT_ASSERT_EQ(test, ret, 0);
	}
	ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, cpu9_attempt,
		GEMINI_TRANSITION_LEDGER_TERMINAL,
		GEMINI_CPU9_LEDGER_MEMBERSHIP,
		GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, owner.attempted);
	KUNIT_EXPECT_TRUE(test, owner.ledger.sealed);
	valid = gemini_transition_ledger_read_latest(&cpu9_ledger_test_ops,
						     &cpu9, &latest, &copy);
	KUNIT_ASSERT_TRUE(test, valid);
	KUNIT_EXPECT_EQ(test, latest.attempt_id, cpu9_attempt);
	KUNIT_EXPECT_EQ(test, latest.generation, 11U);
	KUNIT_EXPECT_EQ(test, latest.phase,
			(u32)GEMINI_TRANSITION_LEDGER_TERMINAL);
	KUNIT_EXPECT_EQ(test, latest.stage,
			(u32)GEMINI_CPU9_LEDGER_MEMBERSHIP);
	KUNIT_EXPECT_EQ(test, latest.terminal,
			(u32)GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF);
}

static void gemini_cpu9_transition_ledger_raw_lane_test(struct kunit *test)
{
	struct gemini_cpu9_ledger_test_state cpu8;
	struct gemini_cpu9_ledger_test_state cpu9;
	struct gemini_cpu9_transition_ledger_owner owner = {};
	const u64 cpu8_attempt = 41;
	int ret;

	cpu9_ledger_test_empty(&cpu8);
	cpu9_ledger_test_raw(&cpu9);
	ret = cpu9_ledger_test_seed_cpu8(&cpu8, cpu8_attempt, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_begin(&owner, &cpu8, &cpu9, cpu8_attempt, 42);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, 42,
		GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_LEDGER_PRESTATE, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, cpu9.words[0],
			GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE);
	KUNIT_EXPECT_EQ(test, cpu9.words[1],
			GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES);
	KUNIT_EXPECT_EQ(test, cpu9.words[2],
			GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES);
}

static void gemini_cpu9_transition_ledger_cpu8_gate_test(struct kunit *test)
{
	struct gemini_cpu9_ledger_test_state cpu8;
	struct gemini_cpu9_ledger_test_state cpu9;
	struct gemini_cpu9_transition_ledger_owner missing = {};
	struct gemini_cpu9_transition_ledger_owner partial = {};
	struct gemini_cpu9_transition_ledger_owner wrong = {};
	const u64 cpu8_attempt = 51;
	int ret;

	cpu9_ledger_test_empty(&cpu8);
	cpu9_ledger_test_empty(&cpu9);
	ret = cpu9_ledger_test_begin(&missing, &cpu8, &cpu9, cpu8_attempt, 52);
	KUNIT_EXPECT_EQ(test, ret, -ENODATA);
	ret = cpu9_ledger_test_begin(&missing, &cpu8, &cpu9, cpu8_attempt, 52);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	ret = cpu9_ledger_test_seed_cpu8(&cpu8, cpu8_attempt, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_begin(&partial, &cpu8, &cpu9,
				     cpu8_attempt, 52);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	cpu9_ledger_test_empty(&cpu8);
	ret = cpu9_ledger_test_seed_cpu8(&cpu8, cpu8_attempt, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_begin(&wrong, &cpu8, &cpu9,
				     cpu8_attempt + 1, 52);
	KUNIT_EXPECT_EQ(test, ret, -EACCES);
	KUNIT_EXPECT_EQ(test, cpu9.writes, 0U);
}

static void gemini_cpu9_transition_ledger_corrupt_cpu8_test(struct kunit *test)
{
	struct gemini_cpu9_ledger_test_state cpu8;
	struct gemini_cpu9_ledger_test_state cpu9;
	struct gemini_cpu9_transition_ledger_owner owner = {};
	const u64 cpu8_attempt = 61;
	unsigned int copy;
	unsigned int word;
	int ret;

	cpu9_ledger_test_empty(&cpu8);
	cpu9_ledger_test_empty(&cpu9);
	ret = cpu9_ledger_test_seed_cpu8(&cpu8, cpu8_attempt, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	for (copy = 0; copy < GEMINI_TRANSITION_LEDGER_COPIES; copy++) {
		word = cpu9_ledger_test_copy_word(copy,
			GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD);
		cpu8.words[word] ^= BIT(0);
	}
	ret = cpu9_ledger_test_begin(&owner, &cpu8, &cpu9, cpu8_attempt, 62);
	KUNIT_EXPECT_EQ(test, ret, -EBADMSG);
	KUNIT_EXPECT_EQ(test, cpu9.writes, 0U);
}

static void gemini_cpu9_transition_ledger_lane_refusal_test(struct kunit *test)
{
	struct gemini_cpu9_ledger_test_state cpu8;
	struct gemini_cpu9_ledger_test_state committed;
	struct gemini_cpu9_ledger_test_state malformed;
	struct gemini_cpu9_transition_ledger_owner owner = {};
	struct gemini_cpu9_transition_ledger_owner second = {};
	struct gemini_transition_ledger_owner seed = {};
	const u64 cpu8_attempt = 71;
	int ret;

	cpu9_ledger_test_empty(&cpu8);
	cpu9_ledger_test_empty(&committed);
	ret = cpu9_ledger_test_seed_cpu8(&cpu8, cpu8_attempt, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_begin(&seed, &cpu9_ledger_test_ops,
						   &committed, 72);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = gemini_transition_ledger_owner_checkpoint(&seed,
		&cpu9_ledger_test_ops, &committed, 72,
		GEMINI_TRANSITION_LEDGER_BEFORE, 1, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_begin(&owner, &cpu8, &committed,
				     cpu8_attempt, 73);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	cpu9_ledger_test_empty(&malformed);
	malformed.words[1] = 1;
	ret = cpu9_ledger_test_begin(&second, &cpu8, &malformed,
				     cpu8_attempt, 73);
	KUNIT_EXPECT_EQ(test, ret, -EBADMSG);
}

static void gemini_cpu9_transition_ledger_ordering_test(struct kunit *test)
{
	struct gemini_cpu9_ledger_test_state cpu8;
	struct gemini_cpu9_ledger_test_state cpu9;
	struct gemini_cpu9_transition_ledger_owner owner = {};
	const u64 cpu8_attempt = 81;
	unsigned int writes;
	int ret;

	cpu9_ledger_test_empty(&cpu8);
	cpu9_ledger_test_empty(&cpu9);
	ret = cpu9_ledger_test_seed_cpu8(&cpu8, cpu8_attempt, true);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_begin(&owner, &cpu8, &cpu9, cpu8_attempt, 82);
	KUNIT_ASSERT_EQ(test, ret, 0);
	writes = cpu9.writes;
	ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, 82,
		GEMINI_TRANSITION_LEDGER_AFTER,
		GEMINI_CPU9_LEDGER_PRESTATE, 0);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, 82,
		GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_LEDGER_MEMBERSHIP + 1, 0);
	KUNIT_EXPECT_EQ(test, ret, -EINVAL);
	KUNIT_EXPECT_EQ(test, cpu9.writes, writes);
	ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, 82,
		GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_LEDGER_PRESTATE, 0);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, 82,
		GEMINI_TRANSITION_LEDGER_TERMINAL,
		GEMINI_CPU9_LEDGER_PRESTATE,
		GEMINI_CPU9_LEDGER_PRESTATE_FAILURE);
	KUNIT_ASSERT_EQ(test, ret, 0);
	writes = cpu9.writes;
	ret = cpu9_ledger_test_checkpoint(&owner, &cpu9, 82,
		GEMINI_TRANSITION_LEDGER_AFTER,
		GEMINI_CPU9_LEDGER_PRESTATE, 0);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	ret = cpu9_ledger_test_begin(&owner, &cpu8, &cpu9, cpu8_attempt, 83);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, cpu9.writes, writes);
}

static struct kunit_case gemini_cpu9_transition_ledger_cases[] = {
	KUNIT_CASE(gemini_cpu9_transition_ledger_sequence_test),
	KUNIT_CASE(gemini_cpu9_transition_ledger_raw_lane_test),
	KUNIT_CASE(gemini_cpu9_transition_ledger_cpu8_gate_test),
	KUNIT_CASE(gemini_cpu9_transition_ledger_corrupt_cpu8_test),
	KUNIT_CASE(gemini_cpu9_transition_ledger_lane_refusal_test),
	KUNIT_CASE(gemini_cpu9_transition_ledger_ordering_test),
	{}
};

static struct kunit_suite gemini_cpu9_transition_ledger_suite = {
	.name = "gemini-cpu9-transition-ledger",
	.test_cases = gemini_cpu9_transition_ledger_cases,
};

kunit_test_suite(gemini_cpu9_transition_ledger_suite);

MODULE_LICENSE("GPL");
