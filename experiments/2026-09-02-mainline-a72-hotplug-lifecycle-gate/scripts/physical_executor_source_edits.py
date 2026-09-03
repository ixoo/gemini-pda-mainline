#!/usr/bin/env python3
"""Add the disconnected hardware-free CPU9 physical executor."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


KCONFIG = dedent("""\
    config MTK_MT6797_A72_HOTPLUG_EXECUTOR
    \tbool "MediaTek MT6797 CPU9 physical-hotplug executor"
    \tdepends on ARM64 && ARCH_MEDIATEK
    \tdefault n
    \thelp
    \t  Build a disconnected, operation-injected state machine for one CPU9
    \t  physical-off transaction while CPU8 remains online. It validates an
    \t  inherited recovery watchdog, one CPU_OFF authorization, one active
    \t  affinity call, independent power readback, and shared-state invariance.

    \t  This option binds no production callback, leaves CPU hotplug vetoed,
    \t  and contains no PSCI, MMIO, watchdog, retained-memory, CPU request, or
    \t  device operation. If unsure, say N.

    config MTK_MT6797_A72_HOTPLUG_EXECUTOR_KUNIT_TEST
    \tbool "KUnit tests for the MT6797 CPU9 hotplug executor"
    \tdepends on KUNIT=y
    \tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR
    \tdefault n
    \thelp
    \t  Exercise the split controller/target lifecycle, exact call budgets,
    \t  readback classifier, reversible pre-commit rejection, terminal
    \t  post-commit failure, and atomic one-shot behavior in memory only.

    \t  These tests perform no CPU, PSCI, MMIO, watchdog, retained-memory, or
    \t  device action. If unsure, say N.

    """)


HEADER = dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __MT6797_A72_HOTPLUG_EXECUTOR_INTERNAL_H
    #define __MT6797_A72_HOTPLUG_EXECUTOR_INTERNAL_H

    #include <linux/atomic.h>
    #include <linux/bitops.h>
    #include <linux/types.h>

    #define MT6797_A72_HOTPLUG_CPU8 8U
    #define MT6797_A72_HOTPLUG_CPU9 9U
    #define MT6797_A72_HOTPLUG_ENTRY_MEMBERS (BIT(0) | BIT(1))
    #define MT6797_A72_HOTPLUG_OFFLINE_MEMBERS BIT(0)
    #define MT6797_A72_HOTPLUG_CPU8_STATUS BIT(7)
    #define MT6797_A72_HOTPLUG_CPU9_STATUS BIT(6)
    #define MT6797_A72_HOTPLUG_EXT_ISO_MASK BIT(1)
    #define MT6797_A72_HOTPLUG_DCM_MASK GENMASK(6, 0)
    #define MT6797_A72_HOTPLUG_CCI_REQUEST_MASK GENMASK(1, 0)
    #define MT6797_A72_HOTPLUG_CCI_PENDING BIT(0)
    #define MT6797_A72_HOTPLUG_AFFINITY_LEVEL0 0U
    #define MT6797_A72_HOTPLUG_AFFINITY_OFF 1
    #define MT6797_A72_HOTPLUG_CLOCK_VALUES 18U
    #define MT6797_A72_HOTPLUG_BIGIDVFS_VALUES 4U

    enum mt6797_a72_hotplug_executor_stage {
    \tMT6797_A72_HOTPLUG_STAGE_NONE,
    \tMT6797_A72_HOTPLUG_STAGE_OWNER_PREPARE,
    \tMT6797_A72_HOTPLUG_STAGE_WATCHDOG_VALIDATE,
    \tMT6797_A72_HOTPLUG_STAGE_BASELINE,
    \tMT6797_A72_HOTPLUG_STAGE_OWNER_VALIDATE,
    \tMT6797_A72_HOTPLUG_STAGE_TARGET_DISABLE,
    \tMT6797_A72_HOTPLUG_STAGE_OFF_COMMIT,
    \tMT6797_A72_HOTPLUG_STAGE_AFFINITY,
    \tMT6797_A72_HOTPLUG_STAGE_POST_STATE,
    \tMT6797_A72_HOTPLUG_STAGE_CPU8_CALLBACK,
    \tMT6797_A72_HOTPLUG_STAGE_OWNER_PROOF,
    \tMT6797_A72_HOTPLUG_STAGE_OWNER_COMPLETE,
    \tMT6797_A72_HOTPLUG_STAGE_COUNT,
    };

    enum mt6797_a72_hotplug_executor_phase {
    \tMT6797_A72_HOTPLUG_BEFORE,
    \tMT6797_A72_HOTPLUG_AFTER,
    };

    enum mt6797_a72_hotplug_executor_terminal {
    \tMT6797_A72_HOTPLUG_TERMINAL_NONE,
    \tMT6797_A72_HOTPLUG_REJECTED_PRECOMMIT,
    \tMT6797_A72_HOTPLUG_FAULT_POSTCOMMIT,
    \tMT6797_A72_HOTPLUG_DOWN_COMPLETE,
    };

    enum mt6797_a72_hotplug_executor_lifecycle {
    \tMT6797_A72_HOTPLUG_LIFECYCLE_IDLE,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_PREFLIGHT,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_PREPARED,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_VALIDATING,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_VALIDATED,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_DISABLING,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_DISABLED,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_COMMITTING,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_OFF_COMMITTED,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_KILLING,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_OFF_PROVEN,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_COMPLETING,
    \tMT6797_A72_HOTPLUG_LIFECYCLE_TERMINAL,
    };

    struct mt6797_a72_hotplug_readback {
    \tu32 spm_pwr_status;
    \tu32 spm_pwr_status_2nd;
    \tu32 spm_cpu_pwr_status;
    \tu32 spm_cpu_pwr_status_2nd;
    \tu32 spm_mp2_cpusys_pwr_con;
    \tu32 spm_mp2_cpu0_pwr_con;
    \tu32 spm_mp2_cpu1_pwr_con;
    \tu32 spm_cpu_ext_buck_iso;
    \tu32 mp2_sync_dcm;
    \tu32 cci_mp2_port_control;
    \tu32 cci_status_before;
    \tu32 cci_status_after;
    \tu8 provider[5];
    \tu32 clock[MT6797_A72_HOTPLUG_CLOCK_VALUES];
    \tu32 bigidvfs[MT6797_A72_HOTPLUG_BIGIDVFS_VALUES];
    \tbool valid;
    };

    struct mt6797_a72_hotplug_executor_controller {
    \tatomic_t consumed;
    \tatomic_t lifecycle;
    };

    #define MT6797_A72_HOTPLUG_EXECUTOR_CONTROLLER_INIT \\
    \t{ .consumed = ATOMIC_INIT(0), \\
    \t  .lifecycle = ATOMIC_INIT(MT6797_A72_HOTPLUG_LIFECYCLE_IDLE) }

    struct mt6797_a72_hotplug_executor_request {
    \tunsigned int cpu;
    \tu32 members;
    \tu32 online_mask;
    \tu64 watchdog_identity;
    \tbool owner_parent_exact;
    \tbool watchdog_owned;
    };

    struct mt6797_a72_hotplug_executor_result {
    \tstruct mt6797_a72_hotplug_readback baseline;
    \tstruct mt6797_a72_hotplug_readback post_state;
    \tenum mt6797_a72_hotplug_executor_terminal terminal;
    \tenum mt6797_a72_hotplug_executor_stage last_stage;
    \ts32 stage_errno;
    \ts32 publication_errno;
    \tu64 watchdog_identity;
    \tu32 cpu_off_authorizations;
    \tu32 affinity_calls;
    \tu32 snapshots;
    \tu32 cpu8_callbacks;
    \tu32 proof_calls;
    \tu32 fail_calls;
    \tu32 checkpoints;
    \tu32 terminal_commits;
    \tbool attempted;
    \tbool owner_prepared;
    \tbool watchdog_validated;
    \tbool off_committed;
    \tbool off_proven;
    \tbool completed;
    };

    struct mt6797_a72_hotplug_executor_ops {
    \tint (*checkpoint)(void *context,
    \t\t\t  enum mt6797_a72_hotplug_executor_phase phase,
    \t\t\t  enum mt6797_a72_hotplug_executor_stage stage,
    \t\t\t  const struct mt6797_a72_hotplug_executor_result *result);
    \tint (*prepare_down)(void *context,
    \t\t\t    const struct mt6797_a72_hotplug_executor_request *request);
    \tint (*watchdog_validate)(void *context, u64 identity);
    \tint (*snapshot)(void *context,
    \t\t\tstruct mt6797_a72_hotplug_readback *readback);
    \tint (*validate_down)(void *context, bool tasks_frozen,
    \t\t\t     bool cpu8_online, bool cpu9_online);
    \tint (*target_disable)(void *context, unsigned int cpu);
    \tint (*commit_off)(void *context, unsigned int cpu);
    \tint (*affinity_info)(void *context, unsigned int cpu,
    \t\t\t     unsigned int level);
    \tint (*cpu8_callback)(void *context, unsigned int cpu);
    \tint (*prove_off)(void *context,
    \t\t\t const struct mt6797_a72_hotplug_executor_result *result);
    \tint (*complete_down)(void *context, bool cpu8_online,
    \t\t\t     bool cpu9_online);
    \tint (*fail_down)(void *context, int error);
    \tint (*terminal)(void *context,
    \t\t\tconst struct mt6797_a72_hotplug_executor_result *result);
    };

    bool mt6797_a72_hotplug_readback_proves_cpu9_off(
    \tconst struct mt6797_a72_hotplug_readback *baseline,
    \tconst struct mt6797_a72_hotplug_readback *post_state);
    int mt6797_a72_hotplug_executor_preflight(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tconst struct mt6797_a72_hotplug_executor_request *request,
    \tstruct mt6797_a72_hotplug_executor_result *result);
    int mt6797_a72_hotplug_executor_validate(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tbool tasks_frozen, bool cpu8_online, bool cpu9_online,
    \tstruct mt6797_a72_hotplug_executor_result *result);
    int mt6797_a72_hotplug_executor_disable(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tunsigned int cpu,
    \tstruct mt6797_a72_hotplug_executor_result *result);
    int mt6797_a72_hotplug_executor_commit(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tunsigned int cpu,
    \tstruct mt6797_a72_hotplug_executor_result *result);
    int mt6797_a72_hotplug_executor_target_returned(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tint error, struct mt6797_a72_hotplug_executor_result *result);
    int mt6797_a72_hotplug_executor_kill(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tunsigned int cpu, bool target_dead, bool cpu8_online,
    \tbool cpu9_online, struct mt6797_a72_hotplug_executor_result *result);
    int mt6797_a72_hotplug_executor_complete(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tbool cpu8_online, bool cpu9_online,
    \tstruct mt6797_a72_hotplug_executor_result *result);
    int mt6797_a72_hotplug_executor_fail(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tint error, struct mt6797_a72_hotplug_executor_result *result);

    #endif /* __MT6797_A72_HOTPLUG_EXECUTOR_INTERNAL_H */
    """)


SOURCE = dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* Hardware-free split executor for one MT6797 CPU9-off transaction. */

    #include <linux/errno.h>
    #include <linux/string.h>

    #include "mt6797-a72-hotplug-executor-internal.h"

    static bool mt6797_a72_hotplug_ops_valid(
    \tconst struct mt6797_a72_hotplug_executor_ops *ops)
    {
    \treturn ops && ops->checkpoint && ops->prepare_down &&
    \t\tops->watchdog_validate && ops->snapshot && ops->validate_down &&
    \t\tops->target_disable && ops->commit_off && ops->affinity_info &&
    \t\tops->cpu8_callback && ops->prove_off && ops->complete_down &&
    \t\tops->fail_down && ops->terminal;
    }

    static bool mt6797_a72_hotplug_request_valid(
    \tconst struct mt6797_a72_hotplug_executor_request *request)
    {
    \treturn request && request->cpu == MT6797_A72_HOTPLUG_CPU9 &&
    \t\trequest->members == MT6797_A72_HOTPLUG_ENTRY_MEMBERS &&
    \t\trequest->online_mask == MT6797_A72_HOTPLUG_ENTRY_MEMBERS &&
    \t\trequest->watchdog_identity && request->owner_parent_exact &&
    \t\trequest->watchdog_owned;
    }

    static bool mt6797_a72_hotplug_status_exact(
    \tconst struct mt6797_a72_hotplug_readback *readback, bool cpu9_online)
    {
    \tu32 required = MT6797_A72_HOTPLUG_CPU8_STATUS;
    \tu32 forbidden = 0;

    \tif (cpu9_online)
    \t\trequired |= MT6797_A72_HOTPLUG_CPU9_STATUS;
    \telse
    \t\tforbidden = MT6797_A72_HOTPLUG_CPU9_STATUS;
    \treturn readback->valid &&
    \t\t(readback->spm_cpu_pwr_status & required) == required &&
    \t\t(readback->spm_cpu_pwr_status_2nd & required) == required &&
    \t\t!(readback->spm_cpu_pwr_status & forbidden) &&
    \t\t!(readback->spm_cpu_pwr_status_2nd & forbidden) &&
    \t\t!((readback->cci_status_before | readback->cci_status_after) &
    \t\t  MT6797_A72_HOTPLUG_CCI_PENDING);
    }

    bool mt6797_a72_hotplug_readback_proves_cpu9_off(
    \tconst struct mt6797_a72_hotplug_readback *baseline,
    \tconst struct mt6797_a72_hotplug_readback *post_state)
    {
    \tif (!baseline || !post_state ||
    \t    !mt6797_a72_hotplug_status_exact(baseline, true) ||
    \t    !mt6797_a72_hotplug_status_exact(post_state, false))
    \t\treturn false;
    \treturn baseline->spm_mp2_cpusys_pwr_con ==
    \t\t\tpost_state->spm_mp2_cpusys_pwr_con &&
    \t\tbaseline->spm_mp2_cpu0_pwr_con ==
    \t\t\tpost_state->spm_mp2_cpu0_pwr_con &&
    \t\t!((baseline->spm_cpu_ext_buck_iso ^
    \t\t   post_state->spm_cpu_ext_buck_iso) &
    \t\t  MT6797_A72_HOTPLUG_EXT_ISO_MASK) &&
    \t\t!((baseline->mp2_sync_dcm ^ post_state->mp2_sync_dcm) &
    \t\t  MT6797_A72_HOTPLUG_DCM_MASK) &&
    \t\t!((baseline->cci_mp2_port_control ^
    \t\t   post_state->cci_mp2_port_control) &
    \t\t  MT6797_A72_HOTPLUG_CCI_REQUEST_MASK) &&
    \t\t!memcmp(baseline->provider, post_state->provider,
    \t\t\tsizeof(baseline->provider)) &&
    \t\t!memcmp(baseline->clock, post_state->clock,
    \t\t\tsizeof(baseline->clock)) &&
    \t\t!memcmp(baseline->bigidvfs, post_state->bigidvfs,
    \t\t\tsizeof(baseline->bigidvfs));
    }

    static int mt6797_a72_hotplug_checkpoint(
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tstruct mt6797_a72_hotplug_executor_result *result,
    \tenum mt6797_a72_hotplug_executor_phase phase,
    \tenum mt6797_a72_hotplug_executor_stage stage)
    {
    \tint ret;

    \tresult->last_stage = stage;
    \tresult->checkpoints++;
    \tret = ops->checkpoint(context, phase, stage, result);
    \tif (ret)
    \t\tresult->publication_errno = ret;
    \treturn ret;
    }

    static int mt6797_a72_hotplug_terminal(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tstruct mt6797_a72_hotplug_executor_result *result,
    \tenum mt6797_a72_hotplug_executor_terminal terminal, int error)
    {
    \tint ret;

    \tresult->terminal = terminal;
    \tresult->terminal_commits++;
    \tret = ops->terminal(context, result);
    \tif (ret) {
    \t\tresult->publication_errno = ret;
    \t\tif (terminal == MT6797_A72_HOTPLUG_DOWN_COMPLETE) {
    \t\t\tresult->terminal = MT6797_A72_HOTPLUG_FAULT_POSTCOMMIT;
    \t\t\tresult->stage_errno = ret;
    \t\t\terror = ret;
    \t\t}
    \t}
    \tatomic_set_release(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_TERMINAL);
    \treturn error;
    }

    static int mt6797_a72_hotplug_reject(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tstruct mt6797_a72_hotplug_executor_result *result, int error)
    {
    \tint fail_ret = 0;

    \tresult->stage_errno = error;
    \tif (result->owner_prepared) {
    \t\tresult->fail_calls++;
    \t\tfail_ret = ops->fail_down(context, error);
    \t\tif (fail_ret)
    \t\t\tresult->publication_errno = fail_ret;
    \t}
    \treturn mt6797_a72_hotplug_terminal(controller, ops, context, result,
    \t\tMT6797_A72_HOTPLUG_REJECTED_PRECOMMIT,
    \t\tfail_ret ? fail_ret : error);
    }

    static int mt6797_a72_hotplug_fault(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tstruct mt6797_a72_hotplug_executor_result *result, int error)
    {
    \tint fail_ret;

    \tresult->stage_errno = error;
    \tresult->fail_calls++;
    \tfail_ret = ops->fail_down(context, error);
    \tif (fail_ret)
    \t\tresult->publication_errno = fail_ret;
    \treturn mt6797_a72_hotplug_terminal(controller, ops, context, result,
    \t\tMT6797_A72_HOTPLUG_FAULT_POSTCOMMIT,
    \t\tfail_ret ? fail_ret : error);
    }

    static int mt6797_a72_hotplug_precommit_checkpoint(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tstruct mt6797_a72_hotplug_executor_result *result,
    \tenum mt6797_a72_hotplug_executor_phase phase,
    \tenum mt6797_a72_hotplug_executor_stage stage)
    {
    \tint ret = mt6797_a72_hotplug_checkpoint(ops, context, result,
    \t\t\t\t\t       phase, stage);

    \treturn ret ? mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t\t result, ret) : 0;
    }

    int mt6797_a72_hotplug_executor_preflight(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tconst struct mt6797_a72_hotplug_executor_request *request,
    \tstruct mt6797_a72_hotplug_executor_result *result)
    {
    \tint ret;

    \tif (!result)
    \t\treturn -EINVAL;
    \tmemset(result, 0, sizeof(*result));
    \tresult->terminal = MT6797_A72_HOTPLUG_REJECTED_PRECOMMIT;
    \tif (!controller || !mt6797_a72_hotplug_ops_valid(ops) ||
    \t    !mt6797_a72_hotplug_request_valid(request))
    \t\treturn -EINVAL;
    \tif (atomic_cmpxchg(&controller->consumed, 0, 1))
    \t\treturn -EALREADY;
    \tif (atomic_cmpxchg(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_IDLE,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_PREFLIGHT) !=
    \t    MT6797_A72_HOTPLUG_LIFECYCLE_IDLE)
    \t\treturn -EALREADY;
    \tresult->attempted = true;
    \tresult->terminal = MT6797_A72_HOTPLUG_TERMINAL_NONE;
    \tresult->watchdog_identity = request->watchdog_identity;

    \tret = mt6797_a72_hotplug_precommit_checkpoint(controller, ops,
    \t\tcontext, result, MT6797_A72_HOTPLUG_BEFORE,
    \t\tMT6797_A72_HOTPLUG_STAGE_OWNER_PREPARE);
    \tif (ret)
    \t\treturn ret;
    \tret = ops->prepare_down(context, request);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, ret);
    \tresult->owner_prepared = true;
    \tret = mt6797_a72_hotplug_precommit_checkpoint(controller, ops,
    \t\tcontext, result, MT6797_A72_HOTPLUG_AFTER,
    \t\tMT6797_A72_HOTPLUG_STAGE_OWNER_PREPARE);
    \tif (ret)
    \t\treturn ret;

    \tret = mt6797_a72_hotplug_precommit_checkpoint(controller, ops,
    \t\tcontext, result, MT6797_A72_HOTPLUG_BEFORE,
    \t\tMT6797_A72_HOTPLUG_STAGE_WATCHDOG_VALIDATE);
    \tif (ret)
    \t\treturn ret;
    \tret = ops->watchdog_validate(context, request->watchdog_identity);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, ret);
    \tresult->watchdog_validated = true;
    \tret = mt6797_a72_hotplug_precommit_checkpoint(controller, ops,
    \t\tcontext, result, MT6797_A72_HOTPLUG_AFTER,
    \t\tMT6797_A72_HOTPLUG_STAGE_WATCHDOG_VALIDATE);
    \tif (ret)
    \t\treturn ret;

    \tret = mt6797_a72_hotplug_precommit_checkpoint(controller, ops,
    \t\tcontext, result, MT6797_A72_HOTPLUG_BEFORE,
    \t\tMT6797_A72_HOTPLUG_STAGE_BASELINE);
    \tif (ret)
    \t\treturn ret;
    \tresult->snapshots++;
    \tret = ops->snapshot(context, &result->baseline);
    \tif (ret || !mt6797_a72_hotplug_status_exact(&result->baseline, true))
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, ret ? ret : -EPROTO);
    \tret = mt6797_a72_hotplug_precommit_checkpoint(controller, ops,
    \t\tcontext, result, MT6797_A72_HOTPLUG_AFTER,
    \t\tMT6797_A72_HOTPLUG_STAGE_BASELINE);
    \tif (ret)
    \t\treturn ret;
    \tatomic_set_release(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_PREPARED);
    \treturn 0;
    }

    int mt6797_a72_hotplug_executor_validate(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tbool tasks_frozen, bool cpu8_online, bool cpu9_online,
    \tstruct mt6797_a72_hotplug_executor_result *result)
    {
    \tint ret;

    \tif (!controller || !result || !mt6797_a72_hotplug_ops_valid(ops))
    \t\treturn -EINVAL;
    \tif (atomic_cmpxchg(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_PREPARED,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_VALIDATING) !=
    \t    MT6797_A72_HOTPLUG_LIFECYCLE_PREPARED)
    \t\treturn -EALREADY;
    \tresult->last_stage = MT6797_A72_HOTPLUG_STAGE_OWNER_VALIDATE;
    \tif (tasks_frozen || !cpu8_online || !cpu9_online)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, -EPERM);
    \tret = ops->validate_down(context, tasks_frozen, cpu8_online,
    \t\t\t\t cpu9_online);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, ret);
    \tatomic_set_release(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_VALIDATED);
    \treturn 0;
    }

    int mt6797_a72_hotplug_executor_disable(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tunsigned int cpu,
    \tstruct mt6797_a72_hotplug_executor_result *result)
    {
    \tint ret;

    \tif (!controller || !result || !mt6797_a72_hotplug_ops_valid(ops))
    \t\treturn -EINVAL;
    \tif (atomic_cmpxchg(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_VALIDATED,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_DISABLING) !=
    \t    MT6797_A72_HOTPLUG_LIFECYCLE_VALIDATED)
    \t\treturn -EALREADY;
    \tresult->last_stage = MT6797_A72_HOTPLUG_STAGE_TARGET_DISABLE;
    \tif (cpu != MT6797_A72_HOTPLUG_CPU9)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, -EINVAL);
    \tret = ops->target_disable(context, cpu);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, ret);
    \tatomic_set_release(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_DISABLED);
    \treturn 0;
    }

    int mt6797_a72_hotplug_executor_commit(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tunsigned int cpu,
    \tstruct mt6797_a72_hotplug_executor_result *result)
    {
    \tint ret;

    \tif (!controller || !result || !mt6797_a72_hotplug_ops_valid(ops))
    \t\treturn -EINVAL;
    \tif (atomic_cmpxchg(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_DISABLED,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_COMMITTING) !=
    \t    MT6797_A72_HOTPLUG_LIFECYCLE_DISABLED)
    \t\treturn -EALREADY;
    \tif (cpu != MT6797_A72_HOTPLUG_CPU9)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, -EINVAL);
    \tret = mt6797_a72_hotplug_precommit_checkpoint(controller, ops,
    \t\tcontext, result, MT6797_A72_HOTPLUG_BEFORE,
    \t\tMT6797_A72_HOTPLUG_STAGE_OFF_COMMIT);
    \tif (ret)
    \t\treturn ret;
    \tret = ops->commit_off(context, cpu);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_reject(controller, ops, context,
    \t\t\t\t\t  result, ret);
    \tresult->off_committed = true;
    \tresult->cpu_off_authorizations = 1;
    \tatomic_set_release(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_OFF_COMMITTED);
    \tret = mt6797_a72_hotplug_checkpoint(ops, context, result,
    \t\t\t\t\tMT6797_A72_HOTPLUG_AFTER,
    \t\t\t\t\tMT6797_A72_HOTPLUG_STAGE_OFF_COMMIT);
    \treturn ret ? mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, ret) : 0;
    }

    int mt6797_a72_hotplug_executor_target_returned(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tint error, struct mt6797_a72_hotplug_executor_result *result)
    {
    \tif (!controller || !result || !mt6797_a72_hotplug_ops_valid(ops))
    \t\treturn -EINVAL;
    \tif (atomic_read_acquire(&controller->lifecycle) !=
    \t    MT6797_A72_HOTPLUG_LIFECYCLE_OFF_COMMITTED)
    \t\treturn -EALREADY;
    \treturn mt6797_a72_hotplug_fault(controller, ops, context, result,
    \t\t\t\t\terror ? error : -EIO);
    }

    int mt6797_a72_hotplug_executor_kill(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tunsigned int cpu, bool target_dead, bool cpu8_online,
    \tbool cpu9_online, struct mt6797_a72_hotplug_executor_result *result)
    {
    \tint ret;

    \tif (!controller || !result || !mt6797_a72_hotplug_ops_valid(ops))
    \t\treturn -EINVAL;
    \tif (atomic_cmpxchg(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_OFF_COMMITTED,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_KILLING) !=
    \t    MT6797_A72_HOTPLUG_LIFECYCLE_OFF_COMMITTED)
    \t\treturn -EALREADY;
    \tif (cpu != MT6797_A72_HOTPLUG_CPU9 || !target_dead ||
    \t    !cpu8_online || cpu9_online)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, -EPROTO);

    \tresult->last_stage = MT6797_A72_HOTPLUG_STAGE_AFFINITY;
    \tresult->affinity_calls++;
    \tret = ops->affinity_info(context, cpu,
    \t\t\t\t MT6797_A72_HOTPLUG_AFFINITY_LEVEL0);
    \tif (ret != MT6797_A72_HOTPLUG_AFFINITY_OFF)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, ret < 0 ? ret : -EIO);

    \tresult->last_stage = MT6797_A72_HOTPLUG_STAGE_POST_STATE;
    \tresult->snapshots++;
    \tret = ops->snapshot(context, &result->post_state);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, ret);

    \tresult->last_stage = MT6797_A72_HOTPLUG_STAGE_CPU8_CALLBACK;
    \tresult->cpu8_callbacks++;
    \tret = ops->cpu8_callback(context, MT6797_A72_HOTPLUG_CPU8);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, ret);
    \tif (!mt6797_a72_hotplug_readback_proves_cpu9_off(
    \t\t    &result->baseline, &result->post_state))
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, -EIO);

    \tresult->last_stage = MT6797_A72_HOTPLUG_STAGE_OWNER_PROOF;
    \tresult->proof_calls++;
    \tret = ops->prove_off(context, result);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, ret);
    \tresult->off_proven = true;
    \tatomic_set_release(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_OFF_PROVEN);
    \treturn 0;
    }

    int mt6797_a72_hotplug_executor_complete(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tbool cpu8_online, bool cpu9_online,
    \tstruct mt6797_a72_hotplug_executor_result *result)
    {
    \tint ret;

    \tif (!controller || !result || !mt6797_a72_hotplug_ops_valid(ops))
    \t\treturn -EINVAL;
    \tif (atomic_cmpxchg(&controller->lifecycle,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_OFF_PROVEN,
    \t\t\t   MT6797_A72_HOTPLUG_LIFECYCLE_COMPLETING) !=
    \t    MT6797_A72_HOTPLUG_LIFECYCLE_OFF_PROVEN)
    \t\treturn -EALREADY;
    \tresult->last_stage = MT6797_A72_HOTPLUG_STAGE_OWNER_COMPLETE;
    \tif (!cpu8_online || cpu9_online)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, -EPROTO);
    \tret = ops->complete_down(context, cpu8_online, cpu9_online);
    \tif (ret)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, ret);
    \tresult->completed = true;
    \treturn mt6797_a72_hotplug_terminal(controller, ops, context, result,
    \t\t\t\t\t MT6797_A72_HOTPLUG_DOWN_COMPLETE, 0);
    }

    int mt6797_a72_hotplug_executor_fail(
    \tstruct mt6797_a72_hotplug_executor_controller *controller,
    \tconst struct mt6797_a72_hotplug_executor_ops *ops, void *context,
    \tint error, struct mt6797_a72_hotplug_executor_result *result)
    {
    \tint lifecycle;

    \tif (!controller || !result || !error ||
    \t    !mt6797_a72_hotplug_ops_valid(ops))
    \t\treturn -EINVAL;
    \tlifecycle = atomic_read_acquire(&controller->lifecycle);
    \tif (lifecycle == MT6797_A72_HOTPLUG_LIFECYCLE_TERMINAL ||
    \t    lifecycle == MT6797_A72_HOTPLUG_LIFECYCLE_IDLE)
    \t\treturn -EALREADY;
    \tif (result->off_committed)
    \t\treturn mt6797_a72_hotplug_fault(controller, ops, context,
    \t\t\t\t\t result, error);
    \treturn mt6797_a72_hotplug_reject(controller, ops, context, result,
    \t\t\t\t\terror);
    }
    """)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    makefile = root / "drivers/soc/mediatek/Makefile"
    source_dir = root / "drivers/soc/mediatek"

    replace_once(kconfig, "config MTK_MMSYS\n", KCONFIG + "config MTK_MMSYS\n")
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR) += mt6797-a72-cpu9-executor.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR) += mt6797-a72-cpu9-executor.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_EXECUTOR) += mt6797-a72-hotplug-executor.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_EXECUTOR_KUNIT_TEST) += mt6797-a72-hotplug-executor-test.o\n",
    )
    (source_dir / "mt6797-a72-hotplug-executor-internal.h").write_text(
        HEADER, encoding="utf-8"
    )
    (source_dir / "mt6797-a72-hotplug-executor.c").write_text(
        SOURCE, encoding="utf-8"
    )


if __name__ == "__main__":
    main()
