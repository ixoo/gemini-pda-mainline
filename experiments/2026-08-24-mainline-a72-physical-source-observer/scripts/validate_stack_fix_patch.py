#!/usr/bin/env python3
"""Validate the generated physical-source KUnit stack-fix patch."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCH = "0355-soc-mediatek-move-A72-physical-source-KUnit-snapshots-off-stack.patch"
EXPECTED_PATH = (
    "drivers/soc/mediatek/mt6797-a72-physical-source-observer-test.c"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    require((patch_dir / "series").read_text().splitlines() == [PATCH],
            "one exact generated patch")
    path = patch_dir / PATCH
    require(path.is_file() and not path.is_symlink(), "safe generated patch")
    text = path.read_text(encoding="utf-8")
    touched = set(re.findall(r"^diff --git a/(.+?) b/", text, re.MULTILINE))
    require(touched == {EXPECTED_PATH}, "test-only path boundary")
    require("Subject: [PATCH] soc: mediatek: move A72 physical-source KUnit"
            in text, "exact patch subject")
    require("KUNIT_ASSERT_NOT_NULL(test, snapshot)" in text,
            "allocation failure gate present")
    require("Signed-off-by: Gemini Mainline Experiment" not in text,
            "synthetic sign-off absent")
    for forbidden in ("cpu_up(", "writel(", "i2c_transfer("):
        require(forbidden not in text, f"physical operation absent: {forbidden}")
    print("validation=a72-physical-source-kunit-stack-fix-patch")
    print("generated_patch_count=1")
    print("changed_files=1")
    print("production_files_changed=0")
    print("hardware_operations=0")
    print("result=pass")


if __name__ == "__main__":
    main()
