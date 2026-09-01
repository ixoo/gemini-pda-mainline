// SPDX-License-Identifier: GPL-2.0-only
/* Hardware-free coordinator for one retained-cluster MT6797 CPU9 transition. */

#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-cpu9-executor-internal.h"

static bool
mt6797_a72_cpu9_executor_ops_valid(
	const struct mt6797_a72_cpu9_executor_ops *ops)
{
	return ops && ops->checkpoint && ops->prestate && ops->cpu_on &&
		ops->secondary_complete && ops->ipi_proof &&
		ops->membership_commit && ops->terminal;
}

static bool
mt6797_a72_cpu9_executor_request_valid(
	const struct mt6797_a72_cpu9_executor_request *request)
{
	return request->cpu8_attempt_id && request->cpu9_attempt_id &&
		request->cpu8_attempt_id != request->cpu9_attempt_id &&
		request->members == BIT(0) &&
		request->retained_mask == MT6797_A72_CPU9_RETAINED_REQUIRED &&
		request->cpu8_terminal_exact &&
		request->cpu8_membership_published &&
		request->provider_retained && request->cpu8_online &&
		!request->cpu9_online;
}

static int
mt6797_a72_cpu9_executor_terminal(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	struct mt6797_a72_cpu9_executor_result *result,
	enum mt6797_a72_cpu9_executor_terminal terminal, int return_errno)
{
	int ret;

	result->terminal = terminal;
	result->retained_mask = MT6797_A72_CPU9_RETAINED_REQUIRED;
	result->terminal_commits++;
	ret = ops->terminal(context, result);
	if (ret) {
		result->checkpoint_errno = ret;
		if (terminal == MT6797_A72_CPU9_ONLINE_PROOF) {
			result->terminal = MT6797_A72_CPU9_FAULT_RETAIN_CPU8;
			result->stage_errno = ret;
			return_errno = ret;
		}
	}
	atomic_set_release(&controller->lifecycle,
			   MT6797_A72_CPU9_LIFECYCLE_TERMINAL);
	return return_errno;
}

static int
mt6797_a72_cpu9_executor_stage_fault(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	struct mt6797_a72_cpu9_executor_result *result,
	enum mt6797_a72_cpu9_executor_stage stage, int error)
{
	enum mt6797_a72_cpu9_executor_terminal terminal;

	result->last_stage = stage;
	result->stage_errno = error;
	terminal = stage == MT6797_A72_CPU9_STAGE_PRESTATE ?
		MT6797_A72_CPU9_REJECTED_PRESTATE :
		MT6797_A72_CPU9_FAULT_RETAIN_CPU8;
	return mt6797_a72_cpu9_executor_terminal(controller, ops, context,
						 result, terminal, error);
}

static int
mt6797_a72_cpu9_executor_checkpoint(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	struct mt6797_a72_cpu9_executor_result *result,
	enum mt6797_a72_cpu9_executor_phase phase,
	enum mt6797_a72_cpu9_executor_stage stage)
{
	int ret;

	result->last_stage = stage;
	result->checkpoints++;
	ret = ops->checkpoint(context, phase, stage, result);
	if (!ret)
		return 0;
	result->checkpoint_errno = ret;
	return mt6797_a72_cpu9_executor_stage_fault(controller, ops, context,
						    result, stage, ret);
}

int mt6797_a72_cpu9_executor_begin(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	const struct mt6797_a72_cpu9_executor_request *request,
	struct mt6797_a72_cpu9_executor_result *result)
{
	int ret;

	if (!result)
		return -EINVAL;
	if (controller &&
	    (atomic_read_acquire(&controller->lifecycle) !=
	     MT6797_A72_CPU9_LIFECYCLE_IDLE ||
	     atomic_read_acquire(&controller->consumed)))
		return -EALREADY;
	memset(result, 0, sizeof(*result));
	result->last_stage = MT6797_A72_CPU9_STAGE_NONE;
	result->terminal = MT6797_A72_CPU9_REJECTED_PRESTATE;
	if (!controller || !request || !mt6797_a72_cpu9_executor_ops_valid(ops))
		return -EINVAL;
	result->cpu8_online = request->cpu8_online;
	result->cpu9_online = request->cpu9_online;
	if (request->cpu != MT6797_A72_CPU9_EXECUTOR_CPU9)
		return -EINVAL;
	if (!mt6797_a72_cpu9_executor_request_valid(request))
		return -EPERM;
	if (atomic_cmpxchg(&controller->consumed, 0, 1))
		return -EALREADY;
	if (atomic_cmpxchg(&controller->lifecycle,
			   MT6797_A72_CPU9_LIFECYCLE_IDLE,
			   MT6797_A72_CPU9_LIFECYCLE_STARTING) !=
	    MT6797_A72_CPU9_LIFECYCLE_IDLE)
		return -EALREADY;
	result->attempted = true;
	result->terminal = MT6797_A72_CPU9_TERMINAL_NONE;

	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_BEFORE, MT6797_A72_CPU9_STAGE_PRESTATE);
	if (ret)
		return ret;
	ret = ops->prestate(context, request);
	if (ret)
		return mt6797_a72_cpu9_executor_stage_fault(
			controller, ops, context, result,
			MT6797_A72_CPU9_STAGE_PRESTATE, ret);
	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_AFTER, MT6797_A72_CPU9_STAGE_PRESTATE);
	if (ret)
		return ret;

	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_BEFORE, MT6797_A72_CPU9_STAGE_CPU_ON);
	if (ret)
		return ret;
	result->cpu_requests++;
	ret = ops->cpu_on(context, MT6797_A72_CPU9_EXECUTOR_CPU9);
	if (ret)
		return mt6797_a72_cpu9_executor_stage_fault(
			controller, ops, context, result,
			MT6797_A72_CPU9_STAGE_CPU_ON, ret);
	result->cpu_on_accepted = true;
	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_AFTER, MT6797_A72_CPU9_STAGE_CPU_ON);
	if (ret)
		return ret;
	atomic_set_release(&controller->lifecycle,
			   MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED);
	return 0;
}

int mt6797_a72_cpu9_executor_secondary_complete(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_cpu9_executor_result *result)
{
	int ret;

	if (!controller || !result || !mt6797_a72_cpu9_executor_ops_valid(ops))
		return -EINVAL;
	if (atomic_cmpxchg(&controller->lifecycle,
			   MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED,
			   MT6797_A72_CPU9_LIFECYCLE_SECONDARY_INFLIGHT) !=
	    MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED)
		return -EALREADY;
	result->cpu8_online = cpu8_online;
	result->cpu9_online = cpu9_online;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    !cpu8_online || !cpu9_online)
		return mt6797_a72_cpu9_executor_stage_fault(
			controller, ops, context, result,
			MT6797_A72_CPU9_STAGE_ONLINE_WAIT, -EPROTO);

	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_BEFORE,
		MT6797_A72_CPU9_STAGE_ONLINE_WAIT);
	if (ret)
		return ret;
	ret = ops->secondary_complete(context, cpu);
	if (ret)
		return mt6797_a72_cpu9_executor_stage_fault(
			controller, ops, context, result,
			MT6797_A72_CPU9_STAGE_ONLINE_WAIT, ret);
	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_AFTER,
		MT6797_A72_CPU9_STAGE_ONLINE_WAIT);
	if (ret)
		return ret;
	atomic_set_release(&controller->lifecycle,
			   MT6797_A72_CPU9_LIFECYCLE_SECONDARY_COMPLETE);
	return 0;
}

int mt6797_a72_cpu9_executor_complete(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_cpu9_executor_result *result)
{
	int ret;

	if (!controller || !result || !mt6797_a72_cpu9_executor_ops_valid(ops))
		return -EINVAL;
	if (atomic_cmpxchg(&controller->lifecycle,
			   MT6797_A72_CPU9_LIFECYCLE_SECONDARY_COMPLETE,
			   MT6797_A72_CPU9_LIFECYCLE_FINAL_INFLIGHT) !=
	    MT6797_A72_CPU9_LIFECYCLE_SECONDARY_COMPLETE)
		return -EALREADY;
	result->cpu8_online = cpu8_online;
	result->cpu9_online = cpu9_online;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 ||
	    !cpu8_online || !cpu9_online)
		return mt6797_a72_cpu9_executor_stage_fault(
			controller, ops, context, result,
			MT6797_A72_CPU9_STAGE_IPI, -EPROTO);

	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_BEFORE, MT6797_A72_CPU9_STAGE_IPI);
	if (ret)
		return ret;
	ret = ops->ipi_proof(context, cpu);
	if (ret)
		return mt6797_a72_cpu9_executor_stage_fault(
			controller, ops, context, result,
			MT6797_A72_CPU9_STAGE_IPI, ret);
	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_AFTER, MT6797_A72_CPU9_STAGE_IPI);
	if (ret)
		return ret;

	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_BEFORE,
		MT6797_A72_CPU9_STAGE_MEMBERSHIP);
	if (ret)
		return ret;
	ret = ops->membership_commit(context, cpu);
	if (ret)
		return mt6797_a72_cpu9_executor_stage_fault(
			controller, ops, context, result,
			MT6797_A72_CPU9_STAGE_MEMBERSHIP, ret);
	result->membership_published = true;
	ret = mt6797_a72_cpu9_executor_checkpoint(
		controller, ops, context, result,
		MT6797_A72_CPU9_PHASE_AFTER,
		MT6797_A72_CPU9_STAGE_MEMBERSHIP);
	if (ret)
		return ret;
	return mt6797_a72_cpu9_executor_terminal(
		controller, ops, context, result,
		MT6797_A72_CPU9_ONLINE_PROOF, 0);
}

int mt6797_a72_cpu9_executor_fail(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online, int error,
	struct mt6797_a72_cpu9_executor_result *result)
{
	int lifecycle, ret;

	if (!controller || !result || !error ||
	    !mt6797_a72_cpu9_executor_ops_valid(ops))
		return -EINVAL;
	lifecycle = atomic_read_acquire(&controller->lifecycle);
	if (lifecycle != MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED &&
	    lifecycle != MT6797_A72_CPU9_LIFECYCLE_SECONDARY_COMPLETE)
		return -EALREADY;
	if (atomic_cmpxchg(&controller->lifecycle, lifecycle,
			   MT6797_A72_CPU9_LIFECYCLE_FINAL_INFLIGHT) != lifecycle)
		return -EALREADY;
	result->cpu8_online = cpu8_online;
	result->cpu9_online = cpu9_online;
	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || !cpu8_online ||
	    (lifecycle == MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED &&
	     cpu9_online) ||
	    (lifecycle == MT6797_A72_CPU9_LIFECYCLE_SECONDARY_COMPLETE &&
	     !cpu9_online))
		error = -EPROTO;
	if (lifecycle == MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED) {
		ret = mt6797_a72_cpu9_executor_checkpoint(
			controller, ops, context, result,
			MT6797_A72_CPU9_PHASE_BEFORE,
			MT6797_A72_CPU9_STAGE_ONLINE_WAIT);
		if (ret)
			return ret;
	}
	return mt6797_a72_cpu9_executor_stage_fault(
		controller, ops, context, result,
		MT6797_A72_CPU9_STAGE_ONLINE_WAIT, error);
}

int mt6797_a72_cpu9_executor_run(
	struct mt6797_a72_cpu9_executor_controller *controller,
	const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
	const struct mt6797_a72_cpu9_executor_request *request,
	struct mt6797_a72_cpu9_executor_result *result)
{
	int ret;

	ret = mt6797_a72_cpu9_executor_begin(controller, ops, context,
					     request, result);
	if (ret)
		return ret;
	ret = mt6797_a72_cpu9_executor_secondary_complete(
		controller, ops, context, MT6797_A72_CPU9_EXECUTOR_CPU9,
		true, true, result);
	if (ret)
		return ret;
	return mt6797_a72_cpu9_executor_complete(
		controller, ops, context, MT6797_A72_CPU9_EXECUTOR_CPU9,
		true, true, result);
}
