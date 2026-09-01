// SPDX-License-Identifier: GPL-2.0-only
/* One-shot CPU9 admission chained after exact same-boot CPU8 success. */

#include <linux/bitops.h>
#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-cpu9-admission-controller-internal.h"

static bool mt6797_a72_cpu9_admission_ops_valid(
	const struct mt6797_a72_cpu9_admission_ops *ops)
{
	return ops && ops->run_cpu8 && ops->cpu8_proof && ops->ready_token &&
	       ops->derive_cpu9 && ops->publish_cpu9 && ops->prepare_cpu9 &&
	       ops->add_cpu;
}

static bool mt6797_a72_cpu9_admission_proof_valid(
	const struct mt6797_a72_cpu9_admission_cpu8_proof *proof)
{
	return proof && proof->attempt_id && proof->cpu_requests == 1 &&
	       proof->lifecycle_terminal && proof->terminal_exact &&
	       proof->membership_published && proof->p27_retained &&
	       proof->provider_retained && proof->cpu8_online &&
	       !proof->cpu9_online;
}

static bool mt6797_a72_cpu9_admission_transaction_valid(
	const struct mt6797_a72_transaction *transaction, bool published)
{
	const struct mt6797_a72_call_budgets *budgets;

	if (!transaction)
		return false;
	budgets = &transaction->budgets;
	return transaction->valid && transaction->a36_valid &&
	       transaction->p30_token_valid &&
	       transaction->p17_p18_published == published &&
	       transaction->identity.abi == MT6797_A72_TRANSACTION_ABI &&
	       transaction->identity.owner ==
		       ARM64_LATE_CPU_STARTUP_OWNER_MEMBERSHIP &&
	       transaction->identity.operation ==
		       ARM64_LATE_CPU_STARTUP_OP_CPU9_UP &&
	       transaction->identity.target_cpu ==
		       MT6797_A72_CPU9_EXECUTOR_CPU9 &&
	       transaction->identity.cpuhp_target == CPUHP_ONLINE &&
	       transaction->identity.target_mpidr == 0x201 &&
	       transaction->identity.generation && transaction->identity.cookie &&
	       transaction->provider_identity.generation &&
	       transaction->provider_identity.cookie &&
	       budgets->preparation == MT6797_A72_BUDGET_NONE &&
	       budgets->provider_acquire == MT6797_A72_BUDGET_NONE &&
	       budgets->postprovider_preparation == MT6797_A72_BUDGET_NONE &&
	       budgets->cpu_on == MT6797_A72_BUDGET_AVAILABLE &&
	       budgets->affinity == MT6797_A72_BUDGET_NONE &&
	       budgets->provider_release == MT6797_A72_BUDGET_NONE &&
	       budgets->provider_abort == MT6797_A72_BUDGET_NONE &&
	       !transaction->p27_valid && !transaction->provider_acquire_valid &&
	       !transaction->provider_rejection_valid &&
	       !transaction->provider_abort_valid && !transaction->p28_valid &&
	       !transaction->p29_valid && !transaction->p32_valid;
}

static int mt6797_a72_cpu9_admission_terminal(
	struct mt6797_a72_cpu9_admission_state *state, u32 stage, int ret)
{
	state->failure_stage = stage;
	state->operation_ret = ret;
	return ret;
}

void mt6797_a72_cpu9_admission_state_init(
	struct mt6797_a72_cpu9_admission_state *state)
{
	memset(state, 0, sizeof(*state));
	atomic_set(&state->consumed, 0);
	state->cpu8_ret = -EINPROGRESS;
	state->cpu8_proof_ret = -EINPROGRESS;
	state->operation_ret = -EINPROGRESS;
}

int mt6797_a72_cpu9_admission_run(
	struct mt6797_a72_cpu9_admission_state *state,
	const struct mt6797_a72_cpu9_admission_ops *ops, void *context)
{
	struct mt6797_a72_cpu9_admission_cpu8_proof proof = {};
	const struct arm64_late_cpu_ready_token *ready;
	int ret;

	if (!state || !mt6797_a72_cpu9_admission_ops_valid(ops))
		return -EINVAL;
	if (atomic_cmpxchg(&state->consumed, 0, 1))
		return -EALREADY;

	state->cpu8_ret = ops->run_cpu8(context);
	if (state->cpu8_ret)
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_CPU8,
			state->cpu8_ret);

	state->cpu8_proof_ret = ops->cpu8_proof(context, &proof);
	if (state->cpu8_proof_ret ||
	    !mt6797_a72_cpu9_admission_proof_valid(&proof))
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_CPU8_PROOF,
			state->cpu8_proof_ret ?: -EPROTO);
	state->cpu8_requests = proof.cpu_requests;

	ready = ops->ready_token(context);
	if (!ready)
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_READY_TOKEN,
			-EAGAIN);

	ret = ops->derive_cpu9(context, ready, &state->cpu9_transaction,
			       &state->derive_stage);
	if (ret || !mt6797_a72_cpu9_admission_transaction_valid(
			   &state->cpu9_transaction, false))
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_DERIVE,
			ret ?: -EPROTO);
	if (state->cpu9_transaction.identity.generation == proof.attempt_id)
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_DERIVE,
			-EPROTO);

	ret = ops->publish_cpu9(context, &state->cpu9_transaction);
	if (ret || !mt6797_a72_cpu9_admission_transaction_valid(
			   &state->cpu9_transaction, true))
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_PUBLISH,
			ret ?: -EPROTO);

	state->cpu9_request = (struct mt6797_a72_cpu9_executor_request){
		.cpu = MT6797_A72_CPU9_EXECUTOR_CPU9,
		.cpu8_attempt_id = proof.attempt_id,
		.cpu9_attempt_id =
			state->cpu9_transaction.identity.generation,
		.members = BIT(0),
		.retained_mask = MT6797_A72_CPU9_RETAINED_REQUIRED,
		.cpu8_terminal_exact = true,
		.cpu8_membership_published = true,
		.provider_retained = true,
		.cpu8_online = true,
		.cpu9_online = false,
	};
	ret = ops->prepare_cpu9(context, &state->cpu9_request);
	if (ret)
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_PREPARE, ret);

	state->cpu9_requests = 1;
	ret = ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9);
	if (ret)
		return mt6797_a72_cpu9_admission_terminal(
			state, MT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,
			ret);
	return mt6797_a72_cpu9_admission_terminal(
		state, MT6797_A72_CPU9_ADMISSION_FAILURE_NONE, 0);
}
