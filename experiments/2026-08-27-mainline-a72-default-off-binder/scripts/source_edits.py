#!/usr/bin/env python3
"""Apply deterministic retained-checkpoint executor repairs."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re


PARENT_HASHES = {
    "fs/pstore/gemini_transition_ledger_internal.h":
        "f84fe27f93dc559ac8a5a47a61a5da42127c0592575c0ba917a6cd60a0254c7b",
    "fs/pstore/gemini_transition_ledger_test.c":
        "056439f55388cb154a97f31d57e71ce01a300fee18ea9caaa84becd90377fe27",
    "drivers/soc/mediatek/mt6797-a72-transition-internal.h":
        "2516bcdc66e345500a0f444a8300ce2c20438efaed10b08304d3d8796b157a6d",
    "drivers/soc/mediatek/mt6797-a72-transition.c":
        "e328368822fbf16425e3506d344a52e0eb5a5e286af824c4463d4b539f571243",
    "drivers/soc/mediatek/mt6797-a72-transition-test.c":
        "1f6d0eeb460ceccb1e88fc07d8feeb6b76a7158f6f44ebeb42fedff908196722",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"source path is not an exact regular file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"source hash changed: {relative}: {actual} != {expected}"
            )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(
            f"{path}: expected one anchor: {old.splitlines()[0]}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_regex(path: Path, pattern: str, replacement: str,
                  expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text)
    if count != expected:
        raise SystemExit(
            f"{path}: expected {expected} regex anchors, found {count}"
        )
    path.write_text(updated, encoding="utf-8")


def apply_header(path: Path) -> None:
    replace_once(
        path,
        "\tMT6797_A72_TRANSITION_STAGE_DCM,\n"
        "\tMT6797_A72_TRANSITION_STAGE_COUNT,\n",
        "\tMT6797_A72_TRANSITION_STAGE_DCM,\n"
        "\tMT6797_A72_TRANSITION_STAGE_MEMBERSHIP,\n"
        "\tMT6797_A72_TRANSITION_STAGE_COUNT,\n",
    )


def apply_ledger(internal: Path, tests: Path) -> None:
    replace_once(
        internal,
        "#define GEMINI_TRANSITION_LEDGER_MAX_STAGE 9U\n",
        "#define GEMINI_TRANSITION_LEDGER_MAX_STAGE 10U\n",
    )
    replace_once(
        tests,
        "\tKUNIT_EXPECT_EQ(test, latest.generation, 19U);\n",
        "\tKUNIT_EXPECT_EQ(test, latest.generation, 21U);\n",
    )


def apply_header_rest(path: Path) -> None:
    replace_once(
        path,
        "\tint stage_errno;\n\tint rollback_errno;\n",
        "\tint stage_errno;\n\tint rollback_errno;\n"
        "\tint checkpoint_errno;\n",
    )
    replace_once(
        path,
        "\tbool p27_owned;\n\tbool provider_owned;\n",
        "\tbool p27_owned;\n\tbool provider_owned;\n"
        "\tbool membership_published;\n",
    )
    replace_once(
        path,
        "\tunsigned int checkpoints;\n\tu32 rollback_mask;\n",
        "\tunsigned int checkpoints;\n"
        "\tunsigned int terminal_commits;\n"
        "\tu32 rollback_mask;\n",
    )
    replace_once(
        path,
        "\tvoid (*checkpoint)(void *context,\n"
        "\t\t\t   enum mt6797_a72_transition_phase phase,\n"
        "\t\t\t   enum mt6797_a72_transition_stage stage,\n"
        "\t\t\t   const struct mt6797_a72_transition_result *result);\n",
        "\tint (*checkpoint)(void *context,\n"
        "\t\t\t  enum mt6797_a72_transition_phase phase,\n"
        "\t\t\t  enum mt6797_a72_transition_stage stage,\n"
        "\t\t\t  const struct mt6797_a72_transition_result *result);\n",
    )
    replace_once(
        path,
        "\tint (*dcm_update)(void *context);\n",
        "\tint (*dcm_update)(void *context);\n"
        "\tint (*membership_commit)(void *context, unsigned int cpu);\n"
        "\tint (*terminal)(void *context,\n"
        "\t\t\tconst struct mt6797_a72_transition_result *result);\n",
    )


def apply_source(path: Path) -> None:
    replace_once(
        path,
        "\t\tops->secondary_complete && ops->ipi_proof && ops->dcm_update;\n",
        "\t\tops->secondary_complete && ops->ipi_proof && ops->dcm_update &&\n"
        "\t\tops->membership_commit && ops->terminal;\n",
    )


def apply_tests(path: Path) -> None:
    replace_once(
        path,
        "#define MT6797_TEST_P27_RELEASE 101U\n",
        "#define MT6797_TEST_P27_RELEASE 101U\n"
        "#define MT6797_TEST_TERMINAL 102U\n",
    )
    replace_once(
        path,
        "\tenum mt6797_a72_transition_stage malformed_stage;\n"
        "\tbool provider_release_fails;\n",
        "\tenum mt6797_a72_transition_stage malformed_stage;\n"
        "\tenum mt6797_a72_transition_stage checkpoint_fail_stage;\n"
        "\tenum mt6797_a72_transition_phase checkpoint_fail_phase;\n"
        "\tenum mt6797_a72_transition_terminal terminal_seen;\n"
        "\tbool checkpoint_fails;\n"
        "\tbool terminal_fails;\n"
        "\tbool provider_release_fails;\n",
    )
    replace_once(
        path,
        "\tunsigned int ipi_target;\n",
        "\tunsigned int ipi_target;\n"
        "\tunsigned int membership_target;\n"
        "\tunsigned int terminal_count;\n",
    )
    replace_once(
        path,
        "static void\n"
        "mt6797_test_checkpoint(void *context,\n"
        "\t\t       enum mt6797_a72_transition_phase phase,\n"
        "\t\t       enum mt6797_a72_transition_stage stage,\n"
        "\t\t       const struct mt6797_a72_transition_result *result)\n"
        "{\n"
        "\tstruct mt6797_transition_test_state *state = context;\n"
        "\tunsigned int slot = phase == MT6797_A72_TRANSITION_BEFORE ?\n"
        "\t\tMT6797_TEST_BEFORE : MT6797_TEST_AFTER;\n\n"
        "\t(void)result;\n"
        "\tmt6797_test_record(state, MT6797_TEST_EVENT(stage, slot));\n"
        "}\n",
        "static int\n"
        "mt6797_test_checkpoint(void *context,\n"
        "\t\t       enum mt6797_a72_transition_phase phase,\n"
        "\t\t       enum mt6797_a72_transition_stage stage,\n"
        "\t\t       const struct mt6797_a72_transition_result *result)\n"
        "{\n"
        "\tstruct mt6797_transition_test_state *state = context;\n"
        "\tunsigned int slot = phase == MT6797_A72_TRANSITION_BEFORE ?\n"
        "\t\tMT6797_TEST_BEFORE : MT6797_TEST_AFTER;\n\n"
        "\t(void)result;\n"
        "\tmt6797_test_record(state, MT6797_TEST_EVENT(stage, slot));\n"
        "\tif (state->checkpoint_fails &&\n"
        "\t    state->checkpoint_fail_stage == stage &&\n"
        "\t    state->checkpoint_fail_phase == phase)\n"
        "\t\treturn -EUCLEAN;\n"
        "\treturn 0;\n"
        "}\n",
    )
    replace_once(
        path,
        "static int mt6797_test_dcm(void *context)\n"
        "{\n"
        "\treturn mt6797_test_effect(context, MT6797_A72_TRANSITION_STAGE_DCM);\n"
        "}\n",
        "static int mt6797_test_dcm(void *context)\n"
        "{\n"
        "\treturn mt6797_test_effect(context, MT6797_A72_TRANSITION_STAGE_DCM);\n"
        "}\n\n"
        "static int mt6797_test_membership(void *context, unsigned int cpu)\n"
        "{\n"
        "\tstruct mt6797_transition_test_state *state = context;\n\n"
        "\tstate->membership_target = cpu;\n"
        "\treturn mt6797_test_effect(state,\n"
        "\t\t\t\t  MT6797_A72_TRANSITION_STAGE_MEMBERSHIP);\n"
        "}\n\n"
        "static int\n"
        "mt6797_test_terminal(void *context,\n"
        "\t\t     const struct mt6797_a72_transition_result *result)\n"
        "{\n"
        "\tstruct mt6797_transition_test_state *state = context;\n\n"
        "\tstate->terminal_seen = result->terminal;\n"
        "\tstate->terminal_count++;\n"
        "\tmt6797_test_record(state, MT6797_TEST_TERMINAL);\n"
        "\treturn state->terminal_fails ? -ENOSPC : 0;\n"
        "}\n",
    )
    replace_once(
        path,
        "\t.dcm_update = mt6797_test_dcm,\n",
        "\t.dcm_update = mt6797_test_dcm,\n"
        "\t.membership_commit = mt6797_test_membership,\n"
        "\t.terminal = mt6797_test_terminal,\n",
    )
    replace_once(
        path,
        "\tKUNIT_EXPECT_EQ(test, result.checkpoints, 18U);\n"
        "\tKUNIT_EXPECT_EQ(test, result.retained_mask,\n",
        "\tKUNIT_EXPECT_EQ(test, result.checkpoints, 20U);\n"
        "\tKUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, result.checkpoint_errno, 0);\n"
        "\tKUNIT_EXPECT_TRUE(test, result.membership_published);\n"
        "\tKUNIT_EXPECT_EQ(test, result.retained_mask,\n",
    )
    replace_once(
        path,
        "\tKUNIT_EXPECT_EQ(test, state.ipi_target,\n"
        "\t\t\tMT6797_A72_TRANSITION_CPU8);\n"
        "\tKUNIT_ASSERT_EQ(test, state.event_count, 27U);\n",
        "\tKUNIT_EXPECT_EQ(test, state.ipi_target,\n"
        "\t\t\tMT6797_A72_TRANSITION_CPU8);\n"
        "\tKUNIT_EXPECT_EQ(test, state.membership_target,\n"
        "\t\t\tMT6797_A72_TRANSITION_CPU8);\n"
        "\tKUNIT_EXPECT_EQ(test, state.terminal_count, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, state.terminal_seen,\n"
        "\t\t\tMT6797_A72_TRANSITION_CPU8_ONLINE_PROOF);\n"
        "\tKUNIT_ASSERT_EQ(test, state.event_count, 31U);\n",
    )
    replace_once(
        path,
        "\t\tKUNIT_EXPECT_EQ(test, state.events[event++],\n"
        "\t\t\t\tMT6797_TEST_EVENT(stage, MT6797_TEST_AFTER));\n"
        "\t}\n"
        "}\n\n"
        "static void mt6797_transition_composed_run_test",
        "\t\tKUNIT_EXPECT_EQ(test, state.events[event++],\n"
        "\t\t\t\tMT6797_TEST_EVENT(stage, MT6797_TEST_AFTER));\n"
        "\t}\n"
        "\tKUNIT_EXPECT_EQ(test, state.events[event++], MT6797_TEST_TERMINAL);\n"
        "}\n\n"
        "static void mt6797_transition_composed_run_test",
    )
    replace_once(
        path,
        "\tKUNIT_EXPECT_EQ(test, result.checkpoints, 18U);\n"
        "\tKUNIT_EXPECT_EQ(test, state.event_count, 27U);\n"
        "}\n\n"
        "static void mt6797_transition_entry_rejections_test",
        "\tKUNIT_EXPECT_EQ(test, result.checkpoints, 20U);\n"
        "\tKUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);\n"
        "\tKUNIT_EXPECT_TRUE(test, result.membership_published);\n"
        "\tKUNIT_EXPECT_EQ(test, state.event_count, 31U);\n"
        "}\n\n"
        "static void mt6797_transition_entry_rejections_test",
    )
    replace_once(
        path,
        "\tops.secondary_complete = NULL;\n",
        "\tops.terminal = NULL;\n",
    )
    replace_once(
        path,
        "\tKUNIT_EXPECT_EQ(test, ret, -EALREADY);\n"
        "\tKUNIT_EXPECT_FALSE(test, result.attempted);\n"
        "\tKUNIT_EXPECT_EQ(test, result.checkpoints, 0U);\n"
        "\tKUNIT_EXPECT_EQ(test, state.event_count, events);\n"
        "}\n\n"
        "static void mt6797_transition_stage_failures_test",
        "\tKUNIT_EXPECT_EQ(test, ret, -EALREADY);\n"
        "\tKUNIT_EXPECT_TRUE(test, result.attempted);\n"
        "\tKUNIT_EXPECT_EQ(test, result.checkpoints, 20U);\n"
        "\tKUNIT_EXPECT_EQ(test, result.cpu_requests, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, result.terminal,\n"
        "\t\t\tMT6797_A72_TRANSITION_CPU8_ONLINE_PROOF);\n"
        "\tKUNIT_EXPECT_EQ(test, state.event_count, events);\n"
        "}\n\n"
        "static void mt6797_transition_stage_failures_test",
    )
    replace_once(
        path,
        "\t\tKUNIT_EXPECT_EQ_MSG(test, result.cpu_off_requests, 0U,\n"
        "\t\t\t\t    \"stage=%u\", stage);\n",
        "\t\tKUNIT_EXPECT_EQ_MSG(test, result.cpu_off_requests, 0U,\n"
        "\t\t\t\t    \"stage=%u\", stage);\n"
        "\t\tKUNIT_EXPECT_EQ_MSG(test, result.terminal_commits, 1U,\n"
        "\t\t\t\t    \"stage=%u\", stage);\n"
        "\t\tKUNIT_EXPECT_EQ_MSG(test, state.terminal_count, 1U,\n"
        "\t\t\t\t    \"stage=%u\", stage);\n",
    )
    replace_once(
        path,
        "\t\tKUNIT_EXPECT_EQ(test, result.cpu8_online,\n"
        "\t\t\t\tstage >= MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);\n"
        "\t}\n"
        "}\n\n"
        "static void mt6797_transition_lifecycle_failure_test",
        "\t\tKUNIT_EXPECT_EQ(test, result.cpu8_online,\n"
        "\t\t\t\tstage >= MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);\n"
        "\t\tKUNIT_EXPECT_EQ(test, result.membership_published,\n"
        "\t\t\t\tstage > MT6797_A72_TRANSITION_STAGE_MEMBERSHIP);\n"
        "\t}\n"
        "}\n\n"
        "static void mt6797_transition_lifecycle_failure_test",
    )
    insert = r'''
static void mt6797_transition_checkpoint_failures_test(struct kunit *test)
{
	enum mt6797_a72_transition_stage stage;

	for (stage = MT6797_A72_TRANSITION_STAGE_WATCHDOG;
	     stage < MT6797_A72_TRANSITION_STAGE_COUNT; stage++) {
		enum mt6797_a72_transition_phase phase;

		for (phase = MT6797_A72_TRANSITION_BEFORE;
		     phase <= MT6797_A72_TRANSITION_AFTER; phase++) {
			struct mt6797_a72_transition_request request =
				mt6797_test_request();
			struct mt6797_transition_test_state state = {
				.checkpoint_fails = true,
				.checkpoint_fail_stage = stage,
				.checkpoint_fail_phase = phase,
			};
			struct mt6797_a72_transition_result result;
			bool preisolation;
			int ret;

			ret = mt6797_test_run(&state, &request, &result);
			KUNIT_EXPECT_EQ_MSG(test, ret, -EUCLEAN,
					    "stage=%u phase=%u", stage, phase);
			KUNIT_EXPECT_EQ(test, result.checkpoint_errno, -EUCLEAN);
			KUNIT_EXPECT_EQ(test, result.stage_errno, -EUCLEAN);
			KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);
			KUNIT_EXPECT_EQ(test, state.terminal_count, 1U);
			KUNIT_EXPECT_EQ(test, result.cpu_off_requests, 0U);
			KUNIT_EXPECT_EQ(test, result.retries, 0U);
			preisolation =
				stage < MT6797_A72_TRANSITION_STAGE_ISOLATION ||
				(stage == MT6797_A72_TRANSITION_STAGE_ISOLATION &&
				 phase == MT6797_A72_TRANSITION_BEFORE);
			if (stage == MT6797_A72_TRANSITION_STAGE_WATCHDOG &&
			    phase == MT6797_A72_TRANSITION_BEFORE)
				KUNIT_EXPECT_EQ(test, result.terminal,
						MT6797_A72_TRANSITION_REJECTED_PRESTATE);
			else if (preisolation)
				KUNIT_EXPECT_EQ(test, result.terminal,
						MT6797_A72_TRANSITION_ROLLED_BACK_PREISO);
			else
				KUNIT_EXPECT_EQ(test, result.terminal,
						MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO);
			KUNIT_EXPECT_EQ(test, result.membership_published,
					stage == MT6797_A72_TRANSITION_STAGE_MEMBERSHIP &&
					phase == MT6797_A72_TRANSITION_AFTER);
		}
	}
}

static void mt6797_transition_terminal_failures_test(struct kunit *test)
{
	struct mt6797_a72_transition_request request = mt6797_test_request();
	enum mt6797_a72_transition_stage stage;

	for (stage = MT6797_A72_TRANSITION_STAGE_WATCHDOG;
	     stage < MT6797_A72_TRANSITION_STAGE_COUNT; stage++) {
		struct mt6797_transition_test_state state = {
			.fail_stage = stage,
			.terminal_fails = true,
		};
		struct mt6797_a72_transition_result result;
		int ret;

		ret = mt6797_test_run(&state, &request, &result);
		KUNIT_EXPECT_EQ_MSG(test, ret, -EIO, "stage=%u", stage);
		KUNIT_EXPECT_EQ(test, result.stage_errno, -EIO);
		KUNIT_EXPECT_EQ(test, result.checkpoint_errno, -ENOSPC);
		KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);
		KUNIT_EXPECT_EQ(test, state.terminal_count, 1U);
	}
	for (stage = MT6797_A72_TRANSITION_STAGE_WATCHDOG;
	     stage < MT6797_A72_TRANSITION_STAGE_COUNT; stage++) {
		enum mt6797_a72_transition_phase phase;

		for (phase = MT6797_A72_TRANSITION_BEFORE;
		     phase <= MT6797_A72_TRANSITION_AFTER; phase++) {
			struct mt6797_transition_test_state state = {
				.checkpoint_fails = true,
				.checkpoint_fail_stage = stage,
				.checkpoint_fail_phase = phase,
				.terminal_fails = true,
			};
			struct mt6797_a72_transition_result result;
			int ret;

			ret = mt6797_test_run(&state, &request, &result);
			KUNIT_EXPECT_EQ(test, ret, -EUCLEAN);
			KUNIT_EXPECT_EQ(test, result.stage_errno, -EUCLEAN);
			KUNIT_EXPECT_EQ(test, result.checkpoint_errno, -ENOSPC);
			KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);
			KUNIT_EXPECT_EQ(test, state.terminal_count, 1U);
		}
	}
	{
		struct mt6797_transition_test_state state = {
			.terminal_fails = true,
		};
		struct mt6797_a72_transition_result result;
		int ret;

		ret = mt6797_test_run(&state, &request, &result);
		KUNIT_EXPECT_EQ(test, ret, -ENOSPC);
		KUNIT_EXPECT_TRUE(test, result.membership_published);
		KUNIT_EXPECT_EQ(test, result.terminal,
				MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO);
		KUNIT_EXPECT_EQ(test, state.terminal_seen,
				MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF);
		KUNIT_EXPECT_EQ(test, result.checkpoint_errno, -ENOSPC);
		KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);
		KUNIT_EXPECT_EQ(test, state.terminal_count, 1U);
	}
}
'''
    replace_once(
        path,
        "\nstatic struct kunit_case mt6797_transition_cases[] = {\n",
        insert + "\nstatic struct kunit_case mt6797_transition_cases[] = {\n",
    )
    replace_once(
        path,
        "\tKUNIT_CASE(mt6797_transition_stage_failures_test),\n",
        "\tKUNIT_CASE(mt6797_transition_stage_failures_test),\n"
        "\tKUNIT_CASE(mt6797_transition_checkpoint_failures_test),\n"
        "\tKUNIT_CASE(mt6797_transition_terminal_failures_test),\n",
    )


def apply_source_rest(path: Path) -> None:
    replace_once(
        path,
        "static void\n"
        "mt6797_a72_transition_checkpoint(const struct mt6797_a72_transition_ops *ops,\n"
        "\t\t\t\t void *context,\n"
        "\t\t\t\t struct mt6797_a72_transition_result *result,\n"
        "\t\t\t\t enum mt6797_a72_transition_phase phase,\n"
        "\t\t\t\t enum mt6797_a72_transition_stage stage)\n"
        "{\n"
        "\tresult->last_stage = stage;\n"
        "\tresult->checkpoints++;\n"
        "\tops->checkpoint(context, phase, stage, result);\n"
        "}\n",
        "static int\n"
        "mt6797_a72_transition_checkpoint(const struct mt6797_a72_transition_ops *ops,\n"
        "\t\t\t\t void *context,\n"
        "\t\t\t\t struct mt6797_a72_transition_result *result,\n"
        "\t\t\t\t enum mt6797_a72_transition_phase phase,\n"
        "\t\t\t\t enum mt6797_a72_transition_stage stage)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tresult->last_stage = stage;\n"
        "\tresult->checkpoints++;\n"
        "\tret = ops->checkpoint(context, phase, stage, result);\n"
        "\tif (ret)\n"
        "\t\tresult->checkpoint_errno = ret;\n"
        "\treturn ret;\n"
        "}\n",
    )
    replace_once(
        path,
        "static void\n"
        "mt6797_a72_transition_terminal(struct mt6797_a72_transition_controller *controller)\n"
        "{\n"
        "\tatomic_set_release(&controller->lifecycle,\n"
        "\t\t\t   MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL);\n"
        "}\n",
        "static int\n"
        "mt6797_a72_transition_terminal(struct mt6797_a72_transition_controller *controller,\n"
        "\t\t\t       const struct mt6797_a72_transition_ops *ops,\n"
        "\t\t\t       void *context,\n"
        "\t\t\t       struct mt6797_a72_transition_result *result,\n"
        "\t\t\t       enum mt6797_a72_transition_terminal terminal,\n"
        "\t\t\t       int return_errno, u32 uncertain_mask)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tresult->terminal = terminal;\n"
        "\tmt6797_a72_transition_set_retained(result);\n"
        "\tresult->retained_mask |= uncertain_mask;\n"
        "\tresult->terminal_commits++;\n"
        "\tret = ops->terminal(context, result);\n"
        "\tif (ret) {\n"
        "\t\tresult->checkpoint_errno = ret;\n"
        "\t\tif (terminal == MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF) {\n"
        "\t\t\tresult->terminal =\n"
        "\t\t\t\tMT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO;\n"
        "\t\t\tresult->stage_errno = ret;\n"
        "\t\t\treturn_errno = ret;\n"
        "\t\t}\n"
        "\t}\n"
        "\tatomic_set_release(&controller->lifecycle,\n"
        "\t\t\t   MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL);\n"
        "\treturn return_errno;\n"
        "}\n",
    )
    replace_regex(
        path,
        r"\t\t\tresult->terminal =\n"
        r"\t\t\t\tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;\n"
        r"\t\t\tmt6797_a72_transition_set_retained\(result\);\n"
        r"\t\t\tmt6797_a72_transition_terminal\(controller\);\n"
        r"\t\t\treturn ret;\n",
        "\t\t\treturn mt6797_a72_transition_terminal(controller, ops,\n"
        "\t\t\t\tcontext, result,\n"
        "\t\t\t\tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO,\n"
        "\t\t\t\tret, 0);\n",
        2,
    )
    replace_once(
        path,
        "\tresult->terminal = MT6797_A72_TRANSITION_ROLLED_BACK_PREISO;\n"
        "\tmt6797_a72_transition_terminal(controller);\n"
        "\treturn stage_errno;\n",
        "\treturn mt6797_a72_transition_terminal(controller, ops, context,\n"
        "\t\tresult,\n"
        "\t\tMT6797_A72_TRANSITION_ROLLED_BACK_PREISO, stage_errno, 0);\n",
    )
    replace_once(
        path,
        "static int\n"
        "mt6797_a72_owner_fault(struct mt6797_a72_transition_controller *controller,\n"
        "\t\t       struct mt6797_a72_transition_result *result,\n"
        "\t\t       u32 unknown_mask)\n"
        "{\n"
        "\tresult->stage_errno = -EPROTO;\n"
        "\tresult->terminal = MT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO;\n"
        "\tresult->retained_mask = unknown_mask;\n"
        "\tif (result->p27_owned)\n"
        "\t\tresult->retained_mask |= MT6797_A72_TRANSITION_OWNED_P27;\n"
        "\tif (result->provider_owned)\n"
        "\t\tresult->retained_mask |= MT6797_A72_TRANSITION_OWNED_PROVIDER;\n"
        "\tmt6797_a72_transition_terminal(controller);\n"
        "\treturn -EPROTO;\n"
        "}\n",
        "static int\n"
        "mt6797_a72_owner_fault(struct mt6797_a72_transition_controller *controller,\n"
        "\t\t       const struct mt6797_a72_transition_ops *ops,\n"
        "\t\t       void *context,\n"
        "\t\t       struct mt6797_a72_transition_result *result,\n"
        "\t\t       u32 unknown_mask)\n"
        "{\n"
        "\tresult->stage_errno = -EPROTO;\n"
        "\treturn mt6797_a72_transition_terminal(controller, ops, context,\n"
        "\t\tresult,\n"
        "\t\tMT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO, -EPROTO,\n"
        "\t\tunknown_mask);\n"
        "}\n",
    )
    replace_once(
        path,
        "static int\n"
        "mt6797_a72_transition_postiso_fault(struct mt6797_a72_transition_controller *controller,\n"
        "\t\t\t\t    struct mt6797_a72_transition_result *result,\n"
        "\t\t\t\t    int stage_errno)\n"
        "{\n"
        "\tresult->stage_errno = stage_errno;\n"
        "\tresult->terminal = MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO;\n"
        "\tmt6797_a72_transition_set_retained(result);\n"
        "\tmt6797_a72_transition_terminal(controller);\n"
        "\treturn stage_errno;\n"
        "}\n",
        "static int\n"
        "mt6797_a72_transition_postiso_fault(struct mt6797_a72_transition_controller *controller,\n"
        "\t\t\t\t    const struct mt6797_a72_transition_ops *ops,\n"
        "\t\t\t\t    void *context,\n"
        "\t\t\t\t    struct mt6797_a72_transition_result *result,\n"
        "\t\t\t\t    int stage_errno)\n"
        "{\n"
        "\tresult->stage_errno = stage_errno;\n"
        "\treturn mt6797_a72_transition_terminal(controller, ops, context,\n"
        "\t\tresult,\n"
        "\t\tMT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO, stage_errno, 0);\n"
        "}\n\n"
        "static int\n"
        "mt6797_a72_checkpoint_stage(struct mt6797_a72_transition_controller *controller,\n"
        "\t\t\t    const struct mt6797_a72_transition_ops *ops,\n"
        "\t\t\t    void *context,\n"
        "\t\t\t    struct mt6797_a72_transition_result *result,\n"
        "\t\t\t    enum mt6797_a72_transition_phase phase,\n"
        "\t\t\t    enum mt6797_a72_transition_stage stage)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tret = mt6797_a72_transition_checkpoint(ops, context, result,\n"
        "\t\t\t\t\t       phase, stage);\n"
        "\tif (!ret)\n"
        "\t\treturn 0;\n"
        "\tif (stage == MT6797_A72_TRANSITION_STAGE_WATCHDOG &&\n"
        "\t    !result->watchdog_armed) {\n"
        "\t\tresult->stage_errno = ret;\n"
        "\t\treturn mt6797_a72_transition_terminal(controller, ops,\n"
        "\t\t\tcontext, result,\n"
        "\t\t\tMT6797_A72_TRANSITION_REJECTED_PRESTATE, ret, 0);\n"
        "\t}\n"
        "\tif (!result->isolation_attempted)\n"
        "\t\treturn mt6797_a72_transition_rollback(controller, ops,\n"
        "\t\t\t\t\t      context, result, ret);\n"
        "\treturn mt6797_a72_transition_postiso_fault(controller, ops,\n"
        "\t\t\t\t\t     context, result, ret);\n"
        "}\n",
    )
    replace_regex(
        path,
        r"\tmt6797_a72_transition_checkpoint\(ops, context, result,\n"
        r"\t\t\t\t\t (MT6797_A72_TRANSITION_(?:BEFORE|AFTER)),\n"
        r"\t\t\t\t\t (MT6797_A72_TRANSITION_STAGE_[A-Z0-9_]+)\);",
        "\tret = mt6797_a72_checkpoint_stage(controller,\n"
        "\t\t\t\t\t  ops, context, result,\n"
        "\t\t\t\t\t  \\1,\n"
        "\t\t\t\t\t  \\2);\n"
        "\tif (ret)\n"
        "\t\treturn ret;",
        18,
    )
    replace_once(
        path,
        "\tif (lifecycle == MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED)\n"
        "\t\tmt6797_a72_transition_checkpoint(ops, context, result,\n"
        "\t\t\t\t\t\t MT6797_A72_TRANSITION_BEFORE,\n"
        "\t\t\t\t\t\t MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);\n",
        "\tif (lifecycle == MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED) {\n"
        "\t\tret = mt6797_a72_checkpoint_stage(controller,\n"
        "\t\t\t\t\t\t  ops, context, result,\n"
        "\t\t\t\t\t\t  MT6797_A72_TRANSITION_BEFORE,\n"
        "\t\t\t\t\t\t  MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT);\n"
        "\t\tif (ret)\n"
        "\t\t\treturn ret;\n"
        "\t}\n",
    )
    replace_once(
        path,
        "{\n\tint lifecycle;\n\n"
        "\tif (!controller || !result || !error ||\n",
        "{\n\tint lifecycle, ret;\n\n"
        "\tif (!controller || !result || !error ||\n",
    )
    replace_regex(
        path,
        r"mt6797_a72_transition_postiso_fault\(controller, result,",
        "mt6797_a72_transition_postiso_fault(controller, ops, context, result,",
        9,
    )
    replace_regex(
        path,
        r"mt6797_a72_owner_fault\(controller, result,",
        "mt6797_a72_owner_fault(controller, ops, context, result,",
        2,
    )
    replace_once(
        path,
        "\t\tresult->stage_errno = ret;\n"
        "\t\tresult->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;\n"
        "\t\tmt6797_a72_transition_terminal(controller);\n"
        "\t\treturn ret;\n",
        "\t\tresult->stage_errno = ret;\n"
        "\t\treturn mt6797_a72_transition_terminal(controller, ops,\n"
        "\t\t\tcontext, result,\n"
        "\t\t\tMT6797_A72_TRANSITION_REJECTED_PRESTATE, ret, 0);\n",
    )
    replace_once(
        path,
        "\t\tresult->stage_errno = -EPROTO;\n"
        "\t\tresult->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;\n"
        "\t\tmt6797_a72_transition_terminal(controller);\n"
        "\t\treturn -EPROTO;\n",
        "\t\tresult->stage_errno = -EPROTO;\n"
        "\t\treturn mt6797_a72_transition_terminal(controller, ops,\n"
        "\t\t\tcontext, result,\n"
        "\t\t\tMT6797_A72_TRANSITION_REJECTED_PRESTATE, -EPROTO, 0);\n",
    )
    replace_once(
        path,
        "\tresult->terminal = MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF;\n"
        "\tmt6797_a72_transition_set_retained(result);\n"
        "\tmt6797_a72_transition_terminal(controller);\n"
        "\treturn 0;\n",
        "\tret = mt6797_a72_checkpoint_stage(controller,\n"
        "\t\t\t\t\t  ops, context, result,\n"
        "\t\t\t\t\t  MT6797_A72_TRANSITION_BEFORE,\n"
        "\t\t\t\t\t  MT6797_A72_TRANSITION_STAGE_MEMBERSHIP);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\tret = ops->membership_commit(context, MT6797_A72_TRANSITION_CPU8);\n"
        "\tif (ret)\n"
        "\t\treturn mt6797_a72_transition_postiso_fault(controller, ops,\n"
        "\t\t\tcontext, result, ret);\n"
        "\tresult->membership_published = true;\n"
        "\tret = mt6797_a72_checkpoint_stage(controller,\n"
        "\t\t\t\t\t  ops, context, result,\n"
        "\t\t\t\t\t  MT6797_A72_TRANSITION_AFTER,\n"
        "\t\t\t\t\t  MT6797_A72_TRANSITION_STAGE_MEMBERSHIP);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\treturn mt6797_a72_transition_terminal(controller, ops, context,\n"
        "\t\tresult,\n"
        "\t\tMT6797_A72_TRANSITION_CPU8_ONLINE_PROOF, 0, 0);\n",
    )
    replace_once(
        path,
        "\tif (!result)\n"
        "\t\treturn -EINVAL;\n"
        "\tmemset(result, 0, sizeof(*result));\n"
        "\tresult->last_stage = MT6797_A72_TRANSITION_STAGE_ENTRY;\n"
        "\tresult->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;\n"
        "\tif (!controller || !request || !mt6797_a72_transition_ops_valid(ops))\n"
        "\t\treturn -EINVAL;\n"
        "\tif (atomic_read_acquire(&controller->lifecycle) !=\n"
        "\t    MT6797_A72_TRANSITION_LIFECYCLE_IDLE)\n"
        "\t\treturn -EALREADY;\n",
        "\tif (!result)\n"
        "\t\treturn -EINVAL;\n"
        "\tif (controller &&\n"
        "\t    (atomic_read_acquire(&controller->lifecycle) !=\n"
        "\t     MT6797_A72_TRANSITION_LIFECYCLE_IDLE ||\n"
        "\t     atomic_read_acquire(&controller->consumed)))\n"
        "\t\treturn -EALREADY;\n"
        "\tmemset(result, 0, sizeof(*result));\n"
        "\tresult->last_stage = MT6797_A72_TRANSITION_STAGE_ENTRY;\n"
        "\tresult->terminal = MT6797_A72_TRANSITION_REJECTED_PRESTATE;\n"
        "\tif (!controller || !request || !mt6797_a72_transition_ops_valid(ops))\n"
        "\t\treturn -EINVAL;\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_parent(root)
    apply_ledger(
        root / "fs/pstore/gemini_transition_ledger_internal.h",
        root / "fs/pstore/gemini_transition_ledger_test.c",
    )
    apply_header(
        root / "drivers/soc/mediatek/mt6797-a72-transition-internal.h"
    )
    apply_header_rest(
        root / "drivers/soc/mediatek/mt6797-a72-transition-internal.h"
    )
    source = root / "drivers/soc/mediatek/mt6797-a72-transition.c"
    apply_source(source)
    apply_source_rest(source)
    apply_tests(root / "drivers/soc/mediatek/mt6797-a72-transition-test.c")


if __name__ == "__main__":
    main()
