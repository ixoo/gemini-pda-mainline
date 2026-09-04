#!/usr/bin/env python3
"""Validate generated MT6797 thermal serviceability patch boundaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0519-arm64-dts-mediatek-add-MT6797-thermal-reset.patch",
    "0520-arm64-dts-mediatek-add-Gemini-thermal-serviceability.patch",
)


def changed_paths(text: str) -> set[str]:
    pairs = set(re.findall(r"^diff --git a/(\S+) b/(\S+)$", text, re.MULTILINE))
    if any(left != right for left, right in pairs):
        raise SystemExit("rename or cross-path diff is not allowed")
    return {left for left, _ in pairs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    texts: list[str] = []
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

    if changed_paths(texts[0]) != {"arch/arm64/boot/dts/mediatek/mt6797.dtsi"}:
        raise SystemExit("reset patch path boundary changed")
    expected_variant = {
        "arch/arm64/boot/dts/mediatek/Makefile",
        "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-thermal-serviceability.dts",
    }
    if changed_paths(texts[1]) != expected_variant:
        raise SystemExit("serviceability patch path boundary changed")

    combined = "\n".join(texts)
    for required in (
        "+\t\tresets = <&infrasys MT6797_INFRA_THERM_CTRL_RST>;",
        '+#include "mt6797-gemini-pda.dts"',
        "+\tthermal-zones {",
        "+\t\tsoc-thermal {",
        "+\t\t\tthermal-sensors = <&thermal>;",
        "+&thermal {",
        '+\tstatus = "okay";',
    ):
        if required not in combined:
            raise SystemExit(f"required patch contract absent: {required!r}")
    for forbidden in (
        "reset-names", "trips {", "cooling-maps {", "cooling-device",
        "&auxadc {", "cpu8", "cpu9", "cpufreq", "opp-table",
        "request_irq", "boot2", "192.168.",
    ):
        if forbidden in combined:
            raise SystemExit(f"forbidden patch content present: {forbidden!r}")

    print("generated_patch_count=2")
    print("changed_path_count=3")
    print("synthetic_signoff=absent")
    print("hardware_action=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
