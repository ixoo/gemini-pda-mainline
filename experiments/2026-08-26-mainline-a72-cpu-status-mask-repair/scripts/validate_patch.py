#!/usr/bin/env python3
"""Validate exact CPU-status-mask repair patch inventory and scope."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0382-soc-mediatek-mask-A72-CPU-status-stability.patch",
    "0383-soc-mediatek-test-A72-CPU-status-stability-mask.patch",
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
        {"drivers/soc/mediatek/mt6797-a72-platform-state.c"},
        {"drivers/soc/mediatek/mt6797-a72-platform-state-test.c"},
    )
    for name, scope in zip(PATCHES, scopes):
        text = (root / name).read_text(encoding="utf-8")
        require("Signed-off-by:" not in text, f"no synthetic sign-off: {name}")
        files = {
            line[6:] for line in text.splitlines()
            if line.startswith("+++ b/") and line != "+++ b/dev/null"
        }
        require(files == scope, f"exact scope: {name}")
        added = "\n".join(
            line[1:] for line in text.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        for forbidden in ("cpu_up(", "cpu_down(", "psci_ops", "kernel_restart(",
                          "msleep(", "udelay(", "i2c_transfer(", "writel("):
            require(forbidden not in added, f"forbidden action {forbidden}: {name}")
    production = (root / PATCHES[0]).read_text(encoding="utf-8")
    tests = (root / PATCHES[1]).read_text(encoding="utf-8")
    require("MT6797_A72_CPU_PWR_STATUS_MASK" in production,
            "named production mask")
    require("GENMASK(7, 6)" in production, "exact A72 identity mask")
    require(production.count("MT6797_A72_CPU_PWR_STATUS_MASK)") == 2,
            "both words masked")
    require("mt6797_state_each_a72_identity_bit_test" in tests,
            "identity-bit KUnit")
    require("0x003dcf08" in tests and "0x003dc7ff" in tests,
            "exact live pair KUnit")
    print("patch_validation=pass")
    print("generated_patch_count=2")
    print("cpu_status_mask=GENMASK(7,6)")
    print("device_action=none")


if __name__ == "__main__":
    main()
