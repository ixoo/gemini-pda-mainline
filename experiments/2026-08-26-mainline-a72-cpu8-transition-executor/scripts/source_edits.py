#!/usr/bin/env python3
"""Apply deterministic hardware-free CPU8 transition coordinator edits."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


CORE_KCONFIG = dedent("""\
    config MTK_MT6797_A72_TRANSITION_EXECUTOR
    \tbool "MediaTek MT6797 Cortex-A72 injected transition executor"
    \tdepends on ARM64 && ARCH_MEDIATEK
    \tdefault n
    \thelp
    \t  Build the default-off, operation-injected coordinator for one bounded
    \t  MT6797 CPU8 transition. It enforces watchdog-first ordering, one CPU_ON,
    \t  exact pre-isolation rollback, and post-isolation power retention.

    \t  This option adds no device binding, trigger, production caller, MMIO,
    \t  regulator, reset, secure-call, PSCI, CPU-hotplug, retained-memory, or
    \t  watchdog implementation. Physical operations remain unconnected. If
    \t  unsure, say N.

    """)

TEST_KCONFIG = dedent("""\
    config MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST
    \tbool "KUnit tests for the MT6797 A72 transition executor"
    \tdepends on KUNIT=y
    \tdepends on MTK_MT6797_A72_TRANSITION_EXECUTOR
    \tdefault n
    \thelp
    \t  Exhaust the operation-injected CPU8 coordinator success path, every
    \t  stage failure, entry rejection, malformed ownership, rollback fault,
    \t  and atomic one-shot boundary using in-memory callbacks only.

    \t  These tests perform no physical hardware, CPU, watchdog, retained-RAM,
    \t  or device action. If unsure, say N.

    """)

INTERNAL_HEADER = dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __MT6797_A72_TRANSITION_INTERNAL_H
    #define __MT6797_A72_TRANSITION_INTERNAL_H

    #include <linux/atomic.h>
    #include <linux/bitops.h>
    #include <linux/types.h>

    #define MT6797_A72_TRANSITION_CPU8 8U
    #define MT6797_A72_TRANSITION_CPU9 9U
    #define MT6797_A72_TRANSITION_CPU_ON_WAIT_MS 10000U
    #define MT6797_A72_TRANSITION_RECOVERY_MS 15000U

    #define MT6797_A72_TRANSITION_OWNED_P27 BIT(0)
    #define MT6797_A72_TRANSITION_OWNED_PROVIDER BIT(1)
    #define MT6797_A72_TRANSITION_OWNED_CPU8 BIT(2)

    enum mt6797_a72_transition_stage {
    \tMT6797_A72_TRANSITION_STAGE_ENTRY,
    \tMT6797_A72_TRANSITION_STAGE_WATCHDOG,
    \tMT6797_A72_TRANSITION_STAGE_P27,
    \tMT6797_A72_TRANSITION_STAGE_PROVIDER,
    \tMT6797_A72_TRANSITION_STAGE_ISOLATION,
    \tMT6797_A72_TRANSITION_STAGE_SRAM,
    \tMT6797_A72_TRANSITION_STAGE_CPU_ON,
    \tMT6797_A72_TRANSITION_STAGE_ONLINE_WAIT,
    \tMT6797_A72_TRANSITION_STAGE_IPI,
    \tMT6797_A72_TRANSITION_STAGE_DCM,
    \tMT6797_A72_TRANSITION_STAGE_COUNT,
    };

    enum mt6797_a72_transition_phase {
    \tMT6797_A72_TRANSITION_BEFORE,
    \tMT6797_A72_TRANSITION_AFTER,
    };

    enum mt6797_a72_transition_terminal {
    \tMT6797_A72_TRANSITION_TERMINAL_NONE,
    \tMT6797_A72_TRANSITION_REJECTED_PRESTATE,
    \tMT6797_A72_TRANSITION_ROLLED_BACK_PREISO,
    \tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO,
    \tMT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO,
    \tMT6797_A72_TRANSITION_CPU8_ONLINE_PROOF,
    };

    struct mt6797_a72_transition_controller {
    \tatomic_t consumed;
    };

    #define MT6797_A72_TRANSITION_CONTROLLER_INIT \\
    \t{ .consumed = ATOMIC_INIT(0) }

    struct mt6797_a72_transition_request {
    \tunsigned int cpu;
    \tbool token_exact;
    \tbool prefix_complete;
    \tbool cpu8_online;
    \tbool cpu9_online;
    };

    struct mt6797_a72_transition_result {
    \tenum mt6797_a72_transition_terminal terminal;
    \tenum mt6797_a72_transition_stage last_stage;
    \tint stage_errno;
    \tint rollback_errno;
    \tbool attempted;
    \tbool watchdog_armed;
    \tbool isolation_attempted;
    \tbool isolation_crossed;
    \tbool p27_owned;
    \tbool provider_owned;
    \tbool cpu8_online;
    \tbool cpu9_online;
    \tunsigned int cpu_requests;
    \tunsigned int cpu_off_requests;
    \tunsigned int retries;
    \tunsigned int checkpoints;
    \tu32 rollback_mask;
    \tu32 retained_mask;
    \tu64 watchdog_identity;
    };

    struct mt6797_a72_transition_ops {
    \tvoid (*checkpoint)(void *context,
    \t\t\t   enum mt6797_a72_transition_phase phase,
    \t\t\t   enum mt6797_a72_transition_stage stage,
    \t\t\t   const struct mt6797_a72_transition_result *result);
    \tint (*watchdog_arm)(void *context, unsigned int timeout_ms,
    \t\t\t    u64 *identity);
    \tint (*p27_acquire)(void *context, bool *owned);
    \tint (*p27_release)(void *context);
    \tint (*provider_acquire)(void *context, bool *owned);
    \tint (*provider_release)(void *context);
    \tint (*isolation_clear)(void *context);
    \tint (*sram_enable)(void *context);
    \tint (*cpu_on)(void *context, unsigned int cpu);
    \tint (*online_wait)(void *context, unsigned int cpu,
    \t\t\t   unsigned int timeout_ms);
    \tint (*ipi_proof)(void *context, unsigned int cpu);
    \tint (*dcm_update)(void *context);
    };

    int mt6797_a72_transition_run(struct mt6797_a72_transition_controller *controller,
    \t\t\t      const struct mt6797_a72_transition_ops *ops,
    \t\t\t      void *context,
    \t\t\t      const struct mt6797_a72_transition_request *request,
    \t\t\t      struct mt6797_a72_transition_result *result);

    #endif /* __MT6797_A72_TRANSITION_INTERNAL_H */
    """)

CORE_SOURCE = dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* Hardware-free coordinator for one MT6797 CPU8 transition. */

    #include <linux/errno.h>
    #include <linux/string.h>

    #include "mt6797-a72-transition-internal.h"

    static bool
    mt6797_a72_transition_ops_valid(const struct mt6797_a72_transition_ops *ops)
    {
    \treturn ops && ops->checkpoint && ops->watchdog_arm &&
    \t\tops->p27_acquire && ops->p27_release &&
    \t\tops->provider_acquire && ops->provider_release &&
    \t\tops->isolation_clear && ops->sram_enable && ops->cpu_on &&
    \t\tops->online_wait && ops->ipi_proof && ops->dcm_update;
    }

    static void
    mt6797_a72_transition_checkpoint(const struct mt6797_a72_transition_ops *ops,
    \t\t\t\t void *context,
    \t\t\t\t struct mt6797_a72_transition_result *result,
    \t\t\t\t enum mt6797_a72_transition_phase phase,
    \t\t\t\t enum mt6797_a72_transition_stage stage)
    {
    \tresult->last_stage = stage;
    \tresult->checkpoints++;
    \tops->checkpoint(context, phase, stage, result);
    }

    static void
    mt6797_a72_transition_set_retained(struct mt6797_a72_transition_result *result)
    {
    \tresult->retained_mask = 0;
    \tif (result->p27_owned)
    \t\tresult->retained_mask |= MT6797_A72_TRANSITION_OWNED_P27;
    \tif (result->provider_owned)
    \t\tresult->retained_mask |= MT6797_A72_TRANSITION_OWNED_PROVIDER;
    \tif (result->cpu8_online)
    \t\tresult->retained_mask |= MT6797_A72_TRANSITION_OWNED_CPU8;
    }

    static int
    mt6797_a72_transition_rollback(const struct mt6797_a72_transition_ops *ops,
    \t\t\t       void *context,
    \t\t\t       struct mt6797_a72_transition_result *result,
    \t\t\t       int stage_errno)
    {
    \tint ret;

    \tresult->stage_errno = stage_errno;
    \tif (result->provider_owned) {
    \t\tret = ops->provider_release(context);
    \t\tif (ret) {
    \t\t\tresult->rollback_errno = ret;
    \t\t\tresult->terminal =
    \t\t\t\tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;
    \t\t\tmt6797_a72_transition_set_retained(result);
    \t\t\treturn ret;
    \t\t}
    \t\tresult->provider_owned = false;
    \t\tresult->rollback_mask |= MT6797_A72_TRANSITION_OWNED_PROVIDER;
    \t}
    \tif (result->p27_owned) {
    \t\tret = ops->p27_release(context);
    \t\tif (ret) {
    \t\t\tresult->rollback_errno = ret;
    \t\t\tresult->terminal =
    \t\t\t\tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;
    \t\t\tmt6797_a72_transition_set_retained(result);
    \t\t\treturn ret;
    \t\t}
    \t\tresult->p27_owned = false;
    \t\tresult->rollback_mask |= MT6797_A72_TRANSITION_OWNED_P27;
    \t}
    \tresult->terminal = MT6797_A72_TRANSITION_ROLLED_BACK_PREISO;
    \treturn stage_errno;
    }

    static int mt6797_a72_owner_fault(struct mt6797_a72_transition_result *result,
    \t\t\t\t  u32 unknown_mask)
    {
    \tresult->stage_errno = -EPROTO;
    \tresult->terminal = MT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;
    \tresult->retained_mask = unknown_mask;
    \tif (result->p27_owned)
    \t\tresult->retained_mask |= MT6797_A72_TRANSITION_OWNED_P27;
    \tif (result->provider_owned)
    \t\tresult->retained_mask |= MT6797_A72_TRANSITION_OWNED_PROVIDER;
    \treturn -EPROTO;
    }

    static int
    mt6797_a72_transition_postiso_fault(struct mt6797_a72_transition_result *result,
    \t\t\t\t    int stage_errno)
    {
    \tresult->stage_errno = stage_errno;
    \tresult->terminal = MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO;
    \tmt6797_a72_transition_set_retained(result);
    \treturn stage_errno;
    }

    int
    mt6797_a72_transition_run(struct mt6797_a72_transition_controller *controller,
    \t\t\t  const struct mt6797_a72_transition_ops *ops,
    \t\t\t  void *context,
    \t\t\t  const struct mt6797_a72_transition_request *request,
    \t\t\t  struct mt6797_a72_transition_result *result)
    {
    \tbool owned = false;
    \tu64 watchdog_identity = 0;
    \tint ret;

    \tif (!result)
    \t\treturn -EINVAL;
    \tmemset(result, 0, sizeof(*result));
    \tresult->last_stage = MT6797_A72_TRANSITION_STAGE_ENTRY;
    \tresult->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;
    \tif (!controller || !request || !mt6797_a72_transition_ops_valid(ops))
    \t\treturn -EINVAL;
    \tresult->cpu8_online = request->cpu8_online;
    \tresult->cpu9_online = request->cpu9_online;
    \tif (request->cpu != MT6797_A72_TRANSITION_CPU8)
    \t\treturn -EINVAL;
    \tif (!request->token_exact || !request->prefix_complete ||
    \t    request->cpu8_online || request->cpu9_online)
    \t\treturn -EPERM;
    \tif (atomic_cmpxchg(&controller->consumed, 0, 1))
    \t\treturn -EALREADY;
    \tresult->attempted = true;
    \tresult->terminal = MT6797_A72_TRANSITION_TERMINAL_NONE;

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_WATCHDOG);
    \tret = ops->watchdog_arm(context, MT6797_A72_TRANSITION_RECOVERY_MS,
    \t\t\t\t&watchdog_identity);
    \tif (ret) {
    \t\tresult->stage_errno = ret;
    \t\tresult->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;
    \t\treturn ret;
    \t}
    \tif (!watchdog_identity) {
    \t\tresult->stage_errno = -EPROTO;
    \t\tresult->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;
    \t\treturn -EPROTO;
    \t}
    \tresult->watchdog_armed = true;
    \tresult->watchdog_identity = watchdog_identity;
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_WATCHDOG);

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_P27);
    \tret = ops->p27_acquire(context, &owned);
    \tresult->p27_owned = owned;
    \tif (ret)
    \t\treturn mt6797_a72_transition_rollback(ops, context, result, ret);
    \tif (!owned)
    \t\treturn mt6797_a72_owner_fault(result, MT6797_A72_TRANSITION_OWNED_P27);
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_P27);

    \towned = false;
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_PROVIDER);
    \tret = ops->provider_acquire(context, &owned);
    \tresult->provider_owned = owned;
    \tif (ret)
    \t\treturn mt6797_a72_transition_rollback(ops, context, result, ret);
    \tif (!owned)
    \t\treturn mt6797_a72_owner_fault(result,
    \t\t\t\t\t       MT6797_A72_TRANSITION_OWNED_PROVIDER);
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_PROVIDER);

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_ISOLATION);
    \tresult->isolation_attempted = true;
    \tret = ops->isolation_clear(context);
    \tif (ret)
    \t\treturn mt6797_a72_transition_postiso_fault(result, ret);
    \tresult->isolation_crossed = true;
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_ISOLATION);

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_SRAM);
    \tret = ops->sram_enable(context);
    \tif (ret)
    \t\treturn mt6797_a72_transition_postiso_fault(result, ret);
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_SRAM);

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_CPU_ON);
    \tresult->cpu_requests++;
    \tret = ops->cpu_on(context, MT6797_A72_TRANSITION_CPU8);
    \tif (ret)
    \t\treturn mt6797_a72_transition_postiso_fault(result, ret);
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_CPU_ON);

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);
    \tret = ops->online_wait(context, MT6797_A72_TRANSITION_CPU8,
    \t\t\t\tMT6797_A72_TRANSITION_CPU_ON_WAIT_MS);
    \tif (ret)
    \t\treturn mt6797_a72_transition_postiso_fault(result, ret);
    \tresult->cpu8_online = true;
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_IPI);
    \tret = ops->ipi_proof(context, MT6797_A72_TRANSITION_CPU8);
    \tif (ret)
    \t\treturn mt6797_a72_transition_postiso_fault(result, ret);
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_IPI);

    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_DCM);
    \tret = ops->dcm_update(context);
    \tif (ret)
    \t\treturn mt6797_a72_transition_postiso_fault(result, ret);
    \tmt6797_a72_transition_checkpoint(ops, context, result,
    \t\t\t\t\t MT6797_A72_TRANSITION_AFTER,
    \t\t\t\t\t MT6797_A72_TRANSITION_STAGE_DCM);

    \tresult->terminal = MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF;
    \tmt6797_a72_transition_set_retained(result);
    \treturn 0;
    }
    """)

TEST_SOURCE = dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* Injected tests for the hardware-free MT6797 CPU8 transition executor. */

    #include <kunit/test.h>
    #include <linux/errno.h>
    #include <linux/module.h>

    #include "mt6797-a72-transition-internal.h"

    #define MT6797_TEST_EVENT(stage, slot) ((unsigned int)(stage) * 4U + (slot))
    #define MT6797_TEST_BEFORE 0U
    #define MT6797_TEST_EFFECT 1U
    #define MT6797_TEST_AFTER 2U
    #define MT6797_TEST_PROVIDER_RELEASE 100U
    #define MT6797_TEST_P27_RELEASE 101U

    struct mt6797_transition_test_state {
    \tenum mt6797_a72_transition_stage fail_stage;
    \tenum mt6797_a72_transition_stage malformed_stage;
    \tbool provider_release_fails;
    \tbool p27_release_fails;
    \tunsigned int events[64];
    \tunsigned int event_count;
    \tunsigned int watchdog_timeout_ms;
    \tunsigned int online_timeout_ms;
    \tunsigned int cpu_on_target;
    \tunsigned int online_target;
    \tunsigned int ipi_target;
    };

    static void mt6797_test_record(struct mt6797_transition_test_state *state,
    \t\t\t       unsigned int event)
    {
    \tif (state->event_count < ARRAY_SIZE(state->events))
    \t\tstate->events[state->event_count++] = event;
    }

    static int mt6797_test_effect(struct mt6797_transition_test_state *state,
    \t\t\t      enum mt6797_a72_transition_stage stage)
    {
    \tmt6797_test_record(state, MT6797_TEST_EVENT(stage, MT6797_TEST_EFFECT));
    \treturn state->fail_stage == stage ? -EIO : 0;
    }

    static void
    mt6797_test_checkpoint(void *context,
    \t\t       enum mt6797_a72_transition_phase phase,
    \t\t       enum mt6797_a72_transition_stage stage,
    \t\t       const struct mt6797_a72_transition_result *result)
    {
    \tstruct mt6797_transition_test_state *state = context;
    \tunsigned int slot = phase == MT6797_A72_TRANSITION_BEFORE ?
    \t\tMT6797_TEST_BEFORE : MT6797_TEST_AFTER;

    \t(void)result;
    \tmt6797_test_record(state, MT6797_TEST_EVENT(stage, slot));
    }

    static int mt6797_test_watchdog(void *context, unsigned int timeout_ms,
    \t\t\t\tu64 *identity)
    {
    \tstruct mt6797_transition_test_state *state = context;
    \tint ret;

    \tstate->watchdog_timeout_ms = timeout_ms;
    \tret = mt6797_test_effect(state, MT6797_A72_TRANSITION_STAGE_WATCHDOG);
    \tif (ret)
    \t\treturn ret;
    \tif (state->malformed_stage != MT6797_A72_TRANSITION_STAGE_WATCHDOG)
    \t\t*identity = 0x4757415443483031ULL;
    \treturn 0;
    }

    static int mt6797_test_p27_acquire(void *context, bool *owned)
    {
    \tstruct mt6797_transition_test_state *state = context;

    \t*owned = state->malformed_stage != MT6797_A72_TRANSITION_STAGE_P27;
    \treturn mt6797_test_effect(state, MT6797_A72_TRANSITION_STAGE_P27);
    }

    static int mt6797_test_p27_release(void *context)
    {
    \tstruct mt6797_transition_test_state *state = context;

    \tmt6797_test_record(state, MT6797_TEST_P27_RELEASE);
    \treturn state->p27_release_fails ? -EREMOTEIO : 0;
    }

    static int mt6797_test_provider_acquire(void *context, bool *owned)
    {
    \tstruct mt6797_transition_test_state *state = context;

    \t*owned = state->malformed_stage != MT6797_A72_TRANSITION_STAGE_PROVIDER;
    \treturn mt6797_test_effect(state, MT6797_A72_TRANSITION_STAGE_PROVIDER);
    }

    static int mt6797_test_provider_release(void *context)
    {
    \tstruct mt6797_transition_test_state *state = context;

    \tmt6797_test_record(state, MT6797_TEST_PROVIDER_RELEASE);
    \treturn state->provider_release_fails ? -EREMOTEIO : 0;
    }

    static int mt6797_test_isolation(void *context)
    {
    \treturn mt6797_test_effect(context,
    \t\t\tMT6797_A72_TRANSITION_STAGE_ISOLATION);
    }

    static int mt6797_test_sram(void *context)
    {
    \treturn mt6797_test_effect(context, MT6797_A72_TRANSITION_STAGE_SRAM);
    }

    static int mt6797_test_cpu_on(void *context, unsigned int cpu)
    {
    \tstruct mt6797_transition_test_state *state = context;

    \tstate->cpu_on_target = cpu;
    \treturn mt6797_test_effect(state, MT6797_A72_TRANSITION_STAGE_CPU_ON);
    }

    static int mt6797_test_online_wait(void *context, unsigned int cpu,
    \t\t\t\t   unsigned int timeout_ms)
    {
    \tstruct mt6797_transition_test_state *state = context;

    \tstate->online_target = cpu;
    \tstate->online_timeout_ms = timeout_ms;
    \treturn mt6797_test_effect(state,
    \t\t\tMT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);
    }

    static int mt6797_test_ipi(void *context, unsigned int cpu)
    {
    \tstruct mt6797_transition_test_state *state = context;

    \tstate->ipi_target = cpu;
    \treturn mt6797_test_effect(state, MT6797_A72_TRANSITION_STAGE_IPI);
    }

    static int mt6797_test_dcm(void *context)
    {
    \treturn mt6797_test_effect(context, MT6797_A72_TRANSITION_STAGE_DCM);
    }

    static const struct mt6797_a72_transition_ops mt6797_test_ops = {
    \t.checkpoint = mt6797_test_checkpoint,
    \t.watchdog_arm = mt6797_test_watchdog,
    \t.p27_acquire = mt6797_test_p27_acquire,
    \t.p27_release = mt6797_test_p27_release,
    \t.provider_acquire = mt6797_test_provider_acquire,
    \t.provider_release = mt6797_test_provider_release,
    \t.isolation_clear = mt6797_test_isolation,
    \t.sram_enable = mt6797_test_sram,
    \t.cpu_on = mt6797_test_cpu_on,
    \t.online_wait = mt6797_test_online_wait,
    \t.ipi_proof = mt6797_test_ipi,
    \t.dcm_update = mt6797_test_dcm,
    };

    static struct mt6797_a72_transition_request mt6797_test_request(void)
    {
    \treturn (struct mt6797_a72_transition_request) {
    \t\t.cpu = MT6797_A72_TRANSITION_CPU8,
    \t\t.token_exact = true,
    \t\t.prefix_complete = true,
    \t};
    }

    static int mt6797_test_run(struct mt6797_transition_test_state *state,
    \t\t\t   const struct mt6797_a72_transition_request *request,
    \t\t\t   struct mt6797_a72_transition_result *result)
    {
    \tstruct mt6797_a72_transition_controller controller =
    \t\tMT6797_A72_TRANSITION_CONTROLLER_INIT;

    \treturn mt6797_a72_transition_run(&controller, &mt6797_test_ops,
    \t\t\t\t  state, request, result);
    }

    static void mt6797_transition_success_test(struct kunit *test)
    {
    \tstruct mt6797_a72_transition_request request = mt6797_test_request();
    \tstruct mt6797_transition_test_state state = { };
    \tstruct mt6797_a72_transition_result result;
    \tenum mt6797_a72_transition_stage stage;
    \tunsigned int event = 0;
    \tint ret;

    \tret = mt6797_test_run(&state, &request, &result);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\tMT6797_A72_TRANSITION_CPU8_ONLINE_PROOF);
    \tKUNIT_EXPECT_TRUE(test, result.attempted);
    \tKUNIT_EXPECT_TRUE(test, result.watchdog_armed);
    \tKUNIT_EXPECT_TRUE(test, result.isolation_attempted);
    \tKUNIT_EXPECT_TRUE(test, result.isolation_crossed);
    \tKUNIT_EXPECT_TRUE(test, result.p27_owned);
    \tKUNIT_EXPECT_TRUE(test, result.provider_owned);
    \tKUNIT_EXPECT_TRUE(test, result.cpu8_online);
    \tKUNIT_EXPECT_FALSE(test, result.cpu9_online);
    \tKUNIT_EXPECT_EQ(test, result.cpu_requests, 1U);
    \tKUNIT_EXPECT_EQ(test, result.cpu_off_requests, 0U);
    \tKUNIT_EXPECT_EQ(test, result.retries, 0U);
    \tKUNIT_EXPECT_EQ(test, result.checkpoints, 18U);
    \tKUNIT_EXPECT_EQ(test, result.rollback_mask, 0U);
    \tKUNIT_EXPECT_EQ(test, result.retained_mask,
    \t\t\t(u32)(MT6797_A72_TRANSITION_OWNED_P27 |
    \t\t\t      MT6797_A72_TRANSITION_OWNED_PROVIDER |
    \t\t\t      MT6797_A72_TRANSITION_OWNED_CPU8));
    \tKUNIT_EXPECT_NE(test, result.watchdog_identity, 0ULL);
    \tKUNIT_EXPECT_EQ(test, state.watchdog_timeout_ms,
    \t\t\tMT6797_A72_TRANSITION_RECOVERY_MS);
    \tKUNIT_EXPECT_EQ(test, state.online_timeout_ms,
    \t\t\tMT6797_A72_TRANSITION_CPU_ON_WAIT_MS);
    \tKUNIT_EXPECT_EQ(test, state.cpu_on_target,
    \t\t\tMT6797_A72_TRANSITION_CPU8);
    \tKUNIT_EXPECT_EQ(test, state.online_target,
    \t\t\tMT6797_A72_TRANSITION_CPU8);
    \tKUNIT_EXPECT_EQ(test, state.ipi_target,
    \t\t\tMT6797_A72_TRANSITION_CPU8);
    \tKUNIT_ASSERT_EQ(test, state.event_count, 27U);
    \tfor (stage = MT6797_A72_TRANSITION_STAGE_WATCHDOG;
    \t     stage < MT6797_A72_TRANSITION_STAGE_COUNT; stage++) {
    \t\tKUNIT_EXPECT_EQ(test, state.events[event++],
    \t\t\t\tMT6797_TEST_EVENT(stage, MT6797_TEST_BEFORE));
    \t\tKUNIT_EXPECT_EQ(test, state.events[event++],
    \t\t\t\tMT6797_TEST_EVENT(stage, MT6797_TEST_EFFECT));
    \t\tKUNIT_EXPECT_EQ(test, state.events[event++],
    \t\t\t\tMT6797_TEST_EVENT(stage, MT6797_TEST_AFTER));
    \t}
    }

    static void mt6797_transition_entry_rejections_test(struct kunit *test)
    {
    \tstruct mt6797_a72_transition_request requests[] = {
    \t\t{ .cpu = MT6797_A72_TRANSITION_CPU9,
    \t\t  .token_exact = true, .prefix_complete = true },
    \t\t{ .cpu = MT6797_A72_TRANSITION_CPU8,
    \t\t  .prefix_complete = true },
    \t\t{ .cpu = MT6797_A72_TRANSITION_CPU8,
    \t\t  .token_exact = true },
    \t\t{ .cpu = MT6797_A72_TRANSITION_CPU8,
    \t\t  .token_exact = true, .prefix_complete = true,
    \t\t  .cpu8_online = true },
    \t\t{ .cpu = MT6797_A72_TRANSITION_CPU8,
    \t\t  .token_exact = true, .prefix_complete = true,
    \t\t  .cpu9_online = true },
    \t};
    \tunsigned int i;

    \tfor (i = 0; i < ARRAY_SIZE(requests); i++) {
    \t\tstruct mt6797_transition_test_state state = { };
    \t\tstruct mt6797_a72_transition_result result;
    \t\tint ret;

    \t\tret = mt6797_test_run(&state, &requests[i], &result);
    \t\tKUNIT_EXPECT_LT(test, ret, 0);
    \t\tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\t\tMT6797_A72_TRANSITION_REJECTED_PRESTATE);
    \t\tKUNIT_EXPECT_FALSE(test, result.attempted);
    \t\tKUNIT_EXPECT_EQ(test, result.checkpoints, 0U);
    \t\tKUNIT_EXPECT_EQ(test, state.event_count, 0U);
    \t}
    }

    static void mt6797_transition_missing_op_test(struct kunit *test)
    {
    \tstruct mt6797_a72_transition_request request = mt6797_test_request();
    \tstruct mt6797_a72_transition_controller controller =
    \t\tMT6797_A72_TRANSITION_CONTROLLER_INIT;
    \tstruct mt6797_transition_test_state state = { };
    \tstruct mt6797_a72_transition_result result;
    \tstruct mt6797_a72_transition_ops ops = mt6797_test_ops;
    \tint ret;

    \tops.dcm_update = NULL;
    \tret = mt6797_a72_transition_run(&controller, &ops, &state,
    \t\t\t\t\t&request, &result);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tKUNIT_EXPECT_FALSE(test, result.attempted);
    \tKUNIT_EXPECT_EQ(test, result.checkpoints, 0U);
    \tKUNIT_EXPECT_EQ(test, atomic_read(&controller.consumed), 0);
    }

    static void mt6797_transition_one_shot_test(struct kunit *test)
    {
    \tstruct mt6797_a72_transition_request request = mt6797_test_request();
    \tstruct mt6797_a72_transition_controller controller =
    \t\tMT6797_A72_TRANSITION_CONTROLLER_INIT;
    \tstruct mt6797_transition_test_state state = { };
    \tstruct mt6797_a72_transition_result result;
    \tunsigned int events;
    \tint ret;

    \tret = mt6797_a72_transition_run(&controller, &mt6797_test_ops, &state,
    \t\t\t\t\t&request, &result);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tevents = state.event_count;
    \tret = mt6797_a72_transition_run(&controller, &mt6797_test_ops, &state,
    \t\t\t\t\t&request, &result);
    \tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
    \tKUNIT_EXPECT_FALSE(test, result.attempted);
    \tKUNIT_EXPECT_EQ(test, result.checkpoints, 0U);
    \tKUNIT_EXPECT_EQ(test, state.event_count, events);
    }

    static void mt6797_transition_stage_failures_test(struct kunit *test)
    {
    \tenum mt6797_a72_transition_stage stage;

    \tfor (stage = MT6797_A72_TRANSITION_STAGE_WATCHDOG;
    \t     stage < MT6797_A72_TRANSITION_STAGE_COUNT; stage++) {
    \t\tstruct mt6797_a72_transition_request request =
    \t\t\tmt6797_test_request();
    \t\tstruct mt6797_transition_test_state state = {
    \t\t\t.fail_stage = stage,
    \t\t};
    \t\tstruct mt6797_a72_transition_result result;
    \t\tu32 expected_retained =
    \t\t\tMT6797_A72_TRANSITION_OWNED_P27 |
    \t\t\tMT6797_A72_TRANSITION_OWNED_PROVIDER;
    \t\tint ret;

    \t\tret = mt6797_test_run(&state, &request, &result);
    \t\tKUNIT_EXPECT_EQ_MSG(test, ret, -EIO, "stage=%u", stage);
    \t\tKUNIT_EXPECT_EQ_MSG(test, result.cpu_off_requests, 0U,
    \t\t\t\t    "stage=%u", stage);
    \t\tKUNIT_EXPECT_EQ_MSG(test, result.retries, 0U,
    \t\t\t\t    "stage=%u", stage);
    \t\tKUNIT_EXPECT_FALSE(test, result.cpu9_online);
    \t\tKUNIT_EXPECT_EQ_MSG(test, result.checkpoints,
    \t\t\t\t    (unsigned int)(stage -
    \t\t\t\t     MT6797_A72_TRANSITION_STAGE_WATCHDOG) * 2U + 1U,
    \t\t\t\t    "stage=%u", stage);
    \t\tif (stage == MT6797_A72_TRANSITION_STAGE_WATCHDOG) {
    \t\t\tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\t\t\tMT6797_A72_TRANSITION_REJECTED_PRESTATE);
    \t\t\tKUNIT_EXPECT_FALSE(test, result.watchdog_armed);
    \t\t\tcontinue;
    \t\t}
    \t\tKUNIT_EXPECT_TRUE(test, result.watchdog_armed);
    \t\tif (stage == MT6797_A72_TRANSITION_STAGE_P27 ||
    \t\t    stage == MT6797_A72_TRANSITION_STAGE_PROVIDER) {
    \t\t\tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\t\t\tMT6797_A72_TRANSITION_ROLLED_BACK_PREISO);
    \t\t\tKUNIT_EXPECT_FALSE(test, result.p27_owned);
    \t\t\tKUNIT_EXPECT_FALSE(test, result.provider_owned);
    \t\t\tKUNIT_EXPECT_EQ(test, result.retained_mask, 0U);
    \t\t\tcontinue;
    \t\t}
    \t\tif (stage >= MT6797_A72_TRANSITION_STAGE_IPI)
    \t\t\texpected_retained |= MT6797_A72_TRANSITION_OWNED_CPU8;
    \t\tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\t\tMT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO);
    \t\tKUNIT_EXPECT_TRUE(test, result.isolation_attempted);
    \t\tKUNIT_EXPECT_EQ(test, result.isolation_crossed,
    \t\t\t\tstage != MT6797_A72_TRANSITION_STAGE_ISOLATION);
    \t\tKUNIT_EXPECT_EQ(test, result.retained_mask, expected_retained);
    \t\tKUNIT_EXPECT_EQ(test, result.cpu_requests,
    \t\t\t\tstage >= MT6797_A72_TRANSITION_STAGE_CPU_ON ? 1U : 0U);
    \t\tKUNIT_EXPECT_EQ(test, result.cpu8_online,
    \t\t\t\tstage >= MT6797_A72_TRANSITION_STAGE_IPI);
    \t}
    }

    static void mt6797_transition_malformed_ownership_test(struct kunit *test)
    {
    \tstatic const enum mt6797_a72_transition_stage stages[] = {
    \t\tMT6797_A72_TRANSITION_STAGE_WATCHDOG,
    \t\tMT6797_A72_TRANSITION_STAGE_P27,
    \t\tMT6797_A72_TRANSITION_STAGE_PROVIDER,
    \t};
    \tunsigned int i;

    \tfor (i = 0; i < ARRAY_SIZE(stages); i++) {
    \t\tstruct mt6797_a72_transition_request request =
    \t\t\tmt6797_test_request();
    \t\tstruct mt6797_transition_test_state state = {
    \t\t\t.malformed_stage = stages[i],
    \t\t};
    \t\tstruct mt6797_a72_transition_result result;
    \t\tint ret;

    \t\tret = mt6797_test_run(&state, &request, &result);
    \t\tKUNIT_EXPECT_EQ(test, ret, -EPROTO);
    \t\tif (stages[i] == MT6797_A72_TRANSITION_STAGE_WATCHDOG) {
    \t\t\tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\t\t\tMT6797_A72_TRANSITION_REJECTED_PRESTATE);
    \t\t\tKUNIT_EXPECT_FALSE(test, result.watchdog_armed);
    \t\t} else {
    \t\t\tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\t\t\tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO);
    \t\t\tKUNIT_EXPECT_NE(test, result.retained_mask, 0U);
    \t\t}
    \t}
    }

    static void mt6797_transition_rollback_faults_test(struct kunit *test)
    {
    \tstruct mt6797_a72_transition_request request = mt6797_test_request();
    \tstruct mt6797_transition_test_state state = {
    \t\t.fail_stage = MT6797_A72_TRANSITION_STAGE_P27,
    \t\t.p27_release_fails = true,
    \t};
    \tstruct mt6797_a72_transition_result result;
    \tint ret;

    \tret = mt6797_test_run(&state, &request, &result);
    \tKUNIT_EXPECT_EQ(test, ret, -EREMOTEIO);
    \tKUNIT_EXPECT_EQ(test, result.terminal,
    \t\t\tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO);
    \tKUNIT_EXPECT_EQ(test, result.rollback_errno, -EREMOTEIO);
    \tKUNIT_EXPECT_EQ(test, result.retained_mask,
    \t\t\t(u32)MT6797_A72_TRANSITION_OWNED_P27);

    \tstate = (struct mt6797_transition_test_state) {
    \t\t.fail_stage = MT6797_A72_TRANSITION_STAGE_PROVIDER,
    \t\t.provider_release_fails = true,
    \t};
    \tret = mt6797_test_run(&state, &request, &result);
    \tKUNIT_EXPECT_EQ(test, ret, -EREMOTEIO);
    \tKUNIT_EXPECT_EQ(test, result.retained_mask,
    \t\t\t(u32)(MT6797_A72_TRANSITION_OWNED_P27 |
    \t\t\t      MT6797_A72_TRANSITION_OWNED_PROVIDER));

    \tstate = (struct mt6797_transition_test_state) {
    \t\t.fail_stage = MT6797_A72_TRANSITION_STAGE_PROVIDER,
    \t\t.p27_release_fails = true,
    \t};
    \tret = mt6797_test_run(&state, &request, &result);
    \tKUNIT_EXPECT_EQ(test, ret, -EREMOTEIO);
    \tKUNIT_EXPECT_EQ(test, result.rollback_mask,
    \t\t\t(u32)MT6797_A72_TRANSITION_OWNED_PROVIDER);
    \tKUNIT_EXPECT_EQ(test, result.retained_mask,
    \t\t\t(u32)MT6797_A72_TRANSITION_OWNED_P27);
    }

    static struct kunit_case mt6797_transition_cases[] = {
    \tKUNIT_CASE(mt6797_transition_success_test),
    \tKUNIT_CASE(mt6797_transition_entry_rejections_test),
    \tKUNIT_CASE(mt6797_transition_missing_op_test),
    \tKUNIT_CASE(mt6797_transition_one_shot_test),
    \tKUNIT_CASE(mt6797_transition_stage_failures_test),
    \tKUNIT_CASE(mt6797_transition_malformed_ownership_test),
    \tKUNIT_CASE(mt6797_transition_rollback_faults_test),
    \t{ }
    };

    static struct kunit_suite mt6797_transition_suite = {
    \t.name = "mt6797-a72-transition-executor",
    \t.test_cases = mt6797_transition_cases,
    };

    kunit_test_suite(mt6797_transition_suite);

    MODULE_LICENSE("GPL");
    """)


def production(root: Path) -> None:
    soc = root / "drivers/soc/mediatek"
    kconfig = soc / "Kconfig"
    makefile = soc / "Makefile"
    anchor = "config MTK_MT6797_DVFSP_HANDOFF\n"
    replace_once(kconfig, anchor, CORE_KCONFIG + anchor)
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE) += "
        "mt6797-a72-platform-state.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE) += "
        "mt6797-a72-platform-state.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR) += "
        "mt6797-a72-transition.o\n",
    )
    (soc / "mt6797-a72-transition-internal.h").write_text(
        INTERNAL_HEADER, encoding="utf-8"
    )
    (soc / "mt6797-a72-transition.c").write_text(CORE_SOURCE, encoding="utf-8")


def tests(root: Path) -> None:
    soc = root / "drivers/soc/mediatek"
    kconfig = soc / "Kconfig"
    makefile = soc / "Makefile"
    anchor = "config MTK_MT6797_DVFSP_HANDOFF\n"
    replace_once(kconfig, anchor, TEST_KCONFIG + anchor)
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR) += "
        "mt6797-a72-transition.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR) += "
        "mt6797-a72-transition.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST) += "
        "mt6797-a72-transition-test.o\n",
    )
    (soc / "mt6797-a72-transition-test.c").write_text(
        TEST_SOURCE, encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    (production if args.phase == "production" else tests)(root)


if __name__ == "__main__":
    main()
