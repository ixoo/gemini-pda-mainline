#!/usr/bin/env python3
"""Fail-closed source oracle for the disconnected retained-CPU8 observer."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", text, re.S)
    require(match is not None, f"function missing: {name}")
    start = match.end()
    depth = 1
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index]
    raise ValueError(f"unterminated function: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.source_root.resolve()
        mediatek = root / "drivers/soc/mediatek"
        internal = (mediatek / "mt6797-a72-cpu8-observer-internal.h").read_text(
            encoding="utf-8"
        )
        source = (mediatek / "mt6797-a72-cpu8-observer.c").read_text(
            encoding="utf-8"
        )
        test = (mediatek / "mt6797-a72-cpu8-observer-test.c").read_text(
            encoding="utf-8"
        )
        kconfig = (mediatek / "Kconfig").read_text(encoding="utf-8")
        makefile = (mediatek / "Makefile").read_text(encoding="utf-8")

        for token in (
            "MT6797_A72_CPU8_OBSERVER_CPU 8U",
            "MT6797_A72_CPU8_OBSERVER_TIMEOUT_MS 250U",
            "struct completion completion;",
            "struct mt6797_a72_hotplug_identity expected;",
            "atomic_t dispatch_calls;",
            "atomic_t wait_calls;",
            "atomic_t callback_calls;",
            "atomic_t identity_checks;",
            "atomic_t late_callbacks;",
        ):
            require(token in internal, f"observer contract missing: {token}")
        require("reset" not in internal, "observer gained an unsafe reset path")

        dispatch = function_body(source, "mt6797_a72_cpu8_observer_dispatch")
        require(
            "if (wait)" in dispatch and "return -EINVAL;" in dispatch,
            "synchronous dispatch refusal missing",
        )
        require(
            "return smp_call_function_single(cpu, function, info, 0);" in dispatch,
            "production dispatch is not exact wait=0",
        )
        require(
            source.count("smp_call_function_single(") == 1,
            "IPI call-site count changed",
        )

        wait = function_body(source, "mt6797_a72_cpu8_observer_wait")
        require(
            "return wait_for_completion_timeout(completion, timeout);" in wait,
            "bounded completion wrapper changed",
        )
        require(
            source.count("wait_for_completion_timeout(") == 1,
            "completion wait-site count changed",
        )
        require(
            "wait_for_completion(" not in source,
            "unbounded completion wait added",
        )

        identity_valid = function_body(
            source, "mt6797_a72_cpu8_observer_identity_valid"
        )
        for token in (
            "identity->abi == MT6797_A72_HOTPLUG_ABI",
            "MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN",
            "identity->target_cpu == 9",
            "identity->target_mpidr == 0x201",
            "identity->generation",
            "identity->cookie",
            "identity->parent_generation",
            "identity->parent_cookie",
        ):
            require(token in identity_valid, f"down identity shape missing: {token}")

        identity_match = function_body(
            source, "mt6797_a72_cpu8_observer_identity_matches"
        )
        for token in (
            "snapshot->phase == MT6797_A72_HOTPLUG_OFF_COMMITTED",
            "snapshot->owner_health == MT6797_A72_OWNER_AVAILABLE",
            "snapshot->controller_present == 1",
            "snapshot->members == (BIT(0) | BIT(1))",
            "!memcmp(&active->identity, identity, sizeof(*identity))",
            "active->off_committed == 1",
            "!active->off_proven",
            "active->budgets.cpu_off == MT6797_A72_BUDGET_CONSUMED",
            "active->budgets.affinity == MT6797_A72_BUDGET_AVAILABLE",
        ):
            require(token in identity_match, f"owner identity gate missing: {token}")

        check_identity = function_body(
            source, "mt6797_a72_cpu8_observer_check_identity"
        )
        require(
            check_identity.count("mt6797_a72_hotplug_snapshot(&snapshot)") == 1,
            "owner snapshot call count changed",
        )
        require(
            "mt6797_a72_cpu8_observer_identity_matches(&snapshot, identity)" in
            check_identity,
            "exact owner identity predicate disconnected",
        )

        callback = function_body(source, "mt6797_a72_cpu8_observer_callback")
        callback_order = (
            "atomic_read_acquire(&observer->state)",
            "observer->ops->current_cpu(observer->ops_context)",
            "MT6797_A72_CPU8_OBSERVER_CPU",
            "observer->ops->identity_check(observer->ops_context",
            "atomic_cmpxchg(&observer->state",
            "complete(&observer->completion)",
        )
        offsets = [callback.index(token) for token in callback_order]
        require(offsets == sorted(offsets), "callback validation order changed")
        require(
            re.search(
                r"observer->ops->current_cpu\(observer->ops_context\)\s*!=\s*"
                r"MT6797_A72_CPU8_OBSERVER_CPU",
                callback,
            ) is not None,
            "exact CPU8 comparison changed",
        )
        require(
            callback.count("observer->ops->identity_check(") == 1,
            "identity check retry added",
        )
        require(
            callback.count("complete(&observer->completion)") == 1,
            "callback completion publication changed",
        )

        run = function_body(source, "mt6797_a72_cpu8_observer_run_with_ops")
        for token in (
            "MT6797_A72_CPU8_OBSERVER_IDLE",
            "MT6797_A72_CPU8_OBSERVER_ARMED",
            "observer->expected = *identity",
            "observer->ops = ops",
            "MT6797_A72_CPU8_OBSERVER_CPU",
            "mt6797_a72_cpu8_observer_callback, observer",
            "false",
            "msecs_to_jiffies(MT6797_A72_CPU8_OBSERVER_TIMEOUT_MS)",
            "MT6797_A72_CPU8_OBSERVER_TIMED_OUT",
            "return -ETIMEDOUT",
            "return -EALREADY",
        ):
            require(token in run, f"controller gate missing: {token}")
        require(run.count("ops->dispatch(") == 1, "dispatch retry added")
        require(run.count("ops->wait_timeout(") == 1, "controller wait retry added")

        require(
            test.count("KUNIT_CASE(cpu8_observer_") == 7,
            "CPU8 observer KUnit case count changed",
        )
        for token in (
            "cpu8_observer_success_test",
            "cpu8_observer_cpu_refusal_test",
            "cpu8_observer_identity_refusal_test",
            "cpu8_observer_dispatch_refusal_test",
            "cpu8_observer_timeout_late_callback_test",
            "cpu8_observer_one_shot_test",
            "cpu8_observer_snapshot_identity_test",
            "state->dispatch_cpu, 8U",
            "KUNIT_EXPECT_FALSE(test, state->dispatch_wait)",
            "msecs_to_jiffies(250)",
            "MT6797_A72_CPU8_OBSERVER_TIMED_OUT",
            "observer->late_callbacks",
            "state->dispatches, 1U",
        ):
            require(token in test, f"KUnit proof missing: {token}")
        require(
            "struct mt6797_a72_cpu8_observer observer" not in test,
            "callback context moved onto the test stack",
        )

        config_match = re.search(
            r"config MTK_MT6797_A72_CPU8_OBSERVER\n.*?(?=\nconfig |\Z)",
            kconfig,
            re.S,
        )
        require(config_match is not None, "observer Kconfig missing")
        config = config_match.group(0)
        for dependency in (
            "depends on SMP",
            "depends on MTK_MT6797_A72_HOTPLUG_EXECUTOR",
            "depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL",
        ):
            require(dependency in config, f"Kconfig dependency missing: {dependency}")
        require(
            "CONFIG_MTK_MT6797_A72_CPU8_OBSERVER) += mt6797-a72-cpu8-observer.o"
            in makefile,
            "observer Makefile entry missing",
        )
        require(
            "CONFIG_MTK_MT6797_A72_CPU8_OBSERVER_KUNIT_TEST) += "
            "mt6797-a72-cpu8-observer-test.o" in makefile,
            "observer KUnit Makefile entry missing",
        )

        added = internal + source + test
        for token in (
            "cpu_up(",
            "cpu_down(",
            "remove_cpu(",
            "add_cpu(",
            "psci_ops.",
            "cpu_psci_ops.",
            "arm_smccc",
            "readl(",
            "writel(",
            "gemini_protected_readback_ledger",
            "mtk_wdt_recovery_takeover(",
            "platform_driver",
            "of_device_id",
            "kfree(",
            "devm_kfree(",
        ):
            require(token not in added, f"disconnected observer gained effect: {token}")
        require(
            source.count("mt6797_a72_hotplug_snapshot(") == 1,
            "owner snapshot retry added",
        )
        require(
            "mt6797_psci_cpu_can_disable" not in added,
            "CPU-disable veto touched",
        )
    except (OSError, ValueError) as exc:
        print(f"cpu8_observer_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("cpu8_observer_source=pass")
    print("target_cpu=8")
    print("dispatch=smp_call_function_single-wait-0")
    print("dispatch_calls=1")
    print("controller_wait_timeout_ms=250")
    print("context_lifetime=binder-owned-one-shot")
    print("identity=exact-down-off-committed")
    print("retry_calls=0")
    print("synchronous_wait_1_calls=0")
    print("focused_kunit_cases=7")
    print("production_callers=0")
    print("device_tree_nodes=0")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
