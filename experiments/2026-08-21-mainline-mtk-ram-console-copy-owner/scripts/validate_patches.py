#!/usr/bin/env python3
"""Validate the generated retained ram-console copy-owner patch review."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0305-dt-bindings-soc-mediatek-document-retained-ram-console.patch",
    "0306-soc-mediatek-add-retained-ram-console-copy-owner.patch",
    "0307-arm64-dts-mediatek-add-Gemini-ram-console-reader.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()

    series = (patch_dir / "series").read_text().splitlines()
    require(tuple(series) == PATCHES, "patch series order")
    require(tuple(path.name for path in sorted(patch_dir.glob("*.patch"))) ==
            PATCHES, "patch inventory")

    binding, driver, dt = ((patch_dir / name).read_text() for name in PATCHES)
    require("Subject: [PATCH 1/3] dt-bindings: soc: mediatek:" in binding,
            "binding subject")
    require("Subject: [PATCH 2/3] soc: mediatek:" in driver,
            "driver subject")
    require("Subject: [PATCH 3/3] arm64: dts: mediatek:" in dt,
            "DT subject")
    require("mediatek,mt6797-ram-console.yaml" in binding,
            "binding payload")
    require("mtk-ram-console-reader.c" in driver, "driver payload")
    require("ram_console_reserved: memory@44400000" in dt,
            "DT reservation label")
    require('status = "disabled";' in dt, "default-off DT")

    for token in ("0x44400000", "ioremap(", "readl(", "writel("):
        require(token not in driver, f"forbidden driver patch token: {token}")
    for text in (binding, driver, dt):
        require("Signed-off-by: Gemini Mainline Experiment" not in text,
                "synthetic DCO sign-off")

    print("patch_validation=pass")
    print("generated_patch_count=3")
    print("binding_patch_count=1")
    print("driver_patch_count=1")
    print("dt_patch_count=1")
    print("dt_default=disabled")
    print("synthetic_signoff=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
