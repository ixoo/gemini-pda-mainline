#!/usr/bin/env python3
"""Validate the generated pre-P28 provider-abort patch review."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCHES = (
    "0296-arm64-fail-stop-ambiguous-A72-provider-acquire.patch",
    "0297-arm64-add-exact-pre-P28-A72-provider-abort.patch",
    "0298-regulator-make-DA921x-provider-endpoint-injectable.patch",
    "0299-regulator-test-DA921x-pre-P28-membership-abort.patch",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def paths(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))


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
        require(all(name in actual for name in PATCHES),
                f"canonical patch inventory incomplete: {actual}")
    else:
        require(actual == PATCHES, f"unexpected patch inventory: {actual}")
    texts = [(patch_dir / name).read_text(encoding="utf-8") for name in PATCHES]

    for name, text in zip(PATCHES, texts, strict=True):
        require(text.startswith("From "), f"{name}: not a format patch")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in text,
            f"{name}: archive identity changed",
        )
        require("Signed-off-by:" not in text,
                f"{name}: synthetic sign-off forbidden")
    subjects = (
        "Subject: [PATCH 1/4] arm64: fail-stop ambiguous A72 provider acquire",
        "Subject: [PATCH 2/4] arm64: add exact pre-P28 A72 provider abort",
        "Subject: [PATCH 3/4] regulator: make the DA921x provider endpoint",
        "Subject: [PATCH 4/4] regulator: test the DA921x pre-P28 membership",
    )
    for text, subject in zip(texts, subjects, strict=True):
        require(subject in text, f"patch subject changed: {subject}")
    require(paths(texts[0]) == (
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
    ), "fail-stop patch paths changed")
    require(paths(texts[1]) == (
        "arch/arm64/Kconfig",
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
    ), "abort patch paths changed")
    require(paths(texts[2]) == (
        "drivers/regulator/da9213-legacy-provider-contract.h",
        "drivers/regulator/da9213-legacy-regulator.c",
    ), "endpoint patch paths changed")
    require(paths(texts[3]) == (
        "arch/arm64/Kconfig",
        "arch/arm64/include/asm/mt6797_a72_membership.h",
        "arch/arm64/kernel/mt6797_a72_membership.c",
        "drivers/regulator/Kconfig",
        "drivers/regulator/Makefile",
        "drivers/regulator/da9213-legacy-membership-test.c",
    ), "KUnit patch paths changed")

    combined = "\n".join(additions(text) for text in texts)
    for token in (
        "MT6797_A72_PROVIDER_FAULT_UNKNOWN",
        "MT6797_A72_PROVIDER_RELEASE_INFLIGHT",
        "mt6797_a72_membership_run_provider_abort",
        "mt6797_a72_provider_release(&handle, response)",
        "provider_abort_valid",
        "struct da9213_legacy_provider_endpoint",
        "da9213_legacy_provider_test_register",
        "REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST",
    ):
        require(token in combined, f"generated patch token missing: {token}")
    require(additions(texts[3]).count("KUNIT_CASE(") == 6,
            "KUnit case count changed")
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
        require(forbidden not in combined,
                f"forbidden generated token: {forbidden}")

    print("validation=da921x-pre-p28-provider-abort-patches")
    print("patches=4")
    print("kunit_cases=6")
    print("hardware_action=none")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
