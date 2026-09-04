#!/usr/bin/env python3
"""Validate generated MT6797 thermal-stage ledger patch boundaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    (
        "0521-pstore-add-Gemini-MT6797-thermal-stage-ledger.patch",
        "pstore: add Gemini MT6797 thermal-stage ledger",
        {
            "fs/pstore/Kconfig",
            "fs/pstore/Makefile",
            "fs/pstore/gemini_mt6797_thermal_ledger.c",
            "fs/pstore/gemini_mt6797_thermal_ledger_internal.h",
            "include/linux/gemini_mt6797_thermal_ledger.h",
        },
    ),
    (
        "0522-pstore-test-Gemini-MT6797-thermal-stage-ledger.patch",
        "pstore: test Gemini MT6797 thermal-stage ledger",
        {
            "fs/pstore/Kconfig",
            "fs/pstore/Makefile",
            "fs/pstore/gemini_mt6797_thermal_ledger_test.c",
        },
    ),
    (
        "0523-thermal-mediatek-trace-MT6797-probe-stages.patch",
        "thermal: mediatek: trace MT6797 probe stages",
        {
            "drivers/thermal/mediatek/auxadc_thermal.c",
            "drivers/thermal/mediatek/auxadc_thermal_internal.h",
            "drivers/thermal/mediatek/mt6797_auxadc_transaction_test.c",
        },
    ),
)


def changed_paths(text: str) -> set[str]:
    return set(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    series = (args.patch_dir / "series").read_text(encoding="utf-8").splitlines()
    expected_series = [item[0] for item in PATCHES]
    if series != expected_series:
        raise SystemExit("generated series order changed")

    for name, subject, paths in PATCHES:
        text = (args.patch_dir / name).read_text(encoding="utf-8")
        if f"Subject: [PATCH " not in text or subject not in text:
            raise SystemExit(f"{name}: subject changed")
        if changed_paths(text) != paths:
            raise SystemExit(f"{name}: changed-path boundary mismatch")
        if "Signed-off-by: Gemini Mainline Experiment" in text:
            raise SystemExit(f"{name}: synthetic sign-off present")
        if "artifacts/" in text or "/Users/" in text or "/workspace/" in text:
            raise SystemExit(f"{name}: private or generated path present")

    print("patch_validation=pass")
    print("patch_count=3")
    print("synthetic_signoff=absent")
    print("generated_or_private_paths=absent")


if __name__ == "__main__":
    main()
