#!/usr/bin/env python3
"""Validate exact CPU9 progress wiring and its injected tests."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(text: str, token: str, label: str) -> None:
    if token not in text:
        raise ValueError(f"missing {label}: {token}")


def exact(text: str, token: str, count: int, label: str | None = None) -> None:
    actual = text.count(token)
    if actual != count:
        raise ValueError(
            f"{label or token} count changed: expected {count}, got {actual}"
        )


def ordered(text: str, tokens: tuple[str, ...], label: str) -> None:
    positions = [text.index(token) for token in tokens]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError(f"{label} ordering changed")


def validate(root: Path) -> list[str]:
    base = root / "drivers/soc/mediatek"
    kconfig = (base / "Kconfig").read_text(encoding="utf-8")
    production = (base / "mt6797-a72-admission-controller.c").read_text(
        encoding="utf-8"
    )
    controller = (base / "mt6797-a72-cpu9-admission-controller.c").read_text(
        encoding="utf-8"
    )
    controller_header = (
        base / "mt6797-a72-cpu9-admission-controller-internal.h"
    ).read_text(encoding="utf-8")
    controller_test = (
        base / "mt6797-a72-cpu9-admission-controller-test.c"
    ).read_text(encoding="utf-8")
    binder = (base / "mt6797-a72-cpu9-binder.c").read_text(encoding="utf-8")
    binder_header = (base / "mt6797-a72-cpu9-binder-internal.h").read_text(
        encoding="utf-8"
    )
    binder_test = (base / "mt6797-a72-cpu9-binder-test.c").read_text(
        encoding="utf-8"
    )

    exact(
        kconfig,
        "depends on PSTORE_GEMINI_ADMISSION_TRACE=y || "
        "PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y",
        1,
        "CPU8 trace-or-progress dependency",
    )
    exact(
        kconfig,
        "depends on PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y",
        1,
        "progress Kconfig dependencies",
    )
    require(
        kconfig,
        "Ten\n\t  ordered retained progress boundaries cover the pre-ledger path.",
        "CPU9 progress help",
    )

    for token in (
        "gemini_cpu9_progress_begin(cpu8_attempt_id)",
        "gemini_cpu9_progress_checkpoint(cpu8_attempt_id, stage)",
        ".progress_begin = mt6797_a72_admission_progress_begin",
        ".progress_checkpoint = mt6797_a72_admission_progress_checkpoint",
        "cpu9_progress_stage=%u cpu9_progress_ret=%d",
    ):
        exact(production, token, 1)

    for token in (
        "int (*progress_begin)(void *context, u64 cpu8_attempt_id);",
        "int (*progress_checkpoint)(void *context, u64 cpu8_attempt_id,",
        "MT6797_A72_CPU9_ADMISSION_FAILURE_PROGRESS",
        "u32 progress_stage;",
        "int progress_ret;",
        "int cpu9_request_ret;",
    ):
        exact(controller_header, token, 1)

    exact(controller, "ops->progress_begin(context, cpu8_attempt_id)", 1)
    exact(controller, "ops->progress_checkpoint(context, cpu8_attempt_id, stage)", 1)
    exact(controller, "GEMINI_CPU9_PROGRESS_CPU8_PROOF, true", 1)
    exact(controller, "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)", 1)
    exact(controller, "state->cpu9_requests = 1;", 1)
    controller_stages = (
        "GEMINI_CPU9_PROGRESS_CPU8_PROOF",
        "GEMINI_CPU9_PROGRESS_READY_TOKEN",
        "GEMINI_CPU9_PROGRESS_DERIVE",
        "GEMINI_CPU9_PROGRESS_PUBLISH",
        "GEMINI_CPU9_PROGRESS_PREPARE",
        "GEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH",
        "GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN",
    )
    for token in controller_stages:
        exact(controller, token, 1)
    for token in (
        "GEMINI_CPU9_PROGRESS_BINDER_ENTRY",
        "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER",
        "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN",
    ):
        exact(controller, token, 0)
    ordered(
        controller,
        (
            *controller_stages[:6],
            "state->cpu9_requests = 1;",
            "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)",
            controller_stages[6],
        ),
        "controller progress",
    )

    exact(
        binder_header,
        "int (*progress_checkpoint)(u64 cpu8_attempt_id, u32 stage);",
        1,
    )
    for token in (
        ".progress_checkpoint = gemini_cpu9_progress_checkpoint",
        "GEMINI_CPU9_PROGRESS_BINDER_ENTRY",
        "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER",
        "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN",
    ):
        exact(binder, token, 1)
    ordered(
        binder,
        (
            "GEMINI_CPU9_PROGRESS_BINDER_ENTRY",
            "binder->backend->membership_claim(&binder->transaction)",
        ),
        "binder entry",
    )
    ordered(
        binder,
        (
            "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER",
            "binder->backend->ledger_begin(",
            "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN",
            "binder->backend->ledger_checkpoint(",
        ),
        "ledger admission",
    )

    for token in (
        "MT6797_CPU9_ADMISSION_FAIL_PROGRESS",
        "mt6797_a72_cpu9_admission_test_progress_begin",
        "mt6797_a72_cpu9_admission_test_progress_checkpoint",
        "mt6797_a72_cpu9_admission_progress_failures_test",
        "stage <= GEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH",
        "context->controller.cpu9_requests, 0U",
        "context->progress_stages[ret]",
    ):
        require(controller_test, token, "controller progress test")
    exact(
        controller_test,
        "KUNIT_CASE(mt6797_a72_cpu9_admission_progress_failures_test)",
        1,
    )
    for stage in range(1, 11):
        require(
            controller_test,
            "(u32)ret + 1" if stage == 1 else "progress_stages",
            "controller ten-stage assertion",
        )

    for token in (
        "MT6797_CPU9_BINDER_FAIL_PROGRESS",
        "mt6797_cpu9_binder_test_progress_checkpoint",
        "mt6797_cpu9_binder_progress_failures_test",
        "state.progress_checkpoint_calls, 3U",
        "GEMINI_CPU9_PROGRESS_BINDER_ENTRY",
        "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER",
        "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN",
        "state.cpu_boot_calls, 0U",
    ):
        require(binder_test, token, "binder progress test")
    exact(
        binder_test,
        "KUNIT_CASE(mt6797_cpu9_binder_progress_failures_test)",
        1,
    )

    joined = "\n".join(
        (production, controller, controller_header, controller_test,
         binder, binder_header, binder_test)
    )
    for token in (
        "cpu_down(", "remove_cpu(", "psci_cpu_off", "cpu_off(",
        "arm_smccc", "regmap_write(", "kernel_restart(",
        "orderly_poweroff(",
    ):
        exact(joined, token, 0, f"forbidden wiring token {token}")

    return [
        "cpu9_progress_wiring_validation=pass",
        "controller_progress_stages=1-6,10",
        "binder_progress_stages=7-9",
        "progress_attempt_identity=cpu8-attempt",
        "pre_dispatch_progress_fail_closed=6",
        "focused_controller_kunit_cases=9",
        "focused_binder_kunit_cases=9",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    for marker in validate(args.source_root.resolve()):
        print(marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
