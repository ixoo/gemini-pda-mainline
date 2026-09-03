#!/usr/bin/env python3
"""Reject unsafe mutations of the disconnected binder-core source."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_binder_core_source.py"
PATHS = (
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-test.c",
)

MUTATIONS = (
    ("drivers/soc/mediatek/Kconfig",
     "\tdepends on MTK_MT6797_A72_RESTORE_EXECUTOR\n\tdefault n\n",
     "\tdepends on MTK_MT6797_A72_RESTORE_EXECUTOR\n\tdefault y\n"),
    ("drivers/soc/mediatek/Kconfig",
     "\tdepends on PSTORE_GEMINI_A72_HOTPLUG_LEDGER\n", ""),
    ("drivers/soc/mediatek/Kconfig",
     "\tdepends on MTK_MT6797_A72_CPU8_OBSERVER\n", ""),
    ("drivers/soc/mediatek/Kconfig",
     "\tdepends on MTK_MT6797_A72_RESTORE_EXECUTOR\n", ""),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h",
     "MT6797_A72_HOTPLUG_BINDER_CPU9 9U",
     "MT6797_A72_HOTPLUG_BINDER_CPU9 8U"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h",
     "MT6797_A72_HOTPLUG_BINDER_DOWN_STAGE 13U",
     "MT6797_A72_HOTPLUG_BINDER_DOWN_STAGE 12U"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h",
     "MT6797_A72_HOTPLUG_BINDER_RESTORE_STAGE 17U",
     "MT6797_A72_HOTPLUG_BINDER_RESTORE_STAGE 16U"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "proof->online_count != 10", "proof->online_count < 9"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "proof->watchdog_age_ns == age", "proof->watchdog_age_ns >= age"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "age <= MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL",
     "age <= 15000ULL * 1000000ULL"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "ops->current_task_identity(context) != request->task_identity",
     "ops->current_task_identity(context) == request->task_identity"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "atomic_cmpxchg(&controller->consumed, 0, 1)",
     "atomic_cmpxchg(&controller->consumed, 0, 0)"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "mt6797_a72_restore_down_parent_valid(", "true || ("),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "down->identity.parent_cookie == parent->cpu9.cookie",
     "down->identity.parent_cookie != parent->cpu9.cookie"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "down->provider_identity.cookie == parent->provider_cookie",
     "down->provider_identity.cookie != parent->provider_cookie"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "mt6797_a72_restore_transaction_valid(", "true || ("),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "result->remove_cpu_calls++;", "result->remove_cpu_calls += 2;"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "result->restore_add_cpu_calls++;",
     "result->restore_add_cpu_calls += 2;"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "MT6797_A72_HOTPLUG_BINDER_FAULT_POSTCOMMIT :",
     "MT6797_A72_HOTPLUG_BINDER_REJECTED_PRECOMMIT :"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
     "result->completed = true;\n\treturn mt6797_a72_hotplug_binder_terminal(",
     "result->completed = true;\n\tcpu_down(9);\n\treturn "
     "mt6797_a72_hotplug_binder_terminal("),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-test.c",
     "\tBINDER_CORE_FAIL_REMOVE_POSTCOMMIT,",
     "\tBINDER_CORE_FAIL_REMOVE_LATE,"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-test.c",
     "KUNIT_CASE(binder_core_terminal_failure_test),", ""),
)


def load_validator():
    spec = importlib.util.spec_from_file_location("binder_source", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(f"mutation anchor changed: {relative}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = load_validator()
    validator.validate(source, True)
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="binder-core-mutations-") as name:
        base = Path(name) / "base"
        for relative in PATHS:
            target = base / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
        for index, (relative, old, new) in enumerate(MUTATIONS):
            candidate = Path(name) / f"mutation-{index}"
            shutil.copytree(base, candidate)
            replace_once(candidate, relative, old, new)
            try:
                validator.validate(candidate, True)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError(f"unsafe mutation accepted: {index}")
    print("binder_core_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")


if __name__ == "__main__":
    main()
