#!/usr/bin/env python3
"""Validate the durable CPU8 admission trace after each patch stage."""

from __future__ import annotations

import argparse
from pathlib import Path


ENTRY = (
    "====0.000000-D\n"
    "GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
    "kind=entry slot=2\n"
)
TERMINALS = (
    "kind=zero-source-register slot=3",
    "kind=zero-derive slot=3",
    "kind=zero-publish slot=3",
)


def read(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"required source file unavailable: {relative}")
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def ordered(text: str, tokens: tuple[str, ...], message: str) -> None:
    positions = [text.find(token) for token in tokens]
    require(all(position >= 0 for position in positions), f"{message} tokens")
    require(positions == sorted(positions) and len(set(positions)) == len(positions),
            f"{message} order")


def validate_trace(root: Path) -> None:
    source = read(root, "fs/pstore/gemini_admission_trace.c")
    internal = read(root, "fs/pstore/gemini_admission_trace_internal.h")
    public = read(root, "include/linux/gemini_admission_trace.h")
    kconfig = read(root, "fs/pstore/Kconfig")
    makefile = read(root, "fs/pstore/Makefile")
    for token in (
        "#define GEMINI_ADMISSION_TRACE_RESERVE_BASE 0x44410000ULL",
        "#define GEMINI_ADMISSION_TRACE_BASE 0x44411000ULL",
        "#define GEMINI_ADMISSION_TRACE_ENTRY_SLOT 0U",
        "#define GEMINI_ADMISSION_TRACE_TERMINAL_SLOT 1U",
        'of_find_node_by_path("/reserved-memory/ramoops@44410000")',
        "resource_size(&resource) != GEMINI_ADMISSION_TRACE_RESERVE_SIZE",
        "ioremap_wc(GEMINI_ADMISSION_TRACE_BASE",
    ):
        require(source.count(token) == 1, f"one production token {token}")
    require("GEMINI_ADMISSION_TRACE_SLOT_COUNT 2U" in internal,
            "exact two-slot owner")
    require("GEMINI_ADMISSION_TRACE_SLOT_SIZE 0x1000U" in internal,
            "exact 4 KiB records")
    require("GEMINI_ADMISSION_TRACE_HEADER_SIZE 12U" in internal,
            "exact persistent-RAM header")
    require("PSTORE_GEMINI_ADMISSION_TRACE" in public,
            "public API is config-gated")
    require("depends on PSTORE_GEMINI_TRANSITION_LEDGER=y" in kconfig,
            "normal ramoops remains bypassed by transition-ledger owner")
    require(makefile.count(
        "obj-$(CONFIG_PSTORE_GEMINI_ADMISSION_TRACE) += "
        "gemini_admission_trace.o") == 1, "one production object")
    require(source.count("GAAT-20260828-A") == 4,
            "one entry and three terminal record literals")
    require('"kind=entry slot=2\\n"' in source, "exact entry literal")
    for terminal in TERMINALS:
        require(f'"{terminal}\\n"' in source, f"exact terminal {terminal}")
    ordered(
        source[source.index("static int gemini_admission_trace_write("):],
        (
            "ops->write_byte(context, slot,",
            "ops->sync(context);",
            "ops->write_word(context, slot, 1, length);",
            "ops->write_word(context, slot, 2, length);",
            "gemini_admission_trace_slot_exact(ops, context, slot, record)",
            "owner->commits++;",
        ),
        "payload-metadata-readback commit",
    )
    require(source.count("owner->commits++") == 1, "single commit counter path")
    require(source.count("gemini_admission_trace_write(owner") == 2,
            "entry and terminal write call sites only")
    require("GEMINI_ADMISSION_TRACE_ENTRY_SLOT" in source and
            "GEMINI_ADMISSION_TRACE_TERMINAL_SLOT" in source,
            "separate immutable slots")
    for forbidden in (
        "add_cpu(", "cpu_up(", "cpu_down(", "cpu_off(", "kernel_restart(",
        "orderly_reboot(", "orderly_poweroff(", "kernel_power_off(",
        "watchdog", "regulator", "i2c_", "request_firmware", "filp_open",
        "blkdev", "retry",
    ):
        require(forbidden not in source.lower(),
                f"production trace excludes {forbidden}")


def validate_trace_tests(root: Path) -> None:
    test = read(root, "fs/pstore/gemini_admission_trace_test.c")
    kconfig = read(root, "fs/pstore/Kconfig")
    makefile = read(root, "fs/pstore/Makefile")
    for name in (
        "entry_commit", "entry_reentry", "foreign_refusal",
        "terminal_records", "terminal_gates", "torn_write",
    ):
        require(test.count(f"gemini_admission_trace_{name}_test") == 2,
                f"defined and registered trace test {name}")
    require("kunit_kzalloc(test, sizeof(*context), GFP_KERNEL)" in test,
            "large test records are heap-backed")
    require(test.count("trace_test_terminal[result]") == 1,
            "all three exact terminal records are checked")
    require("context->word_writes[0], 2U" in test and
            "context->word_writes[1], 2U" in test,
            "two metadata writes per committed slot")
    require("context->syncs[0], 3U" in test and
            "context->syncs[1], 3U" in test,
            "three ordered barriers per committed slot")
    require("depends on PSTORE_GEMINI_ADMISSION_TRACE=y" in kconfig,
            "trace tests require production owner")
    require(makefile.count(
        "obj-$(CONFIG_PSTORE_GEMINI_ADMISSION_TRACE_KUNIT_TEST) += "
        "gemini_admission_trace_test.o") == 1, "one trace test object")


def validate_controller(root: Path) -> None:
    source = read(root, "drivers/soc/mediatek/mt6797-a72-admission-controller.c")
    internal = read(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h"
    )
    kconfig = read(root, "drivers/soc/mediatek/Kconfig")
    require("depends on PSTORE_GEMINI_ADMISSION_TRACE=y" in kconfig,
            "controller requires durable trace")
    for token in (
        "int (*trace_entry)(void *context);",
        "int (*trace_zero_request)(void *context,",
        "int trace_ret;",
    ):
        require(internal.count(token) == 1, f"one controller interface {token}")
    ordered(
        source[source.index("int\nmt6797_a72_admission_run("):],
        (
            "if (atomic_read(&state->consumed))",
            "ret = ops->trace_entry(context);",
            "if (!ops->binder_ready(context))",
            "ready = ops->ready_token(context);",
            "atomic_cmpxchg(&state->consumed, 0, 1)",
            "ret = ops->source_register(context);",
            "ret = ops->derive_cpu8(context, ready, &state->transaction);",
            "ret = ops->publish_up(context, &state->transaction);",
            "state->cpu_requests++;",
            "ret = ops->add_cpu(context, MT6797_A72_ADMISSION_CPU);",
            "out_unregister:",
            "out_terminal:",
            "ops->trace_zero_request(context, zero_result);",
        ),
        "controller trace and request",
    )
    require(source.count("state->cpu_requests++") == 1,
            "one CPU request counter increment")
    require(source.count("ops->add_cpu(") == 1, "one injected CPU8 request")
    require("#define MT6797_A72_ADMISSION_CPU 8" in source,
            "CPU8 remains exact target")
    for token in (
        "GEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER",
        "GEMINI_ADMISSION_TRACE_ZERO_DERIVE",
        "GEMINI_ADMISSION_TRACE_ZERO_PUBLISH",
    ):
        require(source.count(token) == 1, f"one zero-request result {token}")
    require("if (!state->cpu_requests && zero_result)" in source,
            "terminal trace excludes request path")
    require("cpu9" not in source.lower() and "cpu_off" not in source.lower(),
            "no CPU9 or CPU_OFF path")


def validate_controller_tests(root: Path) -> None:
    test = read(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c"
    )
    for token in (
        "MT6797_ADMISSION_TRACE_ENTRY",
        "MT6797_ADMISSION_TRACE_ZERO_REQUEST",
        "context->trace_zero_fails",
        "results[failure]",
        "mt6797_a72_admission_trace_failures_test",
    ):
        require(token in test, f"controller test trace token {token}")
    require(test.count("GEMINI_ADMISSION_TRACE_ZERO_SOURCE_REGISTER") == 1 and
            test.count("GEMINI_ADMISSION_TRACE_ZERO_DERIVE") == 1 and
            test.count("GEMINI_ADMISSION_TRACE_ZERO_PUBLISH") == 1,
            "three exact terminal result expectations")
    require(test.count("context->controller.cpu_requests, (u32)1") >= 2,
            "success and request-failure remain one request")
    require("context->event_count, 2U" in test and
            "context->event_count, 3U" in test,
            "preconsume trace entry ordering")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=("trace", "trace-tests", "controller", "controller-tests"),
        required=True,
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_trace(root)
    if args.stage in ("trace-tests", "controller", "controller-tests"):
        validate_trace_tests(root)
    if args.stage in ("controller", "controller-tests"):
        validate_controller(root)
    if args.stage == "controller-tests":
        validate_controller_tests(root)
    print("validation=gemini-cpu8-admission-durable-trace-source")
    print(f"stage={args.stage}")
    print("entry_slot=2")
    print("terminal_slot=3")
    print("maximum_trace_record_writes=2")
    print("zero_request_outcomes=3")
    print("cpu8_request_maximum=1")
    print("cpu9_request_paths=0")
    print("cpu_off_paths=0")
    print("retry_paths=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
