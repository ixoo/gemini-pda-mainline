#!/usr/bin/env python3
"""Validate the disconnected CPU9 restore executor and focused tests."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", source, re.S)
    require(match is not None, f"missing function: {name}")
    depth = 0
    for offset in range(match.end() - 1, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():offset + 1]
    raise ValueError(f"unterminated function: {name}")


def validate(root: Path, require_tests: bool) -> None:
    relative = Path("drivers/soc/mediatek")
    kconfig = (root / relative / "Kconfig").read_text(encoding="utf-8")
    makefile = (root / relative / "Makefile").read_text(encoding="utf-8")
    header = (root / relative /
              "mt6797-a72-restore-executor-internal.h").read_text(encoding="utf-8")
    source = (root / relative /
              "mt6797-a72-restore-executor.c").read_text(encoding="utf-8")

    require(kconfig.count("config MTK_MT6797_A72_RESTORE_EXECUTOR\n") == 1,
            "restore executor Kconfig missing or duplicated")
    block = kconfig.split(
        "config MTK_MT6797_A72_RESTORE_EXECUTOR\n", 1)[1]
    block = block.split("\nconfig ", 1)[0]
    for token in (
        "\tdepends on ARM64 && ARCH_MEDIATEK\n",
        "\tdepends on ARM64_MT6797_A72_CPU9_MEMBERSHIP\n",
        "\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR\n",
        "\tdefault n\n",
    ):
        require(token in block, f"restore Kconfig gate missing: {token.strip()}")
    require("\tselect " not in block, "restore executor selects a dependency")
    require(makefile.count(
        "obj-$(CONFIG_MTK_MT6797_A72_RESTORE_EXECUTOR) += "
        "mt6797-a72-restore-executor.o\n") == 1,
        "restore executor Makefile entry changed")

    for token in (
        "MT6797_A72_RESTORE_CPU8 8U",
        "MT6797_A72_RESTORE_CPU9 9U",
        "MT6797_A72_RESTORE_OFFLINE_MEMBERS BIT(0)",
        "MT6797_A72_RESTORE_ONLINE_MEMBERS (BIT(0) | BIT(1))",
        "MT6797_A72_RESTORE_OFFLINE_SYSTEM_MASK GENMASK_ULL(8, 0)",
        "MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK GENMASK_ULL(9, 0)",
        "MT6797_A72_RESTORE_STAGE_PREPARED = 14",
        "MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED = 15",
        "MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE = 16",
        "MT6797_A72_RESTORE_STAGE_FULL_COMPLETE = 17",
        "atomic_t consumed;", "atomic_t lifecycle;",
        "u64 controller_identity;", "u64 watchdog_identity;",
        "bool watchdog_owned;", "bool rollback_suppressed;",
        "int (*cpu_boot)(void *context, unsigned int cpu);",
        "int (*fail_restore)(void *context,",
    ):
        require(token in header, f"restore header contract missing: {token}")

    forbidden = (
        "psci_ops.", "cpu_psci_ops.", "arm_smccc", "cpu_up(", "cpu_down(",
        "add_cpu(", "remove_cpu(", "device_online(", "device_offline(",
        "readl(", "writel(", "ioread", "iowrite", "regmap_",
        "mtk_wdt_", "platform_driver", "of_match_table", "ioremap",
    )
    for token in forbidden:
        require(token not in source + header,
                f"restore executor connected a physical backend: {token}")
    require("retry" not in (source + header).lower(), "restore retry path added")

    parent = function_body(source, "mt6797_a72_restore_down_parent_valid")
    for token in (
        "MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN", "CPUHP_OFFLINE",
        "down_parent->valid == 1", "down_parent->completed == 1",
        "down_parent->off_committed == 1", "down_parent->off_proven == 1",
        "MT6797_A72_BUDGET_CONSUMED", "MT6797_A72_BUDGET_NONE",
        "proof->valid == 1", "proof->affinity_attempted == 1",
        "MT6797_A72_AFFINITY_LEVEL0", "MT6797_A72_AFFINITY_STATE_OFF",
        "proof->cpu9_per_core_off == 1", "proof->cpu8_responsive == 1",
        "proof->shared_state_unchanged == 1",
        "proof->online_mask_after == MT6797_A72_RESTORE_OFFLINE_MEMBERS",
        "memcmp(&proof->provider_identity",
    ):
        require(token in parent, f"exact retired down-parent gate missing: {token}")

    transaction = function_body(
        source, "mt6797_a72_restore_transaction_valid")
    for token in (
        "MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE", "CPUHP_ONLINE",
        "restore->identity.parent_generation ==",
        "restore->identity.parent_cookie ==",
        "restore->identity.generation != down_parent->identity.generation",
        "restore->identity.cookie != down_parent->identity.cookie",
        "memcmp(&restore->provider_identity",
        "restore->budgets.cpu_on == cpu_on", "restore->valid == 1",
        "restore->completed == completed", "restore->restored == completed",
    ):
        require(token in transaction, f"restore identity gate missing: {token}")

    request = function_body(source, "mt6797_a72_restore_request_valid")
    for token in (
        "request->cpu == MT6797_A72_RESTORE_CPU9",
        "request->target == CPUHP_ONLINE",
        "request->members == MT6797_A72_RESTORE_OFFLINE_MEMBERS",
        "request->online_mask == MT6797_A72_RESTORE_OFFLINE_MEMBERS",
        "MT6797_A72_RESTORE_OFFLINE_SYSTEM_MASK",
        "request->controller_identity", "request->watchdog_identity",
        "request->watchdog_owned",
    ):
        require(token in request, f"restore entry gate missing: {token}")
    require("request->controller_identity && request->watchdog_identity &&\n"
            "\t\trequest->watchdog_owned" in request,
            "controller/watchdog conjunction changed")

    preflight = function_body(source, "mt6797_a72_restore_executor_preflight")
    require("atomic_cmpxchg(&controller->consumed, 0, 1)" in preflight,
            "one-shot restore consumption changed")
    require(preflight.count("ops->prepare_restore(") == 1,
            "restore preparation call budget changed")
    require(preflight.count("MT6797_A72_RESTORE_STAGE_PREPARED") >= 2,
            "restore-prepared checkpoint missing")
    boot = function_body(source, "mt6797_a72_restore_executor_boot")
    require(boot.count("ops->begin_restore(") == 1,
            "restore begin call budget changed")
    require(boot.count("ops->cpu_boot(") == 1,
            "injected CPU_ON call budget changed")
    require(boot.count("MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED") >= 2,
            "CPU_ON committed checkpoint missing")
    checkpoint = boot.rindex("MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED")
    physical = boot.index("ops->cpu_boot(")
    require(checkpoint < physical,
            "CPU_ON committed checkpoint no longer precedes injected call")
    require("result->cpu_on_committed = true;" in boot,
            "CPU_ON ownership commit missing")

    secondary = function_body(
        source, "mt6797_a72_restore_executor_secondary_complete")
    require("cpu != MT6797_A72_RESTORE_CPU9" in secondary,
            "secondary CPU identity gate missing")
    require(secondary.count("MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE") >= 2,
            "secondary checkpoint missing")
    complete = function_body(source, "mt6797_a72_restore_executor_complete")
    for token in (
        "MT6797_A72_RESTORE_SECONDARY_RECORDED",
        "members != MT6797_A72_RESTORE_ONLINE_MEMBERS",
        "online_mask != MT6797_A72_RESTORE_ONLINE_MEMBERS",
        "system_online_mask != MT6797_A72_RESTORE_ONLINE_SYSTEM_MASK",
        "ops->complete_restore(", "ops->verify_terminal(",
        "MT6797_A72_RESTORE_STAGE_FULL_COMPLETE",
        "MT6797_A72_RESTORE_SUCCESS",
    ):
        require(token in complete, f"full restore terminal gate missing: {token}")
    require(complete.index("ops->complete_restore(") <
            complete.index("ops->verify_terminal(") <
            complete.index("MT6797_A72_RESTORE_SUCCESS"),
            "full completion/verification/terminal order changed")

    rollback = function_body(source, "mt6797_a72_restore_executor_rollback")
    require("*suppress_initial_rollback = true;" in rollback,
            "unrelated initial rollback is not suppressed")
    require("result->rollback_suppressed = true;" in rollback,
            "rollback suppression is not recorded")
    require("mt6797_a72_restore_fault" in rollback,
            "restore rollback is not routed to fail_restore")
    require(source.count("ops->checkpoint(") == 1,
            "checkpoint callback must have one shared call site")
    require(source.count("mt6797_a72_restore_checkpoint(") == 4,
            "preterminal checkpoint call count changed")
    require(source.count("ops->terminal(") == 1,
            "terminal callback must have one shared call site")

    if require_tests:
        test_source = (root / relative /
                       "mt6797-a72-restore-executor-test.c").read_text(
                           encoding="utf-8")
        require(kconfig.count(
            "config MTK_MT6797_A72_RESTORE_EXECUTOR_KUNIT_TEST\n") == 1,
            "restore test Kconfig missing or duplicated")
        require(makefile.count(
            "obj-$(CONFIG_MTK_MT6797_A72_RESTORE_EXECUTOR_KUNIT_TEST) += "
            "mt6797-a72-restore-executor-test.o\n") == 1,
            "restore test Makefile entry changed")
        require(test_source.count("KUNIT_CASE(restore_executor_") == 10,
                "focused restore KUnit count changed")
        for name in (
            "success", "entry_refusal", "prepare_failure",
            "identity_refusal", "validation_failure", "boot_failure",
            "rollback", "secondary_order", "checkpoint_failure",
            "completion_failure",
        ):
            require(f"KUNIT_CASE(restore_executor_{name}_test)" in test_source,
                    f"missing restore KUnit case: {name}")
        for token in forbidden:
            require(token not in test_source,
                    f"restore test connected physical backend: {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--require-tests", action="store_true")
    args = parser.parse_args()
    try:
        validate(args.source_root.resolve(), args.require_tests)
    except (OSError, ValueError) as exc:
        print(f"restore_executor_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("restore_executor_source=pass")
    print("target_cpu=9")
    print("cpu_on_call_sites=1")
    print("preterminal_checkpoints=3")
    print("terminal_members=0x3")
    print("rollback_suppresses_initial_p32=true")
    print("production_callers=0")
    print("physical_effect_calls=0")
    if args.require_tests:
        print("focused_kunit_cases=10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
