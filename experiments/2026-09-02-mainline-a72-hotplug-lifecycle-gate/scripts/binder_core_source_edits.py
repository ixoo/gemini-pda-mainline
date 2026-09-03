#!/usr/bin/env python3
"""Apply the disconnected one-task A72 hotplug-binder core edits."""

from __future__ import annotations

import argparse
from pathlib import Path


KCONFIG_ANCHOR = """config MTK_MT6797_A72_CPU8_OBSERVER
\tbool \"MediaTek MT6797 retained-CPU8 hotplug observer\"
"""

KCONFIG_BLOCK = """config MTK_MT6797_A72_HOTPLUG_BINDER_CORE
\tbool \"MediaTek MT6797 disconnected A72 hotplug binder core\"
\tdepends on ARM64 && ARCH_MEDIATEK
\tdepends on MTK_MT6797_A72_DEFAULT_OFF_BINDER
\tdepends on PSTORE_GEMINI_A72_HOTPLUG_LEDGER
\tdepends on MTK_MT6797_A72_HOTPLUG_SNAPSHOT
\tdepends on MTK_MT6797_A72_CPU8_OBSERVER
\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR
\tdepends on MTK_MT6797_A72_RESTORE_EXECUTOR
\tdefault n
\thelp
\t  Build a disconnected, operation-injected coordinator for one exact
\t  same-task CPU9 down and parent-linked CPU9 restore. It validates the
\t  established parent, completed down, and completed restore identities.

\t  This core binds no production callback or trigger and contains no direct
\t  CPU, PSCI, MMIO, watchdog, retained-memory, network, storage, or device
\t  operation. If unsure, say N.

"""

HEADER = r'''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_HOTPLUG_BINDER_CORE_INTERNAL_H
#define __MT6797_A72_HOTPLUG_BINDER_CORE_INTERNAL_H

#include <linux/atomic.h>
#include <linux/types.h>

#include <linux/soc/mediatek/mt6797-a72-binder.h>

#include "mt6797-a72-restore-executor-internal.h"

#define MT6797_A72_HOTPLUG_BINDER_CPU9 9U
#define MT6797_A72_HOTPLUG_BINDER_ENTRY_STAGE 1U
#define MT6797_A72_HOTPLUG_BINDER_DOWN_STAGE 13U
#define MT6797_A72_HOTPLUG_BINDER_RESTORE_STAGE 17U

enum mt6797_a72_hotplug_binder_terminal {
	MT6797_A72_HOTPLUG_BINDER_TERMINAL_NONE,
	MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT = 1,
	MT6797_A72_HOTPLUG_BINDER_FAULT_POSTCOMMIT = 3,
	MT6797_A72_HOTPLUG_BINDER_RESTORE_FAULT = 4,
	MT6797_A72_HOTPLUG_BINDER_RESTORED_SUCCESS = 5,
};

enum mt6797_a72_hotplug_binder_lifecycle {
	MT6797_A72_HOTPLUG_BINDER_IDLE,
	MT6797_A72_HOTPLUG_BINDER_RUNNING,
	MT6797_A72_HOTPLUG_BINDER_TERMINAL,
};

struct mt6797_a72_hotplug_binder_controller {
	atomic_t consumed;
	atomic_t lifecycle;
};

struct mt6797_a72_hotplug_binder_request {
	u64 task_identity;
	u64 session_id;
};

struct mt6797_a72_hotplug_binder_result {
	struct mt6797_a72_binder_parent_proof parent;
	struct mt6797_a72_hotplug_transaction down_parent;
	struct mt6797_a72_hotplug_transaction restore;
	enum mt6797_a72_hotplug_binder_terminal terminal;
	u32 last_stage;
	s32 stage_errno;
	s32 publication_errno;
	u64 task_identity;
	u64 session_id;
	u32 current_task_calls;
	u32 parent_proof_calls;
	u32 ledger_begin_calls;
	u32 checkpoint_calls;
	u32 remove_cpu_calls;
	u32 restore_add_cpu_calls;
	u32 terminal_calls;
	u32 retries;
	bool attempted;
	bool ledger_active;
	bool down_completed;
	bool restore_completed;
	bool completed;
};

struct mt6797_a72_hotplug_binder_ops {
	u64 (*current_task_identity)(void *context);
	int (*parent_proof)(void *context,
			    struct mt6797_a72_binder_parent_proof *proof);
	int (*ledger_begin)(void *context, u64 session_id);
	int (*checkpoint)(
		void *context, u32 stage,
		const struct mt6797_a72_hotplug_binder_result *result);
	int (*remove_cpu)(void *context, unsigned int cpu,
			  struct mt6797_a72_hotplug_transaction *down_parent);
	int (*add_cpu_restore)(
		void *context, unsigned int cpu,
		const struct mt6797_a72_hotplug_transaction *down_parent,
		struct mt6797_a72_hotplug_transaction *restore);
	int (*terminal)(
		void *context,
		const struct mt6797_a72_hotplug_binder_result *result);
};

void mt6797_a72_hotplug_binder_init(
	struct mt6797_a72_hotplug_binder_controller *controller);
bool mt6797_a72_hotplug_binder_parent_valid(
	const struct mt6797_a72_binder_parent_proof *proof);
int mt6797_a72_hotplug_binder_run(
	struct mt6797_a72_hotplug_binder_controller *controller,
	const struct mt6797_a72_hotplug_binder_ops *ops, void *context,
	const struct mt6797_a72_hotplug_binder_request *request,
	struct mt6797_a72_hotplug_binder_result *result);

#endif /* __MT6797_A72_HOTPLUG_BINDER_CORE_INTERNAL_H */
'''

SOURCE = r'''// SPDX-License-Identifier: GPL-2.0-only
/* Disconnected one-task CPU9 down/restore binder core. */

#include <linux/bitops.h>
#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-hotplug-binder-core-internal.h"

static bool mt6797_a72_hotplug_binder_ops_valid(
	const struct mt6797_a72_hotplug_binder_ops *ops)
{
	return ops && ops->current_task_identity && ops->parent_proof &&
		ops->ledger_begin && ops->checkpoint && ops->remove_cpu &&
		ops->add_cpu_restore && ops->terminal;
}

static bool mt6797_a72_hotplug_binder_identity_valid(
	const struct mt6797_a72_binder_parent_identity *identity,
	u32 operation, unsigned int cpu, u64 mpidr)
{
	return identity && identity->abi == MT6797_A72_TRANSACTION_ABI &&
		identity->owner == ARM64_LATE_CPU_STARTUP_OWNER_MEMBERSHIP &&
		identity->operation == operation && identity->target_cpu == cpu &&
		identity->cpuhp_target == CPUHP_ONLINE &&
		identity->target_mpidr == mpidr && identity->cpu_on_entry_pa &&
		identity->generation && identity->cookie;
}

bool mt6797_a72_hotplug_binder_parent_valid(
	const struct mt6797_a72_binder_parent_proof *proof)
{
	u64 age;

	if (!proof || proof->abi != MT6797_A72_BINDER_PARENT_PROOF_ABI ||
	    proof->exact != 1 || proof->health != MT6797_A72_OWNER_AVAILABLE ||
	    proof->owner_phase != MT6797_A72_PHASE_IDLE ||
	    proof->hotplug_phase != MT6797_A72_HOTPLUG_IDLE ||
	    proof->members != (BIT(0) | BIT(1)) ||
	    proof->retired_mask != (BIT(0) | BIT(1)) ||
	    proof->hotplug_retired_mask ||
	    proof->provider_state != MT6797_A72_PROVIDER_HELD ||
	    proof->controller_present || proof->active_present ||
	    proof->hotplug_active_present ||
	    proof->online_mask != MT6797_A72_BINDER_PARENT_ONLINE_MASK ||
	    proof->online_count != 10 || !proof->provider_generation ||
	    !proof->provider_cookie || !proof->watchdog_identity ||
	    !proof->watchdog_takeover_ns ||
	    proof->observed_ns < proof->watchdog_takeover_ns)
		return false;
	if (!mt6797_a72_hotplug_binder_identity_valid(
		    &proof->cpu8, ARM64_LATE_CPU_STARTUP_OP_CPU8_UP, 8, 0x200) ||
	    !mt6797_a72_hotplug_binder_identity_valid(
		    &proof->cpu9, ARM64_LATE_CPU_STARTUP_OP_CPU9_UP, 9, 0x201) ||
	    proof->cpu8.generation == proof->cpu9.generation ||
	    proof->cpu8.cookie == proof->cpu9.cookie)
		return false;
	age = proof->observed_ns - proof->watchdog_takeover_ns;
	return proof->watchdog_age_ns == age &&
		age <= MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL;
}

static bool mt6797_a72_hotplug_binder_down_valid(
	const struct mt6797_a72_binder_parent_proof *parent,
	const struct mt6797_a72_hotplug_transaction *down)
{
	return mt6797_a72_restore_down_parent_valid(down) &&
		down->identity.parent_generation == parent->cpu9.generation &&
		down->identity.parent_cookie == parent->cpu9.cookie &&
		down->provider_identity.generation == parent->provider_generation &&
		down->provider_identity.cookie == parent->provider_cookie;
}

void mt6797_a72_hotplug_binder_init(
	struct mt6797_a72_hotplug_binder_controller *controller)
{
	if (!controller)
		return;
	atomic_set(&controller->consumed, 0);
	atomic_set(&controller->lifecycle, MT6797_A72_HOTPLUG_BINDER_IDLE);
}

static int mt6797_a72_hotplug_binder_terminal(
	struct mt6797_a72_hotplug_binder_controller *controller,
	const struct mt6797_a72_hotplug_binder_ops *ops, void *context,
	struct mt6797_a72_hotplug_binder_result *result,
	enum mt6797_a72_hotplug_binder_terminal terminal, int error)
{
	int ret;

	result->terminal = terminal;
	result->terminal_calls++;
	ret = ops->terminal(context, result);
	if (ret) {
		result->publication_errno = ret;
		if (terminal == MT6797_A72_HOTPLUG_BINDER_RESTORED_SUCCESS) {
			result->terminal = MT6797_A72_HOTPLUG_BINDER_RESTORE_FAULT;
			result->stage_errno = ret;
			error = ret;
		}
	}
	atomic_set_release(&controller->lifecycle,
			   MT6797_A72_HOTPLUG_BINDER_TERMINAL);
	return error;
}

static int mt6797_a72_hotplug_binder_fail(
	struct mt6797_a72_hotplug_binder_controller *controller,
	const struct mt6797_a72_hotplug_binder_ops *ops, void *context,
	struct mt6797_a72_hotplug_binder_result *result,
	enum mt6797_a72_hotplug_binder_terminal terminal, int error)
{
	result->stage_errno = error;
	return mt6797_a72_hotplug_binder_terminal(
		controller, ops, context, result, terminal, error);
}

static int mt6797_a72_hotplug_binder_checkpoint(
	struct mt6797_a72_hotplug_binder_controller *controller,
	const struct mt6797_a72_hotplug_binder_ops *ops, void *context,
	struct mt6797_a72_hotplug_binder_result *result, u32 stage,
	enum mt6797_a72_hotplug_binder_terminal failure)
{
	int ret;

	result->last_stage = stage;
	result->checkpoint_calls++;
	ret = ops->checkpoint(context, stage, result);
	if (!ret)
		return 0;
	result->publication_errno = ret;
	return mt6797_a72_hotplug_binder_fail(
		controller, ops, context, result, failure, ret);
}

int mt6797_a72_hotplug_binder_run(
	struct mt6797_a72_hotplug_binder_controller *controller,
	const struct mt6797_a72_hotplug_binder_ops *ops, void *context,
	const struct mt6797_a72_hotplug_binder_request *request,
	struct mt6797_a72_hotplug_binder_result *result)
{
	enum mt6797_a72_hotplug_binder_terminal failure;
	int ret;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	result->terminal = MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT;
	if (!controller || !mt6797_a72_hotplug_binder_ops_valid(ops) ||
	    !request || !request->task_identity || !request->session_id)
		return -EINVAL;
	result->current_task_calls++;
	if (ops->current_task_identity(context) != request->task_identity)
		return -EPERM;
	if (atomic_cmpxchg(&controller->consumed, 0, 1) ||
	    atomic_cmpxchg(&controller->lifecycle,
			   MT6797_A72_HOTPLUG_BINDER_IDLE,
			   MT6797_A72_HOTPLUG_BINDER_RUNNING) !=
		    MT6797_A72_HOTPLUG_BINDER_IDLE)
		return -EALREADY;
	result->attempted = true;
	result->terminal = MT6797_A72_HOTPLUG_BINDER_TERMINAL_NONE;
	result->task_identity = request->task_identity;
	result->session_id = request->session_id;

	result->parent_proof_calls++;
	ret = ops->parent_proof(context, &result->parent);
	if (ret || !mt6797_a72_hotplug_binder_parent_valid(&result->parent))
		return mt6797_a72_hotplug_binder_fail(
			controller, ops, context, result,
			MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT,
			ret ? ret : -EPROTO);
	result->ledger_begin_calls++;
	ret = ops->ledger_begin(context, request->session_id);
	if (ret)
		return mt6797_a72_hotplug_binder_fail(
			controller, ops, context, result,
			MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT, ret);
	result->ledger_active = true;
	ret = mt6797_a72_hotplug_binder_checkpoint(
		controller, ops, context, result,
		MT6797_A72_HOTPLUG_BINDER_ENTRY_STAGE,
		MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT);
	if (ret)
		return ret;

	result->remove_cpu_calls++;
	ret = ops->remove_cpu(context, MT6797_A72_HOTPLUG_BINDER_CPU9,
			      &result->down_parent);
	if (ret || !mt6797_a72_hotplug_binder_down_valid(
			   &result->parent, &result->down_parent)) {
		failure = result->down_parent.off_committed ?
			MT6797_A72_HOTPLUG_BINDER_FAULT_POSTCOMMIT :
			MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT;
		return mt6797_a72_hotplug_binder_fail(
			controller, ops, context, result, failure,
			ret ? ret : -EPROTO);
	}
	result->down_completed = true;
	ret = mt6797_a72_hotplug_binder_checkpoint(
		controller, ops, context, result,
		MT6797_A72_HOTPLUG_BINDER_DOWN_STAGE,
		MT6797_A72_HOTPLUG_BINDER_FAULT_POSTCOMMIT);
	if (ret)
		return ret;

	result->restore_add_cpu_calls++;
	ret = ops->add_cpu_restore(context,
				   MT6797_A72_HOTPLUG_BINDER_CPU9,
				   &result->down_parent, &result->restore);
	if (ret || !mt6797_a72_restore_transaction_valid(
			   &result->down_parent, &result->restore, true, true))
		return mt6797_a72_hotplug_binder_fail(
			controller, ops, context, result,
			MT6797_A72_HOTPLUG_BINDER_RESTORE_FAULT,
			ret ? ret : -EPROTO);
	result->restore_completed = true;
	ret = mt6797_a72_hotplug_binder_checkpoint(
		controller, ops, context, result,
		MT6797_A72_HOTPLUG_BINDER_RESTORE_STAGE,
		MT6797_A72_HOTPLUG_BINDER_RESTORE_FAULT);
	if (ret)
		return ret;
	result->completed = true;
	return mt6797_a72_hotplug_binder_terminal(
		controller, ops, context, result,
		MT6797_A72_HOTPLUG_BINDER_RESTORED_SUCCESS, 0);
}
'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"anchor count changed for {path}: {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    kconfig = source / "drivers/soc/mediatek/Kconfig"
    makefile = source / "drivers/soc/mediatek/Makefile"
    replace_once(kconfig, KCONFIG_ANCHOR, KCONFIG_BLOCK + KCONFIG_ANCHOR)
    make_anchor = (
        "obj-$(CONFIG_MTK_MT6797_A72_RESTORE_EXECUTOR) += "
        "mt6797-a72-restore-executor.o\n"
    )
    replace_once(
        makefile,
        make_anchor,
        make_anchor +
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDER_CORE) += "
        "mt6797-a72-hotplug-binder-core.o\n",
    )
    write_new(
        source / "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h",
        HEADER,
    )
    write_new(
        source / "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
        SOURCE,
    )


if __name__ == "__main__":
    main()
