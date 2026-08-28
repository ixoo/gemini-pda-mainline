#!/usr/bin/env python3
"""Validate live-only trace soft-failure admission semantics."""

from __future__ import annotations

import argparse
from pathlib import Path


def read(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"required source unavailable: {relative}")
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def ordered(text: str, tokens: tuple[str, ...], message: str) -> None:
    positions = [text.find(token) for token in tokens]
    require(all(position >= 0 for position in positions), f"{message} tokens")
    require(
        positions == sorted(positions) and len(set(positions)) == len(positions),
        f"{message} order",
    )


def validate_production(root: Path) -> None:
    source = read(root, "drivers/soc/mediatek/mt6797-a72-admission-controller.c")
    internal = read(
        root,
        "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h",
    )
    require(internal.count("bool allow_trace_failure;") == 1,
            "one injected trace policy bit")
    require(internal.count("int trace_entry_ret;") == 1,
            "one entry trace result")
    core = source[source.index("mt6797_a72_admission_run("):]
    ordered(
        core,
        (
            "state->trace_entry_ret = ops->trace_entry(context)",
            "state->trace_entry_ret && !ops->allow_trace_failure",
            "ops->binder_ready(context)",
            "ops->ready_token(context)",
            "atomic_cmpxchg(&state->consumed, 0, 1)",
            "ops->source_register(context)",
            "ops->derive_cpu8(context, ready, &state->transaction)",
            "ops->publish_up(context, &state->transaction)",
            "state->cpu_requests++",
            "ops->add_cpu(context, MT6797_A72_ADMISSION_CPU)",
        ),
        "trace observation before unchanged one-shot core",
    )
    require(
        "state->trace_ret && !ops->allow_trace_failure" in core,
        "terminal trace result obeys the same explicit policy",
    )
    initializer = source[source.index(
        "mt6797_a72_admission_production_ops = {"
    ):]
    ordered(
        initializer,
        (
            ".allow_trace_failure =",
            "IS_ENABLED(CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER)",
            ".binder_ready =",
        ),
        "live configuration is the only production soft-failure policy",
    )
    require(source.count("return add_cpu(cpu);") == 1,
            "one unchanged physical CPU request call site")
    require(source.count("return mt6797_a72_admission_run(") == 1,
            "one production admission-core call path")
    for field in (
        "operation_ret=%d", "entry_trace_ret=%d",
        "terminal_trace_ret=%d", "core_consumed=%d",
        "cpu_requests=%u", "cpu9_requests=0", "cpu_off_requests=0",
        "retries=0",
    ):
        require(field in source, f"status field {field}")
    for forbidden in (
        "cpu_down(", "remove_cpu(", "cpu_off(", "kernel_restart(",
        "orderly_reboot(", "orderly_poweroff(", "request_firmware(",
        "filp_open(", "blkdev_get",
    ):
        require(forbidden not in source.lower(), f"production excludes {forbidden}")


def validate_tests(root: Path) -> None:
    test = read(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c"
    )
    require(
        test.count("mt6797_a72_admission_live_trace_softfail_test") == 2,
        "live soft-failure test defined and registered",
    )
    require(test.count("KUNIT_CASE(") == 10,
            "ten focused controller cases")
    for token in (
        "live_ops.allow_trace_failure = true;",
        "context->controller.trace_entry_ret, -ENOSPC",
        "context->controller.trace_ret, -ENOSPC",
        "context->controller.operation_ret, -EIO",
        "context->controller.cpu_requests, (u32)1",
        "context->controller.cpu_requests, (u32)0",
    ):
        require(token in test, f"live soft-failure assertion {token}")
    # The pre-existing strict tests remain the fail-closed control.
    strict = test[test.index(
        "mt6797_a72_admission_trace_failures_test("
    ):test.index(
        "mt6797_a72_admission_live_trace_softfail_test("
    )]
    for token in (
        "KUNIT_EXPECT_EQ(test, ret, -ENOSPC)",
        "atomic_read(&context->controller.consumed), 0",
        "context->event_count, 1U",
    ):
        require(token in strict, f"automatic fail-closed control {token}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--stage", choices=("production", "tests"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_production(root)
    if args.stage == "tests":
        validate_tests(root)
    print("validation=gemini-a72-admission-trace-softfail-source")
    print(f"stage={args.stage}")
    print("automatic_probe_action=0")
    print("live_trace_failure_advisory=1")
    print("automatic_trace_failure_fatal=1")
    print("trigger_execution_maximum=1")
    print("admission_core_maximum=1")
    print("cpu8_request_maximum=1")
    print("cpu9_request_paths=0")
    print("cpu_off_paths=0")
    print("retry_paths=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
