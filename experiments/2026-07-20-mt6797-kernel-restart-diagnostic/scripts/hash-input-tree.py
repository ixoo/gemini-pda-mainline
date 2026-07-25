#!/usr/bin/env python3
"""Hash the complete repository input tree used to construct Candidate AB."""

from __future__ import annotations

import argparse
import pathlib
import sys

from ab_contract import EXPECTED_FRAGMENTS, digest_path


STATIC_INPUTS = (
    "kernel/manifest.json",
    "patches/series",
    "scripts/kernel",
    "scripts/validate-kernel-artifact",
    "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py",
    "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py",
    "experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts/validate-ash-dispatch.py",
    "experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh",
    "experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/scripts/derive-installer.py",
    "experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts/derive-installer.py",
    "experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/derive-installer.py",
    "experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/derive-revision-installer.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/initramfs/init",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/initramfs/local-shell",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/initramfs/reboot",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/initramfs/x-record",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/ab_contract.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/validate-aa-baseline.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/validate-package.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/build-initramfs.sh",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/validate-initramfs.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/validate-boot.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/normalize-build-json.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/write-provenance.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/hash-input-tree.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/build-candidate-ab.sh",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/validate-final-artifact.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/test-validator-mutations.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/materialize-aa-r1-installer.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/derive-installer.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/install-candidate-ab-boot2.sh.in",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/derive-installer-wrapper.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/calibrate-installer.py",
    "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/test-installer-static.py",
)


def series_entries(path: pathlib.Path) -> list[str]:
    entries: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        pure = pathlib.PurePosixPath(line)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or any(character.isspace() for character in line)
            or len(pure.parts) < 2
        ):
            raise ValueError(f"unsafe patch-series entry at line {number}")
        entries.append(line)
    if len(entries) != len(set(entries)):
        raise ValueError("duplicate patch-series entry")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        repo_root = args.repo_root.resolve(strict=True)
        paths = set(STATIC_INPUTS) | set(EXPECTED_FRAGMENTS)
        for entry in series_entries(repo_root / "patches/series"):
            paths.add(f"patches/{entry}")
        for relative in sorted(paths):
            path = repo_root / relative
            if path.is_symlink() or not path.is_file() or not path.stat().st_size:
                raise ValueError(f"repository input missing, empty, or unsafe: {relative}")
            print(f"{digest_path(path)}  {relative}")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
