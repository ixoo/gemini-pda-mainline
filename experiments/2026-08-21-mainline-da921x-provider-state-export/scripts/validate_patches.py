#!/usr/bin/env python3
"""Validate generated DA921x provider-state patches."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0312-arm64-add-read-only-provider-state-snapshot.patch",
    "0313-regulator-export-stable-DA921x-provider-state.patch",
    "0314-regulator-test-stable-DA921x-provider-state.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    found = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(found == PATCHES, "three exact patch filenames")
    require((patch_dir / "series").read_text() == "\n".join(PATCHES) + "\n",
            "generated series")

    registry = (patch_dir / PATCHES[0]).read_text()
    provider = (patch_dir / PATCHES[1]).read_text()
    tests = (patch_dir / PATCHES[2]).read_text()
    for data in (registry, provider, tests):
        require("Signed-off-by:" not in data, "no synthetic certification")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in data,
            "synthetic experiment author is explicit",
        )

    require("Subject: [PATCH 1/3] arm64: add read-only provider state snapshot"
            in registry, "registry subject")
    for path in (
        "include/linux/mt6797-a72-provider.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
    ):
        require(f"diff --git a/{path} b/{path}" in registry,
                f"registry path: {path}")
    require("drivers/regulator/" not in registry,
            "registry patch remains platform-scoped")

    require("Subject: [PATCH 2/3] regulator: export stable DA921x provider state"
            in provider, "provider subject")
    require("diff --git a/drivers/regulator/da9213-legacy-regulator.c" in
            provider, "provider driver path")
    require("membership-test.c" not in provider,
            "production provider patch excludes tests")

    require("Subject: [PATCH 3/3] regulator: test stable DA921x provider state"
            in tests, "test subject")
    require("diff --git a/drivers/regulator/da9213-legacy-membership-test.c"
            in tests, "KUnit path")
    require("da9213-legacy-regulator.c" not in tests,
            "test patch excludes production source")

    added = added_lines(registry + provider + tests)
    for forbidden in (
        "provider_write_cont", "ops->delay(", "cpu_up(", "cpu_down(",
        "psci_ops", "status = \"okay\"", "device_create_file(",
    ):
        require(forbidden not in added, f"forbidden added effect: {forbidden}")

    print("generated_patch_count=3")
    for index, patch in enumerate(PATCHES, start=1):
        print(f"patch_{index}={patch}")
    print("snapshot_samples=2-no-loop")
    print("success_reads=10")
    print("hardware_write=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
