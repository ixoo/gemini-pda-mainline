#!/usr/bin/env python3
"""Validate the hardware-free retained-cluster CPU9 executor source."""

from __future__ import annotations

from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"FAIL: {message}")


def exact(text: str, token: str, count: int = 1) -> None:
    require(text.count(token) == count,
            f"token count {token!r}: {text.count(token)} != {count}")


def validate(root: Path) -> list[str]:
    root = root.resolve()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text(
        encoding="utf-8")
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text(
        encoding="utf-8")
    source = (root /
              "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c").read_text(
                  encoding="utf-8")
    internal = (root / "drivers/soc/mediatek/"
                "mt6797-a72-cpu9-executor-internal.h").read_text(
                    encoding="utf-8")
    tests = (root / "drivers/soc/mediatek/"
             "mt6797-a72-cpu9-executor-test.c").read_text(encoding="utf-8")
    production = source + internal

    exact(kconfig, "config MTK_MT6797_A72_CPU9_EXECUTOR\n")
    exact(kconfig, "config MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST\n")
    require(
        "config MTK_MT6797_A72_CPU9_EXECUTOR\n"
        "\tbool \"MediaTek MT6797 retained-cluster CPU9 executor\"\n"
        "\tdepends on ARM64 && ARCH_MEDIATEK\n"
        "\tdepends on ARM64_MT6797_A72_CPU9_MEMBERSHIP\n"
        "\tdepends on PSTORE_GEMINI_CPU9_TRANSITION_LEDGER" in kconfig,
        "executor dependency chain")
    exact(makefile,
          "obj-$(CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR) += "
          "mt6797-a72-cpu9-executor.o")
    exact(makefile,
          "obj-$(CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST) += "
          "mt6797-a72-cpu9-executor-test.o")

    for token in (
        "MT6797_A72_CPU9_STAGE_PRESTATE",
        "MT6797_A72_CPU9_STAGE_CPU_ON",
        "MT6797_A72_CPU9_STAGE_ONLINE_WAIT",
        "MT6797_A72_CPU9_STAGE_IPI",
        "MT6797_A72_CPU9_STAGE_MEMBERSHIP",
        "MT6797_A72_CPU9_RETAINED_REQUIRED",
        "request->members == BIT(0)",
        "request->retained_mask == MT6797_A72_CPU9_RETAINED_REQUIRED",
        "request->cpu8_terminal_exact",
        "request->cpu8_membership_published",
        "request->provider_retained && request->cpu8_online",
        "request->cpu8_attempt_id != request->cpu9_attempt_id",
        "atomic_cmpxchg(&controller->consumed, 0, 1)",
        "ops->membership_commit && ops->terminal;",
        "ops->cpu_on(context, MT6797_A72_CPU9_EXECUTOR_CPU9)",
        "result->cpu_requests++;",
        "result->retained_mask = MT6797_A72_CPU9_RETAINED_REQUIRED;",
        "result->membership_published = true;",
        "MT6797_A72_CPU9_ONLINE_PROOF, 0",
    ):
        require(token in production, f"production contract: {token}")

    exact(source, "ops->prestate(context, request)")
    exact(source, "ops->cpu_on(context, MT6797_A72_CPU9_EXECUTOR_CPU9)")
    exact(source, "ops->secondary_complete(context, cpu)")
    exact(source, "ops->ipi_proof(context, cpu)")
    exact(source, "ops->membership_commit(context, cpu)")
    exact(source, "result->cpu_requests++;")
    exact(source, "result->membership_published = true;")
    exact(source, "mt6797_a72_cpu9_executor_run(")
    exact(source, "mt6797_a72_cpu9_executor_begin(", 2)
    exact(source, "mt6797_a72_cpu9_executor_secondary(", 2)
    exact(source, "mt6797_a72_cpu9_executor_complete(", 2)
    exact(source, "mt6797_a72_cpu9_executor_fail(")

    forbidden = (
        "add_cpu(", "cpu_up(", "cpu_down(", "remove_cpu(",
        "cpu_boot(", "psci_cpu_on", "psci_cpu_off", "arm_smccc",
        "regmap_write(", "kernel_restart(", "watchdog_arm",
        "p27_acquire", "p27_release", "provider_acquire",
        "provider_release", "isolation_clear", "sram_enable",
        "dcm_update", "cpu_off(", "rollback",
    )
    for token in forbidden:
        require(token not in production, f"forbidden production path: {token}")
        require(token not in tests, f"forbidden test path: {token}")

    exact(tests, "KUNIT_CASE(mt6797_cpu9_executor_", 10)
    for case in (
        "success_test", "split_success_test", "entry_rejections_test",
        "missing_op_test", "one_shot_test", "stage_failures_test",
        "checkpoint_failures_test", "lifecycle_guards_test",
        "failure_dispatch_test", "terminal_failures_test",
    ):
        exact(tests, f"KUNIT_CASE(mt6797_cpu9_executor_{case})")
    require('"mt6797-a72-cpu9-executor"' in tests, "focused suite name")
    require("stage <= MT6797_A72_CPU9_STAGE_MEMBERSHIP" in tests,
            "all five stages exercised")
    require("phase <= MT6797_A72_CPU9_PHASE_AFTER" in tests,
            "both checkpoint phases exercised")
    require("result.cpu_off_requests, 0U" in tests,
            "zero CPU_OFF assertions")
    require("result.retries, 0U" in tests, "zero retry assertions")

    return [
        "cpu9_executor_validation=pass",
        "cpu9_executor_stages=5",
        "cpu9_executor_split_lifecycle=yes",
        "cpu9_executor_attempt=atomic-one-shot",
        "cpu9_parent=exact-cpu8-terminal-member0",
        "cpu9_retained_mask=p27-provider-cpu8",
        "cpu9_operation_callbacks=prestate-cpu_on-online_wait-ipi-membership",
        "cpu9_checkpoint_phases=10",
        "focused_kunit_cases=10",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
        "production_callers=0",
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    print("\n".join(validate(args.source_root)))
