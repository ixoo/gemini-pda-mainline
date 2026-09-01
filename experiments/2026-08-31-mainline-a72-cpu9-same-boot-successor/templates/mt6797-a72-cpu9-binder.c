// SPDX-License-Identifier: GPL-2.0-only
/* Production dispatch adapter for one retained-cluster MT6797 CPU9 transition. */

#include <linux/errno.h>
#include <linux/gemini_cpu9_transition_ledger.h>
#include <linux/gemini_transition_ledger.h>
#include <linux/mutex.h>
#include <linux/string.h>

#include <asm/late_cpu_profile.h>

#include "mt6797-a72-cpu9-binder-internal.h"

static DEFINE_MUTEX(mt6797_a72_cpu9_binder_lock);

static bool mt6797_a72_cpu9_binder_backend_valid(
	const struct mt6797_a72_cpu9_binder_backend_ops *ops)
{
	return ops && ops->ledger_begin && ops->ledger_checkpoint &&
	       ops->membership_preflight && ops->membership_claim &&
	       ops->membership_reject && ops->membership_begin_cpu_on &&
	       ops->p30e_prepare && ops->p30e_arm && ops->p30e_readback &&
	       ops->membership_publish_success &&
	       ops->membership_finalize_success && ops->cpu_online &&
	       ops->ipi_call;
}

static bool mt6797_a72_cpu9_binder_request_valid(
	const struct mt6797_a72_cpu9_executor_request *request)
{
	return request && request->cpu == MT6797_A72_CPU9_EXECUTOR_CPU9 &&
	       request->cpu8_attempt_id && request->cpu9_attempt_id &&
	       request->cpu8_attempt_id != request->cpu9_attempt_id &&
	       request->members == BIT(0) &&
	       request->retained_mask == MT6797_A72_CPU9_RETAINED_REQUIRED &&
	       request->cpu8_terminal_exact &&
	       request->cpu8_membership_published &&
	       request->provider_retained && request->cpu8_online &&
	       !request->cpu9_online;
}

static int mt6797_a72_cpu9_binder_stage(
	struct mt6797_a72_cpu9_binder *binder,
	const struct mt6797_a72_cpu9_executor_request *request)
{
	if (!binder || !mt6797_a72_cpu9_binder_backend_valid(binder->backend))
		return -EINVAL;
	if (!mt6797_a72_cpu9_binder_request_valid(request))
		return -EPERM;
	if (atomic_read_acquire(&binder->prepared))
		return -EALREADY;
	binder->request = *request;
	if (atomic_cmpxchg(&binder->prepared, 0, 1))
		return -EALREADY;
	return 0;
}

static int
mt6797_a72_cpu9_binder_check_public(struct mt6797_a72_cpu9_binder *binder,
				    unsigned int cpu, int tasks_frozen,
				    enum cpuhp_state target, bool preflight)
{
	if (!binder || !mt6797_a72_cpu9_binder_backend_valid(binder->backend))
		return -EINVAL;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || target != CPUHP_ONLINE)
		return -EINVAL;
	if (tasks_frozen)
		return -EPERM;
	if (!atomic_read_acquire(&binder->prepared))
		return -EAGAIN;
	return preflight ? binder->backend->membership_preflight() : 0;
}

static void mt6797_a72_cpu9_binder_p30e_request(
	const struct mt6797_a72_p30e_handoff *handoff,
	struct arm64_mt6797_a72_p30e_request *request)
{
	memset(request, 0, sizeof(*request));
	memcpy(request->boot_identity, handoff->wire_boot_identity,
	       sizeof(request->boot_identity));
	memcpy(request->target_boot_identity, handoff->target_boot_identity,
	       sizeof(request->target_boot_identity));
	request->slot_pa = handoff->slot_pa;
	request->entry_pa = handoff->entry_pa;
	request->operation = handoff->operation;
	request->generation = handoff->generation;
	request->cookie = handoff->cookie;
}

static int mt6797_a72_cpu9_binder_p30e_prepare(
	const struct mt6797_a72_transaction *transaction,
	struct mt6797_a72_p30e_handoff *handoff)
{
	const struct arm64_late_cpu_ready_token *ready;

	ready = arm64_get_late_cpu_ready_token();
	return ready ? mt6797_a72_membership_prepare_p30e_handoff(
			       transaction, ready, handoff) :
		       -EAGAIN;
}

static int
mt6797_a72_cpu9_binder_p30e_arm(unsigned int cpu,
				const struct mt6797_a72_p30e_handoff *handoff)
{
	struct arm64_mt6797_a72_p30e_request request;

	if (!handoff || cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    handoff->target_cpu != cpu ||
	    handoff->operation != ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP)
		return -EPERM;
	mt6797_a72_cpu9_binder_p30e_request(handoff, &request);
	return arm64_mt6797_a72_p30e_arm(cpu, &request);
}

static int mt6797_a72_cpu9_binder_p30e_readback(
	unsigned int cpu, const struct mt6797_a72_p30e_handoff *handoff,
	struct arm64_mt6797_a72_p30e_wire *copy)
{
	struct arm64_mt6797_a72_p30e_request request;

	if (!handoff || !copy || cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    handoff->target_cpu != cpu ||
	    handoff->operation != ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP)
		return -EPERM;
	mt6797_a72_cpu9_binder_p30e_request(handoff, &request);
	return arm64_mt6797_a72_p30e_readback(cpu, &request, copy);
}

static bool mt6797_a72_cpu9_binder_cpu_online(unsigned int cpu)
{
	return cpu_online(cpu);
}

static int mt6797_a72_cpu9_binder_ipi_call(unsigned int cpu,
					   smp_call_func_t func, void *info,
					   int wait)
{
	return smp_call_function_single(cpu, func, info, wait);
}

static const struct mt6797_a72_cpu9_binder_backend_ops
	mt6797_a72_cpu9_binder_production_backend = {
		.ledger_begin = gemini_cpu9_ledger_begin,
		.ledger_checkpoint = gemini_cpu9_ledger_checkpoint,
		.membership_preflight = mt6797_a72_membership_preflight_cpu9,
		.membership_claim = mt6797_a72_membership_claim_cpu9,
		.membership_reject = mt6797_a72_membership_reject_cpu9,
		.membership_begin_cpu_on = mt6797_a72_membership_begin_cpu9_on,
		.p30e_prepare = mt6797_a72_cpu9_binder_p30e_prepare,
		.p30e_arm = mt6797_a72_cpu9_binder_p30e_arm,
		.p30e_readback = mt6797_a72_cpu9_binder_p30e_readback,
		.membership_publish_success =
			mt6797_a72_membership_publish_cpu9_success,
		.membership_finalize_success =
			mt6797_a72_membership_finalize_cpu9_success,
		.cpu_online = mt6797_a72_cpu9_binder_cpu_online,
		.ipi_call = mt6797_a72_cpu9_binder_ipi_call,
	};

static struct mt6797_a72_cpu9_binder mt6797_a72_cpu9_binder = {
	.backend = &mt6797_a72_cpu9_binder_production_backend,
	.executor = MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT,
	.prepared = ATOMIC_INIT(0),
	.boot_claimed = ATOMIC_INIT(0),
};

static int mt6797_a72_cpu9_binder_checkpoint(
	void *context, enum mt6797_a72_cpu9_executor_phase phase,
	enum mt6797_a72_cpu9_executor_stage stage,
	const struct mt6797_a72_cpu9_executor_result *result)
{
	struct mt6797_a72_cpu9_binder *binder = context;
	int ret;

	(void)result;
	static_assert(MT6797_A72_CPU9_PHASE_BEFORE ==
		      GEMINI_TRANSITION_LEDGER_BEFORE);
	static_assert(MT6797_A72_CPU9_PHASE_AFTER ==
		      GEMINI_TRANSITION_LEDGER_AFTER);
	static_assert(MT6797_A72_CPU9_STAGE_PRESTATE ==
		      GEMINI_CPU9_LEDGER_PRESTATE);
	static_assert(MT6797_A72_CPU9_STAGE_MEMBERSHIP ==
		      GEMINI_CPU9_LEDGER_MEMBERSHIP);
	if (!binder->ledger_begun) {
		if (phase != MT6797_A72_CPU9_PHASE_BEFORE ||
		    stage != MT6797_A72_CPU9_STAGE_PRESTATE)
			return -EPROTO;
		ret = binder->backend->ledger_begin(
			binder->request.cpu8_attempt_id,
			binder->request.cpu9_attempt_id);
		if (ret)
			return ret;
		binder->ledger_begun = true;
	}
	return binder->backend->ledger_checkpoint(
		binder->request.cpu9_attempt_id, phase, stage, 0);
}

static int mt6797_a72_cpu9_binder_prestate(
	void *context, const struct mt6797_a72_cpu9_executor_request *request)
{
	struct mt6797_a72_cpu9_binder *binder = context;
	const struct mt6797_a72_transaction *transaction = &binder->transaction;

	if (!request || memcmp(request, &binder->request, sizeof(*request)) ||
	    !transaction->valid || !transaction->a36_valid ||
	    !transaction->p30_token_valid || !transaction->p17_p18_published ||
	    transaction->identity.abi != MT6797_A72_TRANSACTION_ABI ||
	    transaction->identity.operation !=
		    ARM64_LATE_CPU_STARTUP_OP_CPU9_UP ||
	    transaction->identity.target_cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    transaction->identity.cpuhp_target != CPUHP_ONLINE ||
	    transaction->identity.target_mpidr !=
		    ARM64_MT6797_A72_P30E_MPIDR_CPU9 ||
	    transaction->identity.generation != request->cpu9_attempt_id ||
	    !transaction->provider_identity.generation ||
	    !transaction->provider_identity.cookie)
		return -EPERM;
	return 0;
}

static int
mt6797_a72_cpu9_binder_readback_once(struct mt6797_a72_cpu9_binder *binder,
				     unsigned int cpu)
{
	if (!binder->p30e_armed)
		return -EPROTO;
	if (binder->p30e_readback_attempted)
		return binder->p30e_readback_ret;
	binder->p30e_readback_attempted = true;
	memset(&binder->p30e_snapshot, 0, sizeof(binder->p30e_snapshot));
	binder->p30e_readback_ret = binder->backend->p30e_readback(
		cpu, &binder->p30e_handoff, &binder->p30e_snapshot);
	return binder->p30e_readback_ret;
}

static int mt6797_a72_cpu9_binder_cpu_on(void *context, unsigned int cpu)
{
	struct mt6797_a72_cpu9_binder *binder = context;
	int ret;

	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || !binder->cpu_boot)
		return -EINVAL;
	binder->p30e_prepare_attempted = true;
	binder->p30e_prepare_ret = binder->backend->p30e_prepare(
		&binder->transaction, &binder->p30e_handoff);
	if (binder->p30e_prepare_ret)
		return binder->p30e_prepare_ret;
	ret = binder->backend->membership_begin_cpu_on(&binder->transaction);
	if (ret)
		return ret;
	binder->p30e_arm_attempted = true;
	binder->p30e_arm_ret =
		binder->backend->p30e_arm(cpu, &binder->p30e_handoff);
	if (binder->p30e_arm_ret)
		return binder->p30e_arm_ret;
	binder->p30e_armed = true;
	ret = binder->cpu_boot(cpu);
	if (ret)
		mt6797_a72_cpu9_binder_readback_once(binder, cpu);
	return ret;
}

static int mt6797_a72_cpu9_binder_secondary(void *context, unsigned int cpu)
{
	struct mt6797_a72_cpu9_binder *binder = context;

	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    !binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU8) ||
	    !binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU9))
		return -EPROTO;
	return mt6797_a72_cpu9_binder_readback_once(binder, cpu);
}

static void mt6797_a72_cpu9_binder_ipi_callback(void *unused)
{
	(void)unused;
}

static int mt6797_a72_cpu9_binder_ipi(void *context, unsigned int cpu)
{
	struct mt6797_a72_cpu9_binder *binder = context;

	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    !binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU8) ||
	    !binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU9))
		return -EPROTO;
	return binder->backend->ipi_call(
		cpu, mt6797_a72_cpu9_binder_ipi_callback, NULL, 1);
}

static int mt6797_a72_cpu9_binder_membership(void *context, unsigned int cpu)
{
	struct mt6797_a72_cpu9_binder *binder = context;

	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9)
		return -EINVAL;
	return binder->backend->membership_publish_success(
		&binder->transaction);
}

static u32 mt6797_a72_cpu9_binder_terminal_value(
	const struct mt6797_a72_cpu9_executor_result *result)
{
	if (result->terminal == MT6797_A72_CPU9_ONLINE_PROOF)
		return GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF;
	switch (result->last_stage) {
	case MT6797_A72_CPU9_STAGE_PRESTATE:
		return GEMINI_CPU9_LEDGER_PRESTATE_FAILURE;
	case MT6797_A72_CPU9_STAGE_CPU_ON:
		return GEMINI_CPU9_LEDGER_CPU_ON_FAILURE;
	case MT6797_A72_CPU9_STAGE_ONLINE_WAIT:
		return GEMINI_CPU9_LEDGER_ONLINE_WAIT_FAILURE;
	case MT6797_A72_CPU9_STAGE_IPI:
	case MT6797_A72_CPU9_STAGE_MEMBERSHIP:
		return GEMINI_CPU9_LEDGER_IPI_FAILURE;
	default:
		return 0;
	}
}

static int mt6797_a72_cpu9_binder_terminal(
	void *context, const struct mt6797_a72_cpu9_executor_result *result)
{
	struct mt6797_a72_cpu9_binder *binder = context;
	u32 terminal;
	int ret;

	if (!result || result->terminal == MT6797_A72_CPU9_TERMINAL_NONE)
		return -EPROTO;
	terminal = mt6797_a72_cpu9_binder_terminal_value(result);
	if (!terminal)
		return -EPROTO;
	if (binder->ledger_begun) {
		ret = binder->backend->ledger_checkpoint(
			binder->request.cpu9_attempt_id,
			GEMINI_TRANSITION_LEDGER_TERMINAL, result->last_stage,
			terminal);
		if (ret)
			return ret;
	}
	switch (result->terminal) {
	case MT6797_A72_CPU9_REJECTED_PRESTATE:
		return binder->backend->membership_reject(&binder->transaction);
	case MT6797_A72_CPU9_FAULT_RETAIN_CPU8:
		return 0;
	case MT6797_A72_CPU9_ONLINE_PROOF:
		return binder->backend->membership_finalize_success(
			&binder->transaction);
	default:
		return -EPROTO;
	}
}

static const struct mt6797_a72_cpu9_executor_ops
	mt6797_a72_cpu9_binder_executor_ops = {
		.checkpoint = mt6797_a72_cpu9_binder_checkpoint,
		.prestate = mt6797_a72_cpu9_binder_prestate,
		.cpu_on = mt6797_a72_cpu9_binder_cpu_on,
		.secondary_complete = mt6797_a72_cpu9_binder_secondary,
		.ipi_proof = mt6797_a72_cpu9_binder_ipi,
		.membership_commit = mt6797_a72_cpu9_binder_membership,
		.terminal = mt6797_a72_cpu9_binder_terminal,
	};

static int mt6797_a72_cpu9_binder_boot(struct mt6797_a72_cpu9_binder *binder,
				       unsigned int cpu,
				       mt6797_a72_cpu_boot_fn cpu_boot)
{
	int ret;

	if (!binder || !mt6797_a72_cpu9_binder_backend_valid(binder->backend) ||
	    cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || !cpu_boot)
		return -EINVAL;
	if (!atomic_read_acquire(&binder->prepared))
		return -EAGAIN;
	if (atomic_cmpxchg(&binder->boot_claimed, 0, 1))
		return -EALREADY;
	ret = binder->backend->membership_claim(&binder->transaction);
	if (ret)
		return ret;
	binder->cpu_boot = cpu_boot;
	ret = mt6797_a72_cpu9_executor_begin(
		&binder->executor, &mt6797_a72_cpu9_binder_executor_ops, binder,
		&binder->request, &binder->result);
	if (ret && !binder->result.attempted)
		binder->backend->membership_reject(&binder->transaction);
	return ret;
}

static int
mt6797_a72_cpu9_binder_drive_secondary(struct mt6797_a72_cpu9_binder *binder,
				       unsigned int cpu)
{
	if (!binder || !mt6797_a72_cpu9_binder_backend_valid(binder->backend))
		return -EINVAL;
	return mt6797_a72_cpu9_executor_secondary(
		&binder->executor, &mt6797_a72_cpu9_binder_executor_ops, binder,
		cpu, binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU8),
		binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU9),
		&binder->result);
}

static int mt6797_a72_cpu9_binder_finish(struct mt6797_a72_cpu9_binder *binder,
					 unsigned int cpu,
					 enum cpuhp_state target)
{
	if (!binder || !mt6797_a72_cpu9_binder_backend_valid(binder->backend) ||
	    target != CPUHP_ONLINE)
		return -EINVAL;
	return mt6797_a72_cpu9_executor_complete(
		&binder->executor, &mt6797_a72_cpu9_binder_executor_ops, binder,
		cpu, binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU8),
		binder->backend->cpu_online(MT6797_A72_CPU9_EXECUTOR_CPU9),
		&binder->result);
}

static int mt6797_a72_cpu9_binder_fail(struct mt6797_a72_cpu9_binder *binder,
				       unsigned int cpu, int error,
				       bool *publish_p32)
{
	int lifecycle;

	if (!binder || !mt6797_a72_cpu9_binder_backend_valid(binder->backend) ||
	    cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || !error || !publish_p32)
		return -EINVAL;
	*publish_p32 = false;
	if (binder->p30e_armed && !binder->p30e_readback_attempted)
		mt6797_a72_cpu9_binder_readback_once(binder, cpu);
	lifecycle = atomic_read_acquire(&binder->executor.lifecycle);
	if (lifecycle != MT6797_A72_CPU9_LIFECYCLE_TERMINAL)
		mt6797_a72_cpu9_executor_fail(
			&binder->executor, &mt6797_a72_cpu9_binder_executor_ops,
			binder, cpu,
			binder->backend->cpu_online(
				MT6797_A72_CPU9_EXECUTOR_CPU8),
			binder->backend->cpu_online(
				MT6797_A72_CPU9_EXECUTOR_CPU9),
			error, &binder->result);
	*publish_p32 = binder->result.terminal ==
		       MT6797_A72_CPU9_FAULT_RETAIN_CPU8;
	return 0;
}

int mt6797_a72_cpu9_binder_prepare(
	const struct mt6797_a72_cpu9_executor_request *request)
{
	int ret;

	mutex_lock(&mt6797_a72_cpu9_binder_lock);
	ret = mt6797_a72_binder_available() ?
		      mt6797_a72_cpu9_binder_stage(&mt6797_a72_cpu9_binder,
						   request) :
		      -EAGAIN;
	mutex_unlock(&mt6797_a72_cpu9_binder_lock);
	return ret;
}

int mt6797_a72_cpu9_binder_preflight(unsigned int cpu, enum cpuhp_state target)
{
	int ret;

	mutex_lock(&mt6797_a72_cpu9_binder_lock);
	ret = mt6797_a72_cpu9_binder_check_public(&mt6797_a72_cpu9_binder, cpu,
						  0, target, true);
	mutex_unlock(&mt6797_a72_cpu9_binder_lock);
	return ret;
}

int mt6797_a72_cpu9_binder_validate(unsigned int cpu, int tasks_frozen,
				    enum cpuhp_state target)
{
	int ret;

	/* Leaf validation runs under the generic CPU-map lock and cannot sleep. */
	ret = mt6797_a72_cpu9_binder_check_public(&mt6797_a72_cpu9_binder, cpu,
						  tasks_frozen, target, false);
	return ret;
}

int mt6797_a72_cpu9_binder_cpu_boot(unsigned int cpu,
				    mt6797_a72_cpu_boot_fn cpu_boot)
{
	int ret;

	mutex_lock(&mt6797_a72_cpu9_binder_lock);
	ret = mt6797_a72_cpu9_binder_boot(&mt6797_a72_cpu9_binder, cpu,
					  cpu_boot);
	mutex_unlock(&mt6797_a72_cpu9_binder_lock);
	return ret;
}

int mt6797_a72_cpu9_binder_secondary_complete(unsigned int cpu)
{
	int ret;

	mutex_lock(&mt6797_a72_cpu9_binder_lock);
	ret = mt6797_a72_cpu9_binder_drive_secondary(&mt6797_a72_cpu9_binder,
						     cpu);
	mutex_unlock(&mt6797_a72_cpu9_binder_lock);
	return ret;
}

int mt6797_a72_cpu9_binder_complete(unsigned int cpu, enum cpuhp_state target)
{
	int ret;

	mutex_lock(&mt6797_a72_cpu9_binder_lock);
	ret = mt6797_a72_cpu9_binder_finish(&mt6797_a72_cpu9_binder, cpu,
					    target);
	mutex_unlock(&mt6797_a72_cpu9_binder_lock);
	return ret;
}

int mt6797_a72_cpu9_binder_failure(unsigned int cpu, int error,
				   bool *publish_p32)
{
	int ret;

	mutex_lock(&mt6797_a72_cpu9_binder_lock);
	ret = mt6797_a72_cpu9_binder_fail(&mt6797_a72_cpu9_binder, cpu, error,
					  publish_p32);
	mutex_unlock(&mt6797_a72_cpu9_binder_lock);
	return ret;
}

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST)
void mt6797_a72_cpu9_binder_test_init(
	struct mt6797_a72_cpu9_binder *binder,
	const struct mt6797_a72_cpu9_binder_backend_ops *backend)
{
	memset(binder, 0, sizeof(*binder));
	binder->backend = backend;
	atomic_set(&binder->executor.consumed, 0);
	atomic_set(&binder->executor.lifecycle, MT6797_A72_CPU9_LIFECYCLE_IDLE);
	atomic_set(&binder->prepared, 0);
	atomic_set(&binder->boot_claimed, 0);
}

int mt6797_a72_cpu9_binder_test_prepare(
	struct mt6797_a72_cpu9_binder *binder,
	const struct mt6797_a72_cpu9_executor_request *request)
{
	return mt6797_a72_cpu9_binder_stage(binder, request);
}

int mt6797_a72_cpu9_binder_test_preflight(struct mt6797_a72_cpu9_binder *binder,
					  unsigned int cpu,
					  enum cpuhp_state target)
{
	return mt6797_a72_cpu9_binder_check_public(binder, cpu, 0, target,
						   true);
}

int mt6797_a72_cpu9_binder_test_validate(struct mt6797_a72_cpu9_binder *binder,
					 unsigned int cpu, int tasks_frozen,
					 enum cpuhp_state target)
{
	return mt6797_a72_cpu9_binder_check_public(binder, cpu, tasks_frozen,
						   target, false);
}

int mt6797_a72_cpu9_binder_test_boot(struct mt6797_a72_cpu9_binder *binder,
				     unsigned int cpu,
				     mt6797_a72_cpu_boot_fn cpu_boot)
{
	return mt6797_a72_cpu9_binder_boot(binder, cpu, cpu_boot);
}

int mt6797_a72_cpu9_binder_test_secondary_complete(
	struct mt6797_a72_cpu9_binder *binder, unsigned int cpu)
{
	return mt6797_a72_cpu9_binder_drive_secondary(binder, cpu);
}

int mt6797_a72_cpu9_binder_test_complete(struct mt6797_a72_cpu9_binder *binder,
					 unsigned int cpu,
					 enum cpuhp_state target)
{
	return mt6797_a72_cpu9_binder_finish(binder, cpu, target);
}

int mt6797_a72_cpu9_binder_test_failure(struct mt6797_a72_cpu9_binder *binder,
					unsigned int cpu, int error,
					bool *publish_p32)
{
	return mt6797_a72_cpu9_binder_fail(binder, cpu, error, publish_p32);
}
#endif
