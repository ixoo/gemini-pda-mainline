#!/usr/bin/env python3
"""Validate the two normal bounded frequency-observer patches."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EXPECTED = {
    "0527-soc-mediatek-add-bounded-MT6797-A72-frequency-observer.patch": {
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mt6797-a72-frequency-observer-internal.h",
        "drivers/soc/mediatek/mt6797-a72-frequency-observer.c",
        "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot-internal.h",
        "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot.c",
    },
    "0528-soc-mediatek-test-bounded-MT6797-A72-frequency-observer.patch": {
        "drivers/soc/mediatek/Kconfig",
        "drivers/soc/mediatek/Makefile",
        "drivers/soc/mediatek/mt6797-a72-frequency-observer-test.c",
    },
}


def paths(text: str) -> set[str]:
    found: set[str] = set()
    for left, right in re.findall(r"^diff --git a/(\S+) b/(\S+)$", text, re.MULTILINE):
        if left != right:
            raise SystemExit(f"rename is not allowed: {left} -> {right}")
        found.add(left)
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", required=True, type=Path)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    series = (patch_dir / "series").read_text().splitlines()
    if series != list(EXPECTED):
        raise SystemExit(f"unexpected generated series: {series!r}")
    for name, expected_paths in EXPECTED.items():
        text = (patch_dir / name).read_text()
        if not text.startswith("From ") or "\nSubject: [PATCH " not in text:
            raise SystemExit(f"not a normal format-patch: {name}")
        if "Signed-off-by:" in text:
            raise SystemExit(f"synthetic sign-off is forbidden: {name}")
        actual = paths(text)
        if actual != expected_paths:
            raise SystemExit(
                f"unexpected changed paths in {name}: {sorted(actual)!r}"
            )
    print("generated_patch_count=2")
    print("changed_path_count=9")
    print("synthetic_signoff=absent")
    print("result=pass")


if __name__ == "__main__":
    main()
