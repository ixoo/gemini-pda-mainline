#!/usr/bin/env python3
"""Apply deterministic live-only admission trace soft-failure edits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


PARENT_HASHES = {
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c":
        "a4d7cdb8097c6d3e3736ea9ee8c71198c835e23481276306e92005505f4cbce1",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h":
        "1354fa2417a92c188dd51a5041f452750370427e5c1482b951e0ed216da1ef60",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c":
        "a586fc64f6e6646d013985bee4a584970d9dc9dce27863c8e632a3a45e517f15",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_file(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"source path is not an exact file: {relative}")
    return path


def validate_hashes(root: Path, relatives: tuple[str, ...]) -> None:
    for relative in relatives:
        actual = sha256(require_file(root, relative))
        if actual != PARENT_HASHES[relative]:
            raise SystemExit(
                f"source hash changed: {relative}: "
                f"{actual} != {PARENT_HASHES[relative]}"
            )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"source anchor count changed in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate_stage_parent(root: Path, stage: str) -> None:
    if stage == "production":
        validate_hashes(root, tuple(PARENT_HASHES))
        return
    validate_hashes(
        root,
        ("drivers/soc/mediatek/mt6797-a72-admission-controller-test.c",),
    )
    source = require_file(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    ).read_text(encoding="utf-8")
    internal = require_file(
        root,
        "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h",
    ).read_text(encoding="utf-8")
    for token in (
        "bool allow_trace_failure;",
        "int trace_entry_ret;",
        "entry_trace_ret=%d terminal_trace_ret=%d",
    ):
        if token not in source and token not in internal:
            raise SystemExit(f"staged production token absent: {token}")


def apply_production(root: Path) -> None:
    internal = (
        root
        / "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h"
    )
    replace_once(
        internal,
        "struct mt6797_a72_admission_controller_ops {\n"
        "\tbool (*binder_ready)(void *context);\n",
        "struct mt6797_a72_admission_controller_ops {\n"
        "\tbool allow_trace_failure;\n"
        "\tbool (*binder_ready)(void *context);\n",
    )
    replace_once(
        internal,
        "\tu32 cpu_requests;\n\tint trace_ret;\n",
        "\tu32 cpu_requests;\n\tint trace_entry_ret;\n\tint trace_ret;\n",
    )

    source = root / "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    replace_once(
        source,
        "\tret = ops->trace_entry(context);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n",
        "\tstate->trace_entry_ret = ops->trace_entry(context);\n"
        "\tif (state->trace_entry_ret && !ops->allow_trace_failure)\n"
        "\t\treturn state->trace_entry_ret;\n",
    )
    replace_once(
        source,
        "\t\tif (state->trace_ret)\n\t\t\tret = state->trace_ret;\n",
        "\t\tif (state->trace_ret && !ops->allow_trace_failure)\n"
        "\t\t\tret = state->trace_ret;\n",
    )
    replace_once(
        source,
        "mt6797_a72_admission_production_ops = {\n"
        "\t.binder_ready = mt6797_a72_admission_binder_ready,\n",
        "mt6797_a72_admission_production_ops = {\n"
        "\t.allow_trace_failure =\n"
        "\t\tIS_ENABLED(CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER),\n"
        "\t.binder_ready = mt6797_a72_admission_binder_ready,\n",
    )
    replace_once(
        source,
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"cpu_requests=%u cpu9_requests=0 \",\n"
        "\t\t\t     READ_ONCE(controller->state.cpu_requests));\n",
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"entry_trace_ret=%d terminal_trace_ret=%d \",\n"
        "\t\t\t     READ_ONCE(controller->state.trace_entry_ret),\n"
        "\t\t\t     READ_ONCE(controller->state.trace_ret));\n"
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"cpu_requests=%u cpu9_requests=0 \",\n"
        "\t\t\t     READ_ONCE(controller->state.cpu_requests));\n",
    )
    replace_once(
        source,
        "\tdev_info(dev, MT6797_A72_ADMISSION_LIVE_TAG\n"
        "\t\t \" state=terminal ret=%d core_consumed=%d requests=%u/0/0 \"\n"
        "\t\t \"retries=0\\n\",\n"
        "\t\t READ_ONCE(controller->trigger.operation_ret),\n"
        "\t\t atomic_read(&controller->state.consumed),\n"
        "\t\t READ_ONCE(controller->state.cpu_requests));\n",
        "\tdev_info(dev, MT6797_A72_ADMISSION_LIVE_TAG\n"
        "\t\t \" state=terminal operation_ret=%d core_consumed=%d \"\n"
        "\t\t \"entry_trace_ret=%d terminal_trace_ret=%d \"\n"
        "\t\t \"requests=%u/0/0 retries=0\\n\",\n"
        "\t\t READ_ONCE(controller->trigger.operation_ret),\n"
        "\t\t atomic_read(&controller->state.consumed),\n"
        "\t\t READ_ONCE(controller->state.trace_entry_ret),\n"
        "\t\t READ_ONCE(controller->state.trace_ret),\n"
        "\t\t READ_ONCE(controller->state.cpu_requests));\n",
    )


def apply_tests(root: Path) -> None:
    test = (
        root
        / "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c"
    )
    anchor = "static void mt6797_a72_admission_repeat_closed_test(struct kunit *test)\n"
    block = r'''static void mt6797_a72_admission_live_trace_softfail_test(struct kunit *test)
{
	struct mt6797_a72_admission_controller_ops live_ops = test_ops;
	struct mt6797_a72_admission_test_context *context;
	int ret;

	live_ops.allow_trace_failure = true;
	context = mt6797_a72_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->fail_event = MT6797_ADMISSION_TRACE_ENTRY;
	ret = mt6797_a72_admission_run(&context->controller, &live_ops, context);
	KUNIT_EXPECT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, context->controller.trace_entry_ret, -ENOSPC);
	KUNIT_EXPECT_EQ(test, atomic_read(&context->controller.consumed), 1);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)1);
	KUNIT_EXPECT_EQ(test, context->requested_cpu, 8U);

	context = mt6797_a72_admission_test_context(test);
	KUNIT_ASSERT_NOT_NULL(test, context);
	context->fail_event = MT6797_ADMISSION_SOURCE_REGISTER;
	context->trace_zero_fails = true;
	ret = mt6797_a72_admission_run(&context->controller, &live_ops, context);
	KUNIT_EXPECT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->controller.trace_entry_ret, 0);
	KUNIT_EXPECT_EQ(test, context->controller.trace_ret, -ENOSPC);
	KUNIT_EXPECT_EQ(test, context->controller.operation_ret, -EIO);
	KUNIT_EXPECT_EQ(test, context->controller.cpu_requests, (u32)0);
}

'''
    replace_once(test, anchor, block + anchor)
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_a72_admission_trace_failures_test),\n"
        "\tKUNIT_CASE(mt6797_a72_admission_repeat_closed_test),\n",
        "\tKUNIT_CASE(mt6797_a72_admission_trace_failures_test),\n"
        "\tKUNIT_CASE(mt6797_a72_admission_live_trace_softfail_test),\n"
        "\tKUNIT_CASE(mt6797_a72_admission_repeat_closed_test),\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--stage", choices=("production", "tests"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_stage_parent(root, args.stage)
    if args.stage == "production":
        apply_production(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
