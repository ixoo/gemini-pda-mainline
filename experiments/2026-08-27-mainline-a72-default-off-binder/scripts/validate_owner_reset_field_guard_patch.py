#!/usr/bin/env python3
"""Validate the generated late-startup online-field reset guard patch."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0404-arm64-guard-late-CPU-online-KUnit-reset-state.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def additions(text: str) -> tuple[str, ...]:
    return tuple(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    parser.add_argument("--canonical-import", action="store_true")
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    if args.canonical_import:
        require(PATCH in actual, f"canonical field-guard patch absent: {actual}")
    else:
        require(actual == (PATCH,), f"unexpected patch inventory: {actual}")

    text = (patch_dir / PATCH).read_text(encoding="utf-8")
    require(text.startswith("From "), "output is not a format patch")
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
        "synthetic archive identity changed",
    )
    require("Signed-off-by:" not in text, "synthetic sign-off forbidden")
    require(
        "Subject: [PATCH 1/1] arm64: guard late CPU online KUnit reset state" in text,
        "field-guard subject changed",
    )
    paths = tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))
    require(paths == ("arch/arm64/kernel/late_cpu_startup.c",),
            f"field-guard paths changed: {paths}")
    added = additions(text)
    require(added == (
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST",
        "#endif",
    ), f"non-guard addition found: {added}")

    print("validation=a72-owner-kunit-reset-field-guard-patch")
    print("patches=1")
    print("changed_files=1")
    print("added_code=preprocessor-guard-only")
    print("guarded_online_fields=2")
    print("production_configuration_change=none")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
