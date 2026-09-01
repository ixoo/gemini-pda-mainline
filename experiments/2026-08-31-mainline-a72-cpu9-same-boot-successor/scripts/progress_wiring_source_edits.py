#!/usr/bin/env python3
"""Apply exact post-0471 CPU9 progress wiring source edits."""

from __future__ import annotations

from pathlib import Path


PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "e2fad634d66ec05f8bd44ebe7fbe8f7adc0c387a3e86aa42bd80b040faffe36c",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c":
        "609404c3778f5953b512cc2f872dee3475e43351f9827dc4e39b8c099f306252",
    "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c":
        "e44a29a4d05d4860a2fc0b8e8eacee80b9060a6d469c8fd959de8ccc3caaf5e8",
    "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-internal.h":
        "de40d0fa6b13d62fa6bff891acbd6444dd52327f20c8d5c6d8c1cce1ee03486d",
    "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-test.c":
        "38c7f1ddf0a2817f4fe609bc38701265c479000c3ab26ced67aefc825d76a2e0",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c":
        "458e530c3d219aaf12ea873877cc185699167384290cc8ed131e231c79b334c7",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h":
        "cb5b50b701d0d15a05822231e0052f6a1f28dba68b75883c391413ab625f6f40",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c":
        "65543583f97d3ea2d3987aaa08e5ded100a5892204acc1cfaf4eb0ea41545337",
}


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"wiring source anchor changed: {path}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply_controller(root: Path) -> None:
    source = root / "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c"
    replace_once(
        source,
        "#include <linux/errno.h>\n#include <linux/string.h>",
        "#include <linux/errno.h>\n"
        "#include <linux/gemini_cpu9_progress_ledger.h>\n"
        "#include <linux/string.h>",
    )


def apply_production_controller(root: Path) -> None:
    path = root / "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    replace_once(
        path,
        "#include <linux/errno.h>\n#include <linux/init.h>",
        "#include <linux/errno.h>\n"
        "#include <linux/gemini_cpu9_progress_ledger.h>\n"
        "#include <linux/init.h>",
    )
    replace_once(
        path,
        "static const struct mt6797_a72_cpu9_admission_ops\n"
        "mt6797_a72_cpu9_admission_production_ops = {",
        "static int mt6797_a72_admission_progress_begin(\n"
        "\tvoid *context, u64 cpu8_attempt_id)\n"
        "{\n"
        "\t(void)context;\n"
        "\treturn gemini_cpu9_progress_begin(cpu8_attempt_id);\n"
        "}\n\n"
        "static int mt6797_a72_admission_progress_checkpoint(\n"
        "\tvoid *context, u64 cpu8_attempt_id, u32 stage)\n"
        "{\n"
        "\t(void)context;\n"
        "\treturn gemini_cpu9_progress_checkpoint(cpu8_attempt_id, stage);\n"
        "}\n\n"
        "static const struct mt6797_a72_cpu9_admission_ops\n"
        "mt6797_a72_cpu9_admission_production_ops = {",
    )
    replace_once(
        path,
        "\t.prepare_cpu9 = mt6797_a72_admission_prepare_cpu9,\n"
        "\t.add_cpu = mt6797_a72_admission_add_cpu,",
        "\t.prepare_cpu9 = mt6797_a72_admission_prepare_cpu9,\n"
        "\t.progress_begin = mt6797_a72_admission_progress_begin,\n"
        "\t.progress_checkpoint = mt6797_a72_admission_progress_checkpoint,\n"
        "\t.add_cpu = mt6797_a72_admission_add_cpu,",
    )
    replace_once(
        path,
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"cpu9_failure_stage=%u cpu9_derive_stage=%u \",\n"
        "\t\tREAD_ONCE(controller->cpu9.failure_stage),\n"
        "\t\tREAD_ONCE(controller->cpu9.derive_stage));",
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"cpu9_failure_stage=%u cpu9_derive_stage=%u \",\n"
        "\t\tREAD_ONCE(controller->cpu9.failure_stage),\n"
        "\t\tREAD_ONCE(controller->cpu9.derive_stage));\n"
        "\tlen += sysfs_emit_at(\n"
        "\t\tbuf, len,\n"
        "\t\t\"cpu9_progress_stage=%u cpu9_progress_ret=%d \",\n"
        "\t\tREAD_ONCE(controller->cpu9.progress_stage),\n"
        "\t\tREAD_ONCE(controller->cpu9.progress_ret));",
    )
    source = root / "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c"
    replace_once(
        source,
        "\t       ops->derive_cpu9 && ops->publish_cpu9 && ops->prepare_cpu9 &&\n"
        "\t       ops->add_cpu;",
        "\t       ops->derive_cpu9 && ops->publish_cpu9 && ops->prepare_cpu9 &&\n"
        "\t       ops->progress_begin && ops->progress_checkpoint &&\n"
        "\t       ops->add_cpu;",
    )
    replace_once(
        source,
        "static int mt6797_a72_cpu9_admission_terminal(\n"
        "\tstruct mt6797_a72_cpu9_admission_state *state, u32 stage, int ret)\n"
        "{\n"
        "\tstate->failure_stage = stage;\n"
        "\tstate->operation_ret = ret;\n"
        "\treturn ret;\n"
        "}\n\n",
        "static int mt6797_a72_cpu9_admission_terminal(\n"
        "\tstruct mt6797_a72_cpu9_admission_state *state, u32 stage, int ret)\n"
        "{\n"
        "\tstate->failure_stage = stage;\n"
        "\tstate->operation_ret = ret;\n"
        "\treturn ret;\n"
        "}\n\n"
        "static int mt6797_a72_cpu9_admission_progress(\n"
        "\tstruct mt6797_a72_cpu9_admission_state *state,\n"
        "\tconst struct mt6797_a72_cpu9_admission_ops *ops, void *context,\n"
        "\tu64 cpu8_attempt_id, u32 stage, bool begin)\n"
        "{\n"
        "\tstate->progress_stage = stage;\n"
        "\tstate->progress_ret = begin ?\n"
        "\t\tops->progress_begin(context, cpu8_attempt_id) :\n"
        "\t\tops->progress_checkpoint(context, cpu8_attempt_id, stage);\n"
        "\treturn state->progress_ret ? mt6797_a72_cpu9_admission_terminal(\n"
        "\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_PROGRESS,\n"
        "\t\tstate->progress_ret) : 0;\n"
        "}\n\n",
    )
    replace_once(
        source,
        "\tstate->cpu8_requests = proof.cpu_requests;\n\n"
        "\tready = ops->ready_token(context);",
        "\tstate->cpu8_requests = proof.cpu_requests;\n"
        "\tret = mt6797_a72_cpu9_admission_progress(\n"
        "\t\tstate, ops, context, proof.attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_CPU8_PROOF, true);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\tready = ops->ready_token(context);",
    )
    replace_once(
        source,
        "\tif (!ready)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_READY_TOKEN,\n"
        "\t\t\t-EAGAIN);\n\n"
        "\tret = ops->derive_cpu9",
        "\tif (!ready)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_READY_TOKEN,\n"
        "\t\t\t-EAGAIN);\n"
        "\tret = mt6797_a72_cpu9_admission_progress(\n"
        "\t\tstate, ops, context, proof.attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_READY_TOKEN, false);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\tret = ops->derive_cpu9",
    )
    replace_once(
        source,
        "\tif (state->cpu9_transaction.identity.generation == proof.attempt_id)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_DERIVE,\n"
        "\t\t\t-EPROTO);\n\n"
        "\tret = ops->publish_cpu9",
        "\tif (state->cpu9_transaction.identity.generation == proof.attempt_id)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_DERIVE,\n"
        "\t\t\t-EPROTO);\n"
        "\tret = mt6797_a72_cpu9_admission_progress(\n"
        "\t\tstate, ops, context, proof.attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_DERIVE, false);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\tret = ops->publish_cpu9",
    )
    replace_once(
        source,
        "\tif (ret || !mt6797_a72_cpu9_admission_transaction_valid(\n"
        "\t\t\t   &state->cpu9_transaction, true))\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_PUBLISH,\n"
        "\t\t\tret ?: -EPROTO);\n\n"
        "\tstate->cpu9_request =",
        "\tif (ret || !mt6797_a72_cpu9_admission_transaction_valid(\n"
        "\t\t\t   &state->cpu9_transaction, true))\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_PUBLISH,\n"
        "\t\t\tret ?: -EPROTO);\n"
        "\tret = mt6797_a72_cpu9_admission_progress(\n"
        "\t\tstate, ops, context, proof.attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_PUBLISH, false);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\tstate->cpu9_request =",
    )
    replace_once(
        source,
        "\tret = ops->prepare_cpu9(context, &state->cpu9_request);\n"
        "\tif (ret)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_PREPARE, ret);\n\n"
        "\tstate->cpu9_requests = 1;\n"
        "\tret = ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9);\n"
        "\tif (ret)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,\n"
        "\t\t\tret);",
        "\tret = ops->prepare_cpu9(context, &state->cpu9_request);\n"
        "\tif (ret)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_PREPARE, ret);\n"
        "\tret = mt6797_a72_cpu9_admission_progress(\n"
        "\t\tstate, ops, context, proof.attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_PREPARE, false);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\tret = mt6797_a72_cpu9_admission_progress(\n"
        "\t\tstate, ops, context, proof.attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH, false);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\tstate->cpu9_requests = 1;\n"
        "\tstate->cpu9_request_ret =\n"
        "\t\tops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9);\n"
        "\tret = mt6797_a72_cpu9_admission_progress(\n"
        "\t\tstate, ops, context, proof.attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_ADD_CPU_RETURN, false);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\tif (state->cpu9_request_ret)\n"
        "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
        "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,\n"
        "\t\t\tstate->cpu9_request_ret);",
    )


def apply_controller_header(root: Path) -> None:
    path = root / "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-internal.h"
    replace_once(
        path,
        "\tMT6797_A72_CPU9_ADMISSION_FAILURE_PREPARE,\n"
        "\tMT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,",
        "\tMT6797_A72_CPU9_ADMISSION_FAILURE_PREPARE,\n"
        "\tMT6797_A72_CPU9_ADMISSION_FAILURE_PROGRESS,\n"
        "\tMT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,",
    )
    replace_once(
        path,
        "\tint (*prepare_cpu9)(\n"
        "\t\tvoid *context,\n"
        "\t\tconst struct mt6797_a72_cpu9_executor_request *request);\n"
        "\tint (*add_cpu)(void *context, unsigned int cpu);",
        "\tint (*prepare_cpu9)(\n"
        "\t\tvoid *context,\n"
        "\t\tconst struct mt6797_a72_cpu9_executor_request *request);\n"
        "\tint (*progress_begin)(void *context, u64 cpu8_attempt_id);\n"
        "\tint (*progress_checkpoint)(void *context, u64 cpu8_attempt_id,\n"
        "\t\t\t\t   u32 stage);\n"
        "\tint (*add_cpu)(void *context, unsigned int cpu);",
    )
    replace_once(
        path,
        "\tu32 failure_stage;\n\tu32 derive_stage;\n"
        "\tint cpu8_ret;\n\tint cpu8_proof_ret;\n\tint operation_ret;",
        "\tu32 failure_stage;\n\tu32 derive_stage;\n\tu32 progress_stage;\n"
        "\tint cpu8_ret;\n\tint cpu8_proof_ret;\n\tint progress_ret;\n"
        "\tint cpu9_request_ret;\n\tint operation_ret;",
    )


def apply_controller_test(root: Path) -> None:
    path = root / "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-test.c"
    replace_once(
        path,
        "\tMT6797_CPU9_ADMISSION_FAIL_PREPARE,\n"
        "\tMT6797_CPU9_ADMISSION_FAIL_ADD_CPU,",
        "\tMT6797_CPU9_ADMISSION_FAIL_PREPARE,\n"
        "\tMT6797_CPU9_ADMISSION_FAIL_PROGRESS,\n"
        "\tMT6797_CPU9_ADMISSION_FAIL_ADD_CPU,",
    )
    replace_once(
        path,
        "\tunsigned int event_count;\n\tunsigned int requested_cpu;",
        "\tunsigned int event_count;\n"
        "\tu32 progress_stages[GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN];\n"
        "\tu32 progress_count;\n\tu32 fail_progress_stage;\n"
        "\tunsigned int requested_cpu;",
    )
    replace_once(
        path,
        "#include <linux/errno.h>\n#include <linux/module.h>",
        "#include <linux/errno.h>\n"
        "#include <linux/gemini_cpu9_progress_ledger.h>\n"
        "#include <linux/module.h>",
    )
    replace_once(
        path,
        "static int mt6797_a72_cpu9_admission_test_add_cpu(void *data,\n",
        "static int mt6797_a72_cpu9_admission_test_progress_record(\n"
        "\tstruct mt6797_a72_cpu9_admission_test_context *context, u32 stage)\n"
        "{\n"
        "\tif (context->progress_count < ARRAY_SIZE(context->progress_stages))\n"
        "\t\tcontext->progress_stages[context->progress_count++] = stage;\n"
        "\treturn context->failure == MT6797_CPU9_ADMISSION_FAIL_PROGRESS &&\n"
        "\t       context->fail_progress_stage == stage ? -EIO : 0;\n"
        "}\n\n"
        "static int mt6797_a72_cpu9_admission_test_progress_begin(\n"
        "\tvoid *data, u64 cpu8_attempt_id)\n"
        "{\n"
        "\tstruct mt6797_a72_cpu9_admission_test_context *context = data;\n\n"
        "\tif (cpu8_attempt_id != context->proof.attempt_id)\n"
        "\t\treturn -EPROTO;\n"
        "\treturn mt6797_a72_cpu9_admission_test_progress_record(\n"
        "\t\tcontext, GEMINI_CPU9_PROGRESS_CPU8_PROOF);\n"
        "}\n\n"
        "static int mt6797_a72_cpu9_admission_test_progress_checkpoint(\n"
        "\tvoid *data, u64 cpu8_attempt_id, u32 stage)\n"
        "{\n"
        "\tstruct mt6797_a72_cpu9_admission_test_context *context = data;\n\n"
        "\tif (cpu8_attempt_id != context->proof.attempt_id)\n"
        "\t\treturn -EPROTO;\n"
        "\treturn mt6797_a72_cpu9_admission_test_progress_record(context, stage);\n"
        "}\n\n"
        "static int mt6797_a72_cpu9_admission_test_add_cpu(void *data,\n",
    )
    replace_once(
        path,
        "\tcontext->requested_cpu = cpu;\n"
        "\treturn context->failure == MT6797_CPU9_ADMISSION_FAIL_ADD_CPU ? -EIO :",
        "\tcontext->requested_cpu = cpu;\n"
        "\tmt6797_a72_cpu9_admission_test_progress_record(\n"
        "\t\tcontext, GEMINI_CPU9_PROGRESS_BINDER_ENTRY);\n"
        "\tmt6797_a72_cpu9_admission_test_progress_record(\n"
        "\t\tcontext, GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER);\n"
        "\tmt6797_a72_cpu9_admission_test_progress_record(\n"
        "\t\tcontext, GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN);\n"
        "\treturn context->failure == MT6797_CPU9_ADMISSION_FAIL_ADD_CPU ? -EIO :",
    )
    replace_once(
        path,
        "\t\t.prepare_cpu9 = mt6797_a72_cpu9_admission_test_prepare,\n"
        "\t\t.add_cpu = mt6797_a72_cpu9_admission_test_add_cpu,",
        "\t\t.prepare_cpu9 = mt6797_a72_cpu9_admission_test_prepare,\n"
        "\t\t.progress_begin =\n"
        "\t\t\tmt6797_a72_cpu9_admission_test_progress_begin,\n"
        "\t\t.progress_checkpoint =\n"
        "\t\t\tmt6797_a72_cpu9_admission_test_progress_checkpoint,\n"
        "\t\t.add_cpu = mt6797_a72_cpu9_admission_test_add_cpu,",
    )
    replace_once(
        path,
        "\tKUNIT_EXPECT_FALSE(test, context->prepared.cpu9_online);\n}",
        "\tKUNIT_EXPECT_FALSE(test, context->prepared.cpu9_online);\n"
        "\tKUNIT_EXPECT_EQ(test, context->progress_count,\n"
        "\t\t\tGEMINI_CPU9_PROGRESS_ADD_CPU_RETURN);\n"
        "\tfor (ret = 0; ret < context->progress_count; ret++)\n"
        "\t\tKUNIT_EXPECT_EQ(test, context->progress_stages[ret],\n"
        "\t\t\t\t(u32)ret + 1);\n}",
    )
    replace_once(
        path,
        "static struct kunit_case mt6797_a72_cpu9_admission_controller_cases[] = {",
        "static void mt6797_a72_cpu9_admission_progress_failures_test(\n"
        "\tstruct kunit *test)\n"
        "{\n"
        "\tu32 stage;\n\n"
        "\tfor (stage = GEMINI_CPU9_PROGRESS_CPU8_PROOF;\n"
        "\t     stage <= GEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH; stage++) {\n"
        "\t\tstruct mt6797_a72_cpu9_admission_test_context *context =\n"
        "\t\t\tmt6797_a72_cpu9_admission_test_context(test);\n\n"
        "\t\tKUNIT_ASSERT_NOT_NULL(test, context);\n"
        "\t\tcontext->failure = MT6797_CPU9_ADMISSION_FAIL_PROGRESS;\n"
        "\t\tcontext->fail_progress_stage = stage;\n"
        "\t\tKUNIT_EXPECT_EQ(test, mt6797_a72_cpu9_admission_run(\n"
        "\t\t\t&context->controller,\n"
        "\t\t\t&mt6797_a72_cpu9_admission_test_ops, context), -EIO);\n"
        "\t\tKUNIT_EXPECT_EQ(test, context->controller.progress_stage, stage);\n"
        "\t\tKUNIT_EXPECT_EQ(test, context->controller.cpu9_requests, 0U);\n"
        "\t\tKUNIT_EXPECT_EQ(test, context->requested_cpu, 0U);\n"
        "\t}\n"
        "}\n\n"
        "static struct kunit_case mt6797_a72_cpu9_admission_controller_cases[] = {",
    )
    replace_once(
        path,
        "\tKUNIT_CASE(mt6797_a72_cpu9_admission_request_failure_test),\n"
        "\t{ }",
        "\tKUNIT_CASE(mt6797_a72_cpu9_admission_request_failure_test),\n"
        "\tKUNIT_CASE(mt6797_a72_cpu9_admission_progress_failures_test),\n"
        "\t{ }",
    )


def apply_binder(root: Path) -> None:
    source = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    replace_once(
        source,
        "#include <linux/errno.h>\n#include <linux/gemini_cpu9_transition_ledger.h>",
        "#include <linux/errno.h>\n"
        "#include <linux/gemini_cpu9_progress_ledger.h>\n"
        "#include <linux/gemini_cpu9_transition_ledger.h>",
    )
    replace_once(
        source,
        "\treturn ops && ops->ledger_begin && ops->ledger_checkpoint &&\n"
        "\t       ops->membership_preflight",
        "\treturn ops && ops->progress_checkpoint && ops->ledger_begin &&\n"
        "\t       ops->ledger_checkpoint && ops->membership_preflight",
    )
    replace_once(
        source,
        "\t\t.ledger_begin = gemini_cpu9_ledger_begin,",
        "\t\t.progress_checkpoint = gemini_cpu9_progress_checkpoint,\n"
        "\t\t.ledger_begin = gemini_cpu9_ledger_begin,",
    )
    replace_once(
        source,
        "\t\tret = binder->backend->ledger_begin(\n"
        "\t\t\tbinder->request.cpu8_attempt_id,\n"
        "\t\t\tbinder->request.cpu9_attempt_id);\n"
        "\t\tif (ret)\n"
        "\t\t\treturn ret;\n"
        "\t\tbinder->ledger_begun = true;",
        "\t\tret = binder->backend->progress_checkpoint(\n"
        "\t\t\tbinder->request.cpu8_attempt_id,\n"
        "\t\t\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER);\n"
        "\t\tif (ret)\n"
        "\t\t\treturn ret;\n"
        "\t\tret = binder->backend->ledger_begin(\n"
        "\t\t\tbinder->request.cpu8_attempt_id,\n"
        "\t\t\tbinder->request.cpu9_attempt_id);\n"
        "\t\tif (ret)\n"
        "\t\t\treturn ret;\n"
        "\t\tbinder->ledger_begun = true;\n"
        "\t\tret = binder->backend->progress_checkpoint(\n"
        "\t\t\tbinder->request.cpu8_attempt_id,\n"
        "\t\t\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN);\n"
        "\t\tif (ret)\n"
        "\t\t\treturn ret;",
    )
    replace_once(
        source,
        "\tif (atomic_cmpxchg(&binder->boot_claimed, 0, 1))\n"
        "\t\treturn -EALREADY;\n"
        "\tret = binder->backend->membership_claim(&binder->transaction);",
        "\tif (atomic_cmpxchg(&binder->boot_claimed, 0, 1))\n"
        "\t\treturn -EALREADY;\n"
        "\tret = binder->backend->progress_checkpoint(\n"
        "\t\tbinder->request.cpu8_attempt_id,\n"
        "\t\tGEMINI_CPU9_PROGRESS_BINDER_ENTRY);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\tret = binder->backend->membership_claim(&binder->transaction);",
    )


def apply_binder_header(root: Path) -> None:
    path = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h"
    replace_once(
        path,
        "struct mt6797_a72_cpu9_binder_backend_ops {\n"
        "\tint (*ledger_begin)(u64 cpu8_attempt_id, u64 cpu9_attempt_id);",
        "struct mt6797_a72_cpu9_binder_backend_ops {\n"
        "\tint (*progress_checkpoint)(u64 cpu8_attempt_id, u32 stage);\n"
        "\tint (*ledger_begin)(u64 cpu8_attempt_id, u64 cpu9_attempt_id);",
    )


def apply_binder_test(root: Path) -> None:
    path = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c"
    replace_once(
        path,
        "#include <linux/errno.h>\n#include <linux/gemini_cpu9_transition_ledger.h>",
        "#include <linux/errno.h>\n"
        "#include <linux/gemini_cpu9_progress_ledger.h>\n"
        "#include <linux/gemini_cpu9_transition_ledger.h>",
    )
    replace_once(
        path,
        "\tMT6797_CPU9_BINDER_FAIL_NONE,\n"
        "\tMT6797_CPU9_BINDER_FAIL_LEDGER_BEGIN,",
        "\tMT6797_CPU9_BINDER_FAIL_NONE,\n"
        "\tMT6797_CPU9_BINDER_FAIL_PROGRESS,\n"
        "\tMT6797_CPU9_BINDER_FAIL_LEDGER_BEGIN,",
    )
    replace_once(
        path,
        "\tunsigned int ledger_begin_calls;\n"
        "\tunsigned int ledger_checkpoint_calls;",
        "\tunsigned int progress_checkpoint_calls;\n"
        "\tu32 progress_stages[3];\n\tu32 fail_progress_stage;\n"
        "\tunsigned int ledger_begin_calls;\n"
        "\tunsigned int ledger_checkpoint_calls;",
    )
    replace_once(
        path,
        "static int mt6797_cpu9_binder_test_ledger_begin(u64 cpu8_attempt_id,",
        "static int mt6797_cpu9_binder_test_progress_checkpoint(\n"
        "\tu64 cpu8_attempt_id, u32 stage)\n"
        "{\n"
        "\tstruct mt6797_cpu9_binder_test_state *state =\n"
        "\t\tmt6797_cpu9_binder_test_active;\n\n"
        "\tif (state->progress_checkpoint_calls <\n"
        "\t    ARRAY_SIZE(state->progress_stages))\n"
        "\t\tstate->progress_stages[state->progress_checkpoint_calls++] =\n"
        "\t\t\tstage;\n"
        "\tif (cpu8_attempt_id !=\n"
        "\t    mt6797_cpu9_binder_test_request().cpu8_attempt_id)\n"
        "\t\treturn -EPROTO;\n"
        "\treturn state->failure == MT6797_CPU9_BINDER_FAIL_PROGRESS &&\n"
        "\t       state->fail_progress_stage == stage ? -EIO : 0;\n"
        "}\n\n"
        "static int mt6797_cpu9_binder_test_ledger_begin(u64 cpu8_attempt_id,",
    )
    replace_once(
        path,
        "static struct mt6797_cpu9_binder_test_state *mt6797_cpu9_binder_test_active;\n\n",
        "static struct mt6797_cpu9_binder_test_state *mt6797_cpu9_binder_test_active;\n"
        "static struct mt6797_a72_cpu9_executor_request\n"
        "mt6797_cpu9_binder_test_request(void);\n\n",
    )
    replace_once(
        path,
        "\tmt6797_cpu9_binder_test_backend = {\n"
        "\t\t.ledger_begin = mt6797_cpu9_binder_test_ledger_begin,",
        "\tmt6797_cpu9_binder_test_backend = {\n"
        "\t\t.progress_checkpoint =\n"
        "\t\t\tmt6797_cpu9_binder_test_progress_checkpoint,\n"
        "\t\t.ledger_begin = mt6797_cpu9_binder_test_ledger_begin,",
    )
    replace_once(
        path,
        "\tKUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 1U);",
        "\tKUNIT_EXPECT_EQ(test, state.progress_checkpoint_calls, 3U);\n"
        "\tKUNIT_EXPECT_EQ(test, state.progress_stages[0],\n"
        "\t\t\t(u32)GEMINI_CPU9_PROGRESS_BINDER_ENTRY);\n"
        "\tKUNIT_EXPECT_EQ(test, state.progress_stages[1],\n"
        "\t\t\t(u32)GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER);\n"
        "\tKUNIT_EXPECT_EQ(test, state.progress_stages[2],\n"
        "\t\t\t(u32)GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN);\n"
        "\tKUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 1U);",
    )
    replace_once(
        path,
        "static struct kunit_case mt6797_cpu9_binder_test_cases[] = {",
        "static void mt6797_cpu9_binder_progress_failures_test(struct kunit *test)\n"
        "{\n"
        "\tstatic const u32 stages[] = {\n"
        "\t\tGEMINI_CPU9_PROGRESS_BINDER_ENTRY,\n"
        "\t\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER,\n"
        "\t\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN,\n"
        "\t};\n"
        "\tunsigned int i;\n\n"
        "\tfor (i = 0; i < ARRAY_SIZE(stages); i++) {\n"
        "\t\tstruct mt6797_a72_cpu9_executor_request request =\n"
        "\t\t\tmt6797_cpu9_binder_test_request();\n"
        "\t\tstruct mt6797_cpu9_binder_test_state state;\n"
        "\t\tstruct mt6797_a72_cpu9_binder binder;\n\n"
        "\t\tmt6797_cpu9_binder_test_reset(&binder, &state);\n"
        "\t\tstate.failure = MT6797_CPU9_BINDER_FAIL_PROGRESS;\n"
        "\t\tstate.fail_progress_stage = stages[i];\n"
        "\t\tKUNIT_ASSERT_EQ(test,\n"
        "\t\t\tmt6797_a72_cpu9_binder_test_prepare(&binder, &request),\n"
        "\t\t\t0);\n"
        "\t\tKUNIT_EXPECT_EQ(test, mt6797_a72_cpu9_binder_test_boot(\n"
        "\t\t\t&binder, 9, mt6797_cpu9_binder_test_cpu_boot), -EIO);\n"
        "\t\tKUNIT_EXPECT_EQ(test, state.cpu_boot_calls, 0U);\n"
        "\t\tKUNIT_EXPECT_EQ(test, state.ledger_begin_calls,\n"
        "\t\t\t\tstages[i] ==\n"
        "\t\t\t\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN ? 1U : 0U);\n"
        "\t}\n"
        "}\n\n"
        "static struct kunit_case mt6797_cpu9_binder_test_cases[] = {",
    )
    replace_once(
        path,
        "\tKUNIT_CASE(mt6797_cpu9_binder_failure_dispatch_test),\n\t{},",
        "\tKUNIT_CASE(mt6797_cpu9_binder_failure_dispatch_test),\n"
        "\tKUNIT_CASE(mt6797_cpu9_binder_progress_failures_test),\n\t{},",
    )


def apply_kconfig(root: Path) -> None:
    path = root / "drivers/soc/mediatek/Kconfig"
    replace_once(
        path,
        "\tdepends on PSTORE_GEMINI_ADMISSION_TRACE=y",
        "\tdepends on PSTORE_GEMINI_ADMISSION_TRACE=y || "
        "PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y",
    )
    replace_once(
        path,
        "\tdepends on MTK_MT6797_A72_CPU9_BINDER\n\tdefault n",
        "\tdepends on MTK_MT6797_A72_CPU9_BINDER\n"
        "\tdepends on PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y\n\tdefault n",
    )
    replace_once(
        path,
        "\t  derives and publishes one retained-cluster CPU9 transaction, stages\n"
        "\t  the CPU9 binder, and makes one synchronous add_cpu(9) request.",
        "\t  derives and publishes one retained-cluster CPU9 transaction, stages\n"
        "\t  the CPU9 binder, and makes one synchronous add_cpu(9) request. Ten\n"
        "\t  ordered retained progress boundaries cover the pre-ledger path.",
    )


def apply(root: Path) -> None:
    apply_kconfig(root)
    apply_production_controller(root)
    apply_controller(root)
    apply_controller_header(root)
    apply_controller_test(root)
    apply_binder(root)
    apply_binder_header(root)
    apply_binder_test(root)
