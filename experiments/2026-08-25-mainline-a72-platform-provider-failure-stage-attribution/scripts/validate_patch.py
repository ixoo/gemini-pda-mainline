#!/usr/bin/env python3
"""Validate exact patch inventory, scope, and forbidden added behavior."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0378-soc-mediatek-report-A72-platform-provider-failure-stage.patch",
    "0379-soc-mediatek-test-A72-platform-provider-failure-stage.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.patch_dir.resolve()
    require(tuple((root / "series").read_text().splitlines()) == PATCHES,
            "exact two-patch series")
    require(tuple(sorted(path.name for path in root.glob("*.patch"))) == PATCHES,
            "exact patch inventory")
    expected_files = (
        {
            "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer-internal.h",
            "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer.c",
        },
        {"drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer-test.c"},
    )
    for name, scope in zip(PATCHES, expected_files):
        text = (root / name).read_text(encoding="utf-8")
        require("Signed-off-by:" not in text, f"no synthetic sign-off: {name}")
        files = {
            line[6:] for line in text.splitlines()
            if line.startswith("+++ b/") and line != "+++ b/dev/null"
        }
        require(files == scope, f"exact file scope: {name}")
        added = "\n".join(
            line[1:] for line in text.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        for forbidden in ("cpu_up(", "cpu_down(", "psci_ops", "kernel_restart(",
                          "msleep(", "udelay(", "i2c_transfer(", "readl(", "writel("):
            require(forbidden not in added, f"forbidden added action {forbidden}: {name}")
    production = (root / PATCHES[0]).read_text(encoding="utf-8")
    tests = (root / PATCHES[1]).read_text(encoding="utf-8")
    require("stage=%s ret=%d" in production, "attributed production log")
    for stage in ("DEPENDENCY", "PLATFORM", "PROVIDER", "BEFORE_CLOCK"):
        require(f"MT6797_A72_PPC_FAILURE_{stage}" in production,
                f"production stage: {stage}")
        require(f"MT6797_A72_PPC_FAILURE_{stage}" in tests,
                f"test stage: {stage}")
    print("patch_validation=pass")
    print("generated_patch_count=2")
    print("device_action=none")


if __name__ == "__main__":
    main()
