// SPDX-License-Identifier: GPL-2.0-only
/* Injected dispatch tests for the retained-cluster MT6797 CPU9 binder. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>

#include "mt6797-a72-cpu9-binder-internal.h"

enum mt6797_cpu9_binder_test_failure {
	MT6797_CPU9_BINDER_FAIL_NONE,
	MT6797_CPU9_BINDER_FAIL_LEDGER_BEGIN,
	MT6797_CPU9_BINDER_FAIL_PREFLIGHT,
	MT6797_CPU9_BINDER_FAIL_CLAIM,
	MT6797_CPU9_BINDER_FAIL_P30E_PREPARE,
	MT6797_CPU9_BINDER_FAIL_CPU_ON_BEGIN,
	MT6797_CPU9_BINDER_FAIL_P30E_ARM,
	MT6797_CPU9_BINDER_FAIL_CPU_BOOT,
	MT6797_CPU9_BINDER_FAIL_P30E_READBACK,
	MT6797_CPU9_BINDER_FAIL_IPI,
	MT6797_CPU9_BINDER_FAIL_PUBLISH,
	MT6797_CPU9_BINDER_FAIL_FINALIZE,
};

struct mt6797_cpu9_binder_test_state {
	enum mt6797_cpu9_binder_test_failure failure;
	struct mt6797_a72_transaction transaction;
	bool cpu8_online;
	bool cpu9_online;
	unsigned int ledger_begin_calls;
	unsigned int ledger_checkpoint_calls;
	unsigned int preflight_calls;
	unsigned int claim_calls;
	unsigned int reject_calls;
	unsigned int cpu_on_begin_calls;
	unsigned int p30e_prepare_calls;
	unsigned int p30e_arm_calls;
	unsigned int cpu_boot_calls;
	unsigned int p30e_readback_calls;
	unsigned int ipi_calls;
	unsigned int publish_calls;
	unsigned int finalize_calls;
	u64 cpu8_attempt_id;
	u64 cpu9_attempt_id;
	u32 terminal_phase;
	u32 terminal_stage;
	u32 terminal_value;
};

static struct mt6797_cpu9_binder_test_state *mt6797_cpu9_binder_test_active;

static int mt6797_cpu9_binder_test_ledger_begin(u64 cpu8_attempt_id,
						u64 cpu9_attempt_id)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	state->ledger_begin_calls++;
	state->cpu8_attempt_id = cpu8_attempt_id;
	state->cpu9_attempt_id = cpu9_attempt_id;
	return state->failure == MT6797_CPU9_BINDER_FAIL_LEDGER_BEGIN ? -EIO :
									0;
}

static int mt6797_cpu9_binder_test_ledger_checkpoint(u64 cpu9_attempt_id,
						     u32 phase, u32 stage,
						     u32 terminal)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	state->ledger_checkpoint_calls++;
	if (phase == GEMINI_TRANSITION_LEDGER_TERMINAL) {
		state->terminal_phase = phase;
		state->terminal_stage = stage;
		state->terminal_value = terminal;
	}
	return cpu9_attempt_id == state->cpu9_attempt_id ? 0 : -EPROTO;
}

static int mt6797_cpu9_binder_test_membership_preflight(void)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	state->preflight_calls++;
	return state->failure == MT6797_CPU9_BINDER_FAIL_PREFLIGHT ? -EIO : 0;
}

static int mt6797_cpu9_binder_test_membership_claim(
	struct mt6797_a72_transaction *transaction)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	state->claim_calls++;
	if (state->failure == MT6797_CPU9_BINDER_FAIL_CLAIM)
		return -EIO;
	*transaction = state->transaction;
	return 0;
}

static int mt6797_cpu9_binder_test_membership_reject(
	struct mt6797_a72_transaction *transaction)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	(void)transaction;
	state->reject_calls++;
	return 0;
}

static int mt6797_cpu9_binder_test_membership_begin_cpu_on(
	struct mt6797_a72_transaction *transaction)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	(void)transaction;
	state->cpu_on_begin_calls++;
	return state->failure == MT6797_CPU9_BINDER_FAIL_CPU_ON_BEGIN ? -EIO :
									0;
}

static int mt6797_cpu9_binder_test_p30e_prepare(
	const struct mt6797_a72_transaction *transaction,
	struct mt6797_a72_p30e_handoff *handoff)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	(void)transaction;
	state->p30e_prepare_calls++;
	if (state->failure == MT6797_CPU9_BINDER_FAIL_P30E_PREPARE)
		return -EIO;
	handoff->target_cpu = MT6797_A72_CPU9_EXECUTOR_CPU9;
	handoff->operation = ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP;
	return 0;
}

static int
mt6797_cpu9_binder_test_p30e_arm(unsigned int cpu,
				 const struct mt6797_a72_p30e_handoff *handoff)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	state->p30e_arm_calls++;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    handoff->target_cpu != cpu ||
	    handoff->operation != ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP)
		return -EPROTO;
	return state->failure == MT6797_CPU9_BINDER_FAIL_P30E_ARM ? -EIO : 0;
}

static int mt6797_cpu9_binder_test_p30e_readback(
	unsigned int cpu, const struct mt6797_a72_p30e_handoff *handoff,
	struct arm64_mt6797_a72_p30e_wire *copy)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	(void)copy;
	state->p30e_readback_calls++;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || handoff->target_cpu != cpu)
		return -EPROTO;
	return state->failure == MT6797_CPU9_BINDER_FAIL_P30E_READBACK ? -EIO :
									 0;
}

static int mt6797_cpu9_binder_test_membership_publish(
	struct mt6797_a72_transaction *transaction)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	(void)transaction;
	state->publish_calls++;
	return state->failure == MT6797_CPU9_BINDER_FAIL_PUBLISH ? -EIO : 0;
}

static int mt6797_cpu9_binder_test_membership_finalize(
	struct mt6797_a72_transaction *transaction)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	(void)transaction;
	state->finalize_calls++;
	return state->failure == MT6797_CPU9_BINDER_FAIL_FINALIZE ? -EIO : 0;
}

static bool mt6797_cpu9_binder_test_cpu_online(unsigned int cpu)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	return cpu == MT6797_A72_CPU9_EXECUTOR_CPU8 ?
		       state->cpu8_online :
		       cpu == MT6797_A72_CPU9_EXECUTOR_CPU9 &&
			       state->cpu9_online;
}

static int mt6797_cpu9_binder_test_ipi_call(unsigned int cpu,
					    smp_call_func_t func, void *info,
					    int wait)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	state->ipi_calls++;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || !func || !wait)
		return -EPROTO;
	func(info);
	return state->failure == MT6797_CPU9_BINDER_FAIL_IPI ? -EIO : 0;
}

static int mt6797_cpu9_binder_test_cpu_boot(unsigned int cpu)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;

	state->cpu_boot_calls++;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9)
		return -EPROTO;
	return state->failure == MT6797_CPU9_BINDER_FAIL_CPU_BOOT ? -EIO : 0;
}

static const struct mt6797_a72_cpu9_binder_backend_ops
	mt6797_cpu9_binder_test_backend = {
		.ledger_begin = mt6797_cpu9_binder_test_ledger_begin,
		.ledger_checkpoint = mt6797_cpu9_binder_test_ledger_checkpoint,
		.membership_preflight =
			mt6797_cpu9_binder_test_membership_preflight,
		.membership_claim = mt6797_cpu9_binder_test_membership_claim,
		.membership_reject = mt6797_cpu9_binder_test_membership_reject,
		.membership_begin_cpu_on =
			mt6797_cpu9_binder_test_membership_begin_cpu_on,
		.p30e_prepare = mt6797_cpu9_binder_test_p30e_prepare,
		.p30e_arm = mt6797_cpu9_binder_test_p30e_arm,
		.p30e_readback = mt6797_cpu9_binder_test_p30e_readback,
		.membership_publish_success =
			mt6797_cpu9_binder_test_membership_publish,
		.membership_finalize_success =
			mt6797_cpu9_binder_test_membership_finalize,
		.cpu_online = mt6797_cpu9_binder_test_cpu_online,
		.ipi_call = mt6797_cpu9_binder_test_ipi_call,
	};

static struct mt6797_a72_cpu9_executor_request
mt6797_cpu9_binder_test_request(void)
{
	return (struct mt6797_a72_cpu9_executor_request){
		.cpu = MT6797_A72_CPU9_EXECUTOR_CPU9,
		.cpu8_attempt_id = 0x4350553850524f4fULL,
		.cpu9_attempt_id = 0x435055394f4e4531ULL,
		.members = BIT(0),
		.retained_mask = MT6797_A72_CPU9_RETAINED_REQUIRED,
		.cpu8_terminal_exact = true,
		.cpu8_membership_published = true,
		.provider_retained = true,
		.cpu8_online = true,
		.cpu9_online = false,
	};
}

static void
mt6797_cpu9_binder_test_reset(struct mt6797_a72_cpu9_binder *binder,
			      struct mt6797_cpu9_binder_test_state *state)
{
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_binder_test_request();

	memset(state, 0, sizeof(*state));
	state->cpu8_online = true;
	state->transaction.valid = 1;
	state->transaction.a36_valid = 1;
	state->transaction.p30_token_valid = 1;
	state->transaction.p17_p18_published = 1;
	state->transaction.identity.abi = MT6797_A72_TRANSACTION_ABI;
	state->transaction.identity.operation =
		ARM64_LATE_CPU_STARTUP_OP_CPU9_UP;
	state->transaction.identity.target_cpu = MT6797_A72_CPU9_EXECUTOR_CPU9;
	state->transaction.identity.cpuhp_target = CPUHP_ONLINE;
	state->transaction.identity.target_mpidr =
		ARM64_MT6797_A72_P30E_MPIDR_CPU9;
	state->transaction.identity.generation = request.cpu9_attempt_id;
	state->transaction.identity.cookie = 0xa72000f1;
	state->transaction.provider_identity.generation = 1;
	state->transaction.provider_identity.cookie = 0xa72000f0;
	mt6797_cpu9_binder_test_active = state;
	mt6797_a72_cpu9_binder_test_init(binder,
					 &mt6797_cpu9_binder_test_backend);
}

static void mt6797_cpu9_binder_success_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_binder_test_request();
	struct mt6797_cpu9_binder_test_state state;
	struct mt6797_a72_cpu9_binder binder;
	int ret;

	mt6797_cpu9_binder_test_reset(&binder, &state);
	ret = mt6797_a72_cpu9_binder_test_prepare(&binder, &request);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_cpu9_binder_test_preflight(&binder, 9, CPUHP_ONLINE);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_cpu9_binder_test_validate(&binder, 9, 0, CPUHP_ONLINE);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_cpu9_binder_test_boot(
		&binder, 9, mt6797_cpu9_binder_test_cpu_boot);
	KUNIT_ASSERT_EQ(test, ret, 0);
	state.cpu9_online = true;
	ret = mt6797_a72_cpu9_binder_test_secondary_complete(&binder, 9);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_cpu9_binder_test_complete(&binder, 9, CPUHP_ONLINE);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.ledger_checkpoint_calls, 11U);
	KUNIT_EXPECT_EQ(test, state.cpu8_attempt_id, request.cpu8_attempt_id);
	KUNIT_EXPECT_EQ(test, state.cpu9_attempt_id, request.cpu9_attempt_id);
	KUNIT_EXPECT_EQ(test, state.preflight_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.claim_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.cpu_on_begin_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.p30e_prepare_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.p30e_arm_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.cpu_boot_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.p30e_readback_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.ipi_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.publish_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.finalize_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.reject_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.terminal_phase,
			(u32)GEMINI_TRANSITION_LEDGER_TERMINAL);
	KUNIT_EXPECT_EQ(test, state.terminal_stage,
			(u32)GEMINI_CPU9_LEDGER_MEMBERSHIP);
	KUNIT_EXPECT_EQ(test, state.terminal_value,
			(u32)GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF);
	KUNIT_EXPECT_EQ(test, binder.result.cpu_requests, 1U);
	KUNIT_EXPECT_EQ(test, binder.result.cpu_off_requests, 0U);
	KUNIT_EXPECT_EQ(test, binder.result.retries, 0U);
}

static void mt6797_cpu9_binder_dispatch_guards_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_binder_test_request();
	struct mt6797_cpu9_binder_test_state state;
	struct mt6797_a72_cpu9_binder binder;
	int ret;

	mt6797_cpu9_binder_test_reset(&binder, &state);
	ret = mt6797_a72_cpu9_binder_test_preflight(&binder, 9, CPUHP_ONLINE);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	ret = mt6797_a72_cpu9_binder_test_validate(&binder, 9, 0, CPUHP_ONLINE);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	ret = mt6797_a72_cpu9_binder_test_boot(
		&binder, 9, mt6797_cpu9_binder_test_cpu_boot);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_cpu9_binder_test_prepare(&binder, &request),
			0);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_cpu9_binder_test_preflight(&binder, 8,
							      CPUHP_ONLINE),
			-EINVAL);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_cpu9_binder_test_preflight(&binder, 9,
							      CPUHP_AP_ONLINE),
			-EINVAL);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_cpu9_binder_test_validate(&binder, 9, 1,
							     CPUHP_ONLINE),
			-EPERM);
	KUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.cpu_boot_calls, 0U);
}

static void mt6797_cpu9_binder_prepare_guards_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_request request;
	struct mt6797_cpu9_binder_test_state state;
	struct mt6797_a72_cpu9_binder binder;
	int ret;

	mt6797_cpu9_binder_test_reset(&binder, &state);
	request = mt6797_cpu9_binder_test_request();
	request.cpu8_terminal_exact = false;
	ret = mt6797_a72_cpu9_binder_test_prepare(&binder, &request);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	request = mt6797_cpu9_binder_test_request();
	request.retained_mask &= ~MT6797_A72_CPU9_RETAINED_PROVIDER;
	ret = mt6797_a72_cpu9_binder_test_prepare(&binder, &request);
	KUNIT_EXPECT_EQ(test, ret, -EPERM);
	request = mt6797_cpu9_binder_test_request();
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_cpu9_binder_test_prepare(&binder, &request),
			0);
	ret = mt6797_a72_cpu9_binder_test_prepare(&binder, &request);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
	KUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.cpu_boot_calls, 0U);
}

static void mt6797_cpu9_binder_claim_failure_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_binder_test_request();
	struct mt6797_cpu9_binder_test_state state;
	struct mt6797_a72_cpu9_binder binder;
	int ret;

	mt6797_cpu9_binder_test_reset(&binder, &state);
	state.failure = MT6797_CPU9_BINDER_FAIL_CLAIM;
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_cpu9_binder_test_prepare(&binder, &request),
			0);
	ret = mt6797_a72_cpu9_binder_test_boot(
		&binder, 9, mt6797_cpu9_binder_test_cpu_boot);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.claim_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.cpu_boot_calls, 0U);
	ret = mt6797_a72_cpu9_binder_test_boot(
		&binder, 9, mt6797_cpu9_binder_test_cpu_boot);
	KUNIT_EXPECT_EQ(test, ret, -EALREADY);
}

static void mt6797_cpu9_binder_cpu_on_failures_test(struct kunit *test)
{
	static const enum mt6797_cpu9_binder_test_failure failures[] = {
		MT6797_CPU9_BINDER_FAIL_P30E_PREPARE,
		MT6797_CPU9_BINDER_FAIL_CPU_ON_BEGIN,
		MT6797_CPU9_BINDER_FAIL_P30E_ARM,
		MT6797_CPU9_BINDER_FAIL_CPU_BOOT,
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(failures); i++) {
		struct mt6797_a72_cpu9_executor_request request =
			mt6797_cpu9_binder_test_request();
		struct mt6797_cpu9_binder_test_state state;
		struct mt6797_a72_cpu9_binder binder;
		int ret;

		mt6797_cpu9_binder_test_reset(&binder, &state);
		state.failure = failures[i];
		KUNIT_ASSERT_EQ(test,
				mt6797_a72_cpu9_binder_test_prepare(&binder,
								    &request),
				0);
		ret = mt6797_a72_cpu9_binder_test_boot(
			&binder, 9, mt6797_cpu9_binder_test_cpu_boot);
		KUNIT_EXPECT_EQ(test, ret, -EIO);
		KUNIT_EXPECT_EQ(test, binder.result.terminal,
				(enum mt6797_a72_cpu9_executor_terminal)
					MT6797_A72_CPU9_FAULT_RETAIN_CPU8);
		KUNIT_EXPECT_EQ(test, binder.result.cpu_requests, 1U);
		KUNIT_EXPECT_EQ(test, binder.result.cpu_off_requests, 0U);
		KUNIT_EXPECT_EQ(test, binder.result.retries, 0U);
		KUNIT_EXPECT_EQ(test, state.terminal_stage,
				(u32)GEMINI_CPU9_LEDGER_CPU_ON);
		KUNIT_EXPECT_EQ(test, state.terminal_value,
				(u32)GEMINI_CPU9_LEDGER_CPU_ON_FAILURE);
	}
}

static void mt6797_cpu9_binder_secondary_failure_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_binder_test_request();
	struct mt6797_cpu9_binder_test_state state;
	struct mt6797_a72_cpu9_binder binder;
	bool publish_p32 = false;
	int ret;

	mt6797_cpu9_binder_test_reset(&binder, &state);
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_cpu9_binder_test_prepare(&binder, &request),
			0);
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_cpu9_binder_test_boot(
				&binder, 9, mt6797_cpu9_binder_test_cpu_boot),
			0);
	state.cpu9_online = true;
	state.failure = MT6797_CPU9_BINDER_FAIL_P30E_READBACK;
	ret = mt6797_a72_cpu9_binder_test_secondary_complete(&binder, 9);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, state.p30e_readback_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.terminal_stage,
			(u32)GEMINI_CPU9_LEDGER_ONLINE_WAIT);
	KUNIT_EXPECT_EQ(test, state.terminal_value,
			(u32)GEMINI_CPU9_LEDGER_ONLINE_WAIT_FAILURE);
	ret = mt6797_a72_cpu9_binder_test_failure(&binder, 9, -EIO,
						  &publish_p32);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, publish_p32);
	KUNIT_EXPECT_EQ(test, state.p30e_readback_calls, 1U);
	KUNIT_EXPECT_EQ(test, binder.result.cpu_off_requests, 0U);
	KUNIT_EXPECT_EQ(test, binder.result.retries, 0U);
}

static void mt6797_cpu9_binder_completion_failures_test(struct kunit *test)
{
	static const enum mt6797_cpu9_binder_test_failure failures[] = {
		MT6797_CPU9_BINDER_FAIL_IPI,
		MT6797_CPU9_BINDER_FAIL_PUBLISH,
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(failures); i++) {
		struct mt6797_a72_cpu9_executor_request request =
			mt6797_cpu9_binder_test_request();
		struct mt6797_cpu9_binder_test_state state;
		struct mt6797_a72_cpu9_binder binder;
		int ret;

		mt6797_cpu9_binder_test_reset(&binder, &state);
		KUNIT_ASSERT_EQ(test,
				mt6797_a72_cpu9_binder_test_prepare(&binder,
								    &request),
				0);
		KUNIT_ASSERT_EQ(test,
				mt6797_a72_cpu9_binder_test_boot(
					&binder, 9,
					mt6797_cpu9_binder_test_cpu_boot),
				0);
		state.cpu9_online = true;
		KUNIT_ASSERT_EQ(test,
				mt6797_a72_cpu9_binder_test_secondary_complete(
					&binder, 9),
				0);
		state.failure = failures[i];
		ret = mt6797_a72_cpu9_binder_test_complete(&binder, 9,
							   CPUHP_ONLINE);
		KUNIT_EXPECT_EQ(test, ret, -EIO);
		KUNIT_EXPECT_EQ(test, binder.result.terminal,
				(enum mt6797_a72_cpu9_executor_terminal)
					MT6797_A72_CPU9_FAULT_RETAIN_CPU8);
		KUNIT_EXPECT_EQ(test, binder.result.cpu_off_requests, 0U);
		KUNIT_EXPECT_EQ(test, binder.result.retries, 0U);
		KUNIT_EXPECT_EQ(test, state.terminal_value,
				(u32)GEMINI_CPU9_LEDGER_IPI_FAILURE);
	}
}

static void mt6797_cpu9_binder_failure_dispatch_test(struct kunit *test)
{
	struct mt6797_a72_cpu9_executor_request request =
		mt6797_cpu9_binder_test_request();
	struct mt6797_cpu9_binder_test_state state;
	struct mt6797_a72_cpu9_binder binder;
	bool publish_p32 = false;
	int ret;

	mt6797_cpu9_binder_test_reset(&binder, &state);
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_cpu9_binder_test_prepare(&binder, &request),
			0);
	KUNIT_ASSERT_EQ(test,
			mt6797_a72_cpu9_binder_test_boot(
				&binder, 9, mt6797_cpu9_binder_test_cpu_boot),
			0);
	ret = mt6797_a72_cpu9_binder_test_failure(&binder, 9, -ETIMEDOUT,
						  &publish_p32);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, publish_p32);
	KUNIT_EXPECT_EQ(test, binder.result.last_stage,
			(enum mt6797_a72_cpu9_executor_stage)
				MT6797_A72_CPU9_STAGE_ONLINE_WAIT);
	KUNIT_EXPECT_EQ(test, binder.result.terminal,
			(enum mt6797_a72_cpu9_executor_terminal)
				MT6797_A72_CPU9_FAULT_RETAIN_CPU8);
	KUNIT_EXPECT_EQ(test, state.p30e_readback_calls, 1U);
	KUNIT_EXPECT_EQ(test, state.terminal_value,
			(u32)GEMINI_CPU9_LEDGER_ONLINE_WAIT_FAILURE);
	KUNIT_EXPECT_EQ(test, binder.result.cpu_off_requests, 0U);
	KUNIT_EXPECT_EQ(test, binder.result.retries, 0U);
}

static struct kunit_case mt6797_cpu9_binder_test_cases[] = {
	KUNIT_CASE(mt6797_cpu9_binder_success_test),
	KUNIT_CASE(mt6797_cpu9_binder_dispatch_guards_test),
	KUNIT_CASE(mt6797_cpu9_binder_prepare_guards_test),
	KUNIT_CASE(mt6797_cpu9_binder_claim_failure_test),
	KUNIT_CASE(mt6797_cpu9_binder_cpu_on_failures_test),
	KUNIT_CASE(mt6797_cpu9_binder_secondary_failure_test),
	KUNIT_CASE(mt6797_cpu9_binder_completion_failures_test),
	KUNIT_CASE(mt6797_cpu9_binder_failure_dispatch_test),
	{},
};

static struct kunit_suite mt6797_cpu9_binder_test_suite = {
	.name = "mt6797-a72-cpu9-binder",
	.test_cases = mt6797_cpu9_binder_test_cases,
};

kunit_test_suite(mt6797_cpu9_binder_test_suite);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("KUnit tests for the MT6797 retained-cluster CPU9 binder");
