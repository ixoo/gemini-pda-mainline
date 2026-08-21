#!/usr/bin/env python3
"""Validate the generated stack-safety follow-up patch."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCH = "0300-regulator-move-DA921x-membership-test-state-off-stack.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


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
        require(PATCH in actual, f"canonical stack-fix patch absent: {actual}")
    else:
        require(actual == (PATCH,), f"unexpected patch inventory: {actual}")

    text = (patch_dir / PATCH).read_text(encoding="utf-8")
    require(text.startswith("From "), "stack-fix output is not a format patch")
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
        in text,
        "stack-fix archive identity changed",
    )
    require("Signed-off-by:" not in text, "synthetic sign-off forbidden")
    require(
        "Subject: [PATCH 1/1] regulator: move DA921x membership test state off"
        in text,
        "stack-fix subject changed",
    )
    paths = tuple(
        re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE)
    )
    require(
        paths == ("drivers/regulator/da9213-legacy-membership-test.c",),
        f"stack-fix paths changed: {paths}",
    )
    added = additions(text)
    require(added.count("kunit_kzalloc(test, sizeof(*state), GFP_KERNEL)") == 6,
            "KUnit heap-state allocation inventory changed")
    for token in (
        "struct da9213_membership_test_state",
        "mt6797_a72_membership_snapshot(&synthetic->snapshot)",
    ):
        require(token in added, f"stack-fix token missing: {token}")
    for forbidden in (
        "i2c_add_adapter",
        "i2c_new_client",
        "ioremap",
        "writel(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
    ):
        require(forbidden not in added,
                f"forbidden generated token: {forbidden}")

    print("validation=da921x-pre-p28-provider-abort-stack-fix-patch")
    print("patches=1")
    print("kunit_cases=6")
    print("production_code_changed=false")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
