#!/usr/bin/env python3
"""Add the disconnected retained-CPU8 observer and focused KUnit tests."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def kernel_text(value: str) -> str:
    lines = []
    for line in dedent(value).lstrip("\n").splitlines(keepends=True):
        stripped = line.lstrip(" ")
        spaces = len(line) - len(stripped)
        lines.append("\t" * (spaces // 8) + " " * (spaces % 8) + stripped)
    return "".join(lines)


INTERNAL_HEADER = kernel_text(r"""
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __MT6797_A72_CPU8_OBSERVER_INTERNAL_H
    #define __MT6797_A72_CPU8_OBSERVER_INTERNAL_H

    #include <asm/mt6797_a72_membership.h>

    #include <linux/atomic.h>
    #include <linux/completion.h>
    #include <linux/smp.h>
    #include <linux/types.h>

    #define MT6797_A72_CPU8_OBSERVER_CPU 8U
    #define MT6797_A72_CPU8_OBSERVER_TIMEOUT_MS 250U

    enum mt6797_a72_cpu8_observer_state {
            MT6797_A72_CPU8_OBSERVER_IDLE,
            MT6797_A72_CPU8_OBSERVER_ARMED,
            MT6797_A72_CPU8_OBSERVER_SUCCEEDED,
            MT6797_A72_CPU8_OBSERVER_CALLBACK_FAILED,
            MT6797_A72_CPU8_OBSERVER_DISPATCH_FAILED,
            MT6797_A72_CPU8_OBSERVER_TIMED_OUT,
    };

    struct mt6797_a72_cpu8_observer_ops {
            int (*dispatch)(void *context, unsigned int cpu,
                            smp_call_func_t function, void *info, bool wait);
            unsigned long (*wait_timeout)(void *context,
                            struct completion *completion,
                            unsigned long timeout);
            unsigned int (*current_cpu)(void *context);
            int (*identity_check)(void *context,
                            const struct mt6797_a72_hotplug_identity *identity);
    };

    struct mt6797_a72_cpu8_observer {
            atomic_t state;
            struct completion completion;
            struct mt6797_a72_hotplug_identity expected;
            const struct mt6797_a72_cpu8_observer_ops *ops;
            void *ops_context;
            atomic_t dispatch_calls;
            atomic_t wait_calls;
            atomic_t callback_calls;
            atomic_t identity_checks;
            atomic_t late_callbacks;
            s32 callback_errno;
    };

    void mt6797_a72_cpu8_observer_init(
            struct mt6797_a72_cpu8_observer *observer);
    bool mt6797_a72_cpu8_observer_identity_matches(
            const struct mt6797_a72_hotplug_snapshot *snapshot,
            const struct mt6797_a72_hotplug_identity *identity);
    int mt6797_a72_cpu8_observer_run_with_ops(
            struct mt6797_a72_cpu8_observer *observer,
            const struct mt6797_a72_cpu8_observer_ops *ops,
            void *ops_context,
            const struct mt6797_a72_hotplug_identity *identity);
    int mt6797_a72_cpu8_observer_run(
            struct mt6797_a72_cpu8_observer *observer,
            const struct mt6797_a72_hotplug_identity *identity);

    #endif /* __MT6797_A72_CPU8_OBSERVER_INTERNAL_H */
    """)


SOURCE = kernel_text(r"""
    // SPDX-License-Identifier: GPL-2.0-only
    /* Disconnected one-shot retained-CPU8 observation for CPU9 hotplug. */

    #include <asm/mt6797_a72_membership.h>

    #include <linux/bitops.h>
    #include <linux/completion.h>
    #include <linux/errno.h>
    #include <linux/jiffies.h>
    #include <linux/smp.h>
    #include <linux/string.h>

    #include "mt6797-a72-cpu8-observer-internal.h"

    static bool mt6797_a72_cpu8_observer_identity_valid(
            const struct mt6797_a72_hotplug_identity *identity)
    {
            return identity && identity->abi == MT6797_A72_HOTPLUG_ABI &&
                    identity->operation ==
                            MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN &&
                    identity->target_cpu == 9 &&
                    identity->target_mpidr == 0x201 &&
                    identity->generation && identity->cookie &&
                    identity->parent_generation && identity->parent_cookie &&
                    identity->generation != ~0ULL && identity->cookie != ~0ULL &&
                    identity->parent_generation != ~0ULL &&
                    identity->parent_cookie != ~0ULL;
    }

    bool mt6797_a72_cpu8_observer_identity_matches(
            const struct mt6797_a72_hotplug_snapshot *snapshot,
            const struct mt6797_a72_hotplug_identity *identity)
    {
            const struct mt6797_a72_hotplug_transaction *active;

            if (!snapshot || !mt6797_a72_cpu8_observer_identity_valid(identity))
                    return false;
            active = &snapshot->active;
            return snapshot->abi == MT6797_A72_HOTPLUG_ABI &&
                    snapshot->phase == MT6797_A72_HOTPLUG_OFF_COMMITTED &&
                    snapshot->owner_health == MT6797_A72_OWNER_AVAILABLE &&
                    snapshot->controller_present == 1 &&
                    snapshot->members == (BIT(0) | BIT(1)) && active->valid == 1 &&
                    !memcmp(&active->identity, identity, sizeof(*identity)) &&
                    active->off_committed == 1 && !active->off_proven &&
                    !active->completed && !active->restored &&
                    active->budgets.cpu_off == MT6797_A72_BUDGET_CONSUMED &&
                    active->budgets.affinity == MT6797_A72_BUDGET_AVAILABLE;
    }

    static int mt6797_a72_cpu8_observer_dispatch(
            void *context, unsigned int cpu, smp_call_func_t function, void *info,
            bool wait)
    {
            if (wait)
                    return -EINVAL;
            return smp_call_function_single(cpu, function, info, 0);
    }

    static unsigned long mt6797_a72_cpu8_observer_wait(
            void *context, struct completion *completion, unsigned long timeout)
    {
            return wait_for_completion_timeout(completion, timeout);
    }

    static unsigned int mt6797_a72_cpu8_observer_current_cpu(void *context)
    {
            return smp_processor_id();
    }

    static int mt6797_a72_cpu8_observer_check_identity(
            void *context, const struct mt6797_a72_hotplug_identity *identity)
    {
            struct mt6797_a72_hotplug_snapshot snapshot;

            mt6797_a72_hotplug_snapshot(&snapshot);
            return mt6797_a72_cpu8_observer_identity_matches(&snapshot, identity) ?
                    0 : -ESTALE;
    }

    static const struct mt6797_a72_cpu8_observer_ops
    mt6797_a72_cpu8_observer_production_ops = {
            .dispatch = mt6797_a72_cpu8_observer_dispatch,
            .wait_timeout = mt6797_a72_cpu8_observer_wait,
            .current_cpu = mt6797_a72_cpu8_observer_current_cpu,
            .identity_check = mt6797_a72_cpu8_observer_check_identity,
    };

    void mt6797_a72_cpu8_observer_init(
            struct mt6797_a72_cpu8_observer *observer)
    {
            if (!observer)
                    return;
            memset(observer, 0, sizeof(*observer));
            atomic_set(&observer->state, MT6797_A72_CPU8_OBSERVER_IDLE);
            init_completion(&observer->completion);
    }

    static bool mt6797_a72_cpu8_observer_ops_valid(
            const struct mt6797_a72_cpu8_observer_ops *ops)
    {
            return ops && ops->dispatch && ops->wait_timeout &&
                    ops->current_cpu && ops->identity_check;
    }

    static void mt6797_a72_cpu8_observer_callback(void *info)
    {
            struct mt6797_a72_cpu8_observer *observer = info;
            enum mt6797_a72_cpu8_observer_state terminal;
            int ret;

            atomic_inc(&observer->callback_calls);
            if (atomic_read_acquire(&observer->state) !=
                MT6797_A72_CPU8_OBSERVER_ARMED) {
                    atomic_inc(&observer->late_callbacks);
                    return;
            }
            if (observer->ops->current_cpu(observer->ops_context) !=
                MT6797_A72_CPU8_OBSERVER_CPU) {
                    ret = -EPROTO;
            } else {
                    atomic_inc(&observer->identity_checks);
                    ret = observer->ops->identity_check(observer->ops_context,
                                                         &observer->expected);
            }
            WRITE_ONCE(observer->callback_errno, ret);
            terminal = ret ? MT6797_A72_CPU8_OBSERVER_CALLBACK_FAILED :
                    MT6797_A72_CPU8_OBSERVER_SUCCEEDED;
            if (atomic_cmpxchg(&observer->state,
                               MT6797_A72_CPU8_OBSERVER_ARMED,
                               terminal) == MT6797_A72_CPU8_OBSERVER_ARMED)
                    complete(&observer->completion);
            else
                    atomic_inc(&observer->late_callbacks);
    }

    int mt6797_a72_cpu8_observer_run_with_ops(
            struct mt6797_a72_cpu8_observer *observer,
            const struct mt6797_a72_cpu8_observer_ops *ops,
            void *ops_context,
            const struct mt6797_a72_hotplug_identity *identity)
    {
            enum mt6797_a72_cpu8_observer_state state;
            unsigned long completed;
            int ret;

            if (!observer || !mt6797_a72_cpu8_observer_ops_valid(ops) ||
                !mt6797_a72_cpu8_observer_identity_valid(identity))
                    return -EINVAL;
            if (atomic_cmpxchg(&observer->state,
                               MT6797_A72_CPU8_OBSERVER_IDLE,
                               MT6797_A72_CPU8_OBSERVER_ARMED) !=
                MT6797_A72_CPU8_OBSERVER_IDLE)
                    return -EALREADY;
            observer->expected = *identity;
            observer->ops = ops;
            observer->ops_context = ops_context;
            smp_wmb();

            atomic_inc(&observer->dispatch_calls);
            ret = ops->dispatch(ops_context, MT6797_A72_CPU8_OBSERVER_CPU,
                                mt6797_a72_cpu8_observer_callback, observer,
                                false);
            if (ret) {
                    atomic_cmpxchg(&observer->state,
                                   MT6797_A72_CPU8_OBSERVER_ARMED,
                                   MT6797_A72_CPU8_OBSERVER_DISPATCH_FAILED);
                    return ret;
            }

            atomic_inc(&observer->wait_calls);
            completed = ops->wait_timeout(
                    ops_context, &observer->completion,
                    msecs_to_jiffies(MT6797_A72_CPU8_OBSERVER_TIMEOUT_MS));
            if (!completed &&
                atomic_cmpxchg(&observer->state,
                               MT6797_A72_CPU8_OBSERVER_ARMED,
                               MT6797_A72_CPU8_OBSERVER_TIMED_OUT) ==
                MT6797_A72_CPU8_OBSERVER_ARMED)
                    return -ETIMEDOUT;

            state = atomic_read_acquire(&observer->state);
            if (state == MT6797_A72_CPU8_OBSERVER_SUCCEEDED)
                    return 0;
            if (state == MT6797_A72_CPU8_OBSERVER_CALLBACK_FAILED)
                    return READ_ONCE(observer->callback_errno) ?: -EPROTO;
            if (state == MT6797_A72_CPU8_OBSERVER_TIMED_OUT)
                    return -ETIMEDOUT;
            return -EPROTO;
    }

    int mt6797_a72_cpu8_observer_run(
            struct mt6797_a72_cpu8_observer *observer,
            const struct mt6797_a72_hotplug_identity *identity)
    {
            return mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &mt6797_a72_cpu8_observer_production_ops, NULL,
                    identity);
    }
    """)


TEST_SOURCE = kernel_text(r"""
    // SPDX-License-Identifier: GPL-2.0-only
    /* KUnit tests for the disconnected retained-CPU8 observer. */

    #include <kunit/test.h>

    #include <linux/completion.h>
    #include <linux/errno.h>
    #include <linux/jiffies.h>

    #include "mt6797-a72-cpu8-observer-internal.h"

    struct cpu8_observer_test_state {
            unsigned int dispatch_cpu;
            bool dispatch_wait;
            smp_call_func_t pending_function;
            void *pending_info;
            unsigned long wait_timeout;
            unsigned int current_cpu;
            int dispatch_errno;
            int identity_errno;
            bool hold_callback;
            bool force_timeout;
            u32 dispatches;
            u32 waits;
            u32 current_cpu_calls;
            u32 identity_calls;
    };

    static int cpu8_observer_test_dispatch(
            void *context, unsigned int cpu, smp_call_func_t function, void *info,
            bool wait)
    {
            struct cpu8_observer_test_state *state = context;

            state->dispatches++;
            state->dispatch_cpu = cpu;
            state->dispatch_wait = wait;
            state->pending_function = function;
            state->pending_info = info;
            if (state->dispatch_errno)
                    return state->dispatch_errno;
            if (!state->hold_callback)
                    function(info);
            return 0;
    }

    static unsigned long cpu8_observer_test_wait(
            void *context, struct completion *completion, unsigned long timeout)
    {
            struct cpu8_observer_test_state *state = context;

            state->waits++;
            state->wait_timeout = timeout;
            if (state->force_timeout)
                    return 0;
            return completion_done(completion);
    }

    static unsigned int cpu8_observer_test_current_cpu(void *context)
    {
            struct cpu8_observer_test_state *state = context;

            state->current_cpu_calls++;
            return state->current_cpu;
    }

    static int cpu8_observer_test_identity(
            void *context, const struct mt6797_a72_hotplug_identity *identity)
    {
            struct cpu8_observer_test_state *state = context;

            state->identity_calls++;
            return state->identity_errno;
    }

    static const struct mt6797_a72_cpu8_observer_ops cpu8_observer_test_ops = {
            .dispatch = cpu8_observer_test_dispatch,
            .wait_timeout = cpu8_observer_test_wait,
            .current_cpu = cpu8_observer_test_current_cpu,
            .identity_check = cpu8_observer_test_identity,
    };

    static void cpu8_observer_test_identity_init(
            struct mt6797_a72_hotplug_identity *identity)
    {
            memset(identity, 0, sizeof(*identity));
            identity->abi = MT6797_A72_HOTPLUG_ABI;
            identity->operation = MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN;
            identity->target_cpu = 9;
            identity->cpuhp_target = CPUHP_OFFLINE;
            identity->target_mpidr = 0x201;
            identity->generation = 41;
            identity->cookie = 42;
            identity->parent_generation = 31;
            identity->parent_cookie = 32;
    }

    static struct mt6797_a72_cpu8_observer *
    cpu8_observer_test_observer(struct kunit *test)
    {
            struct mt6797_a72_cpu8_observer *observer;

            observer = kunit_kzalloc(test, sizeof(*observer), GFP_KERNEL);
            mt6797_a72_cpu8_observer_init(observer);
            return observer;
    }

    static struct cpu8_observer_test_state *
    cpu8_observer_test_state(struct kunit *test)
    {
            struct cpu8_observer_test_state *state;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            if (state)
                    state->current_cpu = MT6797_A72_CPU8_OBSERVER_CPU;
            return state;
    }

    static void cpu8_observer_success_test(struct kunit *test)
    {
            struct mt6797_a72_cpu8_observer *observer =
                    cpu8_observer_test_observer(test);
            struct cpu8_observer_test_state *state =
                    cpu8_observer_test_state(test);
            struct mt6797_a72_hotplug_identity identity;

            KUNIT_ASSERT_NOT_NULL(test, observer);
            KUNIT_ASSERT_NOT_NULL(test, state);
            cpu8_observer_test_identity_init(&identity);
            KUNIT_EXPECT_EQ(test, mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &cpu8_observer_test_ops, state, &identity), 0);
            KUNIT_EXPECT_EQ(test, state->dispatch_cpu, 8U);
            KUNIT_EXPECT_FALSE(test, state->dispatch_wait);
            KUNIT_EXPECT_EQ(test, state->dispatches, 1U);
            KUNIT_EXPECT_EQ(test, state->waits, 1U);
            KUNIT_EXPECT_EQ(test, state->wait_timeout,
                            msecs_to_jiffies(250));
            KUNIT_EXPECT_EQ(test, state->current_cpu_calls, 1U);
            KUNIT_EXPECT_EQ(test, state->identity_calls, 1U);
            KUNIT_EXPECT_EQ(test, atomic_read(&observer->state),
                            MT6797_A72_CPU8_OBSERVER_SUCCEEDED);
    }

    static void cpu8_observer_cpu_refusal_test(struct kunit *test)
    {
            struct mt6797_a72_cpu8_observer *observer =
                    cpu8_observer_test_observer(test);
            struct cpu8_observer_test_state *state =
                    cpu8_observer_test_state(test);
            struct mt6797_a72_hotplug_identity identity;

            KUNIT_ASSERT_NOT_NULL(test, observer);
            KUNIT_ASSERT_NOT_NULL(test, state);
            cpu8_observer_test_identity_init(&identity);
            state->current_cpu = 7;
            KUNIT_EXPECT_EQ(test, mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &cpu8_observer_test_ops, state, &identity),
                            -EPROTO);
            KUNIT_EXPECT_EQ(test, state->identity_calls, 0U);
            KUNIT_EXPECT_EQ(test, atomic_read(&observer->state),
                            MT6797_A72_CPU8_OBSERVER_CALLBACK_FAILED);
    }

    static void cpu8_observer_identity_refusal_test(struct kunit *test)
    {
            struct mt6797_a72_cpu8_observer *observer =
                    cpu8_observer_test_observer(test);
            struct cpu8_observer_test_state *state =
                    cpu8_observer_test_state(test);
            struct mt6797_a72_hotplug_identity identity;

            KUNIT_ASSERT_NOT_NULL(test, observer);
            KUNIT_ASSERT_NOT_NULL(test, state);
            cpu8_observer_test_identity_init(&identity);
            state->identity_errno = -ESTALE;
            KUNIT_EXPECT_EQ(test, mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &cpu8_observer_test_ops, state, &identity),
                            -ESTALE);
            KUNIT_EXPECT_EQ(test, state->identity_calls, 1U);
    }

    static void cpu8_observer_dispatch_refusal_test(struct kunit *test)
    {
            struct mt6797_a72_cpu8_observer *observer =
                    cpu8_observer_test_observer(test);
            struct cpu8_observer_test_state *state =
                    cpu8_observer_test_state(test);
            struct mt6797_a72_hotplug_identity identity;

            KUNIT_ASSERT_NOT_NULL(test, observer);
            KUNIT_ASSERT_NOT_NULL(test, state);
            cpu8_observer_test_identity_init(&identity);
            state->dispatch_errno = -ENXIO;
            KUNIT_EXPECT_EQ(test, mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &cpu8_observer_test_ops, state, &identity),
                            -ENXIO);
            KUNIT_EXPECT_EQ(test, state->dispatches, 1U);
            KUNIT_EXPECT_EQ(test, state->waits, 0U);
            KUNIT_EXPECT_EQ(test, atomic_read(&observer->state),
                            MT6797_A72_CPU8_OBSERVER_DISPATCH_FAILED);
    }

    static void cpu8_observer_timeout_late_callback_test(struct kunit *test)
    {
            struct mt6797_a72_cpu8_observer *observer =
                    cpu8_observer_test_observer(test);
            struct cpu8_observer_test_state *state =
                    cpu8_observer_test_state(test);
            struct mt6797_a72_hotplug_identity identity;

            KUNIT_ASSERT_NOT_NULL(test, observer);
            KUNIT_ASSERT_NOT_NULL(test, state);
            cpu8_observer_test_identity_init(&identity);
            state->hold_callback = true;
            state->force_timeout = true;
            KUNIT_EXPECT_EQ(test, mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &cpu8_observer_test_ops, state, &identity),
                            -ETIMEDOUT);
            KUNIT_ASSERT_NOT_NULL(test, state->pending_function);
            state->pending_function(state->pending_info);
            KUNIT_EXPECT_EQ(test, atomic_read(&observer->state),
                            MT6797_A72_CPU8_OBSERVER_TIMED_OUT);
            KUNIT_EXPECT_EQ(test, atomic_read(&observer->late_callbacks), 1);
            KUNIT_EXPECT_EQ(test, state->current_cpu_calls, 0U);
            KUNIT_EXPECT_EQ(test, state->identity_calls, 0U);
            KUNIT_EXPECT_FALSE(test, completion_done(&observer->completion));
    }

    static void cpu8_observer_one_shot_test(struct kunit *test)
    {
            struct mt6797_a72_cpu8_observer *observer =
                    cpu8_observer_test_observer(test);
            struct cpu8_observer_test_state *state =
                    cpu8_observer_test_state(test);
            struct mt6797_a72_hotplug_identity identity;

            KUNIT_ASSERT_NOT_NULL(test, observer);
            KUNIT_ASSERT_NOT_NULL(test, state);
            cpu8_observer_test_identity_init(&identity);
            KUNIT_ASSERT_EQ(test, mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &cpu8_observer_test_ops, state, &identity), 0);
            KUNIT_EXPECT_EQ(test, mt6797_a72_cpu8_observer_run_with_ops(
                    observer, &cpu8_observer_test_ops, state, &identity),
                            -EALREADY);
            KUNIT_EXPECT_EQ(test, state->dispatches, 1U);
            KUNIT_EXPECT_EQ(test, atomic_read(&observer->dispatch_calls), 1);
    }

    static void cpu8_observer_snapshot_identity_test(struct kunit *test)
    {
            struct mt6797_a72_hotplug_snapshot snapshot = { };
            struct mt6797_a72_hotplug_identity identity;

            cpu8_observer_test_identity_init(&identity);
            snapshot.abi = MT6797_A72_HOTPLUG_ABI;
            snapshot.phase = MT6797_A72_HOTPLUG_OFF_COMMITTED;
            snapshot.owner_health = MT6797_A72_OWNER_AVAILABLE;
            snapshot.controller_present = 1;
            snapshot.members = BIT(0) | BIT(1);
            snapshot.active.valid = 1;
            snapshot.active.identity = identity;
            snapshot.active.off_committed = 1;
            snapshot.active.budgets.cpu_off = MT6797_A72_BUDGET_CONSUMED;
            snapshot.active.budgets.affinity = MT6797_A72_BUDGET_AVAILABLE;
            KUNIT_EXPECT_TRUE(test, mt6797_a72_cpu8_observer_identity_matches(
                    &snapshot, &identity));
            snapshot.phase = MT6797_A72_HOTPLUG_OFF_PROVEN;
            KUNIT_EXPECT_FALSE(test, mt6797_a72_cpu8_observer_identity_matches(
                    &snapshot, &identity));
            snapshot.phase = MT6797_A72_HOTPLUG_OFF_COMMITTED;
            snapshot.active.identity.cookie++;
            KUNIT_EXPECT_FALSE(test, mt6797_a72_cpu8_observer_identity_matches(
                    &snapshot, &identity));
            KUNIT_EXPECT_FALSE(test, mt6797_a72_cpu8_observer_identity_matches(
                    NULL, &identity));
    }

    static struct kunit_case cpu8_observer_cases[] = {
            KUNIT_CASE(cpu8_observer_success_test),
            KUNIT_CASE(cpu8_observer_cpu_refusal_test),
            KUNIT_CASE(cpu8_observer_identity_refusal_test),
            KUNIT_CASE(cpu8_observer_dispatch_refusal_test),
            KUNIT_CASE(cpu8_observer_timeout_late_callback_test),
            KUNIT_CASE(cpu8_observer_one_shot_test),
            KUNIT_CASE(cpu8_observer_snapshot_identity_test),
            { }
    };

    static struct kunit_suite cpu8_observer_suite = {
            .name = "mt6797-a72-cpu8-observer",
            .test_cases = cpu8_observer_cases,
    };

    kunit_test_suite(cpu8_observer_suite);
    """)


KCONFIG = kernel_text(r"""
    config MTK_MT6797_A72_CPU8_OBSERVER
            bool "MediaTek MT6797 retained-CPU8 hotplug observer"
            depends on SMP
            depends on MTK_MT6797_A72_HOTPLUG_EXECUTOR
            depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
            default n
            help
              Build a disconnected one-shot observer for the retained CPU8 during
              a CPU9-off transaction. It queues one asynchronous CPU8 callback,
              validates the active down identity, and waits at most 250 ms.

              No production caller is provided, CPU hotplug remains vetoed, and
              no CPU request, PSCI, MMIO, retained-memory, watchdog, or device
              action is issued unless a later binder explicitly calls it.

    config MTK_MT6797_A72_CPU8_OBSERVER_KUNIT_TEST
            bool "KUnit tests for the MT6797 retained-CPU8 observer"
            depends on KUNIT=y
            depends on MTK_MT6797_A72_CPU8_OBSERVER
            default n
            help
              Exercise exact CPU and identity checking, one asynchronous dispatch,
              bounded completion, dispatch failure, timeout, late-callback refusal,
              and one-shot behavior through injected operations only.

              These tests issue no IPI, CPU request, PSCI, MMIO, retained-memory,
              watchdog, network, storage, or device action. If unsure, say N.

    """)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    mediatek = root / "drivers/soc/mediatek"
    for relative in (
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "arch/arm64/include/asm/mt6797_a72_membership.h",
    ):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"unsafe or absent source: {relative}")
    outputs = {
        mediatek / "mt6797-a72-cpu8-observer-internal.h": INTERNAL_HEADER,
        mediatek / "mt6797-a72-cpu8-observer.c": SOURCE,
        mediatek / "mt6797-a72-cpu8-observer-test.c": TEST_SOURCE,
    }
    for path, text in outputs.items():
        if path.exists():
            raise SystemExit(f"refusing to overwrite: {path}")
        path.write_text(text, encoding="utf-8")
    replace_once(
        mediatek / "Kconfig",
        "\nconfig MTK_MMSYS\n",
        "\n" + KCONFIG + "config MTK_MMSYS\n",
    )
    replace_once(
        mediatek / "Makefile",
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT_KUNIT_TEST) += "
        "mt6797-a72-hotplug-snapshot-test.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT_KUNIT_TEST) += "
        "mt6797-a72-hotplug-snapshot-test.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU8_OBSERVER) += "
        "mt6797-a72-cpu8-observer.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU8_OBSERVER_KUNIT_TEST) += "
        "mt6797-a72-cpu8-observer-test.o\n",
    )


if __name__ == "__main__":
    main()
