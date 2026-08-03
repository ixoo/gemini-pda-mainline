#!/usr/bin/env python3
"""Validate the one-way CPU8 compile lane without building a kernel."""

from __future__ import annotations

import hashlib
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
OBSERVER = REPOSITORY / "experiments/2026-07-23-gemian-a72-owner-observer"
ROLLBACK = REPOSITORY / "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator"


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
    rollback_hash = patchset_hash(ROLLBACK / "patches")
    one_way_hash = patchset_hash(EXPERIMENT / "patches")

    expected = {
        parent_hash: "3584e9dd5ffb041573b851f31f3a96eaa0a684acb880fd59560762e5abc58be0",
        rollback_hash: "fd4da13202c62a6ea21a216ffc9eb2650d70dcaa216a8ca1b3c64e5ef5c10b9d",
        one_way_hash: "2ce261bdd9bcd5fe02133414c7d6535c213c06ad3af0e37ffbbc34feee7819c2",
    }
    require(all(actual == wanted for actual, wanted in expected.items()),
            "compile patch foundation changed")

    for token in [
        "build-gemian-one-way-compile",
        "fetch-gemian-one-way-compile",
        "gemian-a72-one-way-compile-review",
        "baseline_source_parent_rollback",
        *expected.values(),
    ]:
        require(token in buildbox, f"Buildbox wrapper missing {token!r}")

    for token in [
        'readonly SOURCE_COMMIT=59e00a9144d782e148332009a835b99c43382467',
        'readonly TARGET_EXTRA_CFLAGS=-fstack-usage',
        '"${parent_patchset_sha}:${rollback_patchset_sha}" 0',
        '"${parent_patchset_sha}:${rollback_patchset_sha}:${one_way_patchset_sha}" 1',
        "--enable MTK_A72_TRANSITION_OBSERVER",
        "--enable MTK_A72_ONE_WAY_CPU8",
        'baseline_source_parent_rollback: true',
        'purpose: "one-way-compile-review-only"',
        'boot_candidate: false',
        'outputs/baseline/stack-usage.tar',
        "diagnostic_comparison=identical",
        "mtk_wd_a72_recovery_takeover",
        "mt6797_a72_one_way_sram_set_verify",
        "mt6797_a72_one_way_dcm_enable",
        "mt6797_a72_one_way_secondary_complete",
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

    require(lane.count("Image.gz-dtb >") == 2,
            "compile lane must build exactly one-way and parent rollback")
    require(lane.count("stack-usage.tar") == 6,
            "both stack-usage archives are not fully validated")
    print("PASS: one-way CPU8 Buildbox compile lane is pinned and device-inert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
