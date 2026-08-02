#!/usr/bin/env python3
"""Validate the rollback compile-review lane without running a kernel build."""

from __future__ import annotations

import hashlib
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
OBSERVER = REPOSITORY / "experiments/2026-07-23-gemian-a72-owner-observer"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def patchset_hash(directory: Path) -> str:
    names = [line for line in (directory / "series").read_text().splitlines() if line]
    manifest = bytearray()
    for name in names:
        require("/" not in name and name.endswith(".patch"), "unsafe series name")
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        manifest.extend(f"{digest}  {name}\n".encode())
    return hashlib.sha256(manifest).hexdigest()


def main() -> int:
    buildbox = (REPOSITORY / "scripts/buildbox").read_text()
    lane = (EXPERIMENT / "scripts/build-on-buildbox").read_text()
    parent_hash = patchset_hash(OBSERVER / "patches")
    rollback_hash = patchset_hash(EXPERIMENT / "patches")

    require(
        parent_hash == "3584e9dd5ffb041573b851f31f3a96eaa0a684acb880fd59560762e5abc58be0",
        "parent observer patchset identity changed",
    )
    require(
        rollback_hash == "f034724759eebc611d6f16dea3448f1ee1ebcff0939a6e62e686c0a6261162a7",
        "rollback patchset identity changed",
    )

    for token in [
        "build-gemian-rollback-compile",
        "fetch-gemian-rollback-compile",
        "gemian-a72-preiso-rollback-compile-review",
        "baseline_source_parent_observer",
        parent_hash,
        rollback_hash,
    ]:
        require(token in buildbox, f"Buildbox wrapper missing {token!r}")

    for token in [
        'readonly SOURCE_COMMIT=59e00a9144d782e148332009a835b99c43382467',
        'readonly TARGET_EXTRA_CFLAGS=-fstack-usage',
        '"${parent_patchset_sha}" 0',
        '"${parent_patchset_sha}:${rollback_patchset_sha}" 1',
        "--enable MTK_A72_TRANSITION_OBSERVER",
        "--enable MTK_A72_PREISO_ROLLBACK_DISCRIMINATOR",
        'baseline_source_parent_observer: true',
        'purpose: "rollback-compile-review-only"',
        'boot_candidate: false',
        'outputs/baseline/stack-usage.tar',
        "diagnostic_comparison=identical",
        "da9214_a72_diag_compare_update",
        "mt6797_a72_diag_spm_compare_update",
        "mt6797_a72_diag_toprgu_compare_update",
        "mt6797_a72_obs_rollback_terminal",
    ]:
        require(token in lane, f"compile lane missing {token!r}")

    for forbidden in [
        "scripts/dev-vm",
        "--backend vm",
        "scp ",
        "rsync ",
        "boot2",
        "/dev/mmc",
    ]:
        require(forbidden not in lane, f"compile lane contains {forbidden!r}")

    require(
        lane.count("Image.gz-dtb >") == 2,
        "compile lane must build exactly rollback and parent observer",
    )
    require(
        lane.count("stack-usage.tar") == 6,
        "both stack-usage archives are not fully validated",
    )
    print("PASS: rollback Buildbox compile lane is pinned and device-inert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
