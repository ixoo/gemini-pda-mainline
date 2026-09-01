#!/usr/bin/env python3
"""Validate the isolated retained-cluster CPU9 dispatch adapter."""

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
    psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text(
        encoding="utf-8")
    membership = (root / "arch/arm64/kernel/mt6797_a72_membership.c").read_text(
        encoding="utf-8")
    public = (root / "include/linux/soc/mediatek/"
              "mt6797-a72-cpu9-binder.h").read_text(encoding="utf-8")
    internal = (root / "drivers/soc/mediatek/"
                "mt6797-a72-cpu9-binder-internal.h").read_text(
                    encoding="utf-8")
    source = (root / "drivers/soc/mediatek/"
              "mt6797-a72-cpu9-binder.c").read_text(encoding="utf-8")
    tests = (root / "drivers/soc/mediatek/"
             "mt6797-a72-cpu9-binder-test.c").read_text(encoding="utf-8")
    production = public + internal + source

    exact(kconfig, "config MTK_MT6797_A72_CPU9_BINDER\n")
    exact(kconfig, "config MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST\n")
    require(
        "config MTK_MT6797_A72_CPU9_BINDER\n"
        "\tbool \"MediaTek MT6797 retained-cluster CPU9 dispatch binder\"\n"
        "\tdepends on ARM64 && ARCH_MEDIATEK\n"
        "\tdepends on MTK_MT6797_A72_DEFAULT_OFF_BINDER\n"
        "\tdepends on MTK_MT6797_A72_CPU9_EXECUTOR\n"
        "\tdepends on ARM64_MT6797_A72_P30E_WIRE" in kconfig,
        "CPU9 binder dependency chain")
    exact(makefile,
          "obj-$(CONFIG_MTK_MT6797_A72_CPU9_BINDER) += "
          "mt6797-a72-cpu9-binder.o")
    exact(makefile,
          "obj-$(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST) += "
          "mt6797-a72-cpu9-binder-test.o")

    for token in (
        "mt6797_a72_cpu9_binder_preflight(cpu, target)",
        "mt6797_a72_cpu9_binder_validate(",
        "mt6797_a72_cpu9_binder_failure(",
        "mt6797_a72_cpu9_binder_secondary_complete(cpu)",
        "mt6797_a72_cpu9_binder_complete(cpu, target)",
        "mt6797_a72_cpu9_binder_cpu_boot(",
    ):
        require(token in psci, f"PSCI CPU9 dispatch: {token}")
    for token in (
        "mt6797_a72_binder_preflight(cpu, target)",
        "mt6797_a72_binder_validate(cpu, tasks_frozen, target)",
        "mt6797_a72_binder_failure(cpu, error, &publish_p32)",
        "mt6797_a72_binder_secondary_complete(cpu)",
        "mt6797_a72_binder_complete(cpu, target)",
        "mt6797_a72_binder_cpu_boot(cpu, cpu_psci_ops.cpu_boot)",
    ):
        exact(psci, token, 1)
    require(
        "if (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)"
        in psci, "CPU9-only PSCI selection")
    require(
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER) && cpu == 9)\n"
        "\t\treturn mt6797_a72_cpu9_binder_cpu_boot(" in psci,
        "CPU9-only PSCI boot selection")
    exact(psci, "#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>")

    require("bool cpu8_on_ready;\n\tbool cpu9_on_ready;" in membership,
            "separate CPU8/CPU9 P30E readiness")
    require(
        "cpu9_on_ready = identity->operation ==\n"
        "\t\tARM64_LATE_CPU_STARTUP_OP_CPU9_UP" in membership,
        "CPU9 P30E operation readiness")
    for token in (
        "a72_owner.members == BIT(0)",
        "a72_owner.provider_state == MT6797_A72_PROVIDER_HELD",
        "a72_owner.active.p17_p18_published",
        "a72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_AVAILABLE",
        "!a72_owner.active.p27_valid",
        "!a72_owner.active.provider_acquire_valid",
        "!a72_owner.active.provider_abort_valid",
        "!a72_owner.active.p28_valid && !a72_owner.active.p29_valid",
        "!cpu8_on_ready && !cpu9_on_ready",
    ):
        require(token in membership, f"CPU9 P30E retained gate: {token}")
    exact(membership,
          "cpu8_on_ready = identity->operation ==\n"
          "\t\tARM64_LATE_CPU_STARTUP_OP_CPU8_UP")

    for token in (
        "request->cpu == MT6797_A72_CPU9_EXECUTOR_CPU9",
        "request->members == BIT(0)",
        "request->retained_mask == MT6797_A72_CPU9_RETAINED_REQUIRED",
        "request->cpu8_terminal_exact",
        "request->cpu8_membership_published",
        "request->provider_retained",
        "atomic_cmpxchg(&binder->prepared, 0, 1)",
        "atomic_cmpxchg(&binder->boot_claimed, 0, 1)",
        "gemini_cpu9_ledger_begin",
        "gemini_cpu9_ledger_checkpoint",
        "mt6797_a72_membership_preflight_cpu9",
        "mt6797_a72_membership_claim_cpu9",
        "mt6797_a72_membership_begin_cpu9_on",
        "ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP",
        "arm64_mt6797_a72_p30e_arm(cpu, &request)",
        "arm64_mt6797_a72_p30e_readback(cpu, &request, copy)",
        "binder->cpu_boot(cpu)",
        "smp_call_function_single(cpu, func, info, wait)",
        "mt6797_a72_membership_publish_cpu9_success",
        "mt6797_a72_membership_finalize_cpu9_success",
        "MT6797_A72_CPU9_FAULT_RETAIN_CPU8",
        "*publish_p32 = binder->result.terminal ==",
    ):
        require(token in production, f"CPU9 production binding: {token}")
    exact(source, "binder->cpu_boot(cpu)")
    exact(source, ".ledger_begin = gemini_cpu9_ledger_begin")
    exact(source, ".membership_begin_cpu_on = mt6797_a72_membership_begin_cpu9_on")
    exact(source, ".membership_publish_success =")
    exact(source, ".membership_finalize_success =")
    exact(source, "mt6797_a72_cpu9_executor_begin(")
    exact(source, "mt6797_a72_cpu9_executor_secondary(")
    exact(source, "mt6797_a72_cpu9_executor_complete(")
    exact(source, "mt6797_a72_cpu9_executor_fail(")
    require(
        "case MT6797_A72_CPU9_FAULT_RETAIN_CPU8:\n\t\treturn 0;" in source,
        "CPU9 failure retains owner/provider/CPU8 without inverse action")

    forbidden = (
        "add_cpu(", "cpu_up(", "cpu_down(", "remove_cpu(",
        "psci_cpu_off", "cpu_off(", "arm_smccc", "regmap_write(",
        "kernel_restart(", "watchdog_arm", "p27_acquire", "p27_release",
        "provider_acquire", "provider_release", "isolation_clear",
        "sram_enable", "dcm_update", "for (;;)" , "while (",
    )
    for token in forbidden:
        require(token not in production, f"forbidden production path: {token}")
        require(token not in tests, f"forbidden test path: {token}")

    exact(tests, "KUNIT_CASE(mt6797_cpu9_binder_", 8)
    exact(tests, "#include <linux/gemini_cpu9_transition_ledger.h>")
    exact(tests, "#include <linux/gemini_transition_ledger.h>")
    for case in (
        "success_test", "dispatch_guards_test", "prepare_guards_test",
        "claim_failure_test", "cpu_on_failures_test",
        "secondary_failure_test", "completion_failures_test",
        "failure_dispatch_test",
    ):
        exact(tests, f"KUNIT_CASE(mt6797_cpu9_binder_{case})")
    require('"mt6797-a72-cpu9-binder"' in tests, "focused suite name")
    require("binder.result.cpu_off_requests, 0U" in tests,
            "zero CPU_OFF assertions")
    require("binder.result.retries, 0U" in tests,
            "zero retry assertions")
    require("state.cpu_boot_calls, 1U" in tests,
            "one standard PSCI request assertion")
    require("state.ledger_checkpoint_calls, 11U" in tests,
            "ten checkpoints plus one terminal")

    return [
        "cpu9_dispatch_validation=pass",
        "cpu9_dispatch_psci=preflight-validate-boot-secondary-complete-failure",
        "cpu9_dispatch_p30e=cpu9-slot-operation-readback",
        "cpu9_dispatch_ledger=record1-independent-terminal",
        "cpu9_dispatch_membership=cpu9-specific",
        "cpu9_dispatch_cpu_requests=one-standard-psci-callback",
        "cpu9_dispatch_cpu8_binder_changes=0",
        "cpu9_dispatch_controller_callers=0",
        "cpu9_dispatch_add_cpu_callers=0",
        "cpu9_dispatch_cpu_off_paths=0",
        "cpu9_dispatch_retry_paths=0",
        "cpu9_dispatch_cluster_effect_paths=0",
        "focused_kunit_cases=8",
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    print("\n".join(validate(args.source_root)))
