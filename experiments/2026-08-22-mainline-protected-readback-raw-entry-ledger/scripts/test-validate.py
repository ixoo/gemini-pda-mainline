#!/usr/bin/env python3
"""Negative semantic mutations for the raw-entry ledger definition."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0331-pstore-accept-Gemini-raw-entry-ledger.patch"
FRAGMENT = ROOT / "configs/gemini-protected-readback-raw-entry-ledger.fragment"
MODE = "PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER"
EXPECTED_FRAGMENT = FRAGMENT.read_text(encoding="utf-8")


def additions(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def accepted(patch: str, fragment: str) -> bool:
    added = additions(patch)
    required_once = (
        f"config {MODE}",
        "\tdefault n",
        "\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "\tdepends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y",
        "readl(slot) == ~0U",
        "readl((u8 __iomem *)slot + 4) == ~0U",
        "readl((u8 __iomem *)slot + 8) == ~0U",
        "writel(GEMINI_PRB_SIGNATURE, slot)",
        "gemini_protected_readback_ledger_checkpoint(0)",
        "mt6797_dvfsp_clock_backend_read(&clock_backend->dev,",
        "gemini_protected_readback_ledger_checkpoint(1)",
        '" state=complete attempts=1 clock_calls=1 bigidvfs_calls=0"',
    )
    if any(added.count(item) != 1 for item in required_once):
        return False
    if patch.index("writel(len, (u8 __iomem *)slot + 8)") > patch.index(
            "writel(GEMINI_PRB_SIGNATURE, slot)"):
        return False
    if any(item in added for item in (
        "mt6797_bigidvfs_backend_read(", "cpu_up(", "cpu_down(",
        "kernel_restart(", "schedule_delayed_work(",
    )):
        return False
    return fragment == EXPECTED_FRAGMENT


def main() -> None:
    patch = PATCH.read_text(encoding="utf-8")
    fragment = EXPECTED_FRAGMENT
    if not accepted(patch, fragment):
        raise AssertionError("positive definition rejected")

    mutations = (
        (patch.replace(f"config {MODE}", "config BROKEN_RAW_LEDGER", 1), fragment),
        (patch.replace("\tdefault n", "\tdefault y", 1), fragment),
        (patch.replace("\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
                       "\tdepends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER", 1), fragment),
        (patch.replace("readl(slot) == ~0U", "readl(slot) == 0", 1), fragment),
        (patch.replace("readl((u8 __iomem *)slot + 4) == ~0U",
                       "readl((u8 __iomem *)slot + 4) == 0", 1), fragment),
        (patch.replace("writel(GEMINI_PRB_SIGNATURE, slot)",
                       "writel(0, slot)", 1), fragment),
        (patch.replace("gemini_protected_readback_ledger_checkpoint(0)",
                       "gemini_protected_readback_ledger_checkpoint(2)", 1), fragment),
        (patch.replace("mt6797_dvfsp_clock_backend_read(&clock_backend->dev,",
                       "mt6797_bigidvfs_backend_read(&clock_backend->dev,", 1), fragment),
        (patch.replace("bigidvfs_calls=0", "bigidvfs_calls=1", 1), fragment),
        (patch.replace("\tret = 0;", "\tcpu_up(8);\n\tret = 0;", 1), fragment),
        (patch, fragment.replace(f"CONFIG_{MODE}=y", f"# CONFIG_{MODE} is not set", 1)),
        (patch, fragment.replace("-gemini-protected-raw", "-gemini-wrong", 1)),
    )
    accepted_indices = [
        index
        for index, (mutated_patch, mutated_fragment) in enumerate(mutations)
        if accepted(mutated_patch, mutated_fragment)
    ]
    rejected = len(mutations) - len(accepted_indices)
    if rejected != len(mutations):
        raise AssertionError(f"unsafe mutation accepted: {accepted_indices}")

    print("validation=protected-readback-raw-entry-ledger-mutations")
    print(f"unsafe_mutations_rejected={rejected}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
