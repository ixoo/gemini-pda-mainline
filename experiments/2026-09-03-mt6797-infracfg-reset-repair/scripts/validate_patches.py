#!/usr/bin/env python3
"""Validate generated MT6797 infracfg reset patch boundaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0514-clk-mediatek-repair-MT6797-infracfg-resets.patch",
    "0515-clk-mediatek-test-MT6797-infracfg-reset-translation.patch",
)

PRODUCTION_PATHS = {
    "drivers/clk/mediatek/clk-mt6797-reset.h",
    "drivers/clk/mediatek/clk-mt6797.c",
    "drivers/clk/mediatek/reset.c",
    "drivers/clk/mediatek/reset.h",
    "include/dt-bindings/reset/mt6797-resets.h",
}

TEST_PATHS = {
    "drivers/clk/mediatek/Kconfig",
    "drivers/clk/mediatek/Makefile",
    "drivers/clk/mediatek/clk-mt6797-reset-test.c",
}


def changed_paths(text: str) -> set[str]:
    paths = set(re.findall(r"^diff --git a/(\S+) b/(\S+)$", text, re.MULTILINE))
    if any(left != right for left, right in paths):
        raise SystemExit("rename or cross-path diff is not allowed")
    return {left for left, _ in paths}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    texts = []
    for name in PATCHES:
        path = args.patch_dir / name
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"missing or unsafe patch: {path}")
        text = path.read_text(encoding="utf-8")
        if not text.startswith("From ") or "\nSubject: [PATCH " not in text:
            raise SystemExit(f"not a normal format-patch: {name}")
        if "Signed-off-by:" in text:
            raise SystemExit(f"synthetic sign-off forbidden: {name}")
        if "status = \"okay\"" in text or "status = \"ok\"" in text:
            raise SystemExit(f"DT enable forbidden: {name}")
        texts.append(text)

    if changed_paths(texts[0]) != PRODUCTION_PATHS:
        raise SystemExit("production patch path boundary changed")
    if changed_paths(texts[1]) != TEST_PATHS:
        raise SystemExit("KUnit patch path boundary changed")

    combined = "\n".join(texts)
    required = (
        "+#define MT6797_INFRA_PMIC_WRAP_RST\t1",
        "+\tINFRA_RST0_SET_OFFSET,",
        "+\tINFRA_RST2_SET_OFFSET,",
        "+\t.version = MTK_RST_SET_CLR,",
        "+mtk_reset_set_clr_reg(",
        "+config COMMON_CLK_MT6797_RESET_KUNIT_TEST",
        '+\t.name = "mt6797-infracfg-reset-translation",',
    )
    for needle in required:
        if needle not in combined:
            raise SystemExit(f"required patch contract absent: {needle!r}")
    forbidden = (
        "+\tINFRA_RST1_SET_OFFSET,",
        "+\t.version = MTK_RST_SIMPLE,",
        "+#define MT6797_INFRA_PMIC_WRAP_RST\t64",
        "boot2",
        "192.168.",
    )
    for needle in forbidden:
        if needle in combined:
            raise SystemExit(f"forbidden patch content present: {needle!r}")

    print("generated_patch_count=2")
    print("production_path_count=5")
    print("kunit_path_count=3")
    print("synthetic_signoff=absent")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
