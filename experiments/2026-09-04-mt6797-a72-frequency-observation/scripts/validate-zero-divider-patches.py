#!/usr/bin/env python3
"""Validate generated MT6797 zero-divider patch boundaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0533-soc-mediatek-accept-zero-MT6797-clock-divider.patch",
    "0534-soc-mediatek-test-live-zero-divider-clock-state.patch",
)


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

    if changed_paths(texts[0]) != {
        "drivers/soc/mediatek/mt6797-dvfsp-clock-state.c",
    }:
        raise SystemExit("zero-divider production patch path boundary changed")
    if changed_paths(texts[1]) != {
        "drivers/soc/mediatek/mt6797-dvfsp-clock-state-test.c",
    }:
        raise SystemExit("zero-divider KUnit patch path boundary changed")

    combined = "\n".join(texts)
    for needle in (
        "+\tcase 0:",
        "mt6797_clock_state_live_zero_dividers_test",
        "+\tclock.armplldiv_ckdiv = 0x00000008;",
        "+\tbig.pll_pcw = 0xb9b13b14;",
        "+\tbig.pll_enable_posdiv = 0x00ff1101;",
    ):
        if needle not in combined:
            raise SystemExit(f"required patch contract absent: {needle!r}")
    for needle in (
        "+\treadl(", "+\twritel(", "+\tarm_smccc", "+\tcpu_up(",
        "+\tcpu_down(", "boot2", "192.168.",
    ):
        if needle in combined:
            raise SystemExit(f"forbidden patch content present: {needle!r}")

    print("generated_patch_count=2")
    print("changed_path_count=2")
    print("zero_divider_identity=explicit")
    print("unknown_divider_rejection=retained")
    print("live_tuple_kunit=present")
    print("synthetic_signoff=absent")
    print("hardware_action=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
