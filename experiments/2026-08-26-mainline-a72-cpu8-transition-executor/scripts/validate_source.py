#!/usr/bin/env python3
"""Validate generated CPU8 transition coordinator source without hardware."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    soc = root / "drivers/soc/mediatek"
    kconfig = (soc / "Kconfig").read_text(encoding="utf-8")
    makefile = (soc / "Makefile").read_text(encoding="utf-8")
    header = (soc / "mt6797-a72-transition-internal.h").read_text(
        encoding="utf-8"
    )
    source = (soc / "mt6797-a72-transition.c").read_text(encoding="utf-8")

    require(kconfig.count("config MTK_MT6797_A72_TRANSITION_EXECUTOR\n") == 1,
            "core Kconfig definition")
    require(makefile.count("mt6797-a72-transition.o\n") == 1,
            "core Makefile object")
    for token in (
        "MT6797_A72_TRANSITION_CPU8 8U",
        "MT6797_A72_TRANSITION_CPU9 9U",
        "MT6797_A72_TRANSITION_CPU_ON_WAIT_MS 10000U",
        "MT6797_A72_TRANSITION_RECOVERY_MS 15000U",
        "atomic_t consumed",
        "cpu_off_requests",
        "rollback_mask",
        "retained_mask",
        "watchdog_identity",
    ):
        require(token in header, f"header token: {token}")
    for token in (
        "atomic_cmpxchg(&controller->consumed, 0, 1)",
        "ops->watchdog_arm(context, MT6797_A72_TRANSITION_RECOVERY_MS",
        "ops->p27_acquire(context, &owned)",
        "ops->provider_acquire(context, &owned)",
        "result->isolation_attempted = true;",
        "ops->isolation_clear(context)",
        "ops->sram_enable(context)",
        "result->cpu_requests++;",
        "ops->cpu_on(context, MT6797_A72_TRANSITION_CPU8)",
        "MT6797_A72_TRANSITION_CPU_ON_WAIT_MS",
        "ops->ipi_proof(context, MT6797_A72_TRANSITION_CPU8)",
        "ops->dcm_update(context)",
        "MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO",
    ):
        require(token in source, f"source token: {token}")
    require(source.count("mt6797_a72_transition_checkpoint(") == 19,
            "nine before and nine after checkpoint calls plus definition")
    require(source.count("ops->cpu_on(") == 1, "one CPU request callback")
    require("cpu_off(" not in source, "no CPU_OFF callback")
    require("watchdog_cancel" not in source, "no watchdog cancellation")
    require(source.index("result->isolation_attempted = true;") <
            source.index("ops->isolation_clear(context)"),
            "isolation boundary recorded before callback")
    require(source.index("ops->watchdog_arm(") < source.index("ops->p27_acquire("),
            "watchdog before mutation")
    require(source.index("ops->provider_release(") < source.index("ops->p27_release("),
            "provider rollback before P27")

    forbidden = (
        "#include <linux/io.h>", "#include <linux/regmap.h>",
        "#include <linux/reset.h>", "#include <linux/regulator/",
        "#include <linux/arm-smccc.h>", "#include <linux/cpu.h>",
        "writel(", "regmap_write(", "reset_control_assert(",
        "reset_control_deassert(", "regulator_enable(", "arm_smccc_",
        "psci_", "cpu_up(", "cpu_down(", "smp_call_function",
        "platform_driver", "module_init(", "debugfs", "sysfs",
        "EXPORT_SYMBOL",
    )
    for token in forbidden:
        require(token not in source, f"forbidden physical/caller token: {token}")

    if args.phase == "tests":
        test_source = (soc / "mt6797-a72-transition-test.c").read_text(
            encoding="utf-8"
        )
        require(kconfig.count(
            "config MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST\n") == 1,
            "test Kconfig definition")
        require(makefile.count("mt6797-a72-transition-test.o\n") == 1,
                "test Makefile object")
        require(test_source.count("KUNIT_CASE(") == 7, "seven focused cases")
        for token in (
            "mt6797_transition_success_test",
            "mt6797_transition_entry_rejections_test",
            "mt6797_transition_missing_op_test",
            "mt6797_transition_one_shot_test",
            "mt6797_transition_stage_failures_test",
            "mt6797_transition_malformed_ownership_test",
            "mt6797_transition_rollback_faults_test",
            "stage < MT6797_A72_TRANSITION_STAGE_COUNT",
            "result.cpu_off_requests, 0U",
            "result.retries, 0U",
            "state.event_count, 27U",
            "MT6797_A72_TRANSITION_RECOVERY_MS",
            "MT6797_A72_TRANSITION_CPU_ON_WAIT_MS",
        ):
            require(token in test_source, f"test token: {token}")
        for token in forbidden:
            require(token not in test_source,
                    f"forbidden test physical token: {token}")
    else:
        require(not (soc / "mt6797-a72-transition-test.c").exists(),
                "test source absent from production phase")
        require("TRANSITION_EXECUTOR_KUNIT_TEST" not in kconfig,
                "test Kconfig absent from production phase")

    print(f"source_phase={args.phase}")
    print("transition_stages=9")
    print("success_checkpoints=18")
    print("cpu_requests_maximum=1")
    print("cpu_off_requests=0")
    print("retries=0")
    print("physical_backends=0")
    print("production_callers=0")
    print("device_action=none")
    print("source_validation=pass")


if __name__ == "__main__":
    main()
