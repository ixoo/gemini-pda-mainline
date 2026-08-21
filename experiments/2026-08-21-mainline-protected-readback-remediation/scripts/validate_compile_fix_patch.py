#!/usr/bin/env python3
"""Validate the generated protected-readback compile-fix patch."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCH = "0319-soc-mediatek-fix-protected-readback-test-settle-name.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    found = tuple(path.name for path in patch_dir.glob("*.patch"))
    require(found == (PATCH,), "one exact compile-fix patch")
    require((patch_dir / "series").read_text() == PATCH + "\n", "series")
    text = (patch_dir / PATCH).read_text()

    require(
        "Subject: [PATCH] soc: mediatek: fix protected readback test settle name"
        in text,
        "patch subject",
    )
    require(
        "drivers/soc/mediatek/mt6797-protected-readback-test.c" in text,
        "only intended test path present",
    )
    for forbidden in (
        "mt6797-dvfsp-clock-backend.c",
        "mt6797-bigidvfs-backend.c",
        "Signed-off-by:",
        "cpu_up(",
        "cpu_down(",
        "arm_smccc_smc(",
    ):
        require(forbidden not in text, f"forbidden patch token: {forbidden}")

    print(f"patch={PATCH}")
    print("generated_patch_count=1")
    print("changed_scope=numeric-test-macro-and-expectation-only")
    print("production_source_changed=false")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
