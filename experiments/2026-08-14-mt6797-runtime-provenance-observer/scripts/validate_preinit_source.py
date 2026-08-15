#!/usr/bin/env python3
"""Validate the isolated default-off pre-init recovery source contract."""

from __future__ import annotations

import argparse
from pathlib import Path

from preinit_source_edits import KCONFIG_CHILD, MAKEFILE_CHILD, RECOVERY_SOURCE


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate(source: Path) -> None:
    kconfig_path = source / "drivers/misc/mediatek/base/power/Kconfig"
    makefile_path = source / "drivers/misc/mediatek/base/power/mt6797/Makefile"
    recovery_path = (
        source
        / "drivers/misc/mediatek/base/power/mt6797/"
        "mt6797-dvfsp-provenance-preinit-recovery.c"
    )
    require(source.is_dir(), "source is not a directory")
    require(kconfig_path.is_file(), "Kconfig is missing")
    require(makefile_path.is_file(), "Makefile is missing")
    require(recovery_path.is_file() and not recovery_path.is_symlink(),
            "recovery source is missing or unsafe")

    kconfig = kconfig_path.read_text()
    makefile = makefile_path.read_text()
    recovery = recovery_path.read_text()
    require(kconfig.count(KCONFIG_CHILD) == 1,
            "exact Kconfig parent/child contract changed")
    require(kconfig.count(
        "config GEMINI_MT6797_DVFSP_PROVENANCE_PREINIT_RECOVERY") == 1,
        "recovery Kconfig symbol is not unique")
    require(
        "depends on GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER && "
        "PSTORE_CONSOLE" in kconfig,
        "observer/pstore dependency is absent",
    )
    require("\tdefault n\n" in KCONFIG_CHILD,
            "recovery configuration is not default-off")
    require("\tselect " not in KCONFIG_CHILD,
            "recovery configuration gained a select")
    require(makefile.count(MAKEFILE_CHILD) == 1,
            "exact gated-object Makefile contract changed")
    require(recovery == RECOVERY_SOURCE,
            "recovery source differs from the deterministic contract")

    exact_counts = {
        "GEMINI_DVFSP_PROVENANCE_PREINIT_RECOVERY_20260815": 1,
        "GEMINI_MT6797_PREINIT_RECOVERY_SECONDS\t120": 1,
        "schedule_delayed_work(": 1,
        "emergency_restart();": 1,
        "late_initcall_sync(gemini_mt6797_preinit_recovery_init);": 1,
        "static DECLARE_DELAYED_WORK(": 1,
        "checkpoint=pre-init": 1,
        "recovery=executing": 1,
        "scheduled ? 0 : -EBUSY": 1,
    }
    for needle, expected in exact_counts.items():
        require(recovery.count(needle) == expected,
                f"recovery source count changed for {needle!r}")
    require("late_initcall(" not in recovery,
            "recovery companion is not in the late-sync initcall section")
    require("module_init(" not in recovery,
            "recovery companion gained module initialization")
    require("cancel_delayed_work" not in recovery,
            "bounded recovery can be cancelled")

    forbidden = (
        "wd_config", "get_wd_api", "watchdog", "/dev/", "filp_open",
        "kernel_write", "vfs_write", "regmap_write", "writel(", "writeb(",
        "writew(", "cpu_up(", "cpu_down(", "psci_cpu_on(",
        "regulator_set_voltage", "request_firmware", "kexec",
    )
    for token in forbidden:
        require(token not in recovery, f"forbidden operation present: {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    validate(args.source.resolve())
    print("preinit_recovery_source_validation=passed")
    print("default_off=true")
    print("late_initcall_sync=true")
    print("recovery_deadline_seconds=120")
    print("device_storage_access=none")
    print("dvfsp_hardware_write=none")
    print("cpu8_cpu9_admission=closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        raise SystemExit(f"error: {exc}")
