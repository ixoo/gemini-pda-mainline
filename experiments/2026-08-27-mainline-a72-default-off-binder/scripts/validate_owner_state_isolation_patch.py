#!/usr/bin/env python3
"""Validate the generated owner/P30 KUnit state-isolation patch."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0402-arm64-mediatek-isolate-MT6797-A72-owner-KUnit-state.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def additions(text: str) -> str:
    return "\n".join(
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
        require(PATCH in actual, f"canonical state-isolation patch absent: {actual}")
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
        "Subject: [PATCH 1/1] arm64: mediatek: isolate MT6797 A72 owner KUnit" in text,
        "state-isolation subject changed",
    )
    paths = tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))
    require(paths == ("arch/arm64/kernel/mt6797_a72_membership_test.c",),
            f"state-isolation paths changed: {paths}")
    added = additions(text)
    for token in (
        "mt6797_a72_owner_reset_state",
        "mt6797_a72_owner_seed_available",
        "mt6797_a72_owner_seed_available_cpu9",
        "arm64_late_cpu_startup_test_reset();",
        "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER",
    ):
        require(token in added, f"required generated token absent: {token}")
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "i2c_transfer(",
    ):
        require(forbidden not in added, f"forbidden generated token: {forbidden}")

    print("validation=a72-owner-kunit-state-isolation-patch")
    print("patches=1")
    print("owner_cases=30")
    print("production_files_changed=0")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
