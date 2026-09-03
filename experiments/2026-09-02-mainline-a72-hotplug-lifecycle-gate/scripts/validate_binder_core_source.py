#!/usr/bin/env python3
"""Validate the disconnected one-task A72 hotplug-binder core source."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


CORE = "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c"
HEADER = "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h"
TEST = "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-test.c"
KCONFIG = "drivers/soc/mediatek/Kconfig"
MAKEFILE = "drivers/soc/mediatek/Makefile"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(root: Path, relative: str) -> str:
    path = root / relative
    require(path.is_file() and not path.is_symlink(),
            f"missing or unsafe source: {relative}")
    return path.read_text(encoding="utf-8")


def stanza(config: str, symbol: str) -> str:
    match = re.search(
        rf"^config {re.escape(symbol)}\n(?P<body>.*?)(?=^config |\Z)",
        config,
        re.MULTILINE | re.DOTALL,
    )
    require(match is not None, f"missing Kconfig symbol: {symbol}")
    return match.group("body")


def count(text: str, token: str, expected: int, message: str) -> None:
    observed = text.count(token)
    require(observed == expected,
            f"{message}: expected {expected}, observed {observed}")


def validate(root: Path, require_tests: bool) -> None:
    core = read(root, CORE)
    header = read(root, HEADER)
    kconfig = read(root, KCONFIG)
    makefile = read(root, MAKEFILE)
    core_config = stanza(kconfig, "MTK_MT6797_A72_HOTPLUG_BINDER_CORE")
    for dependency in (
        "ARM64 && ARCH_MEDIATEK",
        "MTK_MT6797_A72_DEFAULT_OFF_BINDER",
        "PSTORE_GEMINI_A72_HOTPLUG_LEDGER",
        "MTK_MT6797_A72_HOTPLUG_SNAPSHOT",
        "MTK_MT6797_A72_CPU8_OBSERVER",
        "MTK_MT6797_A72_HOTPLUG_EXECUTOR",
        "MTK_MT6797_A72_RESTORE_EXECUTOR",
    ):
        require(f"depends on {dependency}" in core_config,
                f"missing core dependency: {dependency}")
    require("default n" in core_config, "binder core default changed")
    require(
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDER_CORE) += "
        "mt6797-a72-hotplug-binder-core.o" in makefile,
        "binder core Makefile entry absent",
    )

    for token in (
        "MT6797_A72_HOTPLUG_BINDER_CPU9 9U",
        "MT6797_A72_HOTPLUG_BINDER_ENTRY_STAGE 1U",
        "MT6797_A72_HOTPLUG_BINDER_DOWN_STAGE 13U",
        "MT6797_A72_HOTPLUG_BINDER_RESTORE_STAGE 17U",
        "MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT = 1",
        "MT6797_A72_HOTPLUG_BINDER_FAULT_POSTCOMMIT = 3",
        "MT6797_A72_HOTPLUG_BINDER_RESTORE_FAULT = 4",
        "MT6797_A72_HOTPLUG_BINDER_RESTORED_SUCCESS = 5",
        "u64 (*current_task_identity)(void *context);",
        "int (*parent_proof)(void *context,",
        "int (*ledger_begin)(void *context, u64 session_id);",
        "int (*remove_cpu)(void *context, unsigned int cpu,",
        "int (*add_cpu_restore)(",
    ):
        require(token in header, f"header contract missing: {token}")

    for token in (
        "proof->online_mask != MT6797_A72_BINDER_PARENT_ONLINE_MASK",
        "proof->online_count != 10",
        "proof->watchdog_age_ns == age",
        "age <= MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL",
        "ops->current_task_identity(context) != request->task_identity",
        "atomic_cmpxchg(&controller->consumed, 0, 1)",
        "mt6797_a72_restore_down_parent_valid(",
        "down->identity.parent_generation == parent->cpu9.generation",
        "down->identity.parent_cookie == parent->cpu9.cookie",
        "down->provider_identity.generation == parent->provider_generation",
        "down->provider_identity.cookie == parent->provider_cookie",
        "mt6797_a72_restore_transaction_valid(",
        "MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT",
        "MT6797_A72_HOTPLUG_BINDER_FAULT_POSTCOMMIT",
        "MT6797_A72_HOTPLUG_BINDER_RESTORE_FAULT",
        "MT6797_A72_HOTPLUG_BINDER_RESTORED_SUCCESS",
    ):
        require(token in core, f"core contract missing: {token}")
    count(core, "ops->current_task_identity(context)", 1,
          "current-task call count changed")
    count(core, "ops->parent_proof(context,", 1,
          "parent-proof call count changed")
    count(core, "ops->ledger_begin(context,", 1,
          "ledger-begin call count changed")
    count(core, "ops->remove_cpu(context,", 1,
          "remove-CPU call count changed")
    count(core, "ops->add_cpu_restore(context,", 1,
          "restore-add-CPU call count changed")
    count(core, "result->retries", 0, "retry mutation added")
    require("result->remove_cpu_calls++;" in core,
            "remove-CPU accounting missing")
    require("result->restore_add_cpu_calls++;" in core,
            "restore-add accounting missing")

    forbidden = (
        "\n\tadd_cpu(", "\n\tremove_cpu(", "\n\tcpu_up(",
        "\n\tcpu_down(",
        "psci_ops.", "cpu_psci_ops.", "arm_smccc", "readl(", "writel(",
        "ioremap", "smp_call_function_single", "wait_for_completion",
        "mtk_wdt_recovery_", "gemini_a72_hotplug_ledger_owner_",
        "platform_driver", "module_platform_driver", "of_match_table",
    )
    for token in forbidden:
        require(token not in core, f"physical or production call added: {token}")

    if not require_tests:
        return
    test = read(root, TEST)
    test_config = stanza(
        kconfig, "MTK_MT6797_A72_HOTPLUG_BINDER_CORE_KUNIT_TEST"
    )
    require("depends on KUNIT=y" in test_config,
            "KUnit dependency missing")
    require("depends on MTK_MT6797_A72_HOTPLUG_BINDER_CORE" in test_config,
            "binder-core KUnit dependency missing")
    require("default n" in test_config, "binder KUnit default changed")
    require(
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDER_CORE_KUNIT_TEST) += "
        "mt6797-a72-hotplug-binder-core-test.o" in makefile,
        "binder core test Makefile entry absent",
    )
    cases = re.findall(r"KUNIT_CASE\((binder_core_[a-z_]+_test)\)", test)
    require(cases == [
        "binder_core_success_test",
        "binder_core_task_refusal_test",
        "binder_core_parent_refusal_test",
        "binder_core_ledger_refusal_test",
        "binder_core_down_failure_test",
        "binder_core_restore_failure_test",
        "binder_core_checkpoint_failure_test",
        "binder_core_terminal_failure_test",
        "binder_core_one_shot_test",
    ], f"KUnit case inventory changed: {cases}")
    require('.name = "mt6797-a72-hotplug-binder-core"' in test,
            "KUnit suite identity changed")
    for token in (
        "BINDER_CORE_TASK = 1",
        "BINDER_CORE_TERMINAL",
        "KUNIT_EXPECT_MEMEQ(test, state->order, expected, sizeof(expected))",
        "BINDER_CORE_FAIL_REMOVE_PRECOMMIT",
        "BINDER_CORE_FAIL_REMOVE_POSTCOMMIT",
        "BINDER_CORE_FAIL_RESTORE_CHECKPOINT",
        "unbound->down.identity.parent_cookie++;",
    ):
        require(token in test, f"KUnit contract missing: {token}")
    for token in forbidden:
        require(token not in test, f"test physical call added: {token}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--require-tests", action="store_true")
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate(root, args.require_tests)
    print("binder_core_source=pass")
    print("target_cpu=9")
    print("ordered_requests=remove9,add9-restore")
    print("parent_proof_calls=1")
    print("ledger_begin_calls=1")
    print("remove_cpu_calls=1")
    print("restore_add_cpu_calls=1")
    print("retries=0")
    print("production_callers=0")
    print("physical_effect_calls=0")
    if args.require_tests:
        print("focused_kunit_cases=9")


if __name__ == "__main__":
    main()
