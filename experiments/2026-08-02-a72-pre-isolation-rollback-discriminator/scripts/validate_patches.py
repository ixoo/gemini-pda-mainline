#!/usr/bin/env python3
"""Validate generated pre-isolation rollback patches and safety ordering."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EXPECTED_SERIES = [
    "0001-diagnostic-extend-A72-observer-rollback-ABI.patch",
    "0002-diagnostic-add-exact-A72-rollback-owner-operations.patch",
    "0003-diagnostic-stop-and-unwind-first-CPU8-pre-isolation.patch",
]

EXPECTED_PATHS = [
    {
        "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c",
        "include/linux/mt6797_a72_transition_observer.h",
    },
    {
        "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c",
        "drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c",
        "drivers/misc/mediatek/base/power/spm_v2/mt_spm.c",
        "drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c",
        "drivers/misc/mediatek/power/mt6797/da9214.c",
        "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c",
        "include/linux/mt6797_a72_transition_observer.h",
    },
    {
        "arch/arm64/kernel/psci.c",
        "drivers/misc/mediatek/base/power/Kconfig",
    },
]


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_tokens(text: str, tokens: list[str], scope: str) -> None:
    for token in tokens:
        require(token in text, f"{scope}: missing {token!r}")


def ordered(text: str, tokens: list[str], scope: str) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        require(position >= 0, f"{scope}: missing ordered token {token!r}")
        cursor = position


def added_text(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def changed_paths(patch: str) -> set[str]:
    return set(
        re.findall(r"^diff --git a/(\S+) b/\1$", patch, flags=re.MULTILINE)
    )


def validate(patch_dir: Path, source: Path | None = None) -> None:
    series_path = patch_dir / "series"
    require(series_path.is_file(), "missing generated series")
    series = [line.strip() for line in series_path.read_text().splitlines() if line]
    require(series == EXPECTED_SERIES, "generated series names/order changed")
    paths = [patch_dir / name for name in series]
    require(all(path.is_file() for path in paths), "generated patch missing")
    patches = [path.read_text() for path in paths]

    for index, (path, patch, expected_paths) in enumerate(
        zip(paths, patches, EXPECTED_PATHS), 1
    ):
        require(
            re.search(r"\AFrom [0-9a-f]{40} Mon Sep 17 00:00:00 2001\n", patch)
            is not None,
            f"patch {index}: not git format-patch output",
        )
        require(
            "From: Gemini A72 experiment <noreply@gemini-a72.invalid>" in patch,
            f"patch {index}: unexpected experiment author",
        )
        require("Signed-off-by:" not in patch, f"patch {index}: synthetic sign-off")
        require(changed_paths(patch) == expected_paths, f"patch {index}: path drift")

    additions = "\n".join(added_text(patch) for patch in patches)
    forbidden_patterns = {
        r"\bBUG(?:_ON)?\s*\(": "new BUG path",
        r"\bWARN(?:_ON(?:_ONCE)?)?\s*\(": "new WARN path",
        r"\bpanic\s*\(": "new panic path",
        r"\bmodule_param": "module control",
        r"\bdebugfs_create": "debugfs surface",
        r"\bcopy_from_user\b": "userspace input",
        r"\bSEC_BIGIDVFS_WRITE\b": "secure write",
        r"\bpsci_ops\.cpu_on\s*\(": "new PSCI call",
        r"\bdcm_mcusys_mp2_sync_dcm\s*\(": "new DCM action",
        r"\bBigiDVFS(?:Enable|SRAM)": "new iDVFS/SRAM action",
        r"\budelay\s*\(240\)": "SRAM interval crossed",
        r"\bMT6797_A72_PHASE_SPM_ISOLATION_CLEAR\b": "isolation boundary crossed",
        r"\.(?:write|unlocked_ioctl|compat_ioctl)\s*=": "writable ABI",
    }
    for pattern, reason in forbidden_patterns.items():
        require(re.search(pattern, additions) is None, reason)

    abi, owners, orchestrator = patches
    require_tokens(
        abi,
        [
            "MT6797_A72_PHASE_PREISO_INJECT_STOP",
            "MT6797_A72_PHASE_ROLLBACK_BUCK_DISABLE",
            "MT6797_A72_PHASE_ROLLBACK_SPM_RESET",
            "MT6797_A72_PHASE_ROLLBACK_PWRAP_DEASSERT",
            "MT6797_A72_PHASE_ROLLBACK_FINAL",
            "MT6797_A72_ROLLBACK_ROLLED_BACK",
            "MT6797_A72_ROLLBACK_FAULT_RETAIN",
            "MT6797_A72_ROLLBACK_REJECTED_PRESTATE",
            'return "rolled-back"',
            'return "fault-retain"',
            'return "rejected-prestate"',
            "abi=mt6797-a72-transition-observer-v3",
        ],
        "ABI patch",
    )
    require(
        added_text(abi).count("MT6797_A72_PHASE_ROLLBACK_FINAL") >= 3,
        "ABI terminal phase is not wired through recorder",
    )

    require_tokens(
        owners,
        [
            "int da9214_a72_diag_compare_update",
            "mutex_lock(&da9214_i2c_access)",
            "snapshot.page_before != 0x80",
            "snapshot.buck_vsel != 0x46",
            "requested != expected",
            "snapshot.page_after != 0x80",
            "int mt6797_a72_diag_spm_compare_update",
            "spin_lock_irqsave(&__spm_lock, flags)",
            "mutation.before != expected",
            "mutation.after != requested",
            "int mt6797_a72_diag_toprgu_compare_update",
            "spin_lock(&rgu_reg_operation_spinlock)",
            "!!(value & snapshot.mask) != expected",
            "!!(snapshot.after & snapshot.mask) != requested",
            "bool mt6797_a72_diag_secure_zero",
            "bool mt6797_a72_diag_dcm_zero",
            "int mt6797_a72_diag_clock_capture",
            "spin_trylock_irqsave(&g_mt6797_0x1001AXXX_lock, flags)",
            "return snapshot->status",
        ],
        "owner patch",
    )
    require(
        added_text(owners).count("snapshot.buck_vsel != 0x46") == 2,
        "DA921x VSEL entry/final equality count changed",
    )
    ordered(
        owners,
        [
            "mutex_lock(&da9214_i2c_access)",
            "snapshot.page_before != 0x80",
            "!!(buck & 1) != expected",
            "requested != expected",
            "!!(buck & 1) != requested",
            "snapshot.page_after != 0x80",
        ],
        "DA921x compare/update/readback order",
    )

    require_tokens(
        orchestrator,
        [
            "config MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR",
            "depends on MTK_A72_TRANSITION_OBSERVER",
            "default n",
            "static atomic_t mt6797_a72_preiso_attempted = ATOMIC_INIT(0)",
            "cpu != 8 || atomic_xchg(&mt6797_a72_preiso_attempted, 1)",
            "bool prestate_bad = false",
            "prestate_bad |= g_cl2_online || cpu_online(8) || cpu_online(9)",
            "cpu_online(8) || cpu_online(9)",
            "MT6797_A72_PHASE_POWER_ON_PRE, &entry_clock",
            "0x00010132, 0x00010133",
            "MT6797_A72_PHASE_PREISO_INJECT_STOP",
            "MT6797_A72_PHASE_ROLLBACK_BUCK_DISABLE",
            "MT6797_A72_PHASE_ROLLBACK_SPM_RESET",
            "MT6797_A72_PHASE_ROLLBACK_PWRAP_DEASSERT",
            "MT6797_A72_ROLLBACK_REJECTED_PRESTATE",
            "entry_clock.pll_con1 != final_clock.pll_con1",
            "entry_clock.muxsel != final_clock.muxsel",
            "entry_clock.ckdiv != final_clock.ckdiv",
            "goto mt6797_a72_boot_out",
            "mt6797_a72_boot_out:",
            "gic_clear_primask();",
        ],
        "orchestrator patch",
    )
    additions3 = added_text(orchestrator)
    require(additions3.count("udelay(1000)") == 1, "settle delay count changed")
    require(additions3.count("cpu == 9") == 1, "CPU9 rejection count changed")
    require(
        additions3.count("if (bypass_boot > 0) {") == 1,
        "diagnostic bypass rejection count changed",
    )
    require(
        additions3.count("goto mt6797_a72_boot_out") == 3,
        "caller exit count changed",
    )
    require(
        additions3.count("prestate_bad |= !!ret;") == 5,
        "complete entry-gate accumulation count changed",
    )
    require(
        additions3.count("fault |= !!ret;") == 5,
        "complete final-gate accumulation count changed",
    )
    ordered(
        orchestrator,
        [
            "MT6797_A72_PHASE_SPM_RESET_RELEASE",
            "MT6797_A72_PHASE_TOPRGU_ASSERT",
            "MT6797_A72_PHASE_BUCK_ENABLE",
            "udelay(1000)",
            "MT6797_A72_PHASE_BUCK_ENABLE_SETTLED",
            "MT6797_A72_PHASE_PREISO_INJECT_STOP",
            "rollback:",
            "MT6797_A72_PHASE_ROLLBACK_BUCK_DISABLE",
            "MT6797_A72_PHASE_ROLLBACK_SPM_RESET",
            "MT6797_A72_PHASE_ROLLBACK_PWRAP_DEASSERT",
            "MT6797_A72_PHASE_ROLLBACK_FINAL",
        ],
        "forward/injection/rollback order",
    )
    ordered(
        orchestrator,
        [
            "prestate_bad |= g_cl2_online",
            "MT6797_A72_PHASE_POWER_ON_PRE, &entry_clock",
            "prestate_bad |= !mt6797_a72_diag_secure_zero",
            "prestate_bad |= !mt6797_a72_diag_dcm_zero",
            "da9214_a72_diag_compare_update(cpu, false, false",
            "0x00010132, 0x00010132",
            "0x290, 0x2, 0x2",
            "mt6797_a72_diag_toprgu_compare_update(cpu, false, false",
            "if (prestate_bad)",
        ],
        "complete pre-state capture order",
    )
    ordered(
        orchestrator,
        [
            "goto mt6797_a72_boot_out",
            "mt6797_a72_boot_out:",
            "gic_clear_primask();",
        ],
        "caller branch and cleanup patch order",
    )
    if source is not None:
        psci = (source / "arch/arm64/kernel/psci.c").read_text()
        require(
            psci.count("err = psci_ops.cpu_on(") == 2,
            "final source PSCI call count changed",
        )
        ordered(
            psci,
            [
                "goto mt6797_a72_boot_out",
                "err = psci_ops.cpu_on",
                "dcm_mcusys_mp2_sync_dcm(1)",
                "BigiDVFSEnable_hp()",
                "mt6797_a72_boot_out:",
                "gic_clear_primask();",
            ],
            "final-source caller dominance and cleanup",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", required=True, type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    validate(
        args.patch_dir.resolve(),
        args.source.resolve() if args.source is not None else None,
    )
    print("PASS: generated rollback patches satisfy static safety contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
