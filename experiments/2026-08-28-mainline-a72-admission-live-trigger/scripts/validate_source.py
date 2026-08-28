#!/usr/bin/env python3
"""Validate serviceability-first admission-trigger source semantics."""

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
    kconfig = read(root, "drivers/soc/mediatek/Kconfig")

    require(
        kconfig.count("config MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER\n") == 1,
        "one default-off live-trigger option",
    )
    for token in (
        "depends on MTK_MT6797_A72_ADMISSION_CONTROLLER",
        "depends on SYSFS",
        "default n",
    ):
        require(token in kconfig, f"Kconfig gate {token}")
    require(
        internal.count(
            '#define MT6797_A72_ADMISSION_TRIGGER_TOKEN \\\n'
            '\t"run-a72-admission-20260828-a\\n"'
        ) == 1,
        "exact newline-terminated trigger token",
    )
    for token in (
        "struct mt6797_a72_admission_trigger_ops",
        "struct mt6797_a72_admission_trigger_state",
        "atomic_t consumed;",
        "bool complete;",
        "u32 executions;",
        "int operation_ret;",
    ):
        require(token in internal, f"trigger interface {token}")

    trigger = source[source.index("mt6797_a72_admission_trigger_run("):]
    ordered(
        trigger,
        (
            "count != sizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 1",
            "memcmp(buf, MT6797_A72_ADMISSION_TRIGGER_TOKEN, count)",
            "atomic_cmpxchg(&state->consumed, 0, 1)",
            "WRITE_ONCE(state->executions, 1)",
            "ret = ops->execute(context)",
            "WRITE_ONCE(state->operation_ret, ret)",
            "smp_store_release(&state->complete, true)",
        ),
        "exact consume-before-execute trigger",
    )
    require(
        trigger.count("ops->execute(context)") == 1,
        "one injected trigger execution",
    )
    require(
        "return 0;" in trigger[trigger.index("ret = ops->execute(context)"):],
        "accepted trigger records underlying result",
    )

    probe = source[source.index("static int mt6797_a72_admission_probe("):]
    live_start = probe.index(
        "if (IS_ENABLED(CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER))"
    )
    live_end = probe.index("\n\t}\n\n\tret = mt6797_a72_admission_execute", live_start)
    live_branch = probe[live_start:live_end]
    ordered(
        probe,
        (
            "mt6797_a72_admission_state_init(&controller->state)",
            "mt6797_a72_admission_trigger_state_init(&controller->trigger)",
            "platform_set_drvdata(pdev, controller)",
            "if (IS_ENABLED(CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER))",
            "devm_device_add_group(dev,",
            '" state=armed trigger_consumed=0 trigger_executions=0 "',
            "return 0;",
            "ret = mt6797_a72_admission_execute(controller)",
        ),
        "dormant live probe before historical automatic path",
    )
    for forbidden in (
        "mt6797_a72_admission_resolve",
        "mt6797_a72_admission_prepare",
        "mt6797_a72_admission_execute",
        "mt6797_a72_admission_run",
        "add_cpu",
    ):
        require(forbidden not in live_branch, f"live probe excludes {forbidden}")

    require(source.count("static DEVICE_ATTR_WO(trigger);") == 1,
            "one root-write-only trigger")
    require(source.count("static DEVICE_ATTR_RO(status);") == 1,
            "one read-only status")
    require('.name = "gemini_admission"' in source,
            "exact attribute group")
    for field in (
        "state=%s", "trigger_consumed=%u", "trigger_executions=%u",
        "operation_ret=%d", "core_consumed=%d", "cpu_requests=%u",
        "cpu9_requests=0", "cpu_off_requests=0", "retries=0",
    ):
        require(field in source, f"status wire {field}")

    execute = source[source.index("static int mt6797_a72_admission_execute("):]
    ordered(
        execute,
        (
            "ret = mt6797_a72_admission_prepare(controller)",
            "return mt6797_a72_admission_run(",
        ),
        "supplier preparation before unchanged core",
    )
    require(source.count("return mt6797_a72_admission_run(") == 1,
            "one production admission-core call path")
    require(source.count("return add_cpu(cpu);") == 1,
            "unchanged single CPU request call site")
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
    for name in (
        "trigger_invalid", "trigger_terminal", "trigger_repeat_closed",
    ):
        require(
            test.count(f"mt6797_a72_admission_{name}_test") == 2,
            f"defined and registered {name} test",
        )
    require(test.count("KUNIT_CASE(") == 9, "nine focused controller cases")
    require(
        "sizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 2" in test,
        "short token mutation",
    )
    require(
        test.count("sizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 1") == 3,
        "three exact-token calls",
    )
    for token in (
        "KUNIT_EXPECT_EQ(test, ret, -EINVAL)",
        "KUNIT_EXPECT_EQ(test, ret, -EALREADY)",
        "KUNIT_EXPECT_EQ(test, trigger.operation_ret, -EIO)",
        "KUNIT_EXPECT_EQ(test, context.trigger_execute_calls, 1U)",
    ):
        require(token in test, f"trigger test assertion {token}")


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
    print("validation=gemini-a72-admission-live-trigger-source")
    print(f"stage={args.stage}")
    print("automatic_probe_action=0")
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
