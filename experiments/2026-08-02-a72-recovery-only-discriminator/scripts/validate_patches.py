#!/usr/bin/env python3
"""Validate generated recovery-only Gemian patches and safety ordering."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EXPECTED_SERIES = [
    "0001-diagnostic-reject-A72-during-recovery-gate.patch",
    "0002-diagnostic-add-exclusive-TOPRGU-recovery-owner.patch",
    "0003-diagnostic-run-bounded-watchdog-pstore-gate.patch",
]
EXPECTED_PATHS = [
    {"arch/arm64/kernel/psci.c", "drivers/watchdog/mediatek/wdt/Kconfig"},
    {
        "drivers/watchdog/mediatek/include/ext_wd_drv.h",
        "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c",
    },
    {"drivers/watchdog/mediatek/wdk/wd_common_drv.c"},
]


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def added_text(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def changed_paths(patch: str) -> set[str]:
    return set(re.findall(r"^diff --git a/(\S+) b/\1$", patch, re.MULTILINE))


def ordered(text: str, tokens: list[str], scope: str) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        require(position >= 0, f"{scope}: missing or unordered {token!r}")
        cursor = position


def validate(patch_dir: Path) -> None:
    series = [
        line.strip()
        for line in (patch_dir / "series").read_text().splitlines()
        if line.strip()
    ]
    require(series == EXPECTED_SERIES, "generated series names/order changed")
    patches = [(patch_dir / name).read_text() for name in series]
    for index, (patch, expected_paths) in enumerate(
        zip(patches, EXPECTED_PATHS), 1
    ):
        require(
            re.match(r"From [0-9a-f]{40} Mon Sep 17 00:00:00 2001\n", patch)
            is not None,
            f"patch {index}: not git format-patch output",
        )
        require(
            "From: Gemini recovery experiment <noreply@gemini-recovery.invalid>"
            in patch,
            f"patch {index}: unexpected synthetic author",
        )
        require("Signed-off-by:" not in patch, f"patch {index}: synthetic sign-off")
        require(changed_paths(patch) == expected_paths, f"patch {index}: path drift")

    guard, owner, trigger = patches
    guard_added = added_text(guard)
    owner_added = added_text(owner)
    trigger_added = added_text(trigger)
    additions = "\n".join((guard_added, owner_added, trigger_added))

    for pattern, reason in {
        r"\bda9214_": "DA921x action",
        r"MT6797_SPM_BASE_ADDR|0x10006290|0x290": "A72 SPM action",
        r"BigiDVFS": "SRAM-LDO or iDVFS action",
        r"psci_ops\.cpu_on": "PSCI CPU-on action",
        r"dcm_mcusys_mp2_sync_dcm": "MP2 DCM action",
        r"\bcpu_up\s*\(|\bcpu_down\s*\(": "CPU online/offline action",
        r"\bmodule_param|\bdebugfs_create|\bproc_create|\bsysfs_create":
            "userspace control surface",
        r"\bpanic\s*\(|\bBUG(?:_ON)?\s*\(": "unbounded crash path",
    }.items():
        require(re.search(pattern, additions) is None, reason)

    for token in (
        "config MTK_A72_RECOVERY_DISCRIMINATOR",
        "depends on MTK_WATCHDOG && MTK_WD_KICKER",
        "depends on PSTORE && PSTORE_CONSOLE && PSTORE_RAM",
        "default n",
        "if (cpu == 8 || cpu == 9)",
        "return -EPERM",
    ):
        require(token in guard_added, f"guard patch: missing {token!r}")
    ordered(
        guard,
        [
            "static int cpu_psci_cpu_boot(unsigned int cpu)",
            "if (cpu == 8 || cpu == 9)",
            "return -EPERM",
        ],
        "CPU guard",
    )

    for token in (
        "static bool mtk_wdt_recovery_owned",
        "int mtk_wdt_recovery_arm(unsigned int timeout",
        "timeout != 12",
        "spin_lock(&rgu_reg_operation_spinlock)",
        "if (!toprgu_base)",
        "mtk_wdt_recovery_owned = true",
        "state->owned = 1",
        "MTK_WDT_MODE_ENABLE | MTK_WDT_MODE_EXTEN",
        "READ_ONCE(mtk_wdt_recovery_owned)",
    ):
        require(token in owner_added, f"owner patch: missing {token!r}")
    ordered(
        owner_added,
        [
            "spin_lock(&rgu_reg_operation_spinlock)",
            "if (!toprgu_base)",
            "state->mode_before = __raw_readl(MTK_WDT_MODE)",
            "mtk_wdt_recovery_owned = true",
            "state->owned = 1",
            "mt_reg_sync_writel(length | MTK_WDT_LENGTH_KEY",
            "mt_reg_sync_writel(mode, MTK_WDT_MODE)",
            "mt_reg_sync_writel(MTK_WDT_RESTART_KEY",
            "state->length_after = __raw_readl(MTK_WDT_LENGTH)",
            "state->mode_after = __raw_readl(MTK_WDT_MODE)",
        ],
        "TOPRGU owner",
    )
    require(owner_added.count("MTK_WDT_RESTART_KEY") == 1, "restart count changed")

    for token in (
        "static struct delayed_work recovery_discriminator_work",
        "spin_lock(&lock)",
        "!g_kicker_init || !g_wd_api || !g_wd_api->ready",
        "g_enable = 0",
        "ret = mtk_wdt_recovery_arm(12, &state)",
        "if (ret && !state.owned)",
        "g_enable = 1",
        "gemini-a72-recovery-v1 stage=armed timeout=12s a72=forbidden",
        "console_lock()",
        "console_unlock()",
        "schedule_delayed_work(&recovery_discriminator_work, 15 * HZ)",
    ):
        require(token in trigger_added, f"trigger patch: missing {token!r}")
    ordered(
        trigger_added,
        [
            "spin_lock(&lock)",
            "g_enable = 0",
            "mtk_wdt_recovery_arm(12, &state)",
            "if (ret && !state.owned)",
            "spin_unlock(&lock)",
            "stage=armed timeout=12s a72=forbidden",
            "console_lock()",
            "console_unlock()",
        ],
        "kicker handoff",
    )
    require(trigger_added.count("schedule_delayed_work") == 1, "trigger count changed")
    require(trigger_added.count("stage=armed") == 1, "terminal marker count changed")

    print("PASS: recovery-only patch series ownership and no-A72 contract")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", required=True, type=Path)
    args = parser.parse_args()
    validate(args.patch_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
