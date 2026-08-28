#!/usr/bin/env python3
"""Apply deterministic durable-admission-trace source edits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


PARENT_HASHES = {
    "fs/pstore/Kconfig":
        "5a87fbe7cd4c6c3815d4ff2e275138fb810c147d24f460b31cd239316ebf4b94",
    "fs/pstore/Makefile":
        "cedf8f145de913bf09be5fe10b8abf0f09a9ef7ee1aed4dc2d55f285a29fe84d",
    "fs/pstore/ram.c":
        "a605ae6211498d9ea260920c719355cbe3af59351ba128ce26127db693d81de9",
    "drivers/soc/mediatek/Kconfig":
        "bcf082d57d18ecfb519cc734c7a3d8f36851642032af3e182773c3dcca69045c",
    "drivers/soc/mediatek/Makefile":
        "51cc36898980788ff5fb352cbfb36e22f363afe2e18b2e2d286a8e7b6b743f92",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c":
        "b03d12563fd90967bfa2a58d5b1581a7c600a6ffe310fd876bbe464d093c8aef",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h":
        "3392018f167f81270cb6f52a2f0075a7b6d45359278fdf9bbea05e0c0be43f1b",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c":
        "707b01baced8948687d02ed25d6a66f3b94cb5af60ba8efb88954b51337ea127",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_hashes(root: Path, relatives: tuple[str, ...]) -> None:
    for relative in relatives:
        expected = PARENT_HASHES[relative]
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"source path is not an exact file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"source hash changed: {relative}: {actual} != {expected}")


def require_file(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"required staged source unavailable: {relative}")
    return path.read_text(encoding="utf-8")


def validate_stage_parent(root: Path, templates: Path, stage: str) -> None:
    if stage == "trace":
        validate_hashes(root, tuple(PARENT_HASHES))
        return

    trace_source = require_file(root, "fs/pstore/gemini_admission_trace.c")
    trace_header = require_file(root, "include/linux/gemini_admission_trace.h")
    require_file(root, "fs/pstore/gemini_admission_trace_internal.h")
    if trace_source != (
        templates / "fs/pstore/gemini_admission_trace.c"
    ).read_text(encoding="utf-8"):
        raise SystemExit("staged admission-trace implementation changed")
    if trace_header != (
        templates / "include/linux/gemini_admission_trace.h"
    ).read_text(encoding="utf-8"):
        raise SystemExit("staged admission-trace API changed")
    if "config PSTORE_GEMINI_ADMISSION_TRACE\n" not in require_file(
        root, "fs/pstore/Kconfig"
    ):
        raise SystemExit("staged admission-trace Kconfig is absent")

    if stage == "trace-tests":
        validate_hashes(
            root,
            tuple(
                relative for relative in PARENT_HASHES
                if not relative.startswith("fs/pstore/")
            ),
        )
        return

    trace_test = require_file(root, "fs/pstore/gemini_admission_trace_test.c")
    if trace_test != (
        templates / "fs/pstore/gemini_admission_trace_test.c"
    ).read_text(encoding="utf-8"):
        raise SystemExit("staged admission-trace test changed")
    if "config PSTORE_GEMINI_ADMISSION_TRACE_KUNIT_TEST\n" not in require_file(
        root, "fs/pstore/Kconfig"
    ):
        raise SystemExit("staged admission-trace KUnit Kconfig is absent")

    if stage == "controller":
        validate_hashes(
            root,
            tuple(
                relative for relative in PARENT_HASHES
                if relative.startswith("drivers/soc/mediatek/")
            ),
        )
        return

    controller = require_file(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    )
    controller_header = require_file(
        root,
        "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h",
    )
    for token in (
        "ops->trace_entry(context)",
        "ops->trace_zero_request(context, zero_result)",
        ".trace_entry = mt6797_a72_admission_trace_entry",
    ):
        if token not in controller:
            raise SystemExit(f"staged controller token absent: {token}")
    if "int trace_ret;" not in controller_header:
        raise SystemExit("staged controller trace result is absent")
    validate_hashes(
        root,
        ("drivers/soc/mediatek/mt6797-a72-admission-controller-test.c",),
    )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"source anchor count changed in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def copy_template(templates: Path, relative: str, root: Path) -> None:
    source = templates / relative
    target = root / relative
    if not source.is_file() or source.is_symlink() or target.exists():
        raise SystemExit(f"unsafe template copy: {relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def apply_trace(root: Path, templates: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    anchor = "config PSTORE_GEMINI_TRANSITION_LEDGER_KUNIT_TEST\n"
    block = """config PSTORE_GEMINI_ADMISSION_TRACE
\tbool "Gemini immutable CPU8 admission trace"
\tdepends on PSTORE_GEMINI_TRANSITION_LEDGER=y
\tdefault n
\thelp
\t  Own dmesg records 2 and 3 beside the existing record-1 transition
\t  ledger. Commit one fixed controller-entry record and at most one fixed
\t  consumed zero-request terminal record for source registration,
\t  derivation, or publication failure.

\t  Accept only exact logical-empty headers, write payload before metadata,
\t  fully read back each record, and never clear, repair, retry, or
\t  overwrite. This option adds no caller or CPU, watchdog, regulator,
\t  clock, firmware, storage, reset, or power operation. If unsure, say N.

"""
    replace_once(kconfig, anchor, block + anchor)
    makefile = root / "fs/pstore/Makefile"
    anchor = "obj-$(CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER) += gemini_transition_ledger.o\n"
    replace_once(
        makefile, anchor,
        anchor + "obj-$(CONFIG_PSTORE_GEMINI_ADMISSION_TRACE) += gemini_admission_trace.o\n",
    )
    for relative in (
        "fs/pstore/gemini_admission_trace.c",
        "fs/pstore/gemini_admission_trace_internal.h",
        "include/linux/gemini_admission_trace.h",
    ):
        copy_template(templates, relative, root)


def apply_trace_tests(root: Path, templates: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    anchor = "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n"
    block = """config PSTORE_GEMINI_ADMISSION_TRACE_KUNIT_TEST
\tbool "KUnit tests for the Gemini CPU8 admission trace"
\tdepends on KUNIT=y
\tdepends on PSTORE_GEMINI_ADMISSION_TRACE=y
\tdefault n
\thelp
\t  Test exact entry and terminal records, payload-before-metadata order,
\t  exact deferred-probe reentry, foreign and torn-record rejection,
\t  full readback, mutual exclusion, and the two-write ceiling in memory.

\t  No retained RAM, MMIO, CPU, watchdog, or device operation is used.

"""
    replace_once(kconfig, anchor, block + anchor)
    makefile = root / "fs/pstore/Makefile"
    anchor = "obj-$(CONFIG_PSTORE_GEMINI_ADMISSION_TRACE) += gemini_admission_trace.o\n"
    replace_once(
        makefile, anchor,
        anchor + "obj-$(CONFIG_PSTORE_GEMINI_ADMISSION_TRACE_KUNIT_TEST) += gemini_admission_trace_test.o\n",
    )
    copy_template(templates, "fs/pstore/gemini_admission_trace_test.c", root)


def apply_controller(root: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    anchor = (
        "config MTK_MT6797_A72_ADMISSION_CONTROLLER\n"
        "\tbool \"MediaTek MT6797 one-shot CPU8 admission controller\"\n"
        "\tdepends on ARM64 && ARCH_MEDIATEK && OF && HOTPLUG_CPU\n"
        "\tdepends on ARM64_MT6797_A72_DERIVED_ADMISSION\n"
        "\tdepends on MTK_MT6797_A72_DEFAULT_OFF_BINDER\n"
        "\tdepends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER\n"
    )
    replace_once(
        kconfig, anchor,
        anchor + "\tdepends on PSTORE_GEMINI_ADMISSION_TRACE=y\n",
    )

    header = root / "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h"
    replace_once(
        header,
        "#include <linux/atomic.h>\n#include <linux/types.h>\n",
        "#include <linux/atomic.h>\n#include <linux/gemini_admission_trace.h>\n#include <linux/types.h>\n",
    )
    replace_once(
        header,
        "\tconst struct arm64_late_cpu_ready_token *(*ready_token)(void *context);\n",
        "\tconst struct arm64_late_cpu_ready_token *(*ready_token)(void *context);\n"
        "\tint (*trace_entry)(void *context);\n"
        "\tint (*trace_zero_request)(void *context,\n"
        "\t\t\t\tenum gemini_admission_trace_zero_result result);\n",
    )
    replace_once(
        header,
        "\tu32 cpu_requests;\n\tint operation_ret;\n",
        "\tu32 cpu_requests;\n\tint trace_ret;\n\tint operation_ret;\n",
    )

    source = root / "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    replace_once(
        source,
        "\treturn ops && ops->binder_ready && ops->ready_token &&\n"
        "\t\tops->source_register && ops->source_unregister &&\n",
        "\treturn ops && ops->binder_ready && ops->ready_token &&\n"
        "\t\tops->trace_entry && ops->trace_zero_request &&\n"
        "\t\tops->source_register && ops->source_unregister &&\n",
    )
    replace_once(
        source,
        "\tconst struct arm64_late_cpu_ready_token *ready;\n"
        "\tbool source_registered = false;\n",
        "\tconst struct arm64_late_cpu_ready_token *ready;\n"
        "\tenum gemini_admission_trace_zero_result zero_result = 0;\n"
        "\tbool source_registered = false;\n",
    )
    replace_once(
        source,
        "\tif (atomic_read(&state->consumed))\n"
        "\t\treturn -EALREADY;\n"
        "\tif (!ops->binder_ready(context))\n",
        "\tif (atomic_read(&state->consumed))\n"
        "\t\treturn -EALREADY;\n"
        "\tret = ops->trace_entry(context);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\tif (!ops->binder_ready(context))\n",
    )
    replace_once(
        source,
        "\tret = ops->source_register(context);\n"
        "\tif (ret)\n"
        "\t\tgoto out_terminal;\n",
        "\tret = ops->source_register(context);\n"
        "\tif (ret) {\n"
        "\t\tzero_result = GEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER;\n"
        "\t\tgoto out_terminal;\n"
        "\t}\n",
    )
    replace_once(
        source,
        "\tret = ops->derive_cpu8(context, ready, &state->transaction);\n"
        "\tif (ret)\n"
        "\t\tgoto out_unregister;\n"
        "\tret = ops->publish_up(context, &state->transaction);\n"
        "\tif (ret)\n"
        "\t\tgoto out_unregister;\n",
        "\tret = ops->derive_cpu8(context, ready, &state->transaction);\n"
        "\tif (ret) {\n"
        "\t\tzero_result = GEMINI_ADMISSION_TRACE_ZERO_DERIVE;\n"
        "\t\tgoto out_unregister;\n"
        "\t}\n"
        "\tret = ops->publish_up(context, &state->transaction);\n"
        "\tif (ret) {\n"
        "\t\tzero_result = GEMINI_ADMISSION_TRACE_ZERO_PUBLISH;\n"
        "\t\tgoto out_unregister;\n"
        "\t}\n",
    )
    replace_once(
        source,
        "out_terminal:\n\tstate->operation_ret = ret;\n",
        "out_terminal:\n"
        "\tif (!state->cpu_requests && zero_result) {\n"
        "\t\tstate->trace_ret = ops->trace_zero_request(context, zero_result);\n"
        "\t\tif (state->trace_ret)\n"
        "\t\t\tret = state->trace_ret;\n"
        "\t}\n"
        "\tstate->operation_ret = ret;\n",
    )
    anchor = "static bool mt6797_a72_admission_binder_ready(void *context)\n"
    wrappers = """static int mt6797_a72_admission_trace_entry(void *context)
{
\t(void)context;
\treturn gemini_admission_trace_entry();
}

static int mt6797_a72_admission_trace_zero_request(
\tvoid *context, enum gemini_admission_trace_zero_result result)
{
\t(void)context;
\treturn gemini_admission_trace_zero_request(result);
}

"""
    replace_once(source, anchor, wrappers + anchor)
    replace_once(
        source,
        "\t.binder_ready = mt6797_a72_admission_binder_ready,\n"
        "\t.ready_token = mt6797_a72_admission_ready_token,\n",
        "\t.binder_ready = mt6797_a72_admission_binder_ready,\n"
        "\t.ready_token = mt6797_a72_admission_ready_token,\n"
        "\t.trace_entry = mt6797_a72_admission_trace_entry,\n"
        "\t.trace_zero_request = mt6797_a72_admission_trace_zero_request,\n",
    )


def apply_controller_tests(root: Path) -> None:
    source = root / "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c"
    replace_once(
        source,
        "enum mt6797_a72_admission_test_event {\n\tMT6797_ADMISSION_BINDER_READY,\n",
        "enum mt6797_a72_admission_test_event {\n"
        "\tMT6797_ADMISSION_TRACE_ENTRY,\n"
        "\tMT6797_ADMISSION_BINDER_READY,\n",
    )
    replace_once(
        source,
        "\tMT6797_ADMISSION_SOURCE_UNREGISTER,\n};\n",
        "\tMT6797_ADMISSION_SOURCE_UNREGISTER,\n"
        "\tMT6797_ADMISSION_TRACE_ZERO_REQUEST,\n};\n",
    )
    replace_once(
        source,
        "\tunsigned int requested_cpu;\n};\n",
        "\tunsigned int requested_cpu;\n"
        "\tenum gemini_admission_trace_zero_result zero_result;\n"
        "\tbool trace_zero_fails;\n};\n",
    )
    anchor = "static bool mt6797_a72_admission_test_binder_ready(void *data)\n"
    callbacks = """static int mt6797_a72_admission_test_trace_entry(void *data)
{
\tstruct mt6797_a72_admission_test_context *context = data;

\tmt6797_a72_admission_test_event(context,
\t\t\t\t\tMT6797_ADMISSION_TRACE_ENTRY, false);
\treturn context->fail_event == MT6797_ADMISSION_TRACE_ENTRY ? -ENOSPC : 0;
}

static int mt6797_a72_admission_test_trace_zero_request(
\tvoid *data, enum gemini_admission_trace_zero_result result)
{
\tstruct mt6797_a72_admission_test_context *context = data;

\tmt6797_a72_admission_test_event(context,
\t\t\t\t\tMT6797_ADMISSION_TRACE_ZERO_REQUEST,
\t\t\t\t\tfalse);
\tcontext->zero_result = result;
\treturn context->trace_zero_fails ? -ENOSPC : 0;
}

"""
    replace_once(source, anchor, callbacks + anchor)
    replace_once(
        source,
        "static const struct mt6797_a72_admission_controller_ops test_ops = {\n"
        "\t.binder_ready = mt6797_a72_admission_test_binder_ready,\n",
        "static const struct mt6797_a72_admission_controller_ops test_ops = {\n"
        "\t.binder_ready = mt6797_a72_admission_test_binder_ready,\n"
        "\t.trace_entry = mt6797_a72_admission_test_trace_entry,\n"
        "\t.trace_zero_request =\n"
        "\t\tmt6797_a72_admission_test_trace_zero_request,\n",
    )
    replace_once(
        source,
        "\tstatic const enum mt6797_a72_admission_test_event expected[] = {\n"
        "\t\tMT6797_ADMISSION_BINDER_READY,\n",
        "\tstatic const enum mt6797_a72_admission_test_event expected[] = {\n"
        "\t\tMT6797_ADMISSION_TRACE_ENTRY,\n"
        "\t\tMT6797_ADMISSION_BINDER_READY,\n",
    )
    replace_once(
        source,
        "\tKUNIT_EXPECT_EQ(test, context->event_count, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);\n",
        "\tKUNIT_EXPECT_EQ(test, context->event_count, 2U);\n"
        "\tKUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);\n",
    )
    replace_once(
        source,
        "\tKUNIT_EXPECT_EQ(test, context->event_count, 2U);\n"
        "\tKUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);\n"
        "}\n\nstatic void mt6797_a72_admission_terminal_failures_test",
        "\tKUNIT_EXPECT_EQ(test, context->event_count, 3U);\n"
        "\tKUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);\n"
        "}\n\nstatic void mt6797_a72_admission_terminal_failures_test",
    )
    replace_once(
        source,
        "static void mt6797_a72_admission_terminal_failures_test(struct kunit *test)\n"
        "{\n"
        "\tstatic const int failures[] = {\n",
        "static void mt6797_a72_admission_terminal_failures_test(struct kunit *test)\n"
        "{\n"
        "\tstatic const enum gemini_admission_trace_zero_result results[] = {\n"
        "\t\tGEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER,\n"
        "\t\tGEMINI_ADMISSION_TRACE_ZERO_DERIVE,\n"
        "\t\tGEMINI_ADMISSION_TRACE_ZERO_PUBLISH,\n"
        "\t};\n"
        "\tstatic const int failures[] = {\n",
    )
    replace_once(
        source,
        "\t\tKUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);\n"
        "\t\tKUNIT_EXPECT_TRUE(test, context->consumed_before_operation);\n",
        "\t\tKUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);\n"
        "\t\tKUNIT_EXPECT_EQ(test, context->events[context->event_count - 1],\n"
        "\t\t\t\tMT6797_ADMISSION_TRACE_ZERO_REQUEST);\n"
        "\t\tKUNIT_EXPECT_EQ(test, context->zero_result,\n"
        "\t\t\t\tresults[failure]);\n"
        "\t\tKUNIT_EXPECT_TRUE(test, context->consumed_before_operation);\n",
    )
    anchor = "static void mt6797_a72_admission_repeat_closed_test(struct kunit *test)\n"
    new_test = """static void mt6797_a72_admission_trace_failures_test(struct kunit *test)
{
\tstruct mt6797_a72_admission_test_context *context;
\tint ret;

\tcontext = mt6797_a72_admission_test_context(test);
\tKUNIT_ASSERT_NOT_NULL(test, context);
\tcontext->fail_event = MT6797_ADMISSION_TRACE_ENTRY;
\tret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
\tKUNIT_EXPECT_EQ(test, ret, -ENOSPC);
\tKUNIT_EXPECT_EQ(test, atomic_read(&context->controller.consumed), 0);
\tKUNIT_EXPECT_EQ(test, context->event_count, 1U);

\tcontext = mt6797_a72_admission_test_context(test);
\tKUNIT_ASSERT_NOT_NULL(test, context);
\tcontext->fail_event = MT6797_ADMISSION_SOURCE_REGISTER;
\tcontext->trace_zero_fails = true;
\tret = mt6797_a72_admission_run(&context->controller, &test_ops, context);
\tKUNIT_EXPECT_EQ(test, ret, -ENOSPC);
\tKUNIT_EXPECT_EQ(test, context->controller.trace_ret, -ENOSPC);
\tKUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);
\tKUNIT_EXPECT_EQ(test, context->events[context->event_count - 1],
\t\t\tMT6797_ADMISSION_TRACE_ZERO_REQUEST);
}

"""
    replace_once(source, anchor, new_test + anchor)
    replace_once(
        source,
        "\tKUNIT_CASE(mt6797_a72_admission_request_failure_test),\n"
        "\tKUNIT_CASE(mt6797_a72_admission_repeat_closed_test),\n",
        "\tKUNIT_CASE(mt6797_a72_admission_request_failure_test),\n"
        "\tKUNIT_CASE(mt6797_a72_admission_trace_failures_test),\n"
        "\tKUNIT_CASE(mt6797_a72_admission_repeat_closed_test),\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--template-root", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=("trace", "trace-tests", "controller", "controller-tests"),
        required=True,
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    templates = args.template_root.resolve()
    validate_stage_parent(root, templates, args.stage)
    if args.stage == "trace":
        apply_trace(root, templates)
    elif args.stage == "trace-tests":
        apply_trace_tests(root, templates)
    elif args.stage == "controller":
        apply_controller(root)
    else:
        apply_controller_tests(root)


if __name__ == "__main__":
    main()
