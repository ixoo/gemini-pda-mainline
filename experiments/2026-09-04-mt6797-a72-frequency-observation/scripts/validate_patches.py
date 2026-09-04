#!/usr/bin/env python3
"""Validate generated MT6797 clock-state decoder patch boundaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0525-soc-mediatek-correct-MT6797-protected-clock-decoding.patch",
    "0526-soc-mediatek-test-MT6797-protected-clock-decoding.patch",
)
REPAIR_PATHS = {
    "drivers/soc/mediatek/mt6797-dvfsp-clock-state.c",
    "include/linux/soc/mediatek/mt6797-dvfsp-clock-state.h",
}
TEST_PATHS = {
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-dvfsp-clock-state-test.c",
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
        texts.append(text)

    if changed_paths(texts[0]) != REPAIR_PATHS:
        raise SystemExit("decoder repair patch path boundary changed")
    if changed_paths(texts[1]) != TEST_PATHS:
        raise SystemExit("KUnit patch path boundary changed")

    combined = "\n".join(texts)
    required = (
        "MT6797_DVFSP_CLOCK_STATE_PCW_STROBE",
        "MT6797_DVFSP_CLOCK_STATE_BIG_PCW_MASK",
        "MT6797_DVFSP_CLOCK_STATE_BIG_POSDIV_MASK",
        "mt6797_dvfsp_clock_big_frequency_decode",
        "config MTK_MT6797_DVFSP_CLOCK_STATE_KUNIT_TEST",
        '.name = "mt6797-dvfsp-clock-state"',
    )
    for needle in required:
        if needle not in combined:
            raise SystemExit(f"required patch contract absent: {needle!r}")
    forbidden = (
        "MT6797_DVFSP_CLOCK_STATE_PLL_CHANGE",
        "+\treadl(",
        "+\twritel(",
        "+\tarm_smccc",
        "+\tcpu_up(",
        "+\tcpu_down(",
        "boot2",
        "192.168.",
    )
    for needle in forbidden:
        if needle in combined:
            raise SystemExit(f"forbidden patch content present: {needle!r}")

    print("generated_patch_count=2")
    print("repair_path_count=2")
    print("kunit_path_count=3")
    print("synthetic_signoff=absent")
    print("hardware_action=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
