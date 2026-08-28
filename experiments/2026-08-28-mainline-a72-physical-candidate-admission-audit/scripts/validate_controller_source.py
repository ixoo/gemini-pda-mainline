#!/usr/bin/env python3
"""Validate the generated one-shot CPU8 admission controller."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def source(root: Path, relative: str) -> str:
    path = root / relative
    require(path.is_file() and not path.is_symlink(), f"exact file: {relative}")
    return path.read_text(encoding="utf-8")


def validate_production(root: Path) -> None:
    binder_header = source(
        root, "include/linux/soc/mediatek/mt6797-a72-binder.h"
    )
    binder = source(root, "drivers/soc/mediatek/mt6797-a72-binder.c")
    physical_header = source(
        root,
        "drivers/soc/mediatek/mt6797-a72-physical-source-observer-internal.h",
    )
    physical = source(
        root, "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    )
    controller_header = source(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h"
    )
    controller = source(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    )
    kconfig = source(root, "drivers/soc/mediatek/Kconfig")
    makefile = source(root, "drivers/soc/mediatek/Makefile")
    base_dts = source(
        root, "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts"
    )

    require(binder_header.count("mt6797_a72_binder_available(void)") == 2,
            "binder readiness declaration and disabled stub")
    for token in (
        "bool mt6797_a72_binder_available(void)",
        "mutex_lock(&mt6797_a72_binder_publish_lock);",
        "available = !!mt6797_a72_binder_ready();",
        "mutex_unlock(&mt6797_a72_binder_publish_lock);",
    ):
        require(token in binder, f"binder token: {token}")
    require(binder.count("bool mt6797_a72_binder_available(void)") == 1,
            "one production binder-ready accessor")

    for token in (
        "mt6797_a72_source_context_init(",
        "mt6797_a72_source_register(",
        "mt6797_a72_source_unregister(",
    ):
        require(token in physical_header, f"physical header token: {token}")
        require(token in physical, f"physical source token: {token}")
    require(physical.count("mt6797_a72_source_register(") == 1,
            "one physical-source registration wrapper")
    require(physical.count("mt6797_a72_source_unregister(") == 1,
            "one physical-source unregistration wrapper")

    for token in (
        "struct mt6797_a72_admission_controller_ops",
        "atomic_t consumed;",
        "u32 cpu_requests;",
        "struct mt6797_a72_transaction transaction;",
    ):
        require(token in controller_header, f"controller header token: {token}")
    for token in (
        "if (!ops->binder_ready(context))",
        "return -EPROBE_DEFER;",
        "ready = ops->ready_token(context);",
        "return -EAGAIN;",
        "atomic_cmpxchg(&state->consumed, 0, 1)",
        "ret = ops->source_register(context);",
        "ret = ops->derive_cpu8(context, ready, &state->transaction);",
        "ret = ops->publish_up(context, &state->transaction);",
        "state->cpu_requests++;",
        "ret = ops->add_cpu(context, MT6797_A72_ADMISSION_CPU);",
        "ops->source_unregister(context);",
        "return add_cpu(cpu);",
        "mt6797_a72_binder_available();",
        "arm64_get_late_cpu_ready_token();",
        "mt6797_a72_membership_derive_cpu8(ready, transaction);",
        "mt6797_a72_membership_publish_up(transaction);",
        '"mediatek,binder"',
        '"mediatek,platform-state"',
        '"mediatek,clock-backend"',
        '"mediatek,bigidvfs-backend"',
        "device_link_add(dev, &pdev->dev, DL_FLAG_AUTOREMOVE_CONSUMER)",
        ".suppress_bind_attrs = true",
        "late_initcall(mt6797_a72_admission_init);",
        "requests=%u/0/0 retries=0",
    ):
        require(token in controller, f"controller token: {token}")
    consumed = controller.index("atomic_cmpxchg(&state->consumed, 0, 1)")
    source_register = controller.index("ret = ops->source_register(context);")
    derive = controller.index("ret = ops->derive_cpu8(")
    publish = controller.index("ret = ops->publish_up(")
    request = controller.index("ret = ops->add_cpu(")
    unregister = controller.index("ops->source_unregister(context);")
    require(consumed < source_register < derive < publish < request < unregister,
            "consumed then source then derive then publish then request")
    require(controller.count("return add_cpu(cpu);") == 1,
            "one production add_cpu call site")
    require(controller.count("MT6797_A72_ADMISSION_CPU 8") == 1,
            "CPU8 is the only target")
    for forbidden in (
        "add_cpu(9)", "cpu_down(", "cpu_off(", "module_param",
        "debugfs", "sysfs", "schedule_work", "queue_work", "kthread",
        "remove =", ".remove", "schedule_delayed_work",
        "-EPROBE_DEFER;\n\tstate->",
    ):
        require(forbidden not in controller,
                f"controller forbidden token: {forbidden}")

    for token in (
        "config MTK_MT6797_A72_ADMISSION_CONTROLLER",
        "depends on ARM64_MT6797_A72_DERIVED_ADMISSION",
        "depends on MTK_MT6797_A72_DEFAULT_OFF_BINDER",
        "depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER",
        "Every later result is terminal",
        "base Gemini Device Tree has no controller or binder node",
    ):
        require(token in kconfig, f"production Kconfig token: {token}")
    require("mt6797-a72-admission-controller.o" in makefile,
            "controller Makefile object")
    require("mt6797-a72-admission-controller" not in base_dts,
            "base DT has no admission controller")
    require("mt6797-a72-binder" not in base_dts,
            "base DT has no binder")


def validate_tests(root: Path) -> None:
    test = source(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c"
    )
    kconfig = source(root, "drivers/soc/mediatek/Kconfig")
    makefile = source(root, "drivers/soc/mediatek/Makefile")
    for token in (
        "config MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST",
        "depends on KUNIT=y",
        "depends on MTK_MT6797_A72_ADMISSION_CONTROLLER",
        "No physical source, CPU, watchdog, retained-RAM",
    ):
        require(token in kconfig, f"test Kconfig token: {token}")
    require("mt6797-a72-admission-controller-test.o" in makefile,
            "controller test object")
    for token in (
        "KUNIT_CASE(mt6797_a72_admission_success_test)",
        "KUNIT_CASE(mt6797_a72_admission_preconsume_gates_test)",
        "KUNIT_CASE(mt6797_a72_admission_terminal_failures_test)",
        "KUNIT_CASE(mt6797_a72_admission_request_failure_test)",
        "KUNIT_CASE(mt6797_a72_admission_repeat_closed_test)",
        '.name = "mt6797-a72-admission-controller"',
        "context->requested_cpu, 8U",
        "context->controller.cpu_requests, (u32)1",
        "context->controller.cpu_requests, (u32)0",
        "ret, -EPROBE_DEFER",
        "ret, -EAGAIN",
        "ret, -EALREADY",
        "context->consumed_before_operation",
        "context->same_task",
    ):
        require(token in test, f"test token: {token}")
    require(test.count("KUNIT_CASE(") == 5, "five controller cases")
    for forbidden in (
        "return add_cpu(", "cpu_down(", "cpu_off(",
        "mt6797_a72_binder_cpu_boot(", "gemini_transition_ledger",
        "mtk_wdt", "readl(", "writel(",
    ):
        require(forbidden not in test, f"test forbidden token: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_production(root)
    if args.stage == "tests":
        validate_tests(root)
    print("validation=mt6797-a72-one-shot-admission-controller")
    print(f"stage={args.stage}")
    print("binder_ready_accessors=1")
    print("source_registrations=1")
    print("production_cpu8_request_call_sites=1")
    print("production_cpu9_request_call_sites=0")
    print("cpu_off_call_sites=0")
    print("retry_call_sites=0")
    print("base_dt_enablements=0")
    if args.stage == "tests":
        print("controller_kunit_cases=5")
    print("result=pass")


if __name__ == "__main__":
    main()
