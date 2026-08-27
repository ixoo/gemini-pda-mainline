// SPDX-License-Identifier: GPL-2.0-only
/* Hardware-free coordinator for one MT6797 CPU8 transition. */

#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-transition-internal.h"

static bool
mt6797_a72_transition_ops_valid(const struct mt6797_a72_transition_ops *ops)
{
	return ops && ops->checkpoint && ops->watchdog_arm &&
		ops->p27_acquire && ops->p27_release &&
		ops->provider_acquire && ops->provider_release &&
		ops->isolation_clear && ops->sram_enable && ops->cpu_on &&
		ops->secondary_complete && ops->ipi_proof && ops->dcm_update;
}

static void
mt6797_a72_transition_checkpoint(const struct mt6797_a72_transition_ops *ops,
				 void *context,
				 struct mt6797_a72_transition_result *result,
				 enum mt6797_a72_transition_phase phase,
				 enum mt6797_a72_transition_stage stage)
{
	result->last_stage = stage;
	result->checkpoints++;
	ops->checkpoint(context, phase, stage, result);
}

static void
mt6797_a72_transition_set_retained(struct mt6797_a72_transition_result *result)
{
	result->retained_mask = 0;
	if (result->p27_owned)
		result->retained_mask |= MT6797_A72_TRANSITION_OWNED_P27;
	if (result->provider_owned)
		result->retained_mask |= MT6797_A72_TRANSITION_OWNED_PROVIDER;
	if (result->cpu8_online)
		result->retained_mask |= MT6797_A72_TRANSITION_OWNED_CPU8;
}

static void
mt6797_a72_transition_terminal(
	struct mt6797_a72_transition_controller *controller)
{
	atomic_set_release(&controller->lifecycle,
			   MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL);
}

static int
mt6797_a72_transition_rollback(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	struct mt6797_a72_transition_result *result, int stage_errno)
{
	int ret;

	result->stage_errno = stage_errno;
	if (result->provider_owned) {
		ret = ops->provider_release(context);
		if (ret) {
			result->rollback_errno = ret;
			result->terminal =
				MT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;
			mt6797_a72_transition_set_retained(result);
			mt6797_a72_transition_terminal(controller);
			return ret;
		}
		result->provider_owned = false;
		result->rollback_mask |= MT6797_A72_TRANSITION_OWNED_PROVIDER;
	}
	if (result->p27_owned) {
		ret = ops->p27_release(context);
		if (ret) {
			result->rollback_errno = ret;
			result->terminal =
				MT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;
			mt6797_a72_transition_set_retained(result);
			mt6797_a72_transition_terminal(controller);
			return ret;
		}
		result->p27_owned = false;
		result->rollback_mask |= MT6797_A72_TRANSITION_OWNED_P27;
	}
	result->terminal = MT6797_A72_TRANSITION_ROLLED_BACK_PREISO;
	mt6797_a72_transition_terminal(controller);
	return stage_errno;
}

static int
mt6797_a72_owner_fault(struct mt6797_a72_transition_controller *controller,
		       struct mt6797_a72_transition_result *result,
		       u32 unknown_mask)
{
	result->stage_errno = -EPROTO;
	result->terminal = MT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;
	result->retained_mask = unknown_mask;
	if (result->p27_owned)
		result->retained_mask |= MT6797_A72_TRANSITION_OWNED_P27;
	if (result->provider_owned)
		result->retained_mask |= MT6797_A72_TRANSITION_OWNED_PROVIDER;
	mt6797_a72_transition_terminal(controller);
	return -EPROTO;
}

static int
mt6797_a72_transition_postiso_fault(
	struct mt6797_a72_transition_controller *controller,
	struct mt6797_a72_transition_result *result, int stage_errno)
{
	result->stage_errno = stage_errno;
	result->terminal = MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO;
	mt6797_a72_transition_set_retained(result);
	mt6797_a72_transition_terminal(controller);
	return stage_errno;
}

int mt6797_a72_transition_begin(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	const struct mt6797_a72_transition_request *request,
	struct mt6797_a72_transition_result *result)
{
	bool owned = false;
	u64 watchdog_identity = 0;
	int ret;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	result->last_stage = MT6797_A72_TRANSITION_STAGE_ENTRY;
	result->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;
	if (!controller || !request || !mt6797_a72_transition_ops_valid(ops))
		return -EINVAL;
	if (atomic_read_acquire(&controller->lifecycle) !=
	    MT6797_A72_TRANSITION_LIFECYCLE_IDLE)
		return -EALREADY;
	result->cpu8_online = request->cpu8_online;
	result->cpu9_online = request->cpu9_online;
	if (request->cpu != MT6797_A72_TRANSITION_CPU8)
		return -EINVAL;
	if (!request->token_exact || !request->prefix_complete ||
	    request->cpu8_online || request->cpu9_online)
		return -EPERM;
	if (atomic_cmpxchg(&controller->consumed, 0, 1))
		return -EALREADY;
	if (atomic_cmpxchg(&controller->lifecycle,
			   MT6797_A72_TRANSITION_LIFECYCLE_IDLE,
			   MT6797_A72_TRANSITION_LIFECYCLE_STARTING) !=
	    MT6797_A72_TRANSITION_LIFECYCLE_IDLE)
		return -EALREADY;
	result->attempted = true;
	result->terminal = MT6797_A72_TRANSITION_TERMINAL_NONE;

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_WATCHDOG);
	ret = ops->watchdog_arm(context, MT6797_A72_TRANSITION_RECOVERY_MS,
				&watchdog_identity);
	if (ret) {
		result->stage_errno = ret;
		result->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;
		mt6797_a72_transition_terminal(controller);
		return ret;
	}
	if (!watchdog_identity) {
		result->stage_errno = -EPROTO;
		result->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;
		mt6797_a72_transition_terminal(controller);
		return -EPROTO;
	}
	result->watchdog_armed = true;
	result->watchdog_identity = watchdog_identity;
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_WATCHDOG);

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_P27);
	ret = ops->p27_acquire(context, &owned);
	result->p27_owned = owned;
	if (ret)
		return mt6797_a72_transition_rollback(controller, ops, context,
						      result, ret);
	if (!owned)
		return mt6797_a72_owner_fault(
			controller, result, MT6797_A72_TRANSITION_OWNED_P27);
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_P27);

	owned = false;
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_PROVIDER);
	ret = ops->provider_acquire(context, &owned);
	result->provider_owned = owned;
	if (ret)
		return mt6797_a72_transition_rollback(controller, ops, context,
						      result, ret);
	if (!owned)
		return mt6797_a72_owner_fault(
			controller, result,
			MT6797_A72_TRANSITION_OWNED_PROVIDER);
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_PROVIDER);

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_ISOLATION);
	result->isolation_attempted = true;
	ret = ops->isolation_clear(context);
	if (ret)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     ret);
	result->isolation_crossed = true;
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_ISOLATION);

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_SRAM);
	ret = ops->sram_enable(context);
	if (ret)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     ret);
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_SRAM);

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_CPU_ON);
	result->cpu_requests++;
	ret = ops->cpu_on(context, MT6797_A72_TRANSITION_CPU8);
	if (ret)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     ret);
	result->cpu_on_accepted = true;
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_CPU_ON);
	atomic_set_release(&controller->lifecycle,
			   MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED);
	return 0;
}

int mt6797_a72_transition_secondary_complete(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_transition_result *result)
{
	int ret;

	if (!controller || !result || !mt6797_a72_transition_ops_valid(ops))
		return -EINVAL;
	if (atomic_cmpxchg(&controller->lifecycle,
			   MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED,
			   MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_INFLIGHT) !=
	    MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED)
		return -EALREADY;
	result->cpu8_online = cpu8_online;
	result->cpu9_online = cpu9_online;
	if (cpu != MT6797_A72_TRANSITION_CPU8 || !cpu8_online || cpu9_online)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     -EPROTO);

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);
	ret = ops->secondary_complete(context, cpu);
	if (ret)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     ret);
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);
	atomic_set_release(&controller->lifecycle,
			   MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE);
	return 0;
}

int mt6797_a72_transition_complete(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_transition_result *result)
{
	int ret;

	if (!controller || !result || !mt6797_a72_transition_ops_valid(ops))
		return -EINVAL;
	if (atomic_cmpxchg(&controller->lifecycle,
			   MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE,
			   MT6797_A72_TRANSITION_LIFECYCLE_FINAL_INFLIGHT) !=
	    MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE)
		return -EALREADY;
	result->cpu8_online = cpu8_online;
	result->cpu9_online = cpu9_online;
	if (cpu != MT6797_A72_TRANSITION_CPU8 || !cpu8_online || cpu9_online)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     -EPROTO);

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_IPI);
	ret = ops->ipi_proof(context, cpu);
	if (ret)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     ret);
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_IPI);

	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_BEFORE,
					 MT6797_A72_TRANSITION_STAGE_DCM);
	ret = ops->dcm_update(context);
	if (ret)
		return mt6797_a72_transition_postiso_fault(controller, result,
							     ret);
	mt6797_a72_transition_checkpoint(ops, context, result,
					 MT6797_A72_TRANSITION_AFTER,
					 MT6797_A72_TRANSITION_STAGE_DCM);

	result->terminal = MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF;
	mt6797_a72_transition_set_retained(result);
	mt6797_a72_transition_terminal(controller);
	return 0;
}

int mt6797_a72_transition_fail(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online, int error,
	struct mt6797_a72_transition_result *result)
{
	int lifecycle;

	if (!controller || !result || !error ||
	    !mt6797_a72_transition_ops_valid(ops))
		return -EINVAL;
	lifecycle = atomic_read_acquire(&controller->lifecycle);
	if (lifecycle != MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED &&
	    lifecycle != MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE)
		return -EALREADY;
	if (atomic_cmpxchg(&controller->lifecycle, lifecycle,
			   MT6797_A72_TRANSITION_LIFECYCLE_FINAL_INFLIGHT) !=
	    lifecycle)
		return -EALREADY;
	result->cpu8_online = cpu8_online;
	result->cpu9_online = cpu9_online;
	if (cpu != MT6797_A72_TRANSITION_CPU8 || cpu9_online ||
	    (lifecycle == MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE &&
	     !cpu8_online))
		error = -EPROTO;
	if (lifecycle == MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED)
		mt6797_a72_transition_checkpoint(
			ops, context, result, MT6797_A72_TRANSITION_BEFORE,
			MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);
	return mt6797_a72_transition_postiso_fault(controller, result, error);
}

int mt6797_a72_transition_run(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	const struct mt6797_a72_transition_request *request,
	struct mt6797_a72_transition_result *result)
{
	int ret;

	ret = mt6797_a72_transition_begin(controller, ops, context, request,
					   result);
	if (ret)
		return ret;
	ret = mt6797_a72_transition_secondary_complete(
		controller, ops, context, MT6797_A72_TRANSITION_CPU8,
		true, false, result);
	if (ret)
		return ret;
	return mt6797_a72_transition_complete(
		controller, ops, context, MT6797_A72_TRANSITION_CPU8,
		true, false, result);
}
