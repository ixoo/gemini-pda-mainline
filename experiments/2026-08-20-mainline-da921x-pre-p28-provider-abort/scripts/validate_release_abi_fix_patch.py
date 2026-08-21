#!/usr/bin/env python3
"""Validate the generated provider-release response ABI patch."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCH = "0301-arm64-reject-malformed-A72-provider-release-ABI.patch"
SOURCE = "arch/arm64/kernel/mt6797_a72_membership.c"


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
        require(PATCH in actual, f"canonical release-ABI patch absent: {actual}")
    else:
        require(actual == (PATCH,), f"unexpected patch inventory: {actual}")

    text = (patch_dir / PATCH).read_text(encoding="utf-8")
    require(text.startswith("From "), "release-ABI output is not a format patch")
    require(
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
        in text,
        "release-ABI archive identity changed",
    )
    require("Signed-off-by:" not in text, "synthetic sign-off forbidden")
    require(
        "Subject: [PATCH 1/1] arm64: reject malformed A72 provider release ABI"
        in text,
        "release-ABI subject changed",
    )
    paths = tuple(
        re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE)
    )
    require(paths == (SOURCE,), f"release-ABI paths changed: {paths}")
    added = additions(text)
    require(added.count(
        "response->abi != MT6797_A72_PROVIDER_CALL_ABI") == 1,
        "release response ABI check inventory changed")
    require("ret = -EPROTO;" in added and "goto out_fault;" in added,
            "release ABI mismatch is not fail-closed")
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "ioremap",
        "writel(",
    ):
        require(forbidden not in added,
                f"forbidden generated token: {forbidden}")

    print("validation=da921x-pre-p28-provider-abort-release-abi-patch")
    print("patches=1")
    print("response_abi_checks=1")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
