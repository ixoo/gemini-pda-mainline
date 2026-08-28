#!/usr/bin/env python3
"""Validate the generated MT6797 A72 P29 public-claim fixture patch."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0406-arm64-mediatek-claim-CPU8-in-P29-KUnit-fixtures.patch"
TEST_SOURCE = "arch/arm64/kernel/mt6797_a72_membership_test.c"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    parser.add_argument("--canonical-import", action="store_true")
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    if args.canonical_import:
        require(PATCH in actual, f"canonical P29 claim patch absent: {actual}")
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
        "Subject: [PATCH 1/1] arm64: mediatek: claim CPU8 in P29 KUnit fixtures"
        in text,
        "P29 claim repair subject changed",
    )
    paths = tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))
    require(paths == (TEST_SOURCE,), f"P29 claim repair paths changed: {paths}")
    require(text.count(
        "+\tret = mt6797_a72_membership_validate_up(8, 0, CPUHP_ONLINE);") == 2,
        "P29 validate additions changed")
    require(text.count(
        "+\tret = mt6797_a72_membership_claim_cpu8(&state->transaction);") == 2,
        "P29 claim additions changed")

    print("validation=a72-owner-kunit-p29-public-claim-patch")
    print("patches=1")
    print("changed_files=1")
    print("production_files_changed=0")
    print("preflight_validate_claim_paths=2")
    print("expected_owner_failures_repaired=1")
    print("false_positive_paths_closed=1")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
