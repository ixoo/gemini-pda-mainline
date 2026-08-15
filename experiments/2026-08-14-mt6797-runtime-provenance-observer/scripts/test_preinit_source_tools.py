#!/usr/bin/env python3
"""Exercise source generation and reject decision-changing mutations."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from preinit_source_edits import (
    EditError,
    KCONFIG_PARENT,
    MAKEFILE_PARENT,
    apply,
)
from validate_preinit_source import ValidationError, validate


def fixture(root: Path) -> Path:
    source = root / "source"
    power = source / "drivers/misc/mediatek/base/power"
    mt6797 = power / "mt6797"
    mt6797.mkdir(parents=True)
    (power / "Kconfig").write_text("parent\n" + KCONFIG_PARENT)
    (mt6797 / "Makefile").write_text("parent\n" + MAKEFILE_PARENT)
    return source


def expect_rejected(source: Path, mutation: str, old: str, new: str) -> None:
    target = source / (
        "drivers/misc/mediatek/base/power/Kconfig"
        if mutation.startswith("kconfig-")
        else "drivers/misc/mediatek/base/power/mt6797/Makefile"
        if mutation.startswith("makefile-")
        else "drivers/misc/mediatek/base/power/mt6797/"
        "mt6797-dvfsp-provenance-preinit-recovery.c"
    )
    text = target.read_text()
    if old not in text:
        raise AssertionError(f"mutation anchor missing: {mutation}")
    target.write_text(text.replace(old, new, 1))
    try:
        validate(source)
    except ValidationError:
        return
    raise AssertionError(f"unsafe mutation accepted: {mutation}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gemini-preinit-tools-") as tmp:
        root = Path(tmp)
        source = fixture(root)
        apply(source)
        validate(source)

        try:
            apply(source)
        except EditError:
            pass
        else:
            raise AssertionError("source editor accepted a second application")

        mutations = (
            ("kconfig-default-on", "\tdefault n\n", "\tdefault y\n"),
            ("kconfig-no-pstore", " && PSTORE_CONSOLE", ""),
            ("kconfig-select", "\tdefault n\n", "\tdefault n\n\tselect PSTORE\n"),
            ("makefile-ungated", "obj-$(CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_PREINIT_RECOVERY)", "obj-y"),
            ("source-deadline", "\t120\n", "\t300\n"),
            ("source-marker", "PREINIT_RECOVERY_20260815", "PREINIT_RECOVERY_MUTATED"),
            ("source-no-schedule", "schedule_delayed_work(", "schedule_work("),
            ("source-no-reset", "emergency_restart();", "return;"),
            ("source-wrong-initcall", "late_initcall_sync(", "late_initcall("),
            ("source-cancellable", "\temergency_restart();", "\tcancel_delayed_work_sync(&gemini_mt6797_preinit_recovery_work);\n\temergency_restart();"),
            ("source-watchdog-owner", "\t(void)work;", "\t(void)work;\n\tget_wd_api(NULL);"),
            ("source-storage", "\t(void)work;", "\t(void)work;\n\tfilp_open(\"/dev/mmcblk0\", 0, 0);"),
            ("source-cpu", "\t(void)work;", "\t(void)work;\n\tcpu_up(8);"),
        )
        rejected = 0
        for mutation, old, new in mutations:
            mutated = root / f"mutation-{rejected}"
            shutil.copytree(source, mutated)
            expect_rejected(mutated, mutation, old, new)
            rejected += 1

    print("preinit_recovery_source_tools=passed")
    print("positive_cases=1")
    print(f"mutations_rejected={rejected}")
    print("second_application_rejected=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
