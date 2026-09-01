#!/usr/bin/env python3
"""Apply the hardware-free retained-cluster CPU9 executor source changes."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
from textwrap import dedent


HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "9a02fc20d391c481ff503c532f984967963e265d0fc8fa0a21b17ce024123751",
    "drivers/soc/mediatek/Makefile":
        "51cc36898980788ff5fb352cbfb36e22f363afe2e18b2e2d286a8e7b6b743f92",
}
NEW_PATHS = (
    "drivers/soc/mediatek/mt6797-a72-cpu9-executor-internal.h",
    "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
    "drivers/soc/mediatek/mt6797-a72-cpu9-executor-test.c",
)

KCONFIG = dedent("""\
    config MTK_MT6797_A72_CPU9_EXECUTOR
    \tbool "MediaTek MT6797 retained-cluster CPU9 executor"
    \tdepends on ARM64 && ARCH_MEDIATEK
    \tdepends on ARM64_MT6797_A72_CPU9_MEMBERSHIP
    \tdepends on PSTORE_GEMINI_CPU9_TRANSITION_LEDGER
    \tdefault n
    \thelp
    \t  Build a separate one-shot coordinator for CPU9 after exact CPU8
    \t  success. Its injected operation table contains only prestate,
    \t  CPU_ON, secondary completion, IPI, membership, and retained
    \t  checkpoint/terminal callbacks.

    \t  This option adds no production caller, CPU request, PSCI binding,
    \t  watchdog action, P27/provider/isolation/SRAM/DCM operation, CPU_OFF,
    \t  retry, device binding, or boot policy. If unsure, say N.

    config MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST
    \tbool "KUnit tests for the MT6797 retained-cluster CPU9 executor"
    \tdepends on KUNIT=y
    \tdepends on MTK_MT6797_A72_CPU9_EXECUTOR
    \tdefault n
    \thelp
    \t  Exercise exact split success, all five operation failures, all ten
    \t  retained-checkpoint failures, entry mutations, missing callbacks,
    \t  lifecycle guards, terminal failure, and atomic one-shot behavior.

    \t  Tests use injected memory-only callbacks and perform no hardware,
    \t  CPU, retained-RAM, watchdog, regulator, clock, or device action.

    """)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"parent source is absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"parent source changed: {relative}: {actual}")
    for relative in NEW_PATHS:
        if (root / relative).exists():
            raise SystemExit(f"new CPU9 executor path already exists: {relative}")


def copy_new(root: Path, relative: str) -> None:
    source = TEMPLATES / Path(relative).name
    target = root / relative
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"template is absent or unsafe: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def apply(root: Path) -> None:
    root = root.resolve()
    validate_parent(root)
    replace_once(
        root / "drivers/soc/mediatek/Kconfig",
        "config MTK_MT6797_A72_DEFAULT_OFF_BINDER\n",
        KCONFIG + "config MTK_MT6797_A72_DEFAULT_OFF_BINDER\n",
    )
    replace_once(
        root / "drivers/soc/mediatek/Makefile",
        "obj-$(CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST) += "
        "mt6797-a72-transition-test.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST) += "
        "mt6797-a72-transition-test.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR) += "
        "mt6797-a72-cpu9-executor.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST) += "
        "mt6797-a72-cpu9-executor-test.o\n",
    )
    for relative in NEW_PATHS:
        copy_new(root, relative)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root)
