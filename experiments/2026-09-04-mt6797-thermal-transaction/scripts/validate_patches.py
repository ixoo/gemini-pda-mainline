#!/usr/bin/env python3
"""Validate generated MT6797 thermal transaction patch boundaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0517-thermal-mediatek-add-MT6797-ordered-transaction.patch",
    "0518-thermal-mediatek-test-MT6797-ordered-transaction.patch",
)

PRODUCTION_PATHS = {
    "drivers/thermal/mediatek/auxadc_thermal.c",
    "drivers/thermal/mediatek/auxadc_thermal_internal.h",
}

TEST_PATHS = {
    "drivers/thermal/mediatek/Kconfig",
    "drivers/thermal/mediatek/Makefile",
    "drivers/thermal/mediatek/mt6797_auxadc_transaction_test.c",
}


def changed_paths(text: str) -> set[str]:
    pairs = set(
        re.findall(r"^diff --git a/(\S+) b/(\S+)$", text, re.MULTILINE)
    )
    if any(left != right for left, right in pairs):
        raise SystemExit("rename or cross-path diff is not allowed")
    return {left for left, _ in pairs}


def main() -> int:
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

    if changed_paths(texts[0]) != PRODUCTION_PATHS:
        raise SystemExit("production patch path boundary changed")
    if changed_paths(texts[1]) != TEST_PATHS:
        raise SystemExit("KUnit patch path boundary changed")

    combined = "\n".join(texts)
    for required in (
        "+mtk_thermal_transaction_execute(",
        "+\tmt->rst = devm_reset_control_get_exclusive",
        "+\treturn value & ~GENMASK(5, 4);",
        "+\treturn !(value & BIT(0));",
        "+\treturn !(value >> 16);",
        "+#define MT6797_TEST_BANKS 6",
        "+#define MT6797_TEST_FALLIBLE_CALLS 31",
        '+\t.name = "mt6797-thermal-transaction",',
    ):
        if required not in combined:
            raise SystemExit(f"required patch contract absent: {required!r}")

    for forbidden in (
        'status = "okay"',
        'status = "ok"',
        "AUXADC_MISC",
        "devm_request_irq",
        "request_irq(",
        "+\t.suspend =",
        "+\t.resume =",
        "cpufreq",
        "boot2",
        "192.168.",
    ):
        if forbidden in combined:
            raise SystemExit(f"forbidden patch content present: {forbidden!r}")

    print("generated_patch_count=2")
    print("production_path_count=2")
    print("kunit_path_count=3")
    print("synthetic_signoff=absent")
    print("hardware_action=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
