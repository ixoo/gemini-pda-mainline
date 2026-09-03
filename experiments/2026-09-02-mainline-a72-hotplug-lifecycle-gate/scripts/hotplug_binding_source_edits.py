#!/usr/bin/env python3
"""Apply the production CPU9 down/restore hotplug binding edits."""

from __future__ import annotations

import argparse
from pathlib import Path


PUBLIC_HEADER = r'''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __LINUX_SOC_MEDIATEK_MT6797_A72_HOTPLUG_BINDING_H
#define __LINUX_SOC_MEDIATEK_MT6797_A72_HOTPLUG_BINDING_H

#include <linux/cpuhotplug.h>
#include <linux/errno.h>
#include <linux/kconfig.h>
#include <linux/types.h>

struct device;

typedef int (*mt6797_a72_hotplug_disable_fn)(unsigned int cpu);
typedef int (*mt6797_a72_hotplug_affinity_fn)(unsigned int cpu,
					       unsigned int level);
typedef int (*mt6797_a72_hotplug_boot_fn)(unsigned int cpu);

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING)
int mt6797_a72_hotplug_binding_run(struct device *platform,
				    struct device *clock,
				    struct device *bigidvfs,
				    u64 session_id);
bool mt6797_a72_hotplug_binding_down_active(unsigned int cpu);
bool mt6797_a72_hotplug_binding_restore_active(unsigned int cpu);
int mt6797_a72_hotplug_binding_down_preflight(unsigned int cpu,
					       enum cpuhp_state target);
int mt6797_a72_hotplug_binding_down_validate(unsigned int cpu,
					      int tasks_frozen,
					      enum cpuhp_state target);
int mt6797_a72_hotplug_binding_down_disable(
	unsigned int cpu, mt6797_a72_hotplug_disable_fn disable);
int mt6797_a72_hotplug_binding_down_commit(unsigned int cpu);
int mt6797_a72_hotplug_binding_down_returned(unsigned int cpu, int error);
int mt6797_a72_hotplug_binding_down_kill(
	unsigned int cpu, mt6797_a72_hotplug_affinity_fn affinity);
int mt6797_a72_hotplug_binding_down_complete(unsigned int cpu,
					      enum cpuhp_state target);
int mt6797_a72_hotplug_binding_down_failed(unsigned int cpu,
					    enum cpuhp_state target,
					    int error);
int mt6797_a72_hotplug_binding_restore_preflight(unsigned int cpu,
						  enum cpuhp_state target);
int mt6797_a72_hotplug_binding_restore_validate(unsigned int cpu,
						 int tasks_frozen,
						 enum cpuhp_state target);
int mt6797_a72_hotplug_binding_restore_boot(
	unsigned int cpu, mt6797_a72_hotplug_boot_fn boot);
int mt6797_a72_hotplug_binding_restore_secondary(unsigned int cpu);
int mt6797_a72_hotplug_binding_restore_complete(unsigned int cpu,
						 enum cpuhp_state target);
int mt6797_a72_hotplug_binding_restore_rollback(unsigned int cpu,
						 enum cpuhp_state state,
						 int error,
						 bool *suppress_initial);
#else
static inline int mt6797_a72_hotplug_binding_run(
	struct device *platform, struct device *clock, struct device *bigidvfs,
	u64 session_id)
{
	(void)platform;
	(void)clock;
	(void)bigidvfs;
	(void)session_id;
	return -EOPNOTSUPP;
}

static inline bool
mt6797_a72_hotplug_binding_down_active(unsigned int cpu)
{
	(void)cpu;
	return false;
}

static inline bool
mt6797_a72_hotplug_binding_restore_active(unsigned int cpu)
{
	(void)cpu;
	return false;
}

static inline int mt6797_a72_hotplug_binding_down_preflight(
	unsigned int cpu, enum cpuhp_state target)
{
	(void)cpu;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_down_validate(
	unsigned int cpu, int tasks_frozen, enum cpuhp_state target)
{
	(void)cpu;
	(void)tasks_frozen;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_down_disable(
	unsigned int cpu, mt6797_a72_hotplug_disable_fn disable)
{
	(void)cpu;
	(void)disable;
	return -EOPNOTSUPP;
}

static inline int
mt6797_a72_hotplug_binding_down_commit(unsigned int cpu)
{
	(void)cpu;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_down_returned(
	unsigned int cpu, int error)
{
	(void)cpu;
	(void)error;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_down_kill(
	unsigned int cpu, mt6797_a72_hotplug_affinity_fn affinity)
{
	(void)cpu;
	(void)affinity;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_down_complete(
	unsigned int cpu, enum cpuhp_state target)
{
	(void)cpu;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_down_failed(
	unsigned int cpu, enum cpuhp_state target, int error)
{
	(void)cpu;
	(void)target;
	(void)error;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_restore_preflight(
	unsigned int cpu, enum cpuhp_state target)
{
	(void)cpu;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_restore_validate(
	unsigned int cpu, int tasks_frozen, enum cpuhp_state target)
{
	(void)cpu;
	(void)tasks_frozen;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_restore_boot(
	unsigned int cpu, mt6797_a72_hotplug_boot_fn boot)
{
	(void)cpu;
	(void)boot;
	return -EOPNOTSUPP;
}

static inline int
mt6797_a72_hotplug_binding_restore_secondary(unsigned int cpu)
{
	(void)cpu;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_restore_complete(
	unsigned int cpu, enum cpuhp_state target)
{
	(void)cpu;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_hotplug_binding_restore_rollback(
	unsigned int cpu, enum cpuhp_state state, int error,
	bool *suppress_initial)
{
	(void)cpu;
	(void)state;
	(void)error;
	if (suppress_initial)
		*suppress_initial = false;
	return -EOPNOTSUPP;
}
#endif

#endif /* __LINUX_SOC_MEDIATEK_MT6797_A72_HOTPLUG_BINDING_H */
'''


INTERNAL_HEADER = r'''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_HOTPLUG_BINDING_INTERNAL_H
#define __MT6797_A72_HOTPLUG_BINDING_INTERNAL_H

#include <linux/device.h>
#include <linux/types.h>

#define MT6797_A72_HOTPLUG_BINDING_CPU9 9U

enum mt6797_a72_hotplug_binding_route {
	MT6797_A72_HOTPLUG_BINDING_IDLE,
	MT6797_A72_HOTPLUG_BINDING_DOWN,
	MT6797_A72_HOTPLUG_BINDING_RESTORE,
	MT6797_A72_HOTPLUG_BINDING_TERMINAL,
};

struct mt6797_a72_hotplug_private_ops {
	struct device *(*cpu_device)(void *context, unsigned int cpu);
	void (*lock)(void *context);
	void (*unlock)(void *context);
	bool (*cpu_online)(void *context, unsigned int cpu);
	u64 (*task_identity)(void *context);
	int (*offline)(void *context, struct device *dev);
};

bool mt6797_a72_hotplug_binding_route_matches(
	enum mt6797_a72_hotplug_binding_route route, unsigned int cpu,
	enum mt6797_a72_hotplug_binding_route expected);
int mt6797_a72_hotplug_private_down_with_ops(
	const struct mt6797_a72_hotplug_private_ops *ops, void *context,
	u64 expected_task, unsigned int cpu);

#endif /* __MT6797_A72_HOTPLUG_BINDING_INTERNAL_H */
'''


SOURCE = r'''// SPDX-License-Identifier: GPL-2.0-only
/* One-shot production binding for the MT6797 CPU9 down/restore experiment. */

#include <asm/mt6797_a72_membership.h>

#include <linux/atomic.h>
#include <linux/bitops.h>
#include <linux/cpu.h>
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/gemini_a72_hotplug_ledger.h>
#include <linux/mutex.h>
#include <linux/sched.h>
#include <linux/smp.h>
#include <linux/string.h>
#include <linux/soc/mediatek/mt6797-a72-binder.h>
#include <linux/soc/mediatek/mt6797-a72-hotplug-binding.h>

#include "mt6797-a72-cpu8-observer-internal.h"
#include "mt6797-a72-hotplug-binder-core-internal.h"
#include "mt6797-a72-hotplug-binding-internal.h"
#include "mt6797-a72-hotplug-executor-internal.h"
#include "mt6797-a72-hotplug-snapshot-internal.h"
#include "mt6797-a72-restore-executor-internal.h"

#define MT6797_A72_HOTPLUG_SYSTEM_ONLINE GENMASK_ULL(9, 0)
#define MT6797_A72_HOTPLUG_SYSTEM_OFFLINE GENMASK_ULL(8, 0)

struct mt6797_a72_hotplug_binding {
	struct mt6797_a72_hotplug_binder_controller binder;
	struct mt6797_a72_hotplug_binder_result binder_result;
	struct mt6797_a72_hotplug_executor_controller down;
	struct mt6797_a72_hotplug_executor_result down_result;
	struct mt6797_a72_restore_executor_controller restore;
	struct mt6797_a72_restore_executor_result restore_result;
	struct mt6797_a72_hotplug_snapshot_source source;
	struct mt6797_a72_cpu8_observer observer;
	struct mt6797_a72_binder_parent_proof parent;
	struct mt6797_a72_hotplug_transaction down_transaction;
	struct mt6797_a72_hotplug_transaction down_parent;
	u64 task_identity;
	u64 session_id;
	u32 next_stage;
	u32 result_flags;
	atomic_t route;
	mt6797_a72_hotplug_disable_fn disable;
	mt6797_a72_hotplug_affinity_fn affinity;
	mt6797_a72_hotplug_boot_fn boot;
	bool ledger_active;
	bool ledger_terminal;
	bool cpu_off_returned;
};

static DEFINE_MUTEX(mt6797_a72_hotplug_binding_lock);
static struct mt6797_a72_hotplug_binding mt6797_a72_binding = {
	.route = ATOMIC_INIT(MT6797_A72_HOTPLUG_BINDING_IDLE),
};

bool mt6797_a72_hotplug_binding_route_matches(
	enum mt6797_a72_hotplug_binding_route route, unsigned int cpu,
	enum mt6797_a72_hotplug_binding_route expected)
{
	return cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 && route == expected;
}

static bool mt6797_a72_hotplug_private_ops_valid(
	const struct mt6797_a72_hotplug_private_ops *ops)
{
	return ops && ops->cpu_device && ops->lock && ops->unlock &&
		ops->cpu_online && ops->task_identity && ops->offline;
}

int mt6797_a72_hotplug_private_down_with_ops(
	const struct mt6797_a72_hotplug_private_ops *ops, void *context,
	u64 expected_task, unsigned int cpu)
{
	struct device *dev;
	int ret;

	if (!mt6797_a72_hotplug_private_ops_valid(ops) || !expected_task ||
	    cpu != MT6797_A72_HOTPLUG_BINDING_CPU9)
		return -EINVAL;
	ops->lock(context);
	dev = ops->cpu_device(context, cpu);
	if (!dev) {
		ret = -ENODEV;
		goto out_unlock;
	}
	if (ops->task_identity(context) != expected_task ||
	    !ops->cpu_online(context, cpu) ||
	    !dev->offline_disabled || dev->offline) {
		ret = -EPERM;
		goto out_unlock;
	}

	dev->offline_disabled = false;
	ret = ops->offline(context, dev);
	dev->offline_disabled = true;
out_unlock:
	ops->unlock(context);
	return ret;
}

static struct device *mt6797_a72_hotplug_cpu_device(void *context,
						     unsigned int cpu)
{
	(void)context;
	return get_cpu_device(cpu);
}

static void mt6797_a72_hotplug_device_lock(void *context)
{
	(void)context;
	lock_device_hotplug();
}

static void mt6797_a72_hotplug_device_unlock(void *context)
{
	(void)context;
	unlock_device_hotplug();
}

static bool mt6797_a72_hotplug_cpu_online(void *context, unsigned int cpu)
{
	(void)context;
	return cpu_online(cpu);
}

static u64 mt6797_a72_hotplug_current_task(void *context)
{
	(void)context;
	return (u64)(uintptr_t)current;
}

static int mt6797_a72_hotplug_device_offline(void *context,
					      struct device *dev)
{
	(void)context;
	return device_offline(dev);
}

static const struct mt6797_a72_hotplug_private_ops
mt6797_a72_hotplug_private_ops = {
	.cpu_device = mt6797_a72_hotplug_cpu_device,
	.lock = mt6797_a72_hotplug_device_lock,
	.unlock = mt6797_a72_hotplug_device_unlock,
	.cpu_online = mt6797_a72_hotplug_cpu_online,
	.task_identity = mt6797_a72_hotplug_current_task,
	.offline = mt6797_a72_hotplug_device_offline,
};

static u64 mt6797_a72_hotplug_online_mask(void)
{
	u64 mask = 0;
	unsigned int cpu;

	for_each_online_cpu(cpu)
		if (cpu < 64)
			mask |= BIT_ULL(cpu);
	return mask;
}

static void mt6797_a72_hotplug_fill_record(
	struct mt6797_a72_hotplug_binding *binding,
	struct gemini_a72_hotplug_ledger_record *record, u32 stage,
	u32 terminal, int error)
{
	struct mt6797_a72_hotplug_snapshot membership = { };

	mt6797_a72_hotplug_snapshot(&membership);
	*record = (struct gemini_a72_hotplug_ledger_record) {
		.session_id = binding->session_id,
		.parent_generation = binding->parent.cpu9.generation,
		.parent_cookie = binding->parent.cpu9.cookie,
		.watchdog_identity = binding->parent.watchdog_identity,
		.down_generation =
			lower_32_bits(binding->down_transaction.identity.generation),
		.down_cookie = binding->down_transaction.identity.cookie,
		.restore_generation = lower_32_bits(
			binding->restore_result.restore.identity.generation),
		.restore_cookie = binding->restore_result.restore.identity.cookie,
		.result_flags = binding->result_flags,
		.cpu_off_calls = binding->down_result.cpu_off_authorizations,
		.affinity_calls = binding->down_result.affinity_calls,
		.cpu8_ipi_calls = binding->down_result.cpu8_callbacks,
		.cpu_on_calls = binding->restore_result.cpu_boot_calls,
		.online_mask = lower_32_bits(mt6797_a72_hotplug_online_mask()),
		.members = membership.members,
		.readback_mismatch = binding->down_result.snapshots == 2 &&
			!mt6797_a72_hotplug_readback_proves_cpu9_off(
				&binding->down_result.baseline,
				&binding->down_result.post_state),
		.stage = stage,
		.terminal = terminal,
		.error = error,
	};
}

static int mt6797_a72_hotplug_publish(
	struct mt6797_a72_hotplug_binding *binding, u32 stage, u32 terminal,
	int error, bool successful_stage)
{
	struct gemini_a72_hotplug_ledger_record record;
	int ret;

	if (!binding->ledger_active || binding->ledger_terminal)
		return -EPERM;
	if (terminal == GEMINI_A72_HOTPLUG_CPU_OFF_RETURN_FAULT) {
		if (binding->next_stage != GEMINI_A72_HOTPLUG_AFFINITY_OFF ||
		    stage != GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED)
			return -EPROTO;
	} else if (stage != binding->next_stage) {
		return -EPROTO;
	}
	if (successful_stage)
		binding->result_flags |= BIT(stage - 1);
	mt6797_a72_hotplug_fill_record(binding, &record, stage, terminal,
				       error);
	ret = gemini_a72_hotplug_ledger_checkpoint(binding->session_id,
						   &record);
	if (ret)
		return ret;
	binding->next_stage = stage + 1;
	if (stage == GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED)
		binding->next_stage = GEMINI_A72_HOTPLUG_AFFINITY_OFF;
	if (terminal) {
		binding->ledger_terminal = true;
		binding->ledger_active = false;
	}
	return 0;
}

static int mt6797_a72_hotplug_parent_proof(
	void *context, struct mt6797_a72_binder_parent_proof *proof)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	ret = mt6797_a72_binder_parent_proof(proof);
	if (!ret)
		binding->parent = *proof;
	return ret;
}

static int mt6797_a72_hotplug_ledger_begin(void *context, u64 session_id)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	ret = gemini_a72_hotplug_ledger_begin(session_id);
	if (!ret) {
		binding->ledger_active = true;
		binding->next_stage = GEMINI_A72_HOTPLUG_BINDING_PARENT;
	}
	return ret;
}

static int mt6797_a72_hotplug_binder_checkpoint(
	void *context, u32 stage,
	const struct mt6797_a72_hotplug_binder_result *result)
{
	struct mt6797_a72_hotplug_binding *binding = context;

	if (stage == GEMINI_A72_HOTPLUG_BINDING_PARENT)
		return mt6797_a72_hotplug_publish(binding, stage, 0, 0, true);
	if (stage == GEMINI_A72_HOTPLUG_DOWN_COMPLETE)
		return binding->next_stage == GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&
			result->down_completed ? 0 : -EPROTO;
	if (stage == GEMINI_A72_HOTPLUG_RESTORE_COMPLETE)
		return binding->ledger_terminal && result->restore_completed ?
			0 : -EPROTO;
	return -EPROTO;
}

static int mt6797_a72_hotplug_down_checkpoint(
	void *context, enum mt6797_a72_hotplug_executor_phase phase,
	enum mt6797_a72_hotplug_executor_stage stage,
	const struct mt6797_a72_hotplug_executor_result *result)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	u32 ledger_stage;

	(void)result;
	if (phase != MT6797_A72_HOTPLUG_AFTER)
		return 0;
	switch (stage) {
	case MT6797_A72_HOTPLUG_STAGE_OWNER_PREPARE:
		ledger_stage = GEMINI_A72_HOTPLUG_DOWN_PREPARED;
		break;
	case MT6797_A72_HOTPLUG_STAGE_WATCHDOG_VALIDATE:
		ledger_stage = GEMINI_A72_HOTPLUG_WATCHDOG_VALID;
		break;
	case MT6797_A72_HOTPLUG_STAGE_BASELINE:
		ledger_stage = GEMINI_A72_HOTPLUG_BASELINE_VALID;
		break;
	case MT6797_A72_HOTPLUG_STAGE_OFF_COMMIT:
		ledger_stage = GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED;
		break;
	default:
		return -EPROTO;
	}
	return mt6797_a72_hotplug_publish(binding, ledger_stage, 0, 0, true);
}

static int mt6797_a72_hotplug_binding_prepare_down(
	void *context, const struct mt6797_a72_hotplug_executor_request *request)
{
	struct mt6797_a72_hotplug_binding *binding = context;

	return mt6797_a72_hotplug_prepare_down(
		request->cpu, CPUHP_OFFLINE, cpu_online(8), cpu_online(9),
		&binding->down_transaction);
}

static int mt6797_a72_hotplug_watchdog_validate(void *context, u64 identity)
{
	struct mt6797_a72_hotplug_binding *binding = context;

	return identity && identity == binding->parent.watchdog_identity &&
		binding->parent.exact == 1 &&
		binding->parent.watchdog_age_ns <=
			MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL ?
		0 : -EPROTO;
}

static int mt6797_a72_hotplug_snapshot_read(
	void *context, struct mt6797_a72_hotplug_readback *readback)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	struct mt6797_a72_hotplug_snapshot_trace trace;
	int ret;

	ret = mt6797_a72_hotplug_snapshot_capture(&binding->source, readback,
						   &trace);
	if (!ret && binding->down_result.snapshots == 2)
		ret = mt6797_a72_hotplug_publish(
			binding, GEMINI_A72_HOTPLUG_POST_STATE_VALID, 0, 0, true);
	return ret;
}

static int mt6797_a72_hotplug_validate_down_op(
	void *context, bool tasks_frozen, bool cpu8_online, bool cpu9_online)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	ret = mt6797_a72_hotplug_validate_down(&binding->down_transaction,
			tasks_frozen, CPUHP_OFFLINE, cpu8_online, cpu9_online);
	return ret ?: mt6797_a72_hotplug_publish(
		binding, GEMINI_A72_HOTPLUG_DOWN_VALID, 0, 0, true);
}

static int mt6797_a72_hotplug_target_disable(void *context,
					      unsigned int cpu)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	if (!binding->disable)
		return -EOPNOTSUPP;
	ret = binding->disable(cpu);
	return ret ?: mt6797_a72_hotplug_publish(
		binding, GEMINI_A72_HOTPLUG_TARGET_DISABLE_VALID, 0, 0, true);
}

static int mt6797_a72_hotplug_binding_commit_off(void *context,
						  unsigned int cpu)
{
	(void)context;
	return mt6797_a72_hotplug_commit_off(cpu);
}

static int mt6797_a72_hotplug_affinity_info(void *context,
					     unsigned int cpu,
					     unsigned int level)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	if (!binding->affinity)
		return -EOPNOTSUPP;
	ret = binding->affinity(cpu, level);
	if (ret == MT6797_A72_HOTPLUG_AFFINITY_OFF) {
		if (mt6797_a72_hotplug_publish(
			    binding, GEMINI_A72_HOTPLUG_AFFINITY_OFF,
			    0, 0, true))
			return -EIO;
	}
	return ret;
}

static int mt6797_a72_hotplug_cpu8_callback(void *context,
					     unsigned int cpu)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	if (cpu != 8)
		return -EINVAL;
	ret = mt6797_a72_cpu8_observer_run(
		&binding->observer, &binding->down_transaction.identity);
	return ret ?: mt6797_a72_hotplug_publish(
		binding, GEMINI_A72_HOTPLUG_CPU8_RESPONSIVE, 0, 0, true);
}

static int mt6797_a72_hotplug_binding_prove_off(
	void *context, const struct mt6797_a72_hotplug_executor_result *result)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	struct mt6797_a72_cpu9_off_proof proof = {
		.abi = MT6797_A72_CPU9_OFF_PROOF_ABI,
		.valid = 1,
		.affinity_attempted = 1,
		.affinity_level = MT6797_A72_AFFINITY_LEVEL0,
		.affinity_state = MT6797_A72_AFFINITY_STATE_OFF,
		.cpu9_per_core_off = 1,
		.cpu8_responsive = 1,
		.shared_state_unchanged = 1,
		.members_before = BIT(0) | BIT(1),
		.online_mask_after = BIT(0),
		.provider_identity = binding->down_transaction.provider_identity,
		.transaction_generation =
			binding->down_transaction.identity.generation,
		.transaction_cookie = binding->down_transaction.identity.cookie,
	};
	int ret;

	if (!mt6797_a72_hotplug_readback_proves_cpu9_off(
		    &result->baseline, &result->post_state))
		return -EIO;
	ret = mt6797_a72_hotplug_prove_off(&binding->down_transaction,
					   &proof);
	return ret ?: mt6797_a72_hotplug_publish(
		binding, GEMINI_A72_HOTPLUG_OFF_PROOF_ACCEPTED, 0, 0, true);
}

static int mt6797_a72_hotplug_complete_down_op(
	void *context, bool cpu8_online, bool cpu9_online)
{
	struct mt6797_a72_hotplug_binding *binding = context;

	return mt6797_a72_hotplug_complete_down(&binding->down_transaction,
						 cpu8_online, cpu9_online);
}

static int mt6797_a72_hotplug_fail_down_op(void *context, int error)
{
	struct mt6797_a72_hotplug_binding *binding = context;

	return mt6797_a72_hotplug_fail_down(&binding->down_transaction, error);
}

static int mt6797_a72_hotplug_down_terminal(
	void *context, const struct mt6797_a72_hotplug_executor_result *result)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	u32 stage = binding->next_stage;
	u32 terminal;

	if (result->terminal == MT6797_A72_HOTPLUG_DOWN_COMPLETE)
		return mt6797_a72_hotplug_publish(
			binding, GEMINI_A72_HOTPLUG_DOWN_COMPLETE, 0, 0, true);
	if (result->terminal == MT6797_A72_HOTPLUG_REJECTED_PRECOMMIT) {
		terminal = GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT;
	} else if (binding->cpu_off_returned) {
		stage = GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED;
		terminal = GEMINI_A72_HOTPLUG_CPU_OFF_RETURN_FAULT;
	} else {
		terminal = GEMINI_A72_HOTPLUG_POSTCOMMIT_DOWN_FAULT;
	}
	return mt6797_a72_hotplug_publish(binding, stage, terminal,
					  result->stage_errno ?: -EIO, false);
}

static const struct mt6797_a72_hotplug_executor_ops
mt6797_a72_hotplug_down_ops = {
	.checkpoint = mt6797_a72_hotplug_down_checkpoint,
	.prepare_down = mt6797_a72_hotplug_binding_prepare_down,
	.watchdog_validate = mt6797_a72_hotplug_watchdog_validate,
	.snapshot = mt6797_a72_hotplug_snapshot_read,
	.validate_down = mt6797_a72_hotplug_validate_down_op,
	.target_disable = mt6797_a72_hotplug_target_disable,
	.commit_off = mt6797_a72_hotplug_binding_commit_off,
	.affinity_info = mt6797_a72_hotplug_affinity_info,
	.cpu8_callback = mt6797_a72_hotplug_cpu8_callback,
	.prove_off = mt6797_a72_hotplug_binding_prove_off,
	.complete_down = mt6797_a72_hotplug_complete_down_op,
	.fail_down = mt6797_a72_hotplug_fail_down_op,
	.terminal = mt6797_a72_hotplug_down_terminal,
};

static int mt6797_a72_hotplug_prepare_restore_op(
	void *context, unsigned int cpu, enum cpuhp_state target,
	bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_hotplug_transaction *restore)
{
	(void)context;
	return mt6797_a72_hotplug_prepare_restore(
		cpu, target, cpu8_online, cpu9_online, restore);
}

static int mt6797_a72_hotplug_validate_restore_op(
	void *context,
	const struct mt6797_a72_restore_executor_request *request,
	const struct mt6797_a72_hotplug_transaction *restore)
{
	struct mt6797_a72_hotplug_snapshot snapshot = { };

	(void)context;
	mt6797_a72_hotplug_snapshot(&snapshot);
	return request->cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 &&
		snapshot.phase == MT6797_A72_HOTPLUG_RESTORE_FROZEN &&
		snapshot.members == BIT(0) && snapshot.controller_present == 1 &&
		snapshot.active.valid == 1 &&
		!memcmp(&snapshot.active.identity, &restore->identity,
			sizeof(restore->identity)) ? 0 : -EPROTO;
}

static int mt6797_a72_hotplug_begin_restore_op(
	void *context, struct mt6797_a72_hotplug_transaction *restore,
	bool cpu8_online, bool cpu9_online)
{
	(void)context;
	return mt6797_a72_hotplug_begin_restore(restore, cpu8_online,
						 cpu9_online);
}

static int mt6797_a72_hotplug_restore_cpu_boot(void *context,
						unsigned int cpu)
{
	struct mt6797_a72_hotplug_binding *binding = context;

	return binding->boot ? binding->boot(cpu) : -EOPNOTSUPP;
}

static int mt6797_a72_hotplug_complete_restore_op(
	void *context, struct mt6797_a72_hotplug_transaction *restore,
	bool cpu8_online, bool cpu9_online)
{
	(void)context;
	return mt6797_a72_hotplug_complete_restore(restore, cpu8_online,
						    cpu9_online);
}

static int mt6797_a72_hotplug_verify_restore(
	void *context,
	const struct mt6797_a72_restore_executor_request *request,
	const struct mt6797_a72_hotplug_transaction *restore,
	u32 members, u32 online_mask, u64 system_online_mask)
{
	struct mt6797_a72_hotplug_snapshot snapshot = { };

	(void)context;
	mt6797_a72_hotplug_snapshot(&snapshot);
	return request->cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 &&
		members == (BIT(0) | BIT(1)) &&
		online_mask == (BIT(0) | BIT(1)) &&
		system_online_mask == MT6797_A72_HOTPLUG_SYSTEM_ONLINE &&
		snapshot.phase == MT6797_A72_HOTPLUG_RESTORED &&
		snapshot.members == (BIT(0) | BIT(1)) &&
		snapshot.retired_mask == (BIT(0) | BIT(1)) &&
		!memcmp(&snapshot.retired[1].identity, &restore->identity,
			sizeof(restore->identity)) ? 0 : -EPROTO;
}

static int mt6797_a72_hotplug_fail_restore_op(
	void *context, struct mt6797_a72_hotplug_transaction *restore,
	int error)
{
	(void)context;
	return mt6797_a72_hotplug_fail_restore(restore, error);
}

static int mt6797_a72_hotplug_restore_checkpoint(
	void *context, enum mt6797_a72_restore_executor_stage stage,
	const struct mt6797_a72_restore_executor_result *result)
{
	struct mt6797_a72_hotplug_binding *binding = context;

	(void)result;
	if (stage != MT6797_A72_RESTORE_STAGE_PREPARED &&
	    stage != MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED &&
	    stage != MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE)
		return -EPROTO;
	return mt6797_a72_hotplug_publish(binding, stage, 0, 0, true);
}

static int mt6797_a72_hotplug_restore_terminal(
	void *context, const struct mt6797_a72_restore_executor_result *result)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	u32 terminal = result->terminal == MT6797_A72_RESTORE_SUCCESS ?
		GEMINI_A72_HOTPLUG_RESTORED_SUCCESS :
		GEMINI_A72_HOTPLUG_RESTORE_FAULT;
	bool success = result->terminal == MT6797_A72_RESTORE_SUCCESS;

	return mt6797_a72_hotplug_publish(
		binding, binding->next_stage, terminal,
		success ? 0 : result->stage_errno ?: -EIO, success);
}

static const struct mt6797_a72_restore_executor_ops
mt6797_a72_hotplug_restore_ops = {
	.checkpoint = mt6797_a72_hotplug_restore_checkpoint,
	.prepare_restore = mt6797_a72_hotplug_prepare_restore_op,
	.validate_restore = mt6797_a72_hotplug_validate_restore_op,
	.begin_restore = mt6797_a72_hotplug_begin_restore_op,
	.cpu_boot = mt6797_a72_hotplug_restore_cpu_boot,
	.complete_restore = mt6797_a72_hotplug_complete_restore_op,
	.verify_terminal = mt6797_a72_hotplug_verify_restore,
	.fail_restore = mt6797_a72_hotplug_fail_restore_op,
	.terminal = mt6797_a72_hotplug_restore_terminal,
};

static int mt6797_a72_hotplug_remove_cpu(
	void *context, unsigned int cpu,
	struct mt6797_a72_hotplug_transaction *down_parent)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	atomic_set_release(&binding->route, MT6797_A72_HOTPLUG_BINDING_DOWN);
	ret = mt6797_a72_hotplug_private_down_with_ops(
		&mt6797_a72_hotplug_private_ops, NULL, binding->task_identity,
		cpu);
	*down_parent = binding->down_transaction;
	return ret;
}

static int mt6797_a72_hotplug_add_cpu_restore(
	void *context, unsigned int cpu,
	const struct mt6797_a72_hotplug_transaction *down_parent,
	struct mt6797_a72_hotplug_transaction *restore)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	int ret;

	if (memcmp(down_parent, &binding->down_transaction,
		   sizeof(*down_parent)))
		return -EPROTO;
	binding->down_parent = *down_parent;
	atomic_set_release(&binding->route,
			   MT6797_A72_HOTPLUG_BINDING_RESTORE);
	ret = add_cpu(cpu);
	*restore = binding->restore_result.restore;
	return ret;
}

static int mt6797_a72_hotplug_binder_terminal(
	void *context, const struct mt6797_a72_hotplug_binder_result *result)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	u32 terminal;

	if (binding->ledger_terminal || !binding->ledger_active)
		return 0;
	switch (result->terminal) {
	case MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT:
		terminal = GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT;
		break;
	case MT6797_A72_HOTPLUG_BINDER_FAULT_POSTCOMMIT:
		terminal = GEMINI_A72_HOTPLUG_POSTCOMMIT_DOWN_FAULT;
		break;
	case MT6797_A72_HOTPLUG_BINDER_RESTORE_FAULT:
		terminal = GEMINI_A72_HOTPLUG_RESTORE_FAULT;
		break;
	default:
		return -EPROTO;
	}
	return mt6797_a72_hotplug_publish(
		binding, binding->next_stage, terminal,
		result->stage_errno ?: -EIO, false);
}

static const struct mt6797_a72_hotplug_binder_ops
mt6797_a72_hotplug_binder_ops = {
	.current_task_identity = mt6797_a72_hotplug_current_task,
	.parent_proof = mt6797_a72_hotplug_parent_proof,
	.ledger_begin = mt6797_a72_hotplug_ledger_begin,
	.checkpoint = mt6797_a72_hotplug_binder_checkpoint,
	.remove_cpu = mt6797_a72_hotplug_remove_cpu,
	.add_cpu_restore = mt6797_a72_hotplug_add_cpu_restore,
	.terminal = mt6797_a72_hotplug_binder_terminal,
};

int mt6797_a72_hotplug_binding_run(struct device *platform,
				    struct device *clock,
				    struct device *bigidvfs,
				    u64 session_id)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;
	struct mt6797_a72_hotplug_binder_request request;
	int ret;

	if (!platform || !clock || !bigidvfs || !session_id)
		return -EINVAL;
	mutex_lock(&mt6797_a72_hotplug_binding_lock);
	if (atomic_read_acquire(&binding->route) !=
	    MT6797_A72_HOTPLUG_BINDING_IDLE) {
		ret = -EALREADY;
		goto out_unlock;
	}
	memset(binding, 0, sizeof(*binding));
	mt6797_a72_hotplug_binder_init(&binding->binder);
	binding->down = (struct mt6797_a72_hotplug_executor_controller)
		MT6797_A72_HOTPLUG_EXECUTOR_CONTROLLER_INIT;
	mt6797_a72_restore_executor_init(&binding->restore);
	mt6797_a72_cpu8_observer_init(&binding->observer);
	mt6797_a72_hotplug_snapshot_source_init(&binding->source, platform,
						 clock, bigidvfs);
	atomic_set(&binding->route, MT6797_A72_HOTPLUG_BINDING_IDLE);
	binding->task_identity = (u64)(uintptr_t)current;
	binding->session_id = session_id;
	request = (struct mt6797_a72_hotplug_binder_request) {
		.task_identity = binding->task_identity,
		.session_id = session_id,
	};
	ret = mt6797_a72_hotplug_binder_run(
		&binding->binder, &mt6797_a72_hotplug_binder_ops, binding,
		&request, &binding->binder_result);
	atomic_set_release(&binding->route,
			   MT6797_A72_HOTPLUG_BINDING_TERMINAL);
out_unlock:
	mutex_unlock(&mt6797_a72_hotplug_binding_lock);
	return ret;
}

bool mt6797_a72_hotplug_binding_down_active(unsigned int cpu)
{
	return mt6797_a72_hotplug_binding_route_matches(
		atomic_read_acquire(&mt6797_a72_binding.route), cpu,
		MT6797_A72_HOTPLUG_BINDING_DOWN);
}

bool mt6797_a72_hotplug_binding_restore_active(unsigned int cpu)
{
	return mt6797_a72_hotplug_binding_route_matches(
		atomic_read_acquire(&mt6797_a72_binding.route), cpu,
		MT6797_A72_HOTPLUG_BINDING_RESTORE);
}

int mt6797_a72_hotplug_binding_down_preflight(unsigned int cpu,
					       enum cpuhp_state target)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;
	struct mt6797_a72_hotplug_executor_request request;

	if (!mt6797_a72_hotplug_binding_down_active(cpu) ||
	    target != CPUHP_OFFLINE ||
	    (u64)(uintptr_t)current != binding->task_identity)
		return -EPERM;
	request = (struct mt6797_a72_hotplug_executor_request) {
		.cpu = cpu,
		.members = BIT(0) | BIT(1),
		.online_mask = BIT(0) | BIT(1),
		.watchdog_identity = binding->parent.watchdog_identity,
		.owner_parent_exact = binding->parent.exact == 1,
		.watchdog_owned = binding->parent.watchdog_identity != 0,
	};
	return mt6797_a72_hotplug_executor_preflight(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding,
		&request, &binding->down_result);
}

int mt6797_a72_hotplug_binding_down_validate(unsigned int cpu,
					      int tasks_frozen,
					      enum cpuhp_state target)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	if (!mt6797_a72_hotplug_binding_down_active(cpu) ||
	    target != CPUHP_OFFLINE)
		return -EPERM;
	return mt6797_a72_hotplug_executor_validate(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding,
		tasks_frozen, cpu_online(8), cpu_online(9),
		&binding->down_result);
}

int mt6797_a72_hotplug_binding_down_disable(
	unsigned int cpu, mt6797_a72_hotplug_disable_fn disable)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;
	int ret;

	if (!mt6797_a72_hotplug_binding_down_active(cpu) || !disable)
		return -EPERM;
	binding->disable = disable;
	ret = mt6797_a72_hotplug_executor_disable(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding, cpu,
		&binding->down_result);
	binding->disable = NULL;
	return ret;
}

int mt6797_a72_hotplug_binding_down_commit(unsigned int cpu)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	if (!mt6797_a72_hotplug_binding_down_active(cpu))
		return -EPERM;
	return mt6797_a72_hotplug_executor_commit(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding, cpu,
		&binding->down_result);
}

int mt6797_a72_hotplug_binding_down_returned(unsigned int cpu, int error)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	if (!mt6797_a72_hotplug_binding_down_active(cpu))
		return -EPERM;
	binding->cpu_off_returned = true;
	return mt6797_a72_hotplug_executor_target_returned(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding,
		error ?: -EIO, &binding->down_result);
}

int mt6797_a72_hotplug_binding_down_kill(
	unsigned int cpu, mt6797_a72_hotplug_affinity_fn affinity)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;
	int ret;

	if (!mt6797_a72_hotplug_binding_down_active(cpu) || !affinity)
		return -EPERM;
	binding->affinity = affinity;
	ret = mt6797_a72_hotplug_executor_kill(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding, cpu,
		true, cpu_online(8), cpu_online(9), &binding->down_result);
	binding->affinity = NULL;
	return ret;
}

int mt6797_a72_hotplug_binding_down_complete(unsigned int cpu,
					      enum cpuhp_state target)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	if (!mt6797_a72_hotplug_binding_down_active(cpu) ||
	    target != CPUHP_OFFLINE)
		return -EPERM;
	return mt6797_a72_hotplug_executor_complete(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding,
		cpu_online(8), cpu_online(9), &binding->down_result);
}

int mt6797_a72_hotplug_binding_down_failed(unsigned int cpu,
					    enum cpuhp_state target,
					    int error)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	if (!mt6797_a72_hotplug_binding_down_active(cpu) ||
	    target != CPUHP_OFFLINE || !error)
		return -EPERM;
	return mt6797_a72_hotplug_executor_fail(
		&binding->down, &mt6797_a72_hotplug_down_ops, binding, error,
		&binding->down_result);
}

int mt6797_a72_hotplug_binding_restore_preflight(unsigned int cpu,
						  enum cpuhp_state target)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;
	struct mt6797_a72_restore_executor_request request;

	if (!mt6797_a72_hotplug_binding_restore_active(cpu) ||
	    target != CPUHP_ONLINE ||
	    (u64)(uintptr_t)current != binding->task_identity)
		return -EPERM;
	request = (struct mt6797_a72_restore_executor_request) {
		.down_parent = binding->down_parent,
		.cpu = cpu,
		.target = target,
		.members = BIT(0),
		.online_mask = BIT(0),
		.system_online_mask = mt6797_a72_hotplug_online_mask(),
		.controller_identity = binding->task_identity,
		.watchdog_identity = binding->parent.watchdog_identity,
		.watchdog_owned = binding->parent.watchdog_identity != 0,
	};
	return mt6797_a72_restore_executor_preflight(
		&binding->restore, &mt6797_a72_hotplug_restore_ops, binding,
		&request, &binding->restore_result);
}

int mt6797_a72_hotplug_binding_restore_validate(unsigned int cpu,
						 int tasks_frozen,
						 enum cpuhp_state target)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	if (!mt6797_a72_hotplug_binding_restore_active(cpu) ||
	    target != CPUHP_ONLINE)
		return -EPERM;
	return mt6797_a72_restore_executor_validate(
		&binding->restore, &mt6797_a72_hotplug_restore_ops, binding,
		tasks_frozen, cpu_online(8), cpu_online(9),
		mt6797_a72_hotplug_online_mask(), &binding->restore_result);
}

int mt6797_a72_hotplug_binding_restore_boot(
	unsigned int cpu, mt6797_a72_hotplug_boot_fn boot)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;
	int ret;

	if (!mt6797_a72_hotplug_binding_restore_active(cpu) || !boot)
		return -EPERM;
	binding->boot = boot;
	ret = mt6797_a72_restore_executor_boot(
		&binding->restore, &mt6797_a72_hotplug_restore_ops, binding,
		cpu, cpu_online(8), cpu_online(9), &binding->restore_result);
	binding->boot = NULL;
	return ret;
}

int mt6797_a72_hotplug_binding_restore_secondary(unsigned int cpu)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	if (!mt6797_a72_hotplug_binding_restore_active(cpu))
		return -EPERM;
	return mt6797_a72_restore_executor_secondary_complete(
		&binding->restore, &mt6797_a72_hotplug_restore_ops, binding,
		cpu, &binding->restore_result);
}

int mt6797_a72_hotplug_binding_restore_complete(unsigned int cpu,
						 enum cpuhp_state target)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;
	u32 online = (cpu_online(8) ? BIT(0) : 0) |
		(cpu_online(9) ? BIT(1) : 0);

	if (!mt6797_a72_hotplug_binding_restore_active(cpu) ||
	    target != CPUHP_ONLINE)
		return -EPERM;
	return mt6797_a72_restore_executor_complete(
		&binding->restore, &mt6797_a72_hotplug_restore_ops, binding,
		cpu, target, cpu_online(8), cpu_online(9), online, online,
		mt6797_a72_hotplug_online_mask(), &binding->restore_result);
}

int mt6797_a72_hotplug_binding_restore_rollback(unsigned int cpu,
						 enum cpuhp_state state,
						 int error,
						 bool *suppress_initial)
{
	struct mt6797_a72_hotplug_binding *binding = &mt6797_a72_binding;

	(void)state;
	if (!mt6797_a72_hotplug_binding_restore_active(cpu))
		return -ENOENT;
	return mt6797_a72_restore_executor_rollback(
		&binding->restore, &mt6797_a72_hotplug_restore_ops, binding,
		cpu, error, &binding->restore_result, suppress_initial);
}
'''


KCONFIG_BLOCK = '''config MTK_MT6797_A72_HOTPLUG_BINDING
\tbool "MediaTek MT6797 production CPU9 hotplug binding"
\tdepends on ARM64 && ARCH_MEDIATEK && HOTPLUG_CPU
\tdepends on ARM64_MT6797_A72_P24_ADMISSION_HOOKS
\tdepends on ARM64_MT6797_A72_P32_ROLLBACK
\tdepends on MTK_MT6797_A72_ADMISSION_CONTROLLER
\tdepends on MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER
\tdepends on MTK_MT6797_A72_HOTPLUG_BINDER_CORE
\tdefault n
\thelp
\t  Bind the proven one-task CPU9 down/restore coordinator to the existing
\t  admission task and arm64 hotplug callbacks. The public architecture
\t  disable answer remains false; only the binder-owned device-lock-scoped
\t  request temporarily clears CPU9's cached offline-disabled flag.

\t  This option contains the physical CPU_OFF, affinity, snapshot, CPU8
\t  observation, and CPU_ON composition. Select it only in an isolated
\t  proof profile until a separately reviewed boot candidate enables it.

'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"anchor count changed for {path}: {old[:60]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    public = root / "include/linux/soc/mediatek/mt6797-a72-hotplug-binding.h"
    internal = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
    source = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
    for path, content in ((public, PUBLIC_HEADER), (internal, INTERNAL_HEADER),
                          (source, SOURCE)):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise SystemExit(f"refusing to overwrite {path}")
        path.write_text(content, encoding="utf-8")

    kconfig = root / "drivers/soc/mediatek/Kconfig"
    kconfig_anchor = "config MTK_MT6797_A72_CPU8_OBSERVER\n"
    replace_once(kconfig, kconfig_anchor, KCONFIG_BLOCK + kconfig_anchor)

    makefile = root / "drivers/soc/mediatek/Makefile"
    make_anchor = (
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDER_CORE) += "
        "mt6797-a72-hotplug-binder-core.o\n"
    )
    replace_once(
        makefile, make_anchor,
        make_anchor +
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING) += "
        "mt6797-a72-hotplug-binding.o\n",
    )

    admission = root / "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    replace_once(
        admission,
        "#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>\n",
        "#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>\n"
        "#include <linux/soc/mediatek/mt6797-a72-hotplug-binding.h>\n",
    )
    replace_once(
        admission,
        "\tstruct device *binder;\n\tstruct mt6797_a72_physical_source_context source;\n",
        "\tstruct device *binder;\n\tstruct device *platform;\n"
        "\tstruct device *clock;\n\tstruct device *bigidvfs;\n"
        "\tstruct mt6797_a72_physical_source_context source;\n",
    )
    replace_once(
        admission,
        "\tmt6797_a72_source_context_init(&controller->source, platform, clock,\n"
        "\t\t\t\t       bigidvfs);\n",
        "\tcontroller->platform = platform;\n\tcontroller->clock = clock;\n"
        "\tcontroller->bigidvfs = bigidvfs;\n"
        "\tmt6797_a72_source_context_init(&controller->source, platform, clock,\n"
        "\t\t\t\t       bigidvfs);\n",
    )
    replace_once(
        admission,
        "\treturn mt6797_a72_cpu9_admission_run(\n"
        "\t\t&controller->cpu9, &mt6797_a72_cpu9_admission_production_ops,\n"
        "\t\tcontroller);\n",
        "\tint ret;\n\n"
        "\tret = mt6797_a72_cpu9_admission_run(\n"
        "\t\t&controller->cpu9, &mt6797_a72_cpu9_admission_production_ops,\n"
        "\t\tcontroller);\n"
        "\tif (ret || !IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING))\n"
        "\t\treturn ret;\n"
        "\treturn mt6797_a72_hotplug_binding_run(\n"
        "\t\tcontroller->platform, controller->clock, controller->bigidvfs,\n"
        "\t\tcontroller->cpu9.cpu9_transaction.identity.generation);\n",
    )

    psci = root / "arch/arm64/kernel/mt6797_psci.c"
    replace_once(
        psci,
        "#include <linux/printk.h>\n",
        "#include <linux/printk.h>\n#include <linux/psci.h>\n",
    )
    replace_once(
        psci,
        "#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>\n",
        "#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>\n"
        "#include <linux/soc/mediatek/mt6797-a72-hotplug-binding.h>\n",
    )
    replace_once(
        psci,
        "static int mt6797_psci_cpu_up_preflight(unsigned int cpu,\n"
        "\t\t\t\t\tenum cpuhp_state target)\n{\n"
        "\tif (!mt6797_psci_is_a72(cpu))\n\t\treturn 0;\n\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)) {\n",
        "static int mt6797_psci_cpu_up_preflight(unsigned int cpu,\n"
        "\t\t\t\t\tenum cpuhp_state target)\n{\n"
        "\tif (!mt6797_psci_is_a72(cpu))\n\t\treturn 0;\n\n"
        "\tif (mt6797_a72_hotplug_binding_restore_active(cpu))\n"
        "\t\treturn mt6797_a72_hotplug_binding_restore_preflight(cpu, target);\n\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)) {\n",
    )
    replace_once(
        psci,
        "static int mt6797_psci_cpu_up_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t\t       enum cpuhp_state target)\n{\n"
        "\tif (!mt6797_psci_is_a72(cpu))\n\t\treturn 0;\n\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)) {\n",
        "static int mt6797_psci_cpu_up_validate(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t\t       enum cpuhp_state target)\n{\n"
        "\tif (!mt6797_psci_is_a72(cpu))\n\t\treturn 0;\n\n"
        "\tif (mt6797_a72_hotplug_binding_restore_active(cpu))\n"
        "\t\treturn mt6797_a72_hotplug_binding_restore_validate(\n"
        "\t\t\tcpu, tasks_frozen, target);\n\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)) {\n",
    )
    replace_once(
        psci,
        "\tif (cpu != 8 && cpu != 9)\n\t\treturn 0;\n",
        "\tif (cpu != 8 && cpu != 9)\n\t\treturn 0;\n"
        "\tif (mt6797_a72_hotplug_binding_restore_active(cpu)) {\n"
        "\t\tret = mt6797_a72_hotplug_binding_restore_rollback(\n"
        "\t\t\tcpu, state, error, &publish_p32);\n"
        "\t\tif (ret || !publish_p32)\n\t\t\treturn ret;\n"
        "\t}\n",
    )
    replace_once(
        psci,
        "#ifdef CONFIG_HOTPLUG_CPU\nstatic int mt6797_psci_cpu_disable(unsigned int cpu)\n",
        "#ifdef CONFIG_HOTPLUG_CPU\n"
        "static int mt6797_psci_affinity_info(unsigned int cpu,\n"
        "\t\t\t\t       unsigned int level)\n"
        "{\n\treturn psci_ops.affinity_info ?\n"
        "\t\tpsci_ops.affinity_info(cpu_logical_map(cpu), level) :\n"
        "\t\t-EOPNOTSUPP;\n}\n\n"
        "static int mt6797_psci_cpu_down_preflight(unsigned int cpu,\n"
        "\t\t\t\t\t   enum cpuhp_state target)\n"
        "{\n\treturn mt6797_a72_hotplug_binding_down_active(cpu) ?\n"
        "\t\tmt6797_a72_hotplug_binding_down_preflight(cpu, target) :\n"
        "\t\t-EOPNOTSUPP;\n}\n\n"
        "static int mt6797_psci_cpu_down_validate(unsigned int cpu,\n"
        "\t\t\t\t\t  int tasks_frozen,\n"
        "\t\t\t\t\t  enum cpuhp_state target)\n"
        "{\n\treturn mt6797_a72_hotplug_binding_down_active(cpu) ?\n"
        "\t\tmt6797_a72_hotplug_binding_down_validate(\n"
        "\t\t\tcpu, tasks_frozen, target) : -EOPNOTSUPP;\n}\n\n"
        "static int mt6797_psci_cpu_down_complete(unsigned int cpu,\n"
        "\t\t\t\t\t  enum cpuhp_state target)\n"
        "{\n\treturn mt6797_a72_hotplug_binding_down_active(cpu) ?\n"
        "\t\tmt6797_a72_hotplug_binding_down_complete(cpu, target) :\n"
        "\t\t-EOPNOTSUPP;\n}\n\n"
        "static int mt6797_psci_cpu_down_failed(unsigned int cpu,\n"
        "\t\t\t\t\tenum cpuhp_state target,\n"
        "\t\t\t\t\tint error)\n"
        "{\n\treturn mt6797_a72_hotplug_binding_down_active(cpu) ?\n"
        "\t\tmt6797_a72_hotplug_binding_down_failed(\n"
        "\t\t\tcpu, target, error) : -EOPNOTSUPP;\n}\n\n"
        "static int mt6797_psci_cpu_disable(unsigned int cpu)\n",
    )
    replace_once(
        psci,
        "\tint ret;\n\n\tret = mt6797_a72_membership_p32_cpu_disable(cpu);\n",
        "\tint ret;\n\n"
        "\tif (mt6797_a72_hotplug_binding_down_active(cpu))\n"
        "\t\treturn mt6797_a72_hotplug_binding_down_disable(\n"
        "\t\t\tcpu, cpu_psci_ops.cpu_disable);\n\n"
        "\tret = mt6797_a72_membership_p32_cpu_disable(cpu);\n",
    )
    replace_once(
        psci,
        "static void mt6797_psci_cpu_die(unsigned int cpu)\n{\n"
        "\tif (mt6797_a72_membership_p32_cpu_die(cpu))\n",
        "static void mt6797_psci_cpu_die(unsigned int cpu)\n{\n"
        "\tif (mt6797_a72_hotplug_binding_down_active(cpu)) {\n"
        "\t\tif (mt6797_a72_hotplug_binding_down_commit(cpu))\n"
        "\t\t\tcpu_park_loop();\n"
        "\t\tcpu_psci_ops.cpu_die(cpu);\n"
        "\t\t(void)mt6797_a72_hotplug_binding_down_returned(\n"
        "\t\t\tcpu, -EIO);\n"
        "\t\tcpu_park_loop();\n"
        "\t}\n"
        "\tif (mt6797_a72_membership_p32_cpu_die(cpu))\n",
    )
    replace_once(
        psci,
        "\tint ret;\n\n\tret = mt6797_a72_membership_p32_cpu_kill(cpu);\n",
        "\tint ret;\n\n"
        "\tif (mt6797_a72_hotplug_binding_down_active(cpu))\n"
        "\t\treturn mt6797_a72_hotplug_binding_down_kill(\n"
        "\t\t\tcpu, mt6797_psci_affinity_info);\n\n"
        "\tret = mt6797_a72_membership_p32_cpu_kill(cpu);\n",
    )
    replace_once(
        psci,
        "static int mt6797_psci_cpu_up_secondary_complete(unsigned int cpu)\n{\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n",
        "static int mt6797_psci_cpu_up_secondary_complete(unsigned int cpu)\n{\n"
        "\tif (mt6797_a72_hotplug_binding_restore_active(cpu))\n"
        "\t\treturn mt6797_a72_hotplug_binding_restore_secondary(cpu);\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n",
    )
    replace_once(
        psci,
        "{\n\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\treturn mt6797_a72_cpu9_binder_complete(cpu, target);\n",
        "{\n\tif (mt6797_a72_hotplug_binding_restore_active(cpu))\n"
        "\t\treturn mt6797_a72_hotplug_binding_restore_complete(cpu, target);\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\treturn mt6797_a72_cpu9_binder_complete(cpu, target);\n",
    )
    replace_once(
        psci,
        "static int mt6797_psci_cpu_boot(unsigned int cpu)\n{\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) && cpu == 8)\n",
        "static int mt6797_psci_cpu_boot(unsigned int cpu)\n{\n"
        "\tif (mt6797_a72_hotplug_binding_restore_active(cpu))\n"
        "\t\treturn mt6797_a72_hotplug_binding_restore_boot(\n"
        "\t\t\tcpu, cpu_psci_ops.cpu_boot);\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) && cpu == 8)\n",
    )
    replace_once(
        psci,
        "\t.cpu_can_disable = mt6797_psci_cpu_can_disable,\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_P32_ROLLBACK\n",
        "\t.cpu_can_disable = mt6797_psci_cpu_can_disable,\n"
        "#ifdef CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING\n"
        "\t.cpu_down_preflight = mt6797_psci_cpu_down_preflight,\n"
        "\t.cpu_down_validate = mt6797_psci_cpu_down_validate,\n"
        "\t.cpu_down_complete = mt6797_psci_cpu_down_complete,\n"
        "\t.cpu_down_failed = mt6797_psci_cpu_down_failed,\n"
        "#endif\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_P32_ROLLBACK\n",
    )

    print("hotplug_binding_source_edits=pass")


if __name__ == "__main__":
    main()
