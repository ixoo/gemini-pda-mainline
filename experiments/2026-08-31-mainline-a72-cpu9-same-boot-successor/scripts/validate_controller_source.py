#!/usr/bin/env python3
"""Validate the candidate-only same-boot CPU9 controller."""

from __future__ import annotations

from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"FAIL: {message}")


def exact(text: str, token: str, count: int = 1) -> None:
    require(text.count(token) == count,
            f"token count {token!r}: {text.count(token)} != {count}")


def ordered(text: str, tokens: tuple[str, ...], message: str) -> None:
    positions = [text.find(token) for token in tokens]
    require(all(position >= 0 for position in positions),
            f"missing token in {message}")
    require(positions == sorted(positions), f"wrong order in {message}")


def validate(root: Path) -> list[str]:
    root = root.resolve()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text(
        encoding="utf-8")
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text(
        encoding="utf-8")
    admission = (root / "drivers/soc/mediatek/"
                 "mt6797-a72-admission-controller.c").read_text(
                     encoding="utf-8")
    public = (root / "include/linux/soc/mediatek/"
              "mt6797-a72-cpu9-binder.h").read_text(encoding="utf-8")
    binder_internal = (root / "drivers/soc/mediatek/"
                       "mt6797-a72-cpu9-binder-internal.h").read_text(
                           encoding="utf-8")
    binder = (root / "drivers/soc/mediatek/"
              "mt6797-a72-cpu9-binder.c").read_text(encoding="utf-8")
    binder_tests = (root / "drivers/soc/mediatek/"
                    "mt6797-a72-cpu9-binder-test.c").read_text(
                        encoding="utf-8")
    controller_internal = (root / "drivers/soc/mediatek/"
                           "mt6797-a72-cpu9-admission-controller-internal.h"
                           ).read_text(encoding="utf-8")
    controller = (root / "drivers/soc/mediatek/"
                  "mt6797-a72-cpu9-admission-controller.c").read_text(
                      encoding="utf-8")
    controller_tests = (root / "drivers/soc/mediatek/"
                        "mt6797-a72-cpu9-admission-controller-test.c"
                        ).read_text(encoding="utf-8")
    production = admission + public + binder_internal + binder + \
        controller_internal + controller

    exact(kconfig, "config MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER\n")
    exact(kconfig,
          "config MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER_KUNIT_TEST\n")
    require(
        "config MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER\n"
        "\tbool \"MediaTek MT6797 same-boot CPU9 admission controller\"\n"
        "\tdepends on MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER\n"
        "\tdepends on MTK_MT6797_A72_CPU9_BINDER" in kconfig,
        "live-trigger and CPU9-binder dependency chain")
    exact(makefile,
          "obj-$(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER) += "
          "mt6797-a72-cpu9-admission-controller.o")
    exact(makefile,
          "obj-$(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER_KUNIT_TEST) "
          "+= mt6797-a72-cpu9-admission-controller-test.o")

    for token in (
        "proof->cpu_requests == 1", "proof->lifecycle_terminal",
        "proof->terminal_exact", "proof->membership_published",
        "proof->p27_retained", "proof->provider_retained",
        "proof->cpu8_online", "!proof->cpu9_online",
        "transaction->identity.operation ==\n\t\t       "
        "ARM64_LATE_CPU_STARTUP_OP_CPU9_UP",
        "transaction->identity.target_cpu ==\n\t\t       "
        "MT6797_A72_CPU9_EXECUTOR_CPU9",
        "transaction->identity.target_mpidr == 0x201",
        "budgets->cpu_on == MT6797_A72_BUDGET_AVAILABLE",
        "budgets->preparation == MT6797_A72_BUDGET_NONE",
        "budgets->provider_acquire == MT6797_A72_BUDGET_NONE",
        "budgets->postprovider_preparation == MT6797_A72_BUDGET_NONE",
        "budgets->affinity == MT6797_A72_BUDGET_NONE",
        "budgets->provider_release == MT6797_A72_BUDGET_NONE",
        "budgets->provider_abort == MT6797_A72_BUDGET_NONE",
        "atomic_cmpxchg(&state->consumed, 0, 1)",
        "state->cpu9_transaction.identity.generation == proof.attempt_id",
        ".retained_mask = MT6797_A72_CPU9_RETAINED_REQUIRED",
        ".cpu8_terminal_exact = true",
        ".cpu8_membership_published = true",
        ".provider_retained = true",
        ".cpu8_online = true", ".cpu9_online = false",
        "state->cpu9_requests = 1",
        "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)",
    ):
        require(token in controller, f"controller contract: {token}")
    ordered(
        controller,
        ("state->cpu8_ret = ops->run_cpu8(context)",
         "ops->cpu8_proof(context, &proof)",
         "ready = ops->ready_token(context)",
         "ret = ops->derive_cpu9(",
         "ret = ops->publish_cpu9(",
         "ret = ops->prepare_cpu9(",
         "state->cpu9_requests = 1",
         "ret = ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)"),
        "same-task CPU8-to-CPU9 chain")
    exact(controller,
          "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)")

    require(
        "static int mt6797_a72_admission_run_cpu8(void *context)\n"
        "{\n\tstruct mt6797_a72_admission_controller *controller = context;\n"
        "\tint ret;\n\n"
        "\tret = mt6797_a72_admission_prepare(controller);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\treturn mt6797_a72_admission_run(&controller->state,\n"
        "\t\t\t\t\t&mt6797_a72_admission_production_ops,\n"
        "\t\t\t\t\tcontroller);\n}"
        in admission,
        "unchanged CPU8 controller body")
    for token in (
        "diagnostic.lifecycle != MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL",
        "diagnostic.terminal != MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF",
        "diagnostic.last_stage != MT6797_A72_TRANSITION_STAGE_MEMBERSHIP",
        "diagnostic.stage_errno || diagnostic.rollback_errno ||",
        "!diagnostic.watchdog_armed || !diagnostic.p27_owned",
        "diagnostic.retained_mask != MT6797_A72_CPU9_RETAINED_REQUIRED",
        "!cpu_online(8) || cpu_online(9)",
        ".run_cpu8 = mt6797_a72_admission_run_cpu8",
        ".derive_cpu9 = mt6797_a72_admission_derive_cpu9",
        ".publish_cpu9 = mt6797_a72_admission_publish_cpu9",
        ".prepare_cpu9 = mt6797_a72_admission_prepare_cpu9",
        ".add_cpu = mt6797_a72_admission_add_cpu",
        "mt6797_a72_cpu9_admission_run(",
        "mt6797_a72_admission_cpu9_status(controller, buf, len)",
    ):
        require(token in admission, f"production integration: {token}")
    exact(admission, "return add_cpu(cpu);")
    require("add_cpu(9)" not in admission,
            "CPU9 request remains target-bound through shared callback")

    exact(public, "#define MT6797_A72_CPU9_BINDER_DIAGNOSTIC_ABI 1U")
    exact(public, "struct mt6797_a72_cpu9_binder_diagnostic {")
    exact(public, "int mt6797_a72_cpu9_binder_diagnostic_snapshot(", 2)
    for token in (
        "snapshot->lifecycle = atomic_read_acquire(&binder->executor.lifecycle)",
        "snapshot->terminal = result->terminal",
        "snapshot->cpu_requests = result->cpu_requests",
        "snapshot->cpu_off_requests = result->cpu_off_requests",
        "snapshot->retries = result->retries",
        "snapshot->cpu8_attempt_id = binder->request.cpu8_attempt_id",
        "snapshot->cpu9_attempt_id = binder->request.cpu9_attempt_id",
        "atomic_read_acquire(&mt6797_a72_cpu9_binder.prepared)",
    ):
        require(token in binder, f"CPU9 diagnostic: {token}")
    exact(binder_internal, "mt6797_a72_cpu9_binder_test_diagnostic(")
    require("diagnostic.cpu_off_requests, 0U" in binder_tests,
            "binder diagnostic zero CPU_OFF assertion")
    require("diagnostic.retries, 0U" in binder_tests,
            "binder diagnostic zero retry assertion")

    exact(controller_tests,
          "KUNIT_CASE(mt6797_a72_cpu9_admission_", 8)
    for case in (
        "success_test", "invalid_repeat_test", "cpu8_failure_test",
        "proof_failures_test", "ready_derive_test",
        "publish_failure_test", "prepare_failure_test",
        "request_failure_test",
    ):
        exact(controller_tests,
              f"KUNIT_CASE(mt6797_a72_cpu9_admission_{case})")
    require('"mt6797-a72-cpu9-admission-controller"' in controller_tests,
            "focused controller suite name")
    require("context->controller.cpu_off_requests, 0U" in controller_tests,
            "zero CPU_OFF assertion")
    require("context->controller.retries, 0U" in controller_tests,
            "zero retry assertion")
    require("context->requested_cpu, 9U" in controller_tests,
            "one CPU9 target assertion")

    forbidden_calls = (
        "cpu_down(", "remove_cpu(", "psci_cpu_off", "cpu_off(",
        "arm_smccc", "regmap_write(", "kernel_restart(",
        "watchdog_arm(", "p27_acquire(", "p27_release(",
        "provider_acquire(", "provider_release(", "isolation_clear(",
        "sram_enable(", "dcm_update(", "for (;;)", "while (",
    )
    for token in forbidden_calls:
        require(token not in production, f"forbidden production path: {token}")
    exact(controller, "state->cpu_off_requests", 0)
    exact(controller, "state->retries", 0)

    return [
        "cpu9_controller_validation=pass",
        "cpu8_path=unchanged-core-one-request",
        "cpu8_gate=terminal-membership-p27-provider-cpu8-online",
        "cpu9_order=derive-publish-prepare-add_cpu",
        "cpu9_attempt=atomic-one-shot",
        "cpu9_request_count=one",
        "cpu9_failure=terminal-retain-cpu8-provider-cluster",
        "cpu9_combined_diagnostic=controller-and-binder",
        "cpu9_cpu_off_paths=0",
        "cpu9_retry_paths=0",
        "cpu9_cluster_effect_paths=0",
        "focused_kunit_cases=8",
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    print("\n".join(validate(args.source_root)))
