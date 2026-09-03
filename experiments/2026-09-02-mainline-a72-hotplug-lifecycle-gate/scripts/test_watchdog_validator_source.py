#!/usr/bin/env python3
"""Require unsafe watchdog-validator source mutations to fail."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_watchdog_validator_source.py"
FILES = (
    "include/linux/mtk_wdt.h",
    "drivers/watchdog/mtk_wdt.c",
    "arch/arm64/kernel/mt6797_psci.c",
)


def run(root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--source-root", str(root),
         "--require-tests"],
        check=False, capture_output=True, text=True,
    )


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor changed: {old}")
    path.write_text(text.replace(old, new, 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    positive = run(source)
    if positive.returncode:
        sys.stderr.write(positive.stderr)
        return 1

    mutations = (
        ("allow-unowned", "drivers/watchdog/mtk_wdt.c",
         "if (!owner->owned)", "if (false)"),
        ("allow-wrong-identity", "drivers/watchdog/mtk_wdt.c",
         "if (identity != owner->identity)", "if (false)"),
        ("drop-mode-mask", "drivers/watchdog/mtk_wdt.c",
         "validation->mode & WDT_MODE_RECOVERY_MASK",
         "validation->mode & 0"),
        ("drop-length-mask", "drivers/watchdog/mtk_wdt.c",
         "validation->length & WDT_LENGTH_TIMEOUT_MASK",
         "validation->length & 0"),
        ("add-write", "drivers/watchdog/mtk_wdt.c",
         "validation->mode = ops->read(context, WDT_MODE);",
         "ops->write(context, WDT_MODE, 0);\n\t"
         "validation->mode = ops->read(context, WDT_MODE);"),
        ("drop-lock", "drivers/watchdog/mtk_wdt.c",
         "spin_lock_irqsave(&mtk_wdt->recovery_lock, flags);",
         "flags = 0;"),
        ("drop-export", "drivers/watchdog/mtk_wdt.c",
         "EXPORT_SYMBOL_GPL(mtk_wdt_recovery_validate);", ""),
        ("add-takeover", "drivers/watchdog/mtk_wdt.c",
         "ret = mtk_wdt_recovery_validate_owner(",
         "mtk_wdt_recovery_takeover(dev, 15000, NULL);\n\t"
         "ret = mtk_wdt_recovery_validate_owner("),
        ("mutable-stub", "include/linux/mtk_wdt.h",
         "return -EOPNOTSUPP;\n}\n#endif",
         "return 0;\n}\n#endif"),
        ("drop-success-test", "drivers/watchdog/mtk_wdt.c",
         "\tKUNIT_CASE(mtk_wdt_recovery_validate_success_test),\n", ""),
        ("bind-production", "arch/arm64/kernel/mt6797_psci.c",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n"
         "\tmtk_wdt_recovery_validate(NULL, 1, NULL);\n"),
        ("open-disable", "arch/arm64/kernel/mt6797_psci.c",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn false;\n}",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn cpu == 9;\n}"),
    )

    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(
            prefix="gemini-watchdog-validator-mutation-"
        ) as temp_name:
            root = pathlib.Path(temp_name)
            for item in FILES:
                target = root / item
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / item, target)
            try:
                replace_once(root / relative, old, new)
            except ValueError as exc:
                print(f"mutation={name} setup=fail reason={exc}",
                      file=sys.stderr)
                return 1
            result = run(root)
            if result.returncode == 0:
                print(f"mutation={name} result=unexpected-pass",
                      file=sys.stderr)
                return 1

    print(f"watchdog_validator_source_mutations={len(mutations)}")
    print("watchdog_validator_source_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
