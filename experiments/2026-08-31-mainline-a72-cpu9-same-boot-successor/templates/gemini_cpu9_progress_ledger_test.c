// SPDX-License-Identifier: GPL-2.0-only
/* In-memory tests for the Gemini CPU9 retained progress ledger. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/gemini_cpu9_progress_ledger.h>
#include <linux/module.h>
#include <linux/string.h>

#include "gemini_cpu9_progress_ledger_internal.h"

struct cpu9_progress_test_state {
	u32 words[GEMINI_TRANSITION_LEDGER_HEADER_WORDS +
		  GEMINI_TRANSITION_LEDGER_COPIES *
		  GEMINI_TRANSITION_LEDGER_COPY_WORDS];
	u32 writes;
};

static u32 cpu9_progress_test_read(void *context, unsigned int word)
{
	struct cpu9_progress_test_state *state = context;

	return state->words[word];
}

static void cpu9_progress_test_write(void *context, unsigned int word,
				     u32 value)
{
	struct cpu9_progress_test_state *state = context;

	state->words[word] = value;
	state->writes++;
}

static void cpu9_progress_test_sync(void *context)
{
	(void)context;
}

static const struct gemini_transition_ledger_ops cpu9_progress_test_ops = {
	.read = cpu9_progress_test_read,
	.write = cpu9_progress_test_write,
	.sync = cpu9_progress_test_sync,
};

static void cpu9_progress_test_empty(struct cpu9_progress_test_state *state)
{
	memset(state, 0, sizeof(*state));
	state->words[0] = GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE;
}

static int cpu9_progress_test_seed_cpu8(
	struct cpu9_progress_test_state *state, u64 attempt_id)
{
	struct gemini_transition_ledger_owner owner = {};
	u32 stage;
	int ret;

	cpu9_progress_test_empty(state);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &cpu9_progress_test_ops, state, attempt_id);
	if (ret)
		return ret;
	for (stage = 1; stage <= GEMINI_TRANSITION_LEDGER_MAX_STAGE; stage++) {
		ret = gemini_transition_ledger_owner_checkpoint(
			&owner, &cpu9_progress_test_ops, state, attempt_id,
			GEMINI_TRANSITION_LEDGER_BEFORE, stage, 0);
		if (ret)
			return ret;
		ret = gemini_transition_ledger_owner_checkpoint(
			&owner, &cpu9_progress_test_ops, state, attempt_id,
			GEMINI_TRANSITION_LEDGER_AFTER, stage, 0);
		if (ret)
			return ret;
	}
	return gemini_transition_ledger_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, state, attempt_id,
		GEMINI_TRANSITION_LEDGER_TERMINAL,
		GEMINI_TRANSITION_LEDGER_MAX_STAGE, 5);
}

static bool cpu9_progress_test_latest(
	struct cpu9_progress_test_state *state,
	struct gemini_transition_ledger_record *latest)
{
	u32 copy = 0;

	return gemini_transition_ledger_read_latest(
		&cpu9_progress_test_ops, state, latest, &copy);
}

static void cpu9_progress_sequence_test(struct kunit *test)
{
	struct cpu9_progress_test_state cpu8;
	struct cpu9_progress_test_state progress;
	struct gemini_cpu9_progress_owner owner = {};
	struct gemini_transition_ledger_record latest;
	u32 stage;
	int ret;

	KUNIT_ASSERT_EQ(test, cpu9_progress_test_seed_cpu8(&cpu8, 1), 0);
	cpu9_progress_test_empty(&progress);
	ret = cpu9_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu8,
		&cpu9_progress_test_ops, &progress, 1);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_ASSERT_TRUE(test, cpu9_progress_test_latest(&progress, &latest));
	KUNIT_EXPECT_EQ(test, latest.generation, 2U);
	KUNIT_EXPECT_EQ(test, latest.phase,
			(u32)GEMINI_TRANSITION_LEDGER_AFTER);
	KUNIT_EXPECT_EQ(test, latest.stage,
			(u32)GEMINI_CPU9_PROGRESS_CPU8_PROOF);
	for (stage = GEMINI_CPU9_PROGRESS_READY_TOKEN;
	     stage <= GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN; stage++)
		KUNIT_ASSERT_EQ(test, cpu9_progress_owner_checkpoint(
			&owner, &cpu9_progress_test_ops, &progress, 1, stage), 0);
	KUNIT_ASSERT_TRUE(test, cpu9_progress_test_latest(&progress, &latest));
	KUNIT_EXPECT_EQ(test, latest.generation, 20U);
	KUNIT_EXPECT_EQ(test, latest.stage,
			(u32)GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN);
	KUNIT_EXPECT_EQ(test, progress.writes, 202U);
	KUNIT_EXPECT_TRUE(test, owner.ledger.sealed);
}

static void cpu9_progress_cpu8_gate_test(struct kunit *test)
{
	struct cpu9_progress_test_state cpu8;
	struct cpu9_progress_test_state progress;
	struct gemini_cpu9_progress_owner owner = {};

	KUNIT_ASSERT_EQ(test, cpu9_progress_test_seed_cpu8(&cpu8, 1), 0);
	cpu9_progress_test_empty(&progress);
	KUNIT_EXPECT_EQ(test, cpu9_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu8,
		&cpu9_progress_test_ops, &progress, 2), -EACCES);
	memset(&owner, 0, sizeof(owner));
	cpu8.words[0] = 0;
	KUNIT_EXPECT_EQ(test, cpu9_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu8,
		&cpu9_progress_test_ops, &progress, 1), -ENODATA);
}

static void cpu9_progress_lane_refusal_test(struct kunit *test)
{
	struct cpu9_progress_test_state cpu8;
	struct cpu9_progress_test_state progress;
	struct gemini_cpu9_progress_owner owner = {};

	KUNIT_ASSERT_EQ(test, cpu9_progress_test_seed_cpu8(&cpu8, 1), 0);
	memset(&progress, 0xff, sizeof(progress));
	KUNIT_EXPECT_EQ(test, cpu9_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu8,
		&cpu9_progress_test_ops, &progress, 1), -EBADMSG);
	memset(&owner, 0, sizeof(owner));
	cpu9_progress_test_empty(&progress);
	progress.words[1] = GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES;
	progress.words[2] = GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES;
	KUNIT_EXPECT_EQ(test, cpu9_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu8,
		&cpu9_progress_test_ops, &progress, 1), -EALREADY);
}

static void cpu9_progress_ordering_test(struct kunit *test)
{
	struct cpu9_progress_test_state cpu8;
	struct cpu9_progress_test_state progress;
	struct gemini_cpu9_progress_owner owner = {};

	KUNIT_ASSERT_EQ(test, cpu9_progress_test_seed_cpu8(&cpu8, 1), 0);
	cpu9_progress_test_empty(&progress);
	KUNIT_ASSERT_EQ(test, cpu9_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu8,
		&cpu9_progress_test_ops, &progress, 1), 0);
	KUNIT_EXPECT_EQ(test, cpu9_progress_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, &progress, 1,
		GEMINI_CPU9_PROGRESS_DERIVE), -EINVAL);
	KUNIT_EXPECT_EQ(test, cpu9_progress_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, &progress, 2,
		GEMINI_CPU9_PROGRESS_READY_TOKEN), -EACCES);
	KUNIT_EXPECT_EQ(test, cpu9_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu8,
		&cpu9_progress_test_ops, &progress, 1), -EALREADY);
}

static struct kunit_case cpu9_progress_cases[] = {
	KUNIT_CASE(cpu9_progress_sequence_test),
	KUNIT_CASE(cpu9_progress_cpu8_gate_test),
	KUNIT_CASE(cpu9_progress_lane_refusal_test),
	KUNIT_CASE(cpu9_progress_ordering_test),
	{ }
};

static struct kunit_suite cpu9_progress_suite = {
	.name = "gemini-cpu9-progress-ledger",
	.test_cases = cpu9_progress_cases,
};

kunit_test_suite(cpu9_progress_suite);

MODULE_LICENSE("GPL");
