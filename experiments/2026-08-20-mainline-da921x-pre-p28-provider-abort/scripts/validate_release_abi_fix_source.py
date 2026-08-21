#!/usr/bin/env python3
"""Validate the focused provider-release response ABI fix."""

from __future__ import annotations

import argparse
from pathlib import Path


CHECK = "response->abi != MT6797_A72_PROVIDER_CALL_ABI"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path, required=True)
    source = parser.parse_args().source_file.resolve()
    require(source.is_file() and not source.is_symlink(),
            "unsafe release-ABI source")
    text = source.read_text(encoding="utf-8")

    require(text.count(CHECK) == 1,
            "release response ABI check inventory changed")
    abort = text.index("mt6797_a72_membership_run_provider_abort(")
    confirm = text.index("mt6797_a72_membership_confirm_abort(transaction, &proof)",
                         abort)
    check = text.index(CHECK, abort)
    require(check < confirm, "release ABI check moved after abort confirmation")
    window = text[check:confirm]
    require("ret = -EPROTO;" in window and "goto out_fault;" in window,
            "release ABI mismatch is not fail-closed")
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on",
        "psci_ops.cpu_off",
        "ioremap",
        "writel(",
    ):
        require(forbidden not in window,
                f"hardware token in release ABI check: {forbidden}")

    print("validation=da921x-pre-p28-provider-abort-release-abi-source")
    print("response_abi_checks=1")
    print("mismatch=protocol-error-provider-fault")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
