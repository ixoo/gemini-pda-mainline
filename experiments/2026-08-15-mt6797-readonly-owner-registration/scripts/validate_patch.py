#!/usr/bin/env python3
"""Validate one generated prerequisite format-patch."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    text = args.patch.read_text()
    if not text.startswith("From 0000000000000000000000000000000000000000 "):
        raise SystemExit("patch is not a zero-commit git format-patch")
    if "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" not in text:
        raise SystemExit("unexpected experiment author identity")
    if "Signed-off-by:" in text:
        raise SystemExit("synthetic experiment patch must not carry a DCO sign-off")
    if "diff --git " not in text:
        raise SystemExit("patch has no diff")
    diff = text[text.index("diff --git "):]
    for forbidden in (
        "readl(", "writel(", "i2c_transfer", "regulator_", "clk_set_",
        "cpu_up(", "cpu_down(", "arm_smccc", "platform_driver_register",
    ):
        if forbidden in diff:
            raise SystemExit(f"unexpected state-changing operation: {forbidden}")
    print(f"patch={args.patch.name}")
    print("format_patch=passed")
    print("synthetic_signoff=absent")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
