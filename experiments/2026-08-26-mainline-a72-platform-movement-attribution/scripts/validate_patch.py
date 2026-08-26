#!/usr/bin/env python3
"""Validate exact movement-attribution patch inventory, scope, and safety."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0380-soc-mediatek-report-A72-platform-state-movement.patch",
    "0381-soc-mediatek-test-A72-platform-state-movement.patch",
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
    scopes = (
        {
            "drivers/soc/mediatek/mt6797-a72-platform-state.c",
            "drivers/soc/mediatek/mt6797-a72-platform-state-internal.h",
            "include/linux/soc/mediatek/mt6797-a72-platform-state.h",
            "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer.c",
            "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer-internal.h",
        },
        {
            "drivers/soc/mediatek/Kconfig",
            "drivers/soc/mediatek/Makefile",
            "drivers/soc/mediatek/mt6797-a72-platform-state-test.c",
            "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer-test.c",
        },
    )
    for name, scope in zip(PATCHES, scopes):
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
                          "msleep(", "udelay(", "i2c_transfer(", "writel("):
            require(forbidden not in added, f"forbidden added action {forbidden}: {name}")
    production = (root / PATCHES[0]).read_text(encoding="utf-8")
    tests = (root / PATCHES[1]).read_text(encoding="utf-8")
    require("movement=%03x" in production, "attributed production log")
    require("snapshot_detailed" in production, "detailed snapshot API")
    require("return -EBUSY" in production and "return -EAGAIN" in production,
            "distinct refusal returns")
    require(production.count("read_once(context, &first)") == 1 and
            production.count("read_once(context, &second)") == 1,
            "exact two reads")
    require("MT6797_A72_PLATFORM_MOVED_ALL = GENMASK(8, 0)" in production,
            "nine-bit range")
    require("mt6797_state_each_movement_test" in tests,
            "per-movement KUnit coverage")
    require("mt6797_state_cci_busy_precedence_test" in tests,
            "CCI precedence KUnit coverage")
    print("patch_validation=pass")
    print("generated_patch_count=2")
    print("movement_bits=9")
    print("device_action=none")


if __name__ == "__main__":
    main()
