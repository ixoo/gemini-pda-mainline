#!/usr/bin/env python3
"""Validate the generated pre-init recovery format patch and series."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from preinit_source_edits import RECOVERY_SOURCE


EXPERIMENT = Path(__file__).resolve().parents[1]
PARENT_PATCH = (
    EXPERIMENT / "patches/0001-power-add-read-only-DVFSP-provenance-observer.patch"
)
PATCH = (
    EXPERIMENT
    / "patches/0002-power-add-provenance-pre-init-recovery-companion.patch"
)
SERIES = EXPERIMENT / "patches/series-preinit-recovery"
EXPECTED_PARENT_SHA256 = (
    "3520538de1c31ea592c2f0c76af7deef10f5c1ee00689d74bdac17def48dbb11"
)
EXPECTED_PATCH_SHA256 = (
    "0ddf2b5b28bb0957a467d38bfece553b89bf6b81c85c365f293d00b94efbd3d1"
)
EXPECTED_COMMIT = "2dbf7be3999120f297aedb9842bce320d759d26e"
EXPECTED_PATHS = (
    "drivers/misc/mediatek/base/power/Kconfig",
    "drivers/misc/mediatek/base/power/mt6797/Makefile",
    "drivers/misc/mediatek/base/power/mt6797/"
    "mt6797-dvfsp-provenance-preinit-recovery.c",
)
EXPECTED_SERIES = (
    "0001-power-add-read-only-DVFSP-provenance-observer.patch\n"
    "0002-power-add-provenance-pre-init-recovery-companion.patch\n"
)


class PatchValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PatchValidationError(message)


def diff_section(patch: str, path: str) -> str:
    marker = f"diff --git a/{path} b/{path}\n"
    require(patch.count(marker) == 1, f"diff section is not unique: {path}")
    start = patch.index(marker)
    end = patch.find("\ndiff --git ", start + len(marker))
    return patch[start:] if end == -1 else patch[start:end]


def added_file(section: str) -> str:
    lines = []
    for line in section.splitlines(keepends=True):
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return "".join(lines)


def validate_patch_text(patch: str, enforce_identity: bool = True) -> None:
    if enforce_identity:
        digest = hashlib.sha256(patch.encode()).hexdigest()
        require(digest == EXPECTED_PATCH_SHA256, "generated patch checksum changed")
    require(
        patch.startswith(f"From {EXPECTED_COMMIT} Mon Sep 17 00:00:00 2001\n"),
        "format-patch commit identity changed",
    )
    require("Signed-off-by:" not in patch, "synthetic sign-off is forbidden")
    require("Subject: [PATCH] power: add provenance pre-init recovery companion\n"
            in patch, "patch subject changed")
    require("GIT binary patch" not in patch, "binary patch content is forbidden")

    paths = re.findall(r"^diff --git a/(.+) b/(.+)$", patch, re.MULTILINE)
    require(all(left == right for left, right in paths),
            "left/right patch paths differ")
    require(tuple(left for left, _ in paths) == EXPECTED_PATHS,
            "changed-path inventory changed")

    kconfig = diff_section(patch, EXPECTED_PATHS[0])
    makefile = diff_section(patch, EXPECTED_PATHS[1])
    recovery = diff_section(patch, EXPECTED_PATHS[2])
    require("+\tdefault n\n" in kconfig, "recovery symbol is not default-off")
    require(
        "+\tdepends on GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER && "
        "PSTORE_CONSOLE\n" in kconfig,
        "observer/pstore dependency changed",
    )
    require("+\tselect " not in kconfig, "recovery symbol gained a select")
    require(
        "+obj-$(CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_PREINIT_RECOVERY) += "
        "mt6797-dvfsp-provenance-preinit-recovery.o\n" in makefile,
        "gated object line changed",
    )
    require(added_file(recovery) == RECOVERY_SOURCE,
            "generated recovery source changed")

    source = added_file(recovery)
    for needle, expected in {
        "GEMINI_DVFSP_PROVENANCE_PREINIT_RECOVERY_20260815": 1,
        "GEMINI_MT6797_PREINIT_RECOVERY_SECONDS\t120": 1,
        "schedule_delayed_work(": 1,
        "emergency_restart();": 1,
        "late_initcall_sync(gemini_mt6797_preinit_recovery_init);": 1,
        "checkpoint=pre-init": 1,
        "recovery=executing": 1,
    }.items():
        require(source.count(needle) == expected,
                f"source count changed for {needle!r}")
    for forbidden in (
        "late_initcall(", "module_init(", "cancel_delayed_work", "get_wd_api",
        "watchdog", "/dev/", "filp_open", "kernel_write", "regmap_write",
        "writel(", "cpu_up(", "cpu_down(", "psci_cpu_on(",
        "regulator_set_voltage",
    ):
        require(forbidden not in source,
                f"forbidden source operation present: {forbidden}")


def main() -> int:
    parent_bytes = PARENT_PATCH.read_bytes()
    require(hashlib.sha256(parent_bytes).hexdigest() == EXPECTED_PARENT_SHA256,
            "historical observer patch changed")
    require(SERIES.read_text() == EXPECTED_SERIES,
            "pre-init recovery series changed")
    validate_patch_text(PATCH.read_text())
    print("preinit_recovery_patch_validation=passed")
    print(f"patch_sha256={EXPECTED_PATCH_SHA256}")
    print(f"generated_vendor_commit={EXPECTED_COMMIT}")
    print("changed_path_count=3")
    print("default_off=true")
    print("recovery_deadline_seconds=120")
    print("boot_candidate=false")
    print("cpu8_cpu9_admission=closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PatchValidationError as exc:
        raise SystemExit(f"error: {exc}")
