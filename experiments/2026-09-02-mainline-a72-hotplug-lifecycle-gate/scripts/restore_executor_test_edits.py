#!/usr/bin/env python3
"""Add focused KUnit coverage for the disconnected CPU9 restore executor."""

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


TEST_SOURCE = kernel_text(r"""
    // SPDX-License-Identifier: GPL-2.0-only
    /* KUnit tests for the disconnected one-shot CPU9 restore executor. */

    #include <kunit/test.h>

    #include <linux/errno.h>
    #include <linux/string.h>

    #include "mt6797-a72-restore-executor-internal.h"

    enum restore_executor_test_failure {
            RESTORE_TEST_NONE,
            RESTORE_TEST_PREPARE,
            RESTORE_TEST_VALIDATE,
            RESTORE_TEST_BEGIN,
            RESTORE_TEST_BOOT,
            RESTORE_TEST_COMPLETE,
            RESTORE_TEST_VERIFY,
            RESTORE_TEST_FAIL,
            RESTORE_TEST_CHECKPOINT_PREPARED,
            RESTORE_TEST_CHECKPOINT_COMMITTED,
            RESTORE_TEST_CHECKPOINT_SECONDARY,
            RESTORE_TEST_TERMINAL,
    };

    struct restore_executor_test_state {
            struct mt6797_a72_restore_executor_controller controller;
            struct mt6797_a72_restore_executor_request request;
            struct mt6797_a72_restore_executor_result result;
            struct mt6797_a72_hotplug_transaction prepared;
            enum restore_executor_test_failure failure;
            enum mt6797_a72_restore_executor_stage checkpoints[3];
            u32 checkpoint_calls;
            u32 prepare_calls;
            u32 validate_calls;
            u32 begin_calls;
            u32 boot_calls;
            u32 complete_calls;
            u32 verify_calls;
            u32 fail_calls;
            u32 terminal_calls;
    };

    static bool restore_executor_test_fails(
            struct restore_executor_test_state *state,
            enum restore_executor_test_failure failure)
    {
            return state->failure == failure;
    }

    static int restore_executor_test_checkpoint(
            void *context, enum mt6797_a72_restore_executor_stage stage,
            const struct mt6797_a72_restore_executor_result *result)
    {
            struct restore_executor_test_state *state = context;

            if (!result->attempted || stage == MT6797_A72_RESTORE_STAGE_NONE)
                    return -EPROTO;
            if (state->checkpoint_calls >= ARRAY_SIZE(state->checkpoints))
                    return -EOVERFLOW;
            state->checkpoints[state->checkpoint_calls++] = stage;
            if ((stage == MT6797_A72_RESTORE_STAGE_PREPARED &&
                 restore_executor_test_fails(
                         state, RESTORE_TEST_CHECKPOINT_PREPARED)) ||
                (stage == MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED &&
                 restore_executor_test_fails(
                         state, RESTORE_TEST_CHECKPOINT_COMMITTED)) ||
                (stage == MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE &&
                 restore_executor_test_fails(
                         state, RESTORE_TEST_CHECKPOINT_SECONDARY)))
                    return -EIO;
            return 0;
    }

    static int restore_executor_test_prepare(
            void *context, unsigned int cpu, enum cpuhp_state target,
            bool cpu8_online, bool cpu9_online,
            struct mt6797_a72_hotplug_transaction *restore)
    {
            struct restore_executor_test_state *state = context;

            state->prepare_calls++;
            if (cpu != MT6797_A72_RESTORE_CPU9 || target != CPUHP_ONLINE ||
                !cpu8_online || cpu9_online)
                    return -EPROTO;
            if (restore_executor_test_fails(state, RESTORE_TEST_PREPARE))
                    return -EIO;
            *restore = state->prepared;
            return 0;
    }

    static int restore_executor_test_validate(
            void *context,
            const struct mt6797_a72_restore_executor_request *request,
            const struct mt6797_a72_hotplug_transaction *restore)
    {
            struct restore_executor_test_state *state = context;

            state->validate_calls++;
            if (request != &state->result.request ||
                restore != &state->result.restore ||
                !mt6797_a72_restore_transaction_valid(
                        &request->down_parent, restore, false, false))
                    return -EPROTO;
            return restore_executor_test_fails(state, RESTORE_TEST_VALIDATE) ?
                    -EIO : 0;
    }

    static int restore_executor_test_begin(
            void *context, struct mt6797_a72_hotplug_transaction *restore,
            bool cpu8_online, bool cpu9_online)
    {
            struct restore_executor_test_state *state = context;

            state->begin_calls++;
            if (!cpu8_online || cpu9_online ||
                !mt6797_a72_restore_transaction_valid(
                        &state->request.down_parent, restore, false, false))
                    return -EPROTO;
            if (restore_executor_test_fails(state, RESTORE_TEST_BEGIN))
                    return -EIO;
            restore->budgets.cpu_on = MT6797_A72_BUDGET_CONSUMED;
            return 0;
    }

    static int restore_executor_test_boot(void *context, unsigned int cpu)
    {
            struct restore_executor_test_state *state = context;

            state->boot_calls++;
            if (cpu != MT6797_A72_RESTORE_CPU9)
                    return -EPROTO;
            return restore_executor_test_fails(state, RESTORE_TEST_BOOT) ?
                    -EIO : 0;
    }

    static int restore_executor_test_complete(
            void *context, struct mt6797_a72_hotplug_transaction *restore,
            bool cpu8_online, bool cpu9_online)
    {
            struct restore_executor_test_state *state = context;

            state->complete_calls++;
            if (!cpu8_online || !cpu9_online ||
                !mt6797_a72_restore_transaction_valid(
                        &state->request.down_parent, restore, true, false))
                    return -EPROTO;
            if (restore_executor_test_fails(state, RESTORE_TEST_COMPLETE))
                    return -EIO;
            restore->completed = 1;
            restore->restored = 1;
            return 0;
    }

    static int restore_executor_test_verify(
            void *context,
            const struct mt6797_a72_restore_executor_request *request,
            const struct mt6797_a72_hotplug_transaction *restore,
            u32 members, u32 online_mask, u64 system_online_mask)
    {
            struct restore_executor_test_state *state = context;

            state->verify_calls++;
            if (request != &state->result.request ||
                members != MT6797_A72_RESTORE_ONLINE_MEMBERS ||
                online_mask != MT6797_A72_RESTORE_ONLINE_MEMBERS ||
                system_online_mask != MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK ||
                !mt6797_a72_restore_transaction_valid(
                        &request->down_parent, restore, true, true))
                    return -EPROTO;
            return restore_executor_test_fails(state, RESTORE_TEST_VERIFY) ?
                    -EIO : 0;
    }

    static int restore_executor_test_fail(
            void *context, struct mt6797_a72_hotplug_transaction *restore,
            int error)
    {
            struct restore_executor_test_state *state = context;

            state->fail_calls++;
            if (restore != &state->result.restore || !error)
                    return -EPROTO;
            return restore_executor_test_fails(state, RESTORE_TEST_FAIL) ?
                    -EIO : 0;
    }

    static int restore_executor_test_terminal(
            void *context,
            const struct mt6797_a72_restore_executor_result *result)
    {
            struct restore_executor_test_state *state = context;

            state->terminal_calls++;
            if (result != &state->result ||
                result->terminal == MT6797_A72_RESTORE_TERMINAL_NONE)
                    return -EPROTO;
            return restore_executor_test_fails(state, RESTORE_TEST_TERMINAL) ?
                    -EIO : 0;
    }

    static const struct mt6797_a72_restore_executor_ops
    restore_executor_test_ops = {
            .checkpoint = restore_executor_test_checkpoint,
            .prepare_restore = restore_executor_test_prepare,
            .validate_restore = restore_executor_test_validate,
            .begin_restore = restore_executor_test_begin,
            .cpu_boot = restore_executor_test_boot,
            .complete_restore = restore_executor_test_complete,
            .verify_terminal = restore_executor_test_verify,
            .fail_restore = restore_executor_test_fail,
            .terminal = restore_executor_test_terminal,
    };

    static void restore_executor_test_down_parent(
            struct mt6797_a72_hotplug_transaction *down)
    {
            memset(down, 0, sizeof(*down));
            down->identity.abi = MT6797_A72_HOTPLUG_ABI;
            down->identity.operation = MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN;
            down->identity.target_cpu = MT6797_A72_RESTORE_CPU9;
            down->identity.cpuhp_target = CPUHP_OFFLINE;
            down->identity.target_mpidr = 0x201;
            down->identity.generation = 0x31;
            down->identity.cookie = 0x41;
            down->identity.parent_generation = 0x11;
            down->identity.parent_cookie = 0x21;
            down->budgets.cpu_off = MT6797_A72_BUDGET_CONSUMED;
            down->budgets.affinity = MT6797_A72_BUDGET_CONSUMED;
            down->provider_identity.generation = 0x51;
            down->provider_identity.cookie = 0x61;
            down->entry_members = MT6797_A72_RESTORE_ONLINE_MEMBERS;
            down->entry_online_mask = MT6797_A72_RESTORE_ONLINE_MEMBERS;
            down->off_committed = 1;
            down->off_proven = 1;
            down->completed = 1;
            down->valid = 1;
            down->off_proof.abi = MT6797_A72_CPU9_OFF_PROOF_ABI;
            down->off_proof.valid = 1;
            down->off_proof.affinity_attempted = 1;
            down->off_proof.affinity_level = MT6797_A72_AFFINITY_LEVEL0;
            down->off_proof.affinity_state = MT6797_A72_AFFINITY_STATE_OFF;
            down->off_proof.cpu9_per_core_off = 1;
            down->off_proof.cpu8_responsive = 1;
            down->off_proof.shared_state_unchanged = 1;
            down->off_proof.members_before = MT6797_A72_RESTORE_ONLINE_MEMBERS;
            down->off_proof.online_mask_after =
                    MT6797_A72_RESTORE_OFFLINE_MEMBERS;
            down->off_proof.provider_identity = down->provider_identity;
            down->off_proof.transaction_generation = down->identity.generation;
            down->off_proof.transaction_cookie = down->identity.cookie;
    }

    static void restore_executor_test_prepared(
            struct mt6797_a72_hotplug_transaction *restore,
            const struct mt6797_a72_hotplug_transaction *down)
    {
            memset(restore, 0, sizeof(*restore));
            restore->identity.abi = MT6797_A72_HOTPLUG_ABI;
            restore->identity.operation =
                    MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE;
            restore->identity.target_cpu = MT6797_A72_RESTORE_CPU9;
            restore->identity.cpuhp_target = CPUHP_ONLINE;
            restore->identity.target_mpidr = 0x201;
            restore->identity.generation = 0x32;
            restore->identity.cookie = 0x42;
            restore->identity.parent_generation = down->identity.generation;
            restore->identity.parent_cookie = down->identity.cookie;
            restore->budgets.cpu_on = MT6797_A72_BUDGET_AVAILABLE;
            restore->provider_identity = down->provider_identity;
            restore->entry_members = MT6797_A72_RESTORE_OFFLINE_MEMBERS;
            restore->entry_online_mask = MT6797_A72_RESTORE_OFFLINE_MEMBERS;
            restore->valid = 1;
    }

    static struct restore_executor_test_state *
    restore_executor_test_new(struct kunit *test)
    {
            struct restore_executor_test_state *state;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            if (!state)
                    return NULL;
            mt6797_a72_restore_executor_init(&state->controller);
            restore_executor_test_down_parent(&state->request.down_parent);
            state->request.cpu = MT6797_A72_RESTORE_CPU9;
            state->request.target = CPUHP_ONLINE;
            state->request.members = MT6797_A72_RESTORE_OFFLINE_MEMBERS;
            state->request.online_mask = MT6797_A72_RESTORE_OFFLINE_MEMBERS;
            state->request.system_online_mask =
                    MT6797_A72_RESTORE_OFFLINE_SYSTEM_MASK;
            state->request.controller_identity = 0x1234;
            state->request.watchdog_identity = 0x6797;
            state->request.watchdog_owned = true;
            restore_executor_test_prepared(&state->prepared,
                                           &state->request.down_parent);
            return state;
    }

    static int restore_executor_test_init(struct kunit *test)
    {
            test->priv = restore_executor_test_new(test);
            return test->priv ? 0 : -ENOMEM;
    }

    static int restore_executor_test_to_validated(
            struct restore_executor_test_state *state)
    {
            int ret;

            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &restore_executor_test_ops, state,
                    &state->request, &state->result);
            if (ret)
                    return ret;
            return mt6797_a72_restore_executor_validate(
                    &state->controller, &restore_executor_test_ops, state,
                    false, true, false,
                    MT6797_A72_RESTORE_OFFLINE_SYSTEM_MASK, &state->result);
    }

    static int restore_executor_test_to_issued(
            struct restore_executor_test_state *state)
    {
            int ret = restore_executor_test_to_validated(state);

            if (ret)
                    return ret;
            return mt6797_a72_restore_executor_boot(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, true, false, &state->result);
    }

    static int restore_executor_test_to_secondary(
            struct restore_executor_test_state *state)
    {
            int ret = restore_executor_test_to_issued(state);

            if (ret)
                    return ret;
            return mt6797_a72_restore_executor_secondary_complete(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, &state->result);
    }

    static void restore_executor_success_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            int ret;

            ret = restore_executor_test_to_secondary(state);
            KUNIT_ASSERT_EQ(test, ret, 0);
            ret = mt6797_a72_restore_executor_complete(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, CPUHP_ONLINE, true, true,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK, &state->result);
            KUNIT_EXPECT_EQ(test, ret, 0);
            KUNIT_EXPECT_EQ(test, state->result.terminal,
                            MT6797_A72_RESTORE_SUCCESS);
            KUNIT_EXPECT_TRUE(test, state->result.completed);
            KUNIT_EXPECT_TRUE(test, state->result.owner_completed);
            KUNIT_EXPECT_EQ(test, state->result.prepare_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.validate_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.begin_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.cpu_boot_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.complete_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.verify_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)0);
            KUNIT_EXPECT_EQ(test, state->result.checkpoint_calls, (u32)3);
            KUNIT_EXPECT_EQ(test, state->result.terminal_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->checkpoint_calls, (u32)3);
            KUNIT_EXPECT_EQ(test, state->checkpoints[0],
                            MT6797_A72_RESTORE_STAGE_PREPARED);
            KUNIT_EXPECT_EQ(test, state->checkpoints[1],
                            MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED);
            KUNIT_EXPECT_EQ(test, state->checkpoints[2],
                            MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE);
            KUNIT_EXPECT_EQ(test, atomic_read(&state->controller.lifecycle),
                            MT6797_A72_RESTORE_TERMINAL);
    }

    static void restore_executor_entry_refusal_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            struct mt6797_a72_restore_executor_ops ops =
                    restore_executor_test_ops;
            int ret;

            state->request.cpu = MT6797_A72_RESTORE_CPU8;
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &ops, state, &state->request,
                    &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EINVAL);
            state->request.cpu = MT6797_A72_RESTORE_CPU9;
            state->request.system_online_mask =
                    MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK;
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &ops, state, &state->request,
                    &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EINVAL);
            state->request.system_online_mask =
                    MT6797_A72_RESTORE_OFFLINE_SYSTEM_MASK;
            state->request.watchdog_owned = false;
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &ops, state, &state->request,
                    &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EINVAL);
            state->request.watchdog_owned = true;
            state->request.down_parent.off_proof.cpu8_responsive = 0;
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &ops, state, &state->request,
                    &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EINVAL);
            state->request.down_parent.off_proof.cpu8_responsive = 1;
            ops.cpu_boot = NULL;
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &ops, state, &state->request,
                    &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EINVAL);
            KUNIT_EXPECT_EQ(test, state->prepare_calls, (u32)0);
            KUNIT_EXPECT_EQ(test, atomic_read(&state->controller.consumed), 0);
    }

    static void restore_executor_prepare_failure_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            int ret;

            state->failure = RESTORE_TEST_PREPARE;
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &restore_executor_test_ops, state,
                    &state->request, &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, state->result.terminal,
                            MT6797_A72_RESTORE_FAULT);
            KUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)0);
            KUNIT_EXPECT_EQ(test, state->terminal_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->boot_calls, (u32)0);
    }

    static void restore_executor_identity_refusal_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            bool suppress = false;
            int ret;

            state->prepared.identity.parent_cookie++;
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &restore_executor_test_ops, state,
                    &state->request, &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EPROTO);
            KUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.terminal,
                            MT6797_A72_RESTORE_FAULT);
            ret = mt6797_a72_restore_executor_rollback(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, -EIO, &state->result, &suppress);
            KUNIT_EXPECT_EQ(test, ret, 0);
            KUNIT_EXPECT_TRUE(test, suppress);
            KUNIT_EXPECT_EQ(test, state->fail_calls, (u32)1);
    }

    static void restore_executor_validation_failure_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            int ret;

            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &restore_executor_test_ops, state,
                    &state->request, &state->result);
            KUNIT_ASSERT_EQ(test, ret, 0);
            state->failure = RESTORE_TEST_VALIDATE;
            ret = mt6797_a72_restore_executor_validate(
                    &state->controller, &restore_executor_test_ops, state,
                    false, true, false,
                    MT6797_A72_RESTORE_OFFLINE_SYSTEM_MASK, &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.terminal,
                            MT6797_A72_RESTORE_FAULT);
            KUNIT_EXPECT_EQ(test, state->boot_calls, (u32)0);
    }

    static void restore_executor_boot_failure_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            bool suppress = false;
            int ret;

            ret = restore_executor_test_to_validated(state);
            KUNIT_ASSERT_EQ(test, ret, 0);
            state->failure = RESTORE_TEST_BOOT;
            ret = mt6797_a72_restore_executor_boot(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, true, false, &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, state->result.begin_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.cpu_boot_calls, (u32)1);
            KUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)1);
            KUNIT_EXPECT_TRUE(test, state->result.cpu_on_committed);
            ret = mt6797_a72_restore_executor_rollback(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, -EIO, &state->result, &suppress);
            KUNIT_EXPECT_EQ(test, ret, 0);
            KUNIT_EXPECT_TRUE(test, suppress);
            KUNIT_EXPECT_EQ(test, state->fail_calls, (u32)1);
    }

    static void restore_executor_rollback_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            enum mt6797_a72_restore_executor_terminal terminal;
            enum mt6797_a72_restore_executor_stage last_stage;
            u32 terminal_calls;
            u32 fail_calls;
            s32 stage_errno;
            bool suppress = false;
            int ret;

            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &restore_executor_test_ops, state,
                    &state->request, &state->result);
            KUNIT_ASSERT_EQ(test, ret, 0);
            ret = mt6797_a72_restore_executor_rollback(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, -ECANCELED,
                    &state->result, &suppress);
            KUNIT_EXPECT_EQ(test, ret, -ECANCELED);
            KUNIT_EXPECT_TRUE(test, suppress);
            KUNIT_EXPECT_TRUE(test, state->result.rollback_suppressed);
            KUNIT_EXPECT_EQ(test, state->fail_calls, (u32)1);
            terminal = state->result.terminal;
            last_stage = state->result.last_stage;
            terminal_calls = state->result.terminal_calls;
            fail_calls = state->result.fail_calls;
            stage_errno = state->result.stage_errno;
            suppress = false;
            ret = mt6797_a72_restore_executor_rollback(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, -EIO, &state->result, &suppress);
            KUNIT_EXPECT_EQ(test, ret, 0);
            KUNIT_EXPECT_TRUE(test, suppress);
            KUNIT_EXPECT_EQ(test, state->fail_calls, (u32)1);
            ret = mt6797_a72_restore_executor_preflight(
                    &state->controller, &restore_executor_test_ops, state,
                    &state->request, &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EALREADY);
            KUNIT_EXPECT_EQ(test, state->result.terminal, terminal);
            KUNIT_EXPECT_EQ(test, state->result.last_stage, last_stage);
            KUNIT_EXPECT_EQ(test, state->result.terminal_calls, terminal_calls);
            KUNIT_EXPECT_EQ(test, state->result.fail_calls, fail_calls);
            KUNIT_EXPECT_EQ(test, state->result.stage_errno, stage_errno);
    }

    static void restore_executor_secondary_order_test(struct kunit *test)
    {
            struct restore_executor_test_state *state = test->priv;
            struct restore_executor_test_state *wrong_cpu;
            int ret;

            ret = restore_executor_test_to_issued(state);
            KUNIT_ASSERT_EQ(test, ret, 0);
            ret = mt6797_a72_restore_executor_complete(
                    &state->controller, &restore_executor_test_ops, state,
                    MT6797_A72_RESTORE_CPU9, CPUHP_ONLINE, true, true,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK, &state->result);
            KUNIT_EXPECT_EQ(test, ret, -EPROTO);
            KUNIT_EXPECT_EQ(test, state->fail_calls, (u32)1);

            wrong_cpu = restore_executor_test_new(test);
            KUNIT_ASSERT_NOT_NULL(test, wrong_cpu);
            ret = restore_executor_test_to_issued(wrong_cpu);
            KUNIT_ASSERT_EQ(test, ret, 0);
            ret = mt6797_a72_restore_executor_secondary_complete(
                    &wrong_cpu->controller, &restore_executor_test_ops,
                    wrong_cpu, MT6797_A72_RESTORE_CPU8, &wrong_cpu->result);
            KUNIT_EXPECT_EQ(test, ret, -EPROTO);
            KUNIT_EXPECT_EQ(test, wrong_cpu->fail_calls, (u32)1);
            KUNIT_EXPECT_FALSE(test, wrong_cpu->result.secondary_completed);
    }

    static void restore_executor_checkpoint_failure_test(struct kunit *test)
    {
            struct restore_executor_test_state *prepared;
            struct restore_executor_test_state *committed;
            struct restore_executor_test_state *secondary;
            int ret;

            prepared = restore_executor_test_new(test);
            KUNIT_ASSERT_NOT_NULL(test, prepared);
            prepared->failure = RESTORE_TEST_CHECKPOINT_PREPARED;
            ret = mt6797_a72_restore_executor_preflight(
                    &prepared->controller, &restore_executor_test_ops, prepared,
                    &prepared->request, &prepared->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, prepared->fail_calls, (u32)1);

            committed = restore_executor_test_new(test);
            KUNIT_ASSERT_NOT_NULL(test, committed);
            ret = restore_executor_test_to_validated(committed);
            KUNIT_ASSERT_EQ(test, ret, 0);
            committed->failure = RESTORE_TEST_CHECKPOINT_COMMITTED;
            ret = mt6797_a72_restore_executor_boot(
                    &committed->controller, &restore_executor_test_ops,
                    committed, MT6797_A72_RESTORE_CPU9, true, false,
                    &committed->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, committed->boot_calls, (u32)0);
            KUNIT_EXPECT_EQ(test, committed->fail_calls, (u32)1);

            secondary = restore_executor_test_new(test);
            KUNIT_ASSERT_NOT_NULL(test, secondary);
            ret = restore_executor_test_to_issued(secondary);
            KUNIT_ASSERT_EQ(test, ret, 0);
            secondary->failure = RESTORE_TEST_CHECKPOINT_SECONDARY;
            ret = mt6797_a72_restore_executor_secondary_complete(
                    &secondary->controller, &restore_executor_test_ops,
                    secondary, MT6797_A72_RESTORE_CPU9, &secondary->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, secondary->fail_calls, (u32)1);
    }

    static void restore_executor_completion_failure_test(struct kunit *test)
    {
            struct restore_executor_test_state *complete;
            struct restore_executor_test_state *verify;
            struct restore_executor_test_state *terminal;
            int ret;

            complete = restore_executor_test_new(test);
            KUNIT_ASSERT_NOT_NULL(test, complete);
            ret = restore_executor_test_to_secondary(complete);
            KUNIT_ASSERT_EQ(test, ret, 0);
            complete->failure = RESTORE_TEST_COMPLETE;
            ret = mt6797_a72_restore_executor_complete(
                    &complete->controller, &restore_executor_test_ops, complete,
                    MT6797_A72_RESTORE_CPU9, CPUHP_ONLINE, true, true,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK, &complete->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, complete->fail_calls, (u32)1);

            verify = restore_executor_test_new(test);
            KUNIT_ASSERT_NOT_NULL(test, verify);
            ret = restore_executor_test_to_secondary(verify);
            KUNIT_ASSERT_EQ(test, ret, 0);
            verify->failure = RESTORE_TEST_VERIFY;
            ret = mt6797_a72_restore_executor_complete(
                    &verify->controller, &restore_executor_test_ops, verify,
                    MT6797_A72_RESTORE_CPU9, CPUHP_ONLINE, true, true,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK, &verify->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_TRUE(test, verify->result.owner_completed);
            KUNIT_EXPECT_EQ(test, verify->fail_calls, (u32)0);

            terminal = restore_executor_test_new(test);
            KUNIT_ASSERT_NOT_NULL(test, terminal);
            ret = restore_executor_test_to_secondary(terminal);
            KUNIT_ASSERT_EQ(test, ret, 0);
            terminal->failure = RESTORE_TEST_TERMINAL;
            ret = mt6797_a72_restore_executor_complete(
                    &terminal->controller, &restore_executor_test_ops, terminal,
                    MT6797_A72_RESTORE_CPU9, CPUHP_ONLINE, true, true,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_MEMBERS,
                    MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK, &terminal->result);
            KUNIT_EXPECT_EQ(test, ret, -EIO);
            KUNIT_EXPECT_EQ(test, terminal->result.terminal,
                            MT6797_A72_RESTORE_FAULT);
            KUNIT_EXPECT_TRUE(test, terminal->result.owner_completed);
            KUNIT_EXPECT_EQ(test, terminal->fail_calls, (u32)0);
            KUNIT_EXPECT_EQ(test, terminal->terminal_calls, (u32)1);
    }

    static struct kunit_case restore_executor_cases[] = {
            KUNIT_CASE(restore_executor_success_test),
            KUNIT_CASE(restore_executor_entry_refusal_test),
            KUNIT_CASE(restore_executor_prepare_failure_test),
            KUNIT_CASE(restore_executor_identity_refusal_test),
            KUNIT_CASE(restore_executor_validation_failure_test),
            KUNIT_CASE(restore_executor_boot_failure_test),
            KUNIT_CASE(restore_executor_rollback_test),
            KUNIT_CASE(restore_executor_secondary_order_test),
            KUNIT_CASE(restore_executor_checkpoint_failure_test),
            KUNIT_CASE(restore_executor_completion_failure_test),
            { }
    };

    static struct kunit_suite restore_executor_suite = {
            .name = "mt6797-a72-restore-executor",
            .init = restore_executor_test_init,
            .test_cases = restore_executor_cases,
    };

    kunit_test_suite(restore_executor_suite);
    """)


KCONFIG = kernel_text(r"""
    config MTK_MT6797_A72_RESTORE_EXECUTOR_KUNIT_TEST
            bool "KUnit tests for the MT6797 CPU9 restore executor"
            depends on KUNIT=y
            depends on MTK_MT6797_A72_RESTORE_EXECUTOR
            default n
            help
              Exercise exact restore identity, one CPU_ON budget, secondary
              and full completion, rollback ownership, publication failures,
              and terminal one-shot behavior through injected operations only.

              These tests issue no CPU request, PSCI, MMIO, retained-memory,
              watchdog, network, storage, or device action. If unsure, say N.

    """)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    mediatek = root / "drivers/soc/mediatek"
    test_path = mediatek / "mt6797-a72-restore-executor-test.c"
    if test_path.exists():
        raise SystemExit(f"refusing to overwrite: {test_path}")
    test_path.write_text(TEST_SOURCE, encoding="utf-8")
    replace_once(
        mediatek / "Kconfig",
        "config MTK_MT6797_A72_CPU8_OBSERVER\n",
        KCONFIG + "config MTK_MT6797_A72_CPU8_OBSERVER\n",
    )
    replace_once(
        mediatek / "Makefile",
        "obj-$(CONFIG_MTK_MT6797_A72_RESTORE_EXECUTOR) += "
        "mt6797-a72-restore-executor.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_RESTORE_EXECUTOR) += "
        "mt6797-a72-restore-executor.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_RESTORE_EXECUTOR_KUNIT_TEST) += "
        "mt6797-a72-restore-executor-test.o\n",
    )


if __name__ == "__main__":
    main()
