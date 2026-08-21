#!/usr/bin/env python3
"""Validate generated protected-readback remediation patches."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0316-soc-mediatek-make-protected-clock-snapshots-atomic.patch",
    "0317-soc-mediatek-require-stable-BigiDVFS-snapshots.patch",
    "0318-soc-mediatek-test-protected-readback-transports.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    found = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(found == PATCHES, "three exact patch filenames")
    require(
        (patch_dir / "series").read_text() == "\n".join(PATCHES) + "\n",
        "generated series",
    )

    clock = (patch_dir / PATCHES[0]).read_text()
    big = (patch_dir / PATCHES[1]).read_text()
    tests = (patch_dir / PATCHES[2]).read_text()
    for data in (clock, big, tests):
        require("Signed-off-by:" not in data, "no synthetic certification")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in data,
            "explicit synthetic experiment author",
        )

    require(
        "Subject: [PATCH 1/3] soc: mediatek: make protected clock snapshots atomic"
        in clock,
        "clock patch subject",
    )
    require("mt6797-dvfsp-clock-backend.c" in clock, "clock implementation")
    require("mt6797-protected-readback-internal.h" in clock,
            "clock test seam")
    require("mt6797-bigidvfs-backend.c" not in clock,
            "clock patch excludes BigiDVFS")

    require(
        "Subject: [PATCH 2/3] soc: mediatek: require stable BigiDVFS snapshots"
        in big,
        "BigiDVFS patch subject",
    )
    require("mt6797-bigidvfs-backend.c" in big, "BigiDVFS implementation")
    require("mt6797-dvfsp-clock-backend.c" not in big,
            "BigiDVFS patch excludes clock implementation")

    require(
        "Subject: [PATCH 3/3] soc: mediatek: test protected readback transports"
        in tests,
        "KUnit patch subject",
    )
    require("mt6797-protected-readback-test.c" in tests, "KUnit source")
    require("drivers/soc/mediatek/Kconfig" in tests, "KUnit Kconfig")
    require("drivers/soc/mediatek/Makefile" in tests, "KUnit Makefile")

    added = added_lines(clock + big + tests)
    for forbidden in (
        "MT6797_BIGIDVFS_FID_WRITE",
        "cpu_up(",
        "cpu_down(",
        "psci_ops",
        'status = "okay"',
        "device_create_file(",
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")

    print("generated_patch_count=3")
    for index, patch in enumerate(PATCHES, start=1):
        print(f"patch_{index}={patch}")
    print("clock_settle_ns=200-once-after-acquire")
    print("clock_publish=after-successful-release")
    print("bigidvfs_samples=2-fixed")
    print("bigidvfs_success_reads=8")
    print("caller_failure_record=all-zero")
    print("secure_write=none")
    print("cpu_admission=closed")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
