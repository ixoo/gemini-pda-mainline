#!/usr/bin/env python3
"""Reject semantic mutations of the generated pre-init recovery patch."""

from __future__ import annotations

from validate_preinit_patch import PATCH, PatchValidationError, validate_patch_text


def main() -> int:
    original = PATCH.read_text()
    validate_patch_text(original)
    mutations = (
        ("default-on", "+\tdefault n\n", "+\tdefault y\n"),
        ("missing-pstore", " && PSTORE_CONSOLE", ""),
        ("select", "+\tdefault n\n", "+\tdefault n\n+\tselect PSTORE\n"),
        ("ungated-object", "+obj-$(CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_PREINIT_RECOVERY)", "+obj-y"),
        ("deadline", "RECOVERY_SECONDS\t120", "RECOVERY_SECONDS\t300"),
        ("marker", "PREINIT_RECOVERY_20260815", "PREINIT_RECOVERY_MUTATED"),
        ("no-schedule", "schedule_delayed_work(", "schedule_work("),
        ("no-reset", "emergency_restart();", "return;"),
        ("wrong-initcall", "late_initcall_sync(", "late_initcall("),
        ("cancellable", "+\temergency_restart();", "+\tcancel_delayed_work_sync(&gemini_mt6797_preinit_recovery_work);\n+\temergency_restart();"),
        ("watchdog-owner", "+\t(void)work;", "+\t(void)work;\n+\tget_wd_api(NULL);"),
        ("storage", "+\t(void)work;", "+\t(void)work;\n+\tfilp_open(\"/dev/mmcblk0\", 0, 0);"),
        ("cpu", "+\t(void)work;", "+\t(void)work;\n+\tcpu_up(8);"),
    )
    rejected = 0
    for name, old, new in mutations:
        if old not in original:
            raise AssertionError(f"mutation anchor missing: {name}")
        mutated = original.replace(old, new, 1)
        try:
            validate_patch_text(mutated, enforce_identity=False)
        except PatchValidationError:
            rejected += 1
            continue
        raise AssertionError(f"unsafe patch mutation accepted: {name}")
    print("preinit_recovery_patch_validator_tests=passed")
    print("positive_cases=1")
    print(f"mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
