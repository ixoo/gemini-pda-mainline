#!/usr/bin/env python3
"""Validate the generated one-file Kconfig follow-up patch."""

from __future__ import annotations

import argparse
from pathlib import Path


OLD = "-\tdepends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y"
NEW = (
    "+\tdepends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y || "
    "MTK_MT6797_DVFSP_CLOCK_BACKEND=y"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", type=Path, required=True)
    args = parser.parse_args()
    text = args.patch.read_text(encoding="utf-8")

    require(text.count("diff --git ") == 1, "one changed file")
    require("diff --git a/fs/pstore/Kconfig b/fs/pstore/Kconfig" in text,
            "only pstore Kconfig is changed")
    require(text.count(OLD) == 1 and text.count(NEW) == 1,
            "exact dependency replacement")
    require("Signed-off-by:" not in text, "no synthetic certification")
    require("Subject: [PATCH] pstore: allow clock entry ledger without observer" in text,
            "exact experiment-only subject")
    require("+++ b/fs/pstore/Kconfig" in text, "expected result path")
    for forbidden in (
        "drivers/", "arch/", "memcpy_toio", "writel(", "readl(",
        "arm_smccc", "clk_prepare_enable", "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in text, f"forbidden patch scope: {forbidden}")

    print("patch_validation=pass")
    print("changed_files=1")
    print("runtime_code_changes=0")


if __name__ == "__main__":
    main()
