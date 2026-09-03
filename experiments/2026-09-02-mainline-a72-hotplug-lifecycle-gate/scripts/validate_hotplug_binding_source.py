#!/usr/bin/env python3
"""Validate the exact production CPU9 hotplug binding composition."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


SOURCE = "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
INTERNAL = "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
PUBLIC = "include/linux/soc/mediatek/mt6797-a72-hotplug-binding.h"
PSCI = "arch/arm64/kernel/mt6797_psci.c"
ADMISSION = "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
KCONFIG = "drivers/soc/mediatek/Kconfig"
MAKEFILE = "drivers/soc/mediatek/Makefile"
TEST = "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c"


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
        config, re.MULTILINE | re.DOTALL,
    )
    require(match is not None, f"missing Kconfig symbol: {symbol}")
    return match.group("body")


def exact(text: str, token: str, count: int, message: str) -> None:
    observed = text.count(token)
    require(observed == count,
            f"{message}: expected {count}, observed {observed}")


def validate(root: Path, require_tests: bool) -> None:
    source = read(root, SOURCE)
    internal = read(root, INTERNAL)
    public = read(root, PUBLIC)
    psci = read(root, PSCI)
    admission = read(root, ADMISSION)
    kconfig = read(root, KCONFIG)
    makefile = read(root, MAKEFILE)
    binding = stanza(kconfig, "MTK_MT6797_A72_HOTPLUG_BINDING")

    for dependency in (
        "ARM64 && ARCH_MEDIATEK && HOTPLUG_CPU",
        "ARM64_MT6797_A72_P24_ADMISSION_HOOKS",
        "ARM64_MT6797_A72_P32_ROLLBACK",
        "MTK_MT6797_A72_ADMISSION_CONTROLLER",
        "MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER",
        "MTK_MT6797_A72_HOTPLUG_BINDER_CORE",
    ):
        require(f"depends on {dependency}" in binding,
                f"missing binding dependency: {dependency}")
    require("default n" in binding, "production binding default changed")
    require(
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING) += "
        "mt6797-a72-hotplug-binding.o" in makefile,
        "binding Makefile entry absent",
    )

    for token in (
        "MT6797_A72_HOTPLUG_BINDING_CPU9 9U",
        "MT6797_A72_HOTPLUG_BINDING_DOWN",
        "MT6797_A72_HOTPLUG_BINDING_RESTORE",
        "struct mt6797_a72_hotplug_private_ops",
        "u64 expected_task, unsigned int cpu",
    ):
        require(token in internal, f"private contract missing: {token}")
    for token in (
        "mt6797_a72_hotplug_binding_run",
        "mt6797_a72_hotplug_binding_down_preflight",
        "mt6797_a72_hotplug_binding_down_validate",
        "mt6797_a72_hotplug_binding_down_disable",
        "mt6797_a72_hotplug_binding_down_commit",
        "mt6797_a72_hotplug_binding_down_returned",
        "mt6797_a72_hotplug_binding_down_kill",
        "mt6797_a72_hotplug_binding_down_complete",
        "mt6797_a72_hotplug_binding_down_failed",
        "mt6797_a72_hotplug_binding_restore_preflight",
        "mt6797_a72_hotplug_binding_restore_validate",
        "mt6797_a72_hotplug_binding_restore_boot",
        "mt6797_a72_hotplug_binding_restore_secondary",
        "mt6797_a72_hotplug_binding_restore_complete",
        "mt6797_a72_hotplug_binding_restore_rollback",
    ):
        require(token in public, f"public callback contract missing: {token}")

    private_order = (
        "ops->lock(context);",
        "dev = ops->cpu_device(context, cpu);",
        "ops->task_identity(context) != expected_task",
        "!ops->cpu_online(context, cpu)",
        "!READ_ONCE(dev->offline_disabled)",
        "READ_ONCE(dev->offline)",
        "WRITE_ONCE(dev->offline_disabled, false);",
        "ret = ops->offline(context, dev);",
        "WRITE_ONCE(dev->offline_disabled, true);",
        "ops->unlock(context);",
    )
    positions = [source.find(token) for token in private_order]
    require(all(position >= 0 for position in positions),
            "private transition contract incomplete")
    require(positions == sorted(positions),
            "private transition lock/gate/restore order changed")
    exact(source, "ret = ops->offline(context, dev);", 1,
          "private offline call count changed")
    exact(source, "WRITE_ONCE(dev->offline_disabled, false);", 1,
          "private veto opening count changed")
    exact(source, "WRITE_ONCE(dev->offline_disabled, true);", 1,
          "private veto restoration count changed")
    exact(source, "ret = add_cpu(cpu);", 1,
          "restore add-CPU call count changed")

    for token in (
        "gemini_a72_hotplug_ledger_begin(session_id)",
        "gemini_a72_hotplug_ledger_checkpoint(binding->session_id,",
        "binding->next_stage = GEMINI_A72_HOTPLUG_BINDING_PARENT;",
        "stage == GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED",
        "binding->next_stage = GEMINI_A72_HOTPLUG_AFFINITY_OFF;",
        "GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED",
        "GEMINI_A72_HOTPLUG_CPU_OFF_RETURN_FAULT",
        "GEMINI_A72_HOTPLUG_RESTORED_SUCCESS",
        "phase != MT6797_A72_HOTPLUG_AFTER",
        "MT6797_A72_HOTPLUG_STAGE_OFF_COMMIT",
        "mt6797_a72_binder_parent_proof(proof)",
        "mt6797_a72_hotplug_snapshot_capture(&binding->source",
        "mt6797_a72_cpu8_observer_run(",
        "mt6797_a72_hotplug_prepare_down(",
        "mt6797_a72_hotplug_validate_down(&binding->down_transaction",
        "mt6797_a72_hotplug_commit_off(cpu)",
        "mt6797_a72_hotplug_prove_off(&binding->down_transaction",
        "mt6797_a72_hotplug_complete_down(&binding->down_transaction",
        "mt6797_a72_hotplug_prepare_restore(",
        "mt6797_a72_hotplug_begin_restore(restore",
        "mt6797_a72_hotplug_complete_restore(restore",
        "mt6797_a72_restore_executor_rollback(",
    ):
        require(token in source, f"production composition missing: {token}")
    exact(source, "mt6797_a72_binder_parent_proof(proof)", 1,
          "parent proof call count changed")
    exact(source, "gemini_a72_hotplug_ledger_begin(session_id)", 1,
          "record-4 begin count changed")
    exact(source, "mt6797_a72_cpu8_observer_run(", 1,
          "CPU8 observer call count changed")

    for stage in (
        "GEMINI_A72_HOTPLUG_BINDING_PARENT",
        "GEMINI_A72_HOTPLUG_DOWN_PREPARED",
        "GEMINI_A72_HOTPLUG_WATCHDOG_VALID",
        "GEMINI_A72_HOTPLUG_BASELINE_VALID",
        "GEMINI_A72_HOTPLUG_DOWN_VALID",
        "GEMINI_A72_HOTPLUG_TARGET_DISABLE_VALID",
        "GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED",
        "GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED",
        "GEMINI_A72_HOTPLUG_AFFINITY_OFF",
        "GEMINI_A72_HOTPLUG_POST_STATE_VALID",
        "GEMINI_A72_HOTPLUG_CPU8_RESPONSIVE",
        "GEMINI_A72_HOTPLUG_OFF_PROOF_ACCEPTED",
        "GEMINI_A72_HOTPLUG_DOWN_COMPLETE",
        "MT6797_A72_RESTORE_STAGE_PREPARED",
        "MT6797_A72_RESTORE_STAGE_CPU_ON_COMMITTED",
        "MT6797_A72_RESTORE_STAGE_SECONDARY_COMPLETE",
        "GEMINI_A72_HOTPLUG_RESTORE_COMPLETE",
    ):
        require(stage in source, f"ledger stage binding missing: {stage}")

    for token in (
        "return false;\n}\n#endif\n\nconst struct cpu_operations",
        "psci_ops.affinity_info(cpu_logical_map(cpu), level)",
        "mt6797_a72_hotplug_binding_down_commit(cpu)",
        "cpu_psci_ops.cpu_die(cpu);",
        "mt6797_a72_hotplug_binding_down_returned(",
        ".cpu_down_preflight = mt6797_psci_cpu_down_preflight",
        ".cpu_down_validate = mt6797_psci_cpu_down_validate",
        ".cpu_down_complete = mt6797_psci_cpu_down_complete",
        ".cpu_down_failed = mt6797_psci_cpu_down_failed",
        "mt6797_a72_hotplug_binding_restore_preflight(cpu, target)",
        "mt6797_a72_hotplug_binding_restore_validate(",
        "mt6797_a72_hotplug_binding_restore_boot(",
        "mt6797_a72_hotplug_binding_restore_secondary(cpu)",
        "mt6797_a72_hotplug_binding_restore_complete(cpu, target)",
        "mt6797_a72_hotplug_binding_restore_rollback(",
    ):
        require(token in psci, f"arm64 callback binding missing: {token}")
    die_sequence = (
        "if (mt6797_a72_hotplug_binding_down_commit(cpu))\n"
        "\t\t\tcpu_park_loop();\n"
        "\t\tcpu_psci_ops.cpu_die(cpu);\n"
        "\t\t(void)mt6797_a72_hotplug_binding_down_returned("
    )
    require(die_sequence in psci,
            "CPU_OFF commit/call/return-fault adjacency changed")
    exact(psci, "psci_ops.affinity_info(cpu_logical_map(cpu), level)", 1,
          "direct affinity call count changed")
    require("static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
            "{\n\treturn false;\n}" in psci,
            "public A72 disable veto opened")

    for token in (
        "struct device *platform;",
        "struct device *clock;",
        "struct device *bigidvfs;",
        "controller->platform = platform;",
        "controller->clock = clock;",
        "controller->bigidvfs = bigidvfs;",
        "ret = mt6797_a72_cpu9_admission_run(",
        "if (ret || !IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING))",
        "controller->cpu9.cpu9_transaction.identity.generation",
    ):
        require(token in admission, f"admission binding missing: {token}")
    exact(admission, "mt6797_a72_hotplug_binding_run(", 1,
          "hotplug binding trigger count changed")

    for token in (
        "psci_ops.", "cpu_psci_ops.", "arm_smccc", "readl(", "writel(",
        "ioremap", "mtk_wdt_recovery_", "platform_driver",
        "of_match_table", "module_platform_driver",
    ):
        require(token not in source,
                f"unexpected direct physical interface in glue: {token}")
    require(re.search(r"(?m)^\s*(?:return\s+)?remove_cpu\(", source) is None,
            "public remove_cpu bypass added to binding")
    require(re.search(r"(?m)^\s*(?:return\s+)?cpu_down\(", source) is None,
            "direct cpu_down bypass added to binding")

    if not require_tests:
        return
    test = read(root, TEST)
    test_config = stanza(kconfig,
                         "MTK_MT6797_A72_HOTPLUG_BINDING_KUNIT_TEST")
    require("depends on KUNIT=y" in test_config,
            "binding KUnit dependency missing")
    require("depends on MTK_MT6797_A72_HOTPLUG_BINDING" in test_config,
            "binding-under-test dependency missing")
    require("default n" in test_config,
            "binding KUnit default changed")
    require(
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING_KUNIT_TEST) += "
        "mt6797-a72-hotplug-binding-test.o" in makefile,
        "binding KUnit Makefile entry absent",
    )
    cases = re.findall(r"KUNIT_CASE\((hotplug_binding_[a-z_]+_test)\)",
                       test)
    require(cases == [
        "hotplug_binding_success_test",
        "hotplug_binding_wrong_task_test",
        "hotplug_binding_wrong_cpu_test",
        "hotplug_binding_missing_device_test",
        "hotplug_binding_public_gate_test",
        "hotplug_binding_already_offline_test",
        "hotplug_binding_target_offline_test",
        "hotplug_binding_failure_restores_gate_test",
        "hotplug_binding_route_test",
    ], f"KUnit case inventory changed: {cases}")
    require('.name = "mt6797-a72-hotplug-binding"' in test,
            "KUnit suite identity changed")
    for token in (
        "state->saw_private_gate = !dev->offline_disabled;",
        "KUNIT_EXPECT_TRUE(test, state->device.offline_disabled);",
        "state->offline_ret = -EIO;",
        "MT6797_A72_HOTPLUG_BINDING_DOWN, 8",
    ):
        require(token in test, f"KUnit contract missing: {token}")
    for token in (
        "device_offline(", "add_cpu(", "remove_cpu(", "cpu_down(",
        "psci_ops.", "cpu_psci_ops.", "readl(", "writel(", "ioremap",
    ):
        require(token not in test, f"physical call added to KUnit: {token}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--require-tests", action="store_true")
    args = parser.parse_args()
    validate(args.source_root.resolve(), args.require_tests)
    print("hotplug_binding_source=pass")
    print("public_cpu_can_disable=false")
    print("private_transition=device-hotplug-lock-scoped-cpu9-only")
    print("private_offline_calls=1")
    print("restore_add_cpu_calls=1")
    print("cpu_off_calls=one-direct-target-callback")
    print("affinity_info_calls=one-direct-level0")
    print("cpu_on_calls=one-restore-boot")
    print("successful_ledger_stages=1-7,9-17")
    print("cpu_off_return_stage=8-terminal-only")
    print("boot_candidate=false")
    print("device_action=none")
    if args.require_tests:
        print("focused_kunit_cases=9")


if __name__ == "__main__":
    main()
