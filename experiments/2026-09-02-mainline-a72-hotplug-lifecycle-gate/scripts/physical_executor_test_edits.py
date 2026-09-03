#!/usr/bin/env python3
"""Add KUnit coverage for the hardware-free CPU9 physical executor."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


TEST_SOURCE = dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* KUnit coverage for the disconnected MT6797 CPU9 hotplug executor. */

    #include <kunit/test.h>
    #include <linux/errno.h>
    #include <linux/string.h>

    #include "mt6797-a72-hotplug-executor-internal.h"

    enum mt6797_hotplug_test_failure {
    \tMT6797_HOTPLUG_TEST_NONE,
    \tMT6797_HOTPLUG_TEST_PREPARE,
    \tMT6797_HOTPLUG_TEST_WATCHDOG,
    \tMT6797_HOTPLUG_TEST_SNAPSHOT,
    \tMT6797_HOTPLUG_TEST_VALIDATE,
    \tMT6797_HOTPLUG_TEST_DISABLE,
    \tMT6797_HOTPLUG_TEST_COMMIT,
    \tMT6797_HOTPLUG_TEST_CPU8,
    \tMT6797_HOTPLUG_TEST_PROOF,
    \tMT6797_HOTPLUG_TEST_COMPLETE,
    \tMT6797_HOTPLUG_TEST_FAIL,
    \tMT6797_HOTPLUG_TEST_TERMINAL,
    };

    struct mt6797_hotplug_test_state {
    \tstruct mt6797_a72_hotplug_executor_controller controller;
    \tstruct mt6797_a72_hotplug_executor_request request;
    \tstruct mt6797_a72_hotplug_executor_result result;
    \tstruct mt6797_a72_hotplug_readback samples[2];
    \tenum mt6797_hotplug_test_failure failure;
    \tint affinity_result;
    \tu32 prepare_calls;
    \tu32 watchdog_calls;
    \tu32 snapshot_calls;
    \tu32 validate_calls;
    \tu32 disable_calls;
    \tu32 commit_calls;
    \tu32 affinity_calls;
    \tu32 cpu8_calls;
    \tu32 proof_calls;
    \tu32 complete_calls;
    \tu32 fail_calls;
    \tu32 terminal_calls;
    };

    static bool mt6797_hotplug_test_fails(
    \tstruct mt6797_hotplug_test_state *state,
    \tenum mt6797_hotplug_test_failure failure)
    {
    \treturn state->failure == failure;
    }

    static int mt6797_hotplug_test_checkpoint(
    \tvoid *context, enum mt6797_a72_hotplug_executor_phase phase,
    \tenum mt6797_a72_hotplug_executor_stage stage,
    \tconst struct mt6797_a72_hotplug_executor_result *result)
    {
    \t(void)context;
    \t(void)phase;
    \t(void)stage;
    \t(void)result;
    \treturn 0;
    }

    static int mt6797_hotplug_test_prepare(
    \tvoid *context,
    \tconst struct mt6797_a72_hotplug_executor_request *request)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->prepare_calls++;
    \tif (request != &state->request)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_PREPARE) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_watchdog(void *context, u64 identity)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->watchdog_calls++;
    \tif (identity != state->request.watchdog_identity)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_WATCHDOG) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_snapshot(
    \tvoid *context, struct mt6797_a72_hotplug_readback *readback)
    {
    \tstruct mt6797_hotplug_test_state *state = context;
    \tu32 index = state->snapshot_calls++;

    \tif (mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_SNAPSHOT))
    \t\treturn -EIO;
    \tif (index >= ARRAY_SIZE(state->samples))
    \t\treturn -EOVERFLOW;
    \t*readback = state->samples[index];
    \treturn 0;
    }

    static int mt6797_hotplug_test_validate(void *context, bool tasks_frozen,
    \t\t\t\t      bool cpu8_online, bool cpu9_online)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->validate_calls++;
    \tif (tasks_frozen || !cpu8_online || !cpu9_online)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_VALIDATE) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_disable(void *context, unsigned int cpu)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->disable_calls++;
    \tif (cpu != MT6797_A72_HOTPLUG_CPU9)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_DISABLE) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_commit(void *context, unsigned int cpu)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->commit_calls++;
    \tif (cpu != MT6797_A72_HOTPLUG_CPU9)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_COMMIT) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_affinity(void *context, unsigned int cpu,
    \t\t\t\t      unsigned int level)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->affinity_calls++;
    \tif (cpu != MT6797_A72_HOTPLUG_CPU9 ||
    \t    level != MT6797_A72_HOTPLUG_AFFINITY_LEVEL0)
    \t\treturn -EPROTO;
    \treturn state->affinity_result;
    }

    static int mt6797_hotplug_test_cpu8(void *context, unsigned int cpu)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->cpu8_calls++;
    \tif (cpu != MT6797_A72_HOTPLUG_CPU8)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_CPU8) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_proof(
    \tvoid *context, const struct mt6797_a72_hotplug_executor_result *result)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->proof_calls++;
    \tif (!result->off_committed || result->affinity_calls != 1 ||
    \t    result->snapshots != 2 || result->cpu8_callbacks != 1)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_PROOF) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_complete(void *context, bool cpu8_online,
    \t\t\t\t      bool cpu9_online)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->complete_calls++;
    \tif (!cpu8_online || cpu9_online)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_COMPLETE) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_fail(void *context, int error)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->fail_calls++;
    \tif (!error)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_FAIL) ?
    \t\t-EIO : 0;
    }

    static int mt6797_hotplug_test_terminal(
    \tvoid *context, const struct mt6797_a72_hotplug_executor_result *result)
    {
    \tstruct mt6797_hotplug_test_state *state = context;

    \tstate->terminal_calls++;
    \tif (result->terminal == MT6797_A72_HOTPLUG_TERMINAL_NONE)
    \t\treturn -EPROTO;
    \treturn mt6797_hotplug_test_fails(state, MT6797_HOTPLUG_TEST_TERMINAL) ?
    \t\t-EIO : 0;
    }

    static const struct mt6797_a72_hotplug_executor_ops mt6797_hotplug_test_ops = {
    \t.checkpoint = mt6797_hotplug_test_checkpoint,
    \t.prepare_down = mt6797_hotplug_test_prepare,
    \t.watchdog_validate = mt6797_hotplug_test_watchdog,
    \t.snapshot = mt6797_hotplug_test_snapshot,
    \t.validate_down = mt6797_hotplug_test_validate,
    \t.target_disable = mt6797_hotplug_test_disable,
    \t.commit_off = mt6797_hotplug_test_commit,
    \t.affinity_info = mt6797_hotplug_test_affinity,
    \t.cpu8_callback = mt6797_hotplug_test_cpu8,
    \t.prove_off = mt6797_hotplug_test_proof,
    \t.complete_down = mt6797_hotplug_test_complete,
    \t.fail_down = mt6797_hotplug_test_fail,
    \t.terminal = mt6797_hotplug_test_terminal,
    };

    static void mt6797_hotplug_test_readback(
    \tstruct mt6797_a72_hotplug_readback *readback, bool cpu9_online)
    {
    \tu32 i;

    \tmemset(readback, 0, sizeof(*readback));
    \treadback->valid = true;
    \treadback->spm_pwr_status = 0x2a00005c;
    \treadback->spm_pwr_status_2nd = 0x2a00004c;
    \treadback->spm_cpu_pwr_status = MT6797_A72_HOTPLUG_CPU8_STATUS;
    \treadback->spm_cpu_pwr_status_2nd = MT6797_A72_HOTPLUG_CPU8_STATUS;
    \tif (cpu9_online) {
    \t\treadback->spm_cpu_pwr_status |= MT6797_A72_HOTPLUG_CPU9_STATUS;
    \t\treadback->spm_cpu_pwr_status_2nd |= MT6797_A72_HOTPLUG_CPU9_STATUS;
    \t}
    \treadback->spm_mp2_cpusys_pwr_con = 0x1013f;
    \treadback->spm_mp2_cpu0_pwr_con = 0x1033f;
    \treadback->spm_mp2_cpu1_pwr_con = cpu9_online ? 0x1033f : 0x10332;
    \treadback->spm_cpu_ext_buck_iso = 0;
    \treadback->mp2_sync_dcm = 0x15;
    \treadback->cci_mp2_port_control = 0xc0000003;
    \tfor (i = 0; i < ARRAY_SIZE(readback->provider); i++)
    \t\treadback->provider[i] = 0x20 + i;
    \tfor (i = 0; i < ARRAY_SIZE(readback->clock); i++)
    \t\treadback->clock[i] = 0x100 + i;
    \tfor (i = 0; i < ARRAY_SIZE(readback->bigidvfs); i++)
    \t\treadback->bigidvfs[i] = 0x200 + i;
    }

    static int mt6797_hotplug_test_init(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state;

    \tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
    \tKUNIT_ASSERT_NOT_NULL(test, state);
    \tatomic_set(&state->controller.consumed, 0);
    \tatomic_set(&state->controller.lifecycle,
    \t\t   MT6797_A72_HOTPLUG_LIFECYCLE_IDLE);
    \tstate->request = (struct mt6797_a72_hotplug_executor_request) {
    \t\t.cpu = MT6797_A72_HOTPLUG_CPU9,
    \t\t.members = MT6797_A72_HOTPLUG_ENTRY_MEMBERS,
    \t\t.online_mask = MT6797_A72_HOTPLUG_ENTRY_MEMBERS,
    \t\t.watchdog_identity = 0x6797,
    \t\t.owner_parent_exact = true,
    \t\t.watchdog_owned = true,
    \t};
    \tmt6797_hotplug_test_readback(&state->samples[0], true);
    \tmt6797_hotplug_test_readback(&state->samples[1], false);
    \tstate->samples[1].spm_pwr_status ^= BIT(20);
    \tstate->samples[1].spm_pwr_status_2nd ^= BIT(21);
    \tstate->affinity_result = MT6797_A72_HOTPLUG_AFFINITY_OFF;
    \ttest->priv = state;
    \treturn 0;
    }

    static int mt6797_hotplug_test_to_commit(
    \tstruct mt6797_hotplug_test_state *state)
    {
    \tint ret;

    \tret = mt6797_a72_hotplug_executor_preflight(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, &state->request,
    \t\t&state->result);
    \tif (ret)
    \t\treturn ret;
    \tret = mt6797_a72_hotplug_executor_validate(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, false, true, true,
    \t\t&state->result);
    \tif (ret)
    \t\treturn ret;
    \tret = mt6797_a72_hotplug_executor_disable(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\t&state->result);
    \tif (ret)
    \t\treturn ret;
    \treturn mt6797_a72_hotplug_executor_commit(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\t&state->result);
    }

    static void mt6797_hotplug_success(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tint ret;

    \tret = mt6797_hotplug_test_to_commit(state);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tret = mt6797_a72_hotplug_executor_kill(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\ttrue, true, false, &state->result);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tret = mt6797_a72_hotplug_executor_complete(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, true, false, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, state->result.terminal,
    \t\t\tMT6797_A72_HOTPLUG_DOWN_COMPLETE);
    \tKUNIT_EXPECT_TRUE(test, state->result.watchdog_validated);
    \tKUNIT_EXPECT_TRUE(test, state->result.off_committed);
    \tKUNIT_EXPECT_TRUE(test, state->result.off_proven);
    \tKUNIT_EXPECT_TRUE(test, state->result.completed);
    \tKUNIT_EXPECT_EQ(test, state->result.cpu_off_authorizations, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->result.affinity_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->result.snapshots, (u32)2);
    \tKUNIT_EXPECT_EQ(test, state->result.cpu8_callbacks, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->result.proof_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)0);
    \tKUNIT_EXPECT_EQ(test, state->result.terminal_commits, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->affinity_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->terminal_calls, (u32)1);
    }

    static void mt6797_hotplug_entry_rejections(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tstruct mt6797_a72_hotplug_executor_ops ops = mt6797_hotplug_test_ops;
    \tint ret;

    \tstate->request.cpu = MT6797_A72_HOTPLUG_CPU8;
    \tret = mt6797_a72_hotplug_executor_preflight(&state->controller, &ops,
    \t\tstate, &state->request, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tstate->request.cpu = MT6797_A72_HOTPLUG_CPU9;
    \tstate->request.watchdog_owned = false;
    \tret = mt6797_a72_hotplug_executor_preflight(&state->controller, &ops,
    \t\tstate, &state->request, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tstate->request.watchdog_owned = true;
    \tops.affinity_info = NULL;
    \tret = mt6797_a72_hotplug_executor_preflight(&state->controller, &ops,
    \t\tstate, &state->request, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tKUNIT_EXPECT_EQ(test, state->prepare_calls, (u32)0);
    }

    static void mt6797_hotplug_precommit_rejection(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tint ret;

    \tstate->failure = MT6797_HOTPLUG_TEST_DISABLE;
    \tret = mt6797_a72_hotplug_executor_preflight(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, &state->request,
    \t\t&state->result);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tret = mt6797_a72_hotplug_executor_validate(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, false, true, true,
    \t\t&state->result);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tret = mt6797_a72_hotplug_executor_disable(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\t&state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EIO);
    \tKUNIT_EXPECT_EQ(test, state->result.terminal,
    \t\t\tMT6797_A72_HOTPLUG_REJECTED_PRECOMMIT);
    \tKUNIT_EXPECT_FALSE(test, state->result.off_committed);
    \tKUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->affinity_calls, (u32)0);
    }

    static void mt6797_hotplug_target_return_is_fault(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tint ret;

    \tret = mt6797_hotplug_test_to_commit(state);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tret = mt6797_a72_hotplug_executor_target_returned(
    \t\t&state->controller, &mt6797_hotplug_test_ops, state,
    \t\t-EIO, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EIO);
    \tKUNIT_EXPECT_EQ(test, state->result.terminal,
    \t\t\tMT6797_A72_HOTPLUG_FAULT_POSTCOMMIT);
    \tKUNIT_EXPECT_TRUE(test, state->result.off_committed);
    \tKUNIT_EXPECT_EQ(test, state->result.fail_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->affinity_calls, (u32)0);
    }

    static void mt6797_hotplug_affinity_is_one_shot(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tint ret;

    \tret = mt6797_hotplug_test_to_commit(state);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tstate->affinity_result = 0;
    \tret = mt6797_a72_hotplug_executor_kill(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\ttrue, true, false, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EIO);
    \tKUNIT_EXPECT_EQ(test, state->affinity_calls, (u32)1);
    \tret = mt6797_a72_hotplug_executor_kill(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\ttrue, true, false, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
    \tKUNIT_EXPECT_EQ(test, state->affinity_calls, (u32)1);
    }

    static void mt6797_hotplug_readback_rejections(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tstruct mt6797_a72_hotplug_readback baseline = state->samples[0];
    \tstruct mt6797_a72_hotplug_readback post = state->samples[1];

    \tKUNIT_EXPECT_TRUE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost.spm_cpu_pwr_status |= MT6797_A72_HOTPLUG_CPU9_STATUS;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.spm_cpu_pwr_status_2nd &= ~MT6797_A72_HOTPLUG_CPU8_STATUS;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.spm_mp2_cpusys_pwr_con ^= 1;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.spm_mp2_cpu0_pwr_con ^= 1;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.spm_cpu_ext_buck_iso ^= MT6797_A72_HOTPLUG_EXT_ISO_MASK;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.mp2_sync_dcm ^= BIT(0);
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.cci_mp2_port_control ^= BIT(0);
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.cci_status_after = MT6797_A72_HOTPLUG_CCI_PENDING;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.provider[0] ^= 1;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.clock[0] ^= 1;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    \tpost = state->samples[1];
    \tpost.bigidvfs[0] ^= 1;
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
    }

    static void mt6797_hotplug_postcommit_callback_fault(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tint ret;

    \tret = mt6797_hotplug_test_to_commit(state);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tstate->failure = MT6797_HOTPLUG_TEST_CPU8;
    \tret = mt6797_a72_hotplug_executor_kill(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\ttrue, true, false, &state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EIO);
    \tKUNIT_EXPECT_EQ(test, state->result.terminal,
    \t\t\tMT6797_A72_HOTPLUG_FAULT_POSTCOMMIT);
    \tKUNIT_EXPECT_EQ(test, state->affinity_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->snapshot_calls, (u32)2);
    \tKUNIT_EXPECT_EQ(test, state->cpu8_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->proof_calls, (u32)0);
    }

    static void mt6797_hotplug_order_and_one_shot(struct kunit *test)
    {
    \tstruct mt6797_hotplug_test_state *state = test->priv;
    \tint ret;

    \tret = mt6797_a72_hotplug_executor_commit(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, MT6797_A72_HOTPLUG_CPU9,
    \t\t&state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
    \tret = mt6797_a72_hotplug_executor_preflight(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, &state->request,
    \t\t&state->result);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tret = mt6797_a72_hotplug_executor_preflight(&state->controller,
    \t\t&mt6797_hotplug_test_ops, state, &state->request,
    \t\t&state->result);
    \tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
    \tKUNIT_EXPECT_EQ(test, state->prepare_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->watchdog_calls, (u32)1);
    \tKUNIT_EXPECT_EQ(test, state->snapshot_calls, (u32)1);
    }

    static struct kunit_case mt6797_hotplug_cases[] = {
    \tKUNIT_CASE(mt6797_hotplug_success),
    \tKUNIT_CASE(mt6797_hotplug_entry_rejections),
    \tKUNIT_CASE(mt6797_hotplug_precommit_rejection),
    \tKUNIT_CASE(mt6797_hotplug_target_return_is_fault),
    \tKUNIT_CASE(mt6797_hotplug_affinity_is_one_shot),
    \tKUNIT_CASE(mt6797_hotplug_readback_rejections),
    \tKUNIT_CASE(mt6797_hotplug_postcommit_callback_fault),
    \tKUNIT_CASE(mt6797_hotplug_order_and_one_shot),
    \t{}
    };

    static struct kunit_suite mt6797_hotplug_suite = {
    \t.name = "mt6797-a72-hotplug-executor",
    \t.init = mt6797_hotplug_test_init,
    \t.test_cases = mt6797_hotplug_cases,
    };

    kunit_test_suite(mt6797_hotplug_suite);

    MODULE_LICENSE("GPL");
    """)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = (args.source_root.resolve() /
              "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c")
    if source.exists():
        raise SystemExit(f"refusing to overwrite {source}")
    source.write_text(TEST_SOURCE, encoding="utf-8")


if __name__ == "__main__":
    main()
