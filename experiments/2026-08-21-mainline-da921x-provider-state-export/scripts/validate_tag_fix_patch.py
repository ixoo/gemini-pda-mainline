#!/usr/bin/env python3
"""Validate the generated provider snapshot tag fix patch."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCH = "0315-arm64-rename-read-only-provider-snapshot-record.patch"
FILES = (
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "drivers/regulator/da9213-legacy-membership-test.c",
    "drivers/regulator/da9213-legacy-regulator.c",
    "include/linux/mt6797-a72-provider.h",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(actual == (PATCH,), f"one exact patch: {actual}")
    require((patch_dir / "series").read_text() == PATCH + "\n",
            "one-patch series")
    text = (patch_dir / PATCH).read_text()
    require(
        "Subject: [PATCH 1/1] arm64: rename read-only provider snapshot record"
        in text,
        "patch subject",
    )
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
        in text,
        "synthetic experiment author",
    )
    require("Signed-off-by:" not in text, "no synthetic certification")
    paths = tuple(re.findall(
        r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE
    ))
    require(paths == FILES, f"exact four-file patch boundary: {paths}")
    additions = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    removals = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )
    require(additions.count("struct mt6797_a72_provider_snapshot") == 13,
            "thirteen renamed additions")
    require(removals.count("struct mt6797_a72_provider_state") == 13,
            "thirteen conflicting removals")
    require("struct mt6797_a72_provider_state" not in additions,
            "old struct tag not re-added")
    for forbidden in (
        "writel(", "provider_write_cont", "ops->delay(", "cpu_up(",
        "cpu_down(", "psci_ops", "status = \"okay\"",
    ):
        require(forbidden not in additions,
                f"forbidden added effect: {forbidden}")

    print("tag_fix_patch_validation=pass")
    print("generated_patch_count=1")
    print("renamed_struct_uses=13")
    print("behavior_change=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
