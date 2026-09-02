#!/usr/bin/env python3
"""Validate the CPU9 CPU_ON substage ledger against its exact contract."""

from __future__ import annotations

import argparse
from pathlib import Path


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
    public = (
        root / "include/linux/gemini_cpu9_progress_ledger.h"
    ).read_text(encoding="utf-8")
    internal = (
        root / "fs/pstore/gemini_cpu9_progress_ledger_internal.h"
    ).read_text(encoding="utf-8")
    ledger = (
        root / "fs/pstore/gemini_cpu9_progress_ledger.c"
    ).read_text(encoding="utf-8")
    ledger_test = (
        root / "fs/pstore/gemini_cpu9_progress_ledger_test.c"
    ).read_text(encoding="utf-8")
    binder_internal = (
        root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h"
    ).read_text(encoding="utf-8")
    binder = (
        root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    ).read_text(encoding="utf-8")
    binder_test = (
        root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c"
    ).read_text(encoding="utf-8")
    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")

    exact(
        public,
        "enum gemini_cpu9_cpu_on_progress_stage {",
        1,
    )
    for token in (
        "GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE = 1",
        "GEMINI_CPU9_CPU_ON_PROGRESS_MEMBERSHIP_BEGIN",
        "GEMINI_CPU9_CPU_ON_PROGRESS_P30E_ARM",
        "GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT",
    ):
        exact(public, token, 1)
    exact(public, "gemini_cpu9_cpu_on_progress_checkpoint(", 2)
    exact(internal, "struct gemini_cpu9_cpu_on_progress_owner {", 1)
    exact(internal, "cpu9_cpu_on_progress_owner_begin(", 1)
    exact(internal, "cpu9_cpu_on_progress_owner_checkpoint(", 1)

    exact(
        ledger,
        "#define GEMINI_CPU9_CPU_ON_PROGRESS_BASE \\\n"
        "\t(GEMINI_CPU9_PROGRESS_CPU8_BASE + 3 * GEMINI_TRANSITION_LEDGER_SLOT_SIZE)",
        1,
    )
    exact(
        ledger,
        "#include <linux/gemini_cpu9_transition_ledger.h>",
        1,
        "CPU9 stage declarations included by progress owner",
    )
    exact(
        ledger_test,
        "#include <linux/gemini_cpu9_transition_ledger.h>",
        1,
        "CPU9 stage declarations included by progress tests",
    )
    exact(ledger, "static int cpu9_cpu_on_progress_validate_cpu9(", 1)
    exact(ledger, "int cpu9_cpu_on_progress_owner_begin(", 1)
    exact(ledger, "int cpu9_cpu_on_progress_owner_checkpoint(", 1)
    exact(ledger, "int gemini_cpu9_cpu_on_progress_checkpoint(", 1)
    exact(ledger, "EXPORT_SYMBOL_GPL(gemini_cpu9_cpu_on_progress_checkpoint);", 1)
    exact(
        ledger,
        "latest.phase != GEMINI_TRANSITION_LEDGER_BEFORE ||\n"
        "\t    latest.stage != GEMINI_CPU9_LEDGER_CPU_ON || latest.terminal",
        1,
        "exact CPU9 before-CPU_ON predecessor gate",
    )
    exact(
        ledger,
        "progress_slot = ioremap_wc(GEMINI_CPU9_CPU_ON_PROGRESS_BASE,",
        1,
    )
    exact(
        ledger,
        "GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE, 0);",
        1,
        "first substage checkpoint",
    )
    exact(
        ledger,
        "stage == GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT) {",
        1,
        "final substage sealing",
    )
    exact(
        ledger,
        "stage == GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT)) {",
        1,
        "final substage unmap",
    )
    for token in (
        "cpu_down(", "remove_cpu(", "psci_cpu_off", "cpu_off(",
        "arm_smccc", "regmap_write(", "kernel_restart(",
        "orderly_poweroff(",
    ):
        exact(ledger, token, 0, f"forbidden ledger token {token}")

    exact(
        binder_internal,
        "int (*cpu_on_progress_checkpoint)(u64 cpu9_attempt_id, u32 phase,",
        1,
    )
    exact(binder, "ops->cpu_on_progress_checkpoint", 1)
    exact(
        binder,
        ".cpu_on_progress_checkpoint =\n"
        "\t\t\tgemini_cpu9_cpu_on_progress_checkpoint,",
        1,
    )
    cpu_on = binder.split(
        "static int mt6797_a72_cpu9_binder_cpu_on(", 1
    )[1].split("static int mt6797_a72_cpu9_binder_secondary(", 1)[0]
    exact(cpu_on, "cpu_on_progress_checkpoint(", 8)
    exact(cpu_on, "binder->backend->p30e_prepare(", 1)
    exact(cpu_on, "binder->backend->membership_begin_cpu_on(", 1)
    exact(cpu_on, "binder->backend->p30e_arm(", 1)
    exact(cpu_on, "binder->cpu_boot(cpu)", 1)
    ordered(
        cpu_on,
        (
            "GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE);",
            "binder->backend->p30e_prepare(",
            "GEMINI_CPU9_CPU_ON_PROGRESS_MEMBERSHIP_BEGIN);",
            "binder->backend->membership_begin_cpu_on(",
            "GEMINI_CPU9_CPU_ON_PROGRESS_P30E_ARM);",
            "binder->backend->p30e_arm(",
            "GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT);",
            "binder->cpu_boot(cpu)",
        ),
        "CPU_ON effects and first boundary for each substage",
    )
    for token in (
        "cpu_down(", "remove_cpu(", "psci_cpu_off", "cpu_off(",
        "arm_smccc", "regmap_write(", "kernel_restart(",
        "orderly_poweroff(", "retry",
    ):
        exact(cpu_on, token, 0, f"forbidden CPU_ON token {token}")

    exact(ledger_test, "cpu9_cpu_on_progress_sequence_test", 2)
    exact(ledger_test, "cpu9_cpu_on_progress_gates_test", 2)
    exact(ledger_test, "cpu9_cpu_on_progress_ordering_test", 2)
    exact(ledger_test, "KUNIT_EXPECT_EQ(test, progress.writes, 82U);", 1)
    exact(
        binder_test,
        "mt6797_cpu9_binder_cpu_on_progress_failures_test",
        2,
    )
    exact(binder_test, "failure_call <= 8", 1)
    exact(kconfig, "eight ordered before/after boundaries", 1)
    exact(kconfig, "record 1 at exact BEFORE CPU_ON", 1)

    return [
        "cpu9_cpu_on_progress_validation=pass",
        "cpu9_predecessor=record1-before-CPU_ON",
        "cpu9_cpu_on_progress_lane=ramoops-record3-0x44413000",
        "cpu9_cpu_on_progress_boundaries=8",
        "cpu9_cpu_on_progress_stages=4",
        "record_commits_maximum=8",
        "word_writes_maximum=83",
        "existing_cpu_boot_calls=1",
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
